from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token, validate_jwt_secret
from app.auth.oauth_state import generate_oauth_state, verify_oauth_state
from app.db.session import get_db
from app.services.user_repository import get_or_create_wechat_user
from config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class DevLoginRequest(BaseModel):
    name: str = Field(default="开发者", min_length=1, max_length=64)
    role: str = Field(default="consultant", pattern="^(user|consultant|admin)$")


@router.get("/wechat/login-url")
async def wechat_login_url():
    """生成微信扫码登录 URL，附带签名 state 用于防 CSRF。"""
    settings = get_settings()
    if not settings.WECHAT_APP_ID or not settings.WECHAT_REDIRECT_URI:
        raise HTTPException(status_code=503, detail="微信登录未配置")

    validate_jwt_secret()  # state 签名依赖 JWT_SECRET_KEY

    state = generate_oauth_state()
    params = {
        "appid": settings.WECHAT_APP_ID,
        "redirect_uri": settings.WECHAT_REDIRECT_URI,
        "response_type": "code",
        "scope": "snsapi_login",
        "state": state,
    }
    url = f"https://open.weixin.qq.com/connect/qrconnect?{urlencode(params)}#wechat_redirect"
    return {"url": url, "state": state}


@router.get("/wechat/callback")
async def wechat_callback(
    code: str = Query(...),
    state: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    """微信 OAuth 回调：校验 state → 换 access_token → 获取用户信息 → 签发 JWT。"""
    settings = get_settings()

    # Step 1: 校验 state，防 CSRF
    if not state or not verify_oauth_state(state):
        raise HTTPException(status_code=400, detail="登录校验失败，请重新扫码")

    # Step 2: 校验微信配置
    if not settings.WECHAT_APP_ID or not settings.WECHAT_APP_SECRET:
        raise HTTPException(status_code=503, detail="微信登录未配置")

    # Step 3: 换 access_token
    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.get(
            "https://api.weixin.qq.com/sns/oauth2/access_token",
            params={
                "appid": settings.WECHAT_APP_ID,
                "secret": settings.WECHAT_APP_SECRET,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
    token_data = token_resp.json()
    if "errcode" in token_data and token_data["errcode"] != 0:
        raise HTTPException(status_code=400, detail=f"微信授权失败: {token_data.get('errmsg', '')}")

    access_token = token_data.get("access_token")
    openid = token_data.get("openid")
    unionid = token_data.get("unionid")
    if not access_token or not openid:
        raise HTTPException(status_code=502, detail="微信返回数据不完整")

    # Step 4: 获取用户信息
    async with httpx.AsyncClient(timeout=15) as client:
        user_resp = await client.get(
            "https://api.weixin.qq.com/sns/userinfo",
            params={
                "access_token": access_token,
                "openid": openid,
            },
        )
    user_data = user_resp.json()
    nickname = user_data.get("nickname")
    avatar_url = user_data.get("headimgurl")

    user = await get_or_create_wechat_user(
        db, openid=openid, unionid=unionid, nickname=nickname, avatar_url=avatar_url
    )

    jwt_token = create_access_token(user_id=str(user.id), role=user.role)

    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "nickname": user.nickname,
            "role": user.role,
        },
    }


@router.post("/dev-login")
async def dev_login(
    body: DevLoginRequest = DevLoginRequest(),
    db: AsyncSession = Depends(get_db),
):
    """开发模式登录：仅在 DEV_MODE=true 时可用。"""
    settings = get_settings()
    if not getattr(settings, "DEV_MODE", False):
        raise HTTPException(status_code=503, detail="开发模式未启用，请设置 DEV_MODE=true")
    from app.models import User

    wechat_openid = f"dev:{body.name}"
    from sqlalchemy import select
    from sqlalchemy.dialects.postgresql import insert

    stmt = (
        insert(User)
        .values(wechat_openid=wechat_openid, nickname=body.name, role=body.role)
        .on_conflict_do_nothing(index_elements=[User.wechat_openid])
        .returning(User.id)
    )
    result = await db.execute(stmt)
    created_id = result.scalar_one_or_none()
    if created_id is not None:
        user = await db.get(User, created_id)
    else:
        user = (await db.execute(select(User).where(User.wechat_openid == wechat_openid))).scalar_one()
        if user.role != body.role:
            user.role = body.role

    jwt_token = create_access_token(user_id=str(user.id), role=user.role)
    return {
        "access_token": jwt_token,
        "token_type": "bearer",
        "user": {"id": str(user.id), "nickname": user.nickname, "role": user.role},
    }

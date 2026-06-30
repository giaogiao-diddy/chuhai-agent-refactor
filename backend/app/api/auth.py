import uuid
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token
from app.db.session import get_db
from app.services.user_repository import get_or_create_wechat_user
from config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/wechat/login-url")
async def wechat_login_url():
    settings = get_settings()
    if not settings.WECHAT_APP_ID or not settings.WECHAT_REDIRECT_URI:
        raise HTTPException(status_code=503, detail="微信登录未配置")
    params = {
        "appid": settings.WECHAT_APP_ID,
        "redirect_uri": settings.WECHAT_REDIRECT_URI,
        "response_type": "code",
        "scope": "snsapi_login",
        "state": uuid.uuid4().hex,
    }
    url = f"https://open.weixin.qq.com/connect/qrconnect?{urlencode(params)}#wechat_redirect"
    return {"url": url}


@router.get("/wechat/callback")
async def wechat_callback(
    code: str = Query(...),
    state: str = Query(""),
    db: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    if not settings.WECHAT_APP_ID or not settings.WECHAT_APP_SECRET:
        raise HTTPException(status_code=503, detail="微信登录未配置")

    # 换 access_token
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

    # 获取用户信息
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

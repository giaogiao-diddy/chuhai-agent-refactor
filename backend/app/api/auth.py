from __future__ import annotations
"""微信登录接口"""

from fastapi import APIRouter

from app.schemas.auth import WechatLoginRequest, WechatLoginResponse

router = APIRouter(tags=["auth"])


@router.post("/auth/wechat-login", response_model=WechatLoginResponse)
async def wechat_login(body: WechatLoginRequest):
    """微信授权登录 — 用临时 code 换取 JWT Token"""
    # TODO: 委托给 auth_service.login()
    raise NotImplementedError

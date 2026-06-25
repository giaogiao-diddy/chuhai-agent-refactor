from __future__ import annotations
"""微信登录接口"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.auth import WechatLoginRequest, WechatLoginResponse
from app.services.auth_service import wechat_login

router = APIRouter(tags=["auth"])


@router.post("/auth/wechat-login", response_model=WechatLoginResponse)
def login(body: WechatLoginRequest, db: Session = Depends(get_db)):
    """微信授权登录 — 用临时 code 换取 JWT Token"""
    try:
        result = wechat_login(db, body.code)
        return result
    except ValueError as e:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

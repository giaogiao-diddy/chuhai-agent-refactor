from __future__ import annotations
"""微信登录 + JWT 签发服务"""

import hashlib
import time

from sqlalchemy.orm import Session

import jwt
from app.models.user import User
from config import settings


def wechat_login(db: Session, code: str) -> dict:
    """用微信临时 code 换取 openid，签发 JWT Token。

    没有配置微信 AppID 时走 mock 模式（开发/测试用）。
    """
    if not code or not code.strip():
        raise ValueError("无效的登录凭证")

    # ── Mock 模式：无微信配置时直接返回模拟 openid ──
    if not settings.wx_appid or not settings.wx_secret:
        openid = f"mock_openid_{hashlib.md5(code.encode()).hexdigest()[:12]}"
    else:
        # ── 真实模式：调用微信 jscode2session ──
        import requests
        url = "https://api.weixin.qq.com/sns/jscode2session"
        params = {
            "appid": settings.wx_appid,
            "secret": settings.wx_secret,
            "js_code": code,
            "grant_type": "authorization_code",
        }
        try:
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()
        except Exception:
            raise ValueError("微信服务不可用，请稍后重试")

        if "errcode" in data and data["errcode"] != 0:
            raise ValueError(f"微信登录失败: {data.get('errmsg', '未知错误')}")
        openid = data["openid"]

    # ── 查询或创建用户 ──
    user = db.query(User).filter_by(openid=openid).first()
    is_new = False
    if not user:
        user = User(openid=openid)
        db.add(user)
        db.flush()
        is_new = True
    else:
        user.last_login_at = None  # SQLAlchemy 会自动更新 onupdate
        db.flush()

    # ── 签发 JWT ──
    now = int(time.time())
    payload = {
        "sub": str(user.id),
        "openid": openid,
        "iat": now,
        "exp": now + settings.jwt_expire_hours * 3600,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    db.commit()

    return {
        "user_id": user.id,
        "openid": openid,
        "token": token,
        "is_new": is_new,
    }

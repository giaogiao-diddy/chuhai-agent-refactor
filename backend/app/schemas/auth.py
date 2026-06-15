from __future__ import annotations
"""微信登录请求/响应"""

from pydantic import BaseModel


class WechatLoginRequest(BaseModel):
    code: str


class WechatLoginResponse(BaseModel):
    user_id: int
    openid: str
    token: str
    is_new: bool = False

from __future__ import annotations
"""微信登录 + JWT 签发服务"""


async def wechat_login(code: str) -> dict:
    """用微信临时 code 换取 openid，签发 JWT Token"""
    # TODO: 调用微信 jscode2session → 查询/创建用户 → 签发 JWT
    raise NotImplementedError

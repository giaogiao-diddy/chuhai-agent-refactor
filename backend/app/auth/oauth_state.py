"""微信 OAuth state 签名生成与校验。

方案：签名 state，不引入 Redis / DB 存储。

state 格式：
    base64url(payload_json).base64url(hmac_sha256_signature)

payload:
    {"nonce": "<random_hex>", "timestamp": <unix_seconds>}

签名密钥：复用 JWT_SECRET_KEY
过期时间：默认 10 分钟

安全属性：
- 签名防篡改
- 时间戳防止重放（在过期窗口内）
- nonce 用于确保 state 唯一
"""

import base64
import hashlib
import hmac
import json
import secrets
import time

from config import get_settings


def _sign(payload_bytes: bytes) -> bytes:
    """使用 JWT_SECRET_KEY 对 payload 做 HMAC-SHA256 签名。"""
    settings = get_settings()
    key = settings.JWT_SECRET_KEY.encode("utf-8")
    return hmac.new(key, payload_bytes, hashlib.sha256).digest()


def _base64url_encode(data: bytes) -> str:
    """Base64url 编码，去除尾随 = 填充。"""
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _base64url_decode(encoded: str) -> bytes:
    """Base64url 解码，自动补齐 = 填充。"""
    padding = 4 - len(encoded) % 4
    if padding != 4:
        encoded += "=" * padding
    return base64.urlsafe_b64decode(encoded)


def generate_oauth_state() -> str:
    """生成带签名的 OAuth state。

    返回值可直接放入微信 OAuth URL 的 state 参数。
    """
    nonce = secrets.token_hex(16)
    timestamp = int(time.time())
    return _build_state(nonce, timestamp)


def generate_oauth_state_for_test(nonce: str, timestamp: int) -> str:
    """测试用：使用指定 nonce 和 timestamp 生成 state。
    生产代码不应调用此函数。
    """
    return _build_state(nonce, timestamp)


def _build_state(nonce: str, timestamp: int) -> str:
    """内部：构建签名 state。"""
    payload = json.dumps({"nonce": nonce, "timestamp": timestamp}, separators=(",", ":"))
    payload_bytes = payload.encode("utf-8")
    signature = _sign(payload_bytes)

    payload_encoded = _base64url_encode(payload_bytes)
    signature_encoded = _base64url_encode(signature)

    return f"{payload_encoded}.{signature_encoded}"


def verify_oauth_state(state: str, max_age_seconds: int = 600) -> bool:
    """校验 OAuth state 是否合法。

    Args:
        state: 待校验的 state 字符串
        max_age_seconds: state 最大有效时间（秒），默认 600（10 分钟）

    Returns:
        True 表示 state 合法且未过期，False 表示校验失败。
    """
    if not state:
        return False

    parts = state.split(".")
    if len(parts) != 2:
        return False

    payload_encoded, signature_encoded = parts

    # 解码 payload
    try:
        payload_bytes = _base64url_decode(payload_encoded)
    except Exception:
        return False

    # 解码签名
    try:
        provided_signature = _base64url_decode(signature_encoded)
    except Exception:
        return False

    # 验签
    expected_signature = _sign(payload_bytes)
    if not hmac.compare_digest(provided_signature, expected_signature):
        return False

    # 解析 payload
    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
        ts = int(payload["timestamp"])
    except (json.JSONDecodeError, KeyError, ValueError):
        return False

    # 检查过期
    if int(time.time()) - ts > max_age_seconds:
        return False

    return True

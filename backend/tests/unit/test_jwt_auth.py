import uuid

import pytest

from config import get_settings


def _set_secret(key: str):
    get_settings().JWT_SECRET_KEY = key


@pytest.fixture(autouse=True)
def _restore_secret():
    old = get_settings().JWT_SECRET_KEY
    yield
    get_settings().JWT_SECRET_KEY = old


# ── JWT secret 强校验 ──

def test_secret_empty_raises():
    _set_secret("")
    from app.auth.jwt import validate_jwt_secret
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        validate_jwt_secret()


def test_secret_change_me_raises():
    _set_secret("change_me")
    from app.auth.jwt import validate_jwt_secret
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        validate_jwt_secret()


def test_secret_your_jwt_secret_here_raises():
    _set_secret("your_jwt_secret_here")
    from app.auth.jwt import validate_jwt_secret
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        validate_jwt_secret()


def test_secret_too_short_raises():
    _set_secret("short")  # < 32 chars
    from app.auth.jwt import validate_jwt_secret
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        validate_jwt_secret()


def test_secret_exactly_32_chars_passes():
    _set_secret("a" * 32)
    from app.auth.jwt import validate_jwt_secret
    validate_jwt_secret()  # should not raise


def test_secret_long_passes():
    _set_secret("a" * 64)
    from app.auth.jwt import validate_jwt_secret
    validate_jwt_secret()  # should not raise


# ── 原有 JWT 签发/解码测试 ──

def test_create_and_decode_token():
    _set_secret("test-secret-key-for-jwt-unit-test-thirty-two-plus")
    from app.auth.jwt import create_access_token, decode_access_token

    user_id = str(uuid.uuid4())
    token = create_access_token(user_id, "user")
    assert token

    payload = decode_access_token(token)
    assert payload["sub"] == user_id
    assert payload["role"] == "user"


def test_missing_secret_raises():
    _set_secret("")
    from app.auth.jwt import create_access_token, decode_access_token

    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        create_access_token("x", "user")
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        decode_access_token("x")


def test_invalid_token_fails():
    _set_secret("test-secret-key-for-jwt-unit-test-thirty-two-plus")
    from app.auth.jwt import decode_access_token

    with pytest.raises(ValueError, match="无效 token"):
        decode_access_token("not.a.token")


def test_expired_token_fails():
    _set_secret("test-secret-key-for-jwt-unit-test-thirty-two-plus")
    from app.auth.jwt import create_access_token, decode_access_token
    from config import get_settings as gs

    gs().JWT_EXPIRE_MINUTES = -1
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id, "user")
    gs().JWT_EXPIRE_MINUTES = 60 * 24 * 7

    with pytest.raises(ValueError, match="已过期"):
        decode_access_token(token)

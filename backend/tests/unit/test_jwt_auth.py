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


def test_create_and_decode_token():
    _set_secret("test-secret-key-for-jwt")
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
    _set_secret("test-secret-key-for-jwt")
    from app.auth.jwt import decode_access_token

    with pytest.raises(ValueError, match="无效 token"):
        decode_access_token("not.a.token")


def test_expired_token_fails():
    _set_secret("test-secret-key-for-jwt")
    from app.auth.jwt import create_access_token, decode_access_token
    from config import get_settings as gs

    gs().JWT_EXPIRE_MINUTES = -1
    user_id = str(uuid.uuid4())
    token = create_access_token(user_id, "user")
    gs().JWT_EXPIRE_MINUTES = 60 * 24 * 7

    with pytest.raises(ValueError, match="已过期"):
        decode_access_token(token)

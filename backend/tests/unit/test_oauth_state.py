"""OAuth state 签名与校验 —— 单元测试。

state 格式: base64url(payload_json).base64url(hmac_signature)
payload: {"nonce": "...", "timestamp": 1234567890}
签名: HMAC-SHA256(payload_bytes, JWT_SECRET_KEY)
"""

import time

import pytest

from config import get_settings


def _set_secret(key: str):
    get_settings().JWT_SECRET_KEY = key


@pytest.fixture(autouse=True)
def _restore_secret():
    old = get_settings().JWT_SECRET_KEY
    yield
    get_settings().JWT_SECRET_KEY = old


# ── 签名生成 ──

def test_generate_state_returns_string():
    _set_secret("a" * 32)
    from app.auth.oauth_state import generate_oauth_state
    state = generate_oauth_state()
    assert isinstance(state, str)
    assert len(state) > 0
    assert "." in state  # payload.signature 格式


def test_generate_state_is_deterministic_for_same_input():
    """同一 nonce + timestamp 产生相同 state（便于测试校验逻辑）。"""
    _set_secret("a" * 32)
    from app.auth.oauth_state import generate_oauth_state_for_test
    s1 = generate_oauth_state_for_test(nonce="abc", timestamp=1000)
    s2 = generate_oauth_state_for_test(nonce="abc", timestamp=1000)
    assert s1 == s2


def test_generate_state_differs_per_call():
    """不同 nonce 产生不同 state。"""
    _set_secret("a" * 32)
    from app.auth.oauth_state import generate_oauth_state
    states = {generate_oauth_state() for _ in range(10)}
    assert len(states) == 10


# ── 签名校验 ──

def test_valid_state_passes_verification():
    _set_secret("a" * 32)
    from app.auth.oauth_state import generate_oauth_state_for_test, verify_oauth_state

    state = generate_oauth_state_for_test(nonce="test123", timestamp=int(time.time()))
    result = verify_oauth_state(state, max_age_seconds=600)
    assert result is True


def test_verify_rejects_empty_state():
    _set_secret("a" * 32)
    from app.auth.oauth_state import verify_oauth_state
    assert verify_oauth_state("") is False


def test_verify_rejects_malformed_state():
    _set_secret("a" * 32)
    from app.auth.oauth_state import verify_oauth_state
    assert verify_oauth_state("not-valid-state-format") is False
    assert verify_oauth_state("a.b.c") is False  # too many parts


def test_verify_rejects_tampered_payload():
    _set_secret("a" * 32)
    from app.auth.oauth_state import generate_oauth_state_for_test, verify_oauth_state

    state = generate_oauth_state_for_test(nonce="original", timestamp=int(time.time()))
    # 篡改 payload 部分（改 nonce）
    parts = state.split(".")
    import base64
    tampered_payload = base64.urlsafe_b64encode(
        '{"nonce":"tampered","timestamp":9999999999}'.encode()
    ).decode().rstrip("=")
    tampered_state = f"{tampered_payload}.{parts[1]}"

    assert verify_oauth_state(tampered_state) is False


def test_verify_rejects_tampered_signature():
    _set_secret("a" * 32)
    from app.auth.oauth_state import generate_oauth_state_for_test, verify_oauth_state

    state = generate_oauth_state_for_test(nonce="original", timestamp=int(time.time()))
    parts = state.split(".")
    # 改一个 signature 字符
    sig = list(parts[1])
    sig[0] = "A" if sig[0] != "A" else "B"
    tampered_state = f"{parts[0]}.{''.join(sig)}"

    assert verify_oauth_state(tampered_state) is False


def test_verify_rejects_wrong_secret():
    _set_secret("a" * 32)
    from app.auth.oauth_state import generate_oauth_state_for_test
    state = generate_oauth_state_for_test(nonce="cross", timestamp=int(time.time()))

    # 切换到不同 secret
    _set_secret("b" * 32)
    from app.auth.oauth_state import verify_oauth_state
    assert verify_oauth_state(state) is False


def test_verify_rejects_expired_state():
    _set_secret("a" * 32)
    from app.auth.oauth_state import generate_oauth_state_for_test, verify_oauth_state

    # 11 分钟前（max_age=600 即 10 分钟）
    old_ts = int(time.time()) - 660
    state = generate_oauth_state_for_test(nonce="old", timestamp=old_ts)

    assert verify_oauth_state(state, max_age_seconds=600) is False


def test_verify_accepts_state_within_window():
    _set_secret("a" * 32)
    from app.auth.oauth_state import generate_oauth_state_for_test, verify_oauth_state

    # 5 分钟前，在 10 分钟窗口内
    recent_ts = int(time.time()) - 300
    state = generate_oauth_state_for_test(nonce="recent", timestamp=recent_ts)

    assert verify_oauth_state(state, max_age_seconds=600) is True

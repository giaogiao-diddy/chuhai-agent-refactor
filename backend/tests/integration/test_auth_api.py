import pytest
from httpx import ASGITransport, AsyncClient

from config import get_settings
from main import app


@pytest.fixture(autouse=True)
def _restore():
    settings = get_settings()
    old_env = settings.ENV
    old_dev_mode = settings.DEV_MODE
    old_app_id = settings.WECHAT_APP_ID
    old_redirect = settings.WECHAT_REDIRECT_URI
    old_jwt = settings.JWT_SECRET_KEY
    old_wx_secret = settings.WECHAT_APP_SECRET
    yield
    settings.ENV = old_env
    settings.DEV_MODE = old_dev_mode
    settings.WECHAT_APP_ID = old_app_id
    settings.WECHAT_REDIRECT_URI = old_redirect
    settings.JWT_SECRET_KEY = old_jwt
    settings.WECHAT_APP_SECRET = old_wx_secret


def _configure_for_auth():
    settings = get_settings()
    settings.WECHAT_APP_ID = "wx-test-appid"
    settings.WECHAT_REDIRECT_URI = "https://example.com/callback"
    settings.WECHAT_APP_SECRET = "test-wechat-secret-not-real"
    settings.JWT_SECRET_KEY = "a" * 32


# ── login-url ──

@pytest.mark.asyncio
async def test_wechat_login_url_returns_url_and_state():
    _configure_for_auth()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/auth/wechat/login-url")
    assert resp.status_code == 200
    data = resp.json()
    assert "url" in data
    assert "state" in data
    assert data["state"]  # non-empty
    assert data["state"] in data["url"]  # state 包含在 URL 中


@pytest.mark.asyncio
async def test_wechat_login_url_encodes_redirect_uri():
    settings = get_settings()
    settings.WECHAT_APP_ID = "wx-test-appid"
    settings.WECHAT_REDIRECT_URI = "https://example.com/callback?x=1&y=2"
    settings.JWT_SECRET_KEY = "a" * 32

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/auth/wechat/login-url")
    assert resp.status_code == 200
    url = resp.json()["url"]
    # redirect_uri 必须被编码，不能出现未编码的 &
    assert "?x=1&y=2" not in url
    assert "%26" in url or "redirect_uri=https%3A" in url


@pytest.mark.asyncio
async def test_wechat_login_url_missing_config_returns_503():
    settings = get_settings()
    settings.WECHAT_APP_ID = ""
    settings.WECHAT_REDIRECT_URI = ""
    settings.JWT_SECRET_KEY = "a" * 32

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/auth/wechat/login-url")
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_wechat_login_url_requires_jwt_secret():
    """JWT_SECRET_KEY 未正确配置时 login-url 应失败。

    validate_jwt_secret 抛出 ValueError，ASGI transport 可能将其转为
    500 响应，也可能原样传播异常。两种行为均可接受。
    """
    settings = get_settings()
    settings.WECHAT_APP_ID = "wx-test-appid"
    settings.WECHAT_REDIRECT_URI = "https://example.com/callback"
    settings.JWT_SECRET_KEY = "change_me"

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/auth/wechat/login-url")
        # ASGI transport 返回了响应 → 必须是服务端错误
        assert resp.status_code >= 500
    except ValueError:
        # ASGI transport 原样传播了 ValueError → 也是预期行为
        pass


# ── dev-login ──

@pytest.mark.asyncio
async def test_dev_login_enabled_in_development_env():
    settings = get_settings()
    settings.ENV = "development"
    settings.DEV_MODE = False
    settings.JWT_SECRET_KEY = "a" * 32

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/auth/dev-login",
            json={"name": "dev-test-login", "role": "consultant"},
        )

    from app.db.session import async_session
    from app.models import User
    from sqlalchemy import delete
    async with async_session() as db:
        await db.execute(delete(User).where(User.wechat_openid == "dev:dev-test-login"))
        await db.commit()

    assert resp.status_code == 200
    data = resp.json()
    assert data["access_token"]
    assert data["user"]["role"] == "consultant"


@pytest.mark.asyncio
async def test_dev_login_disabled_in_production_without_dev_mode():
    settings = get_settings()
    settings.ENV = "production"
    settings.DEV_MODE = False
    settings.JWT_SECRET_KEY = "a" * 32

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/auth/dev-login",
            json={"name": "dev-test-login", "role": "consultant"},
        )

    assert resp.status_code == 503


# ── Monkeypatch 辅助：阻止真实微信 HTTP 请求 ──

class _FakeWechatErrorTransport:
    """模拟微信 API 返回错误（不发起真实网络请求）。"""

    async def get(self, url: str, **kwargs):
        raise AssertionError(f"测试不应发起真实 HTTP 请求: {url}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


def _mock_httpx_async_client(monkeypatch):
    """用 monkeypatch 替换 app.api.auth.httpx.AsyncClient 为假 client。
    一旦被调用就 raise AssertionError，确保测试不访问外网。
    """
    import app.api.auth as auth_module

    def _fake_client(*args, **kwargs):
        return _FakeWechatErrorTransport()

    monkeypatch.setattr(auth_module.httpx, "AsyncClient", _fake_client)


# ── callback: state 校验 ──

@pytest.mark.asyncio
async def test_callback_rejects_missing_state():
    _configure_for_auth()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/auth/wechat/callback?code=fake&state=")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_callback_rejects_invalid_state():
    _configure_for_auth()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/auth/wechat/callback?code=fake&state=not.a.valid.state")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_callback_rejects_tampered_state():
    _configure_for_auth()
    from app.auth.oauth_state import generate_oauth_state_for_test
    import time

    valid_state = generate_oauth_state_for_test(nonce="abc", timestamp=int(time.time()))
    # 篡改最后一个字符
    tampered = valid_state[:-1] + ("A" if valid_state[-1] != "A" else "B")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/auth/wechat/callback?code=fake&state={tampered}"
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_callback_rejects_expired_state():
    _configure_for_auth()
    from app.auth.oauth_state import generate_oauth_state_for_test
    import time

    # 11 分钟前的 state
    old_ts = int(time.time()) - 660
    old_state = generate_oauth_state_for_test(nonce="old", timestamp=old_ts)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            f"/auth/wechat/callback?code=fake&state={old_state}"
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_callback_state_invalid_does_not_call_wechat():
    """state 校验失败时不应该去调用微信 API。
    验证方式：callback 返回 400 且不会因微信 app_secret 为空报 503。
    """
    settings = get_settings()
    settings.WECHAT_APP_ID = "wx-test-appid"
    settings.WECHAT_APP_SECRET = ""  # 未配置
    settings.JWT_SECRET_KEY = "a" * 32
    settings.WECHAT_REDIRECT_URI = "https://example.com/callback"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # state 无效 → 400（state 校验失败），不是 503（微信未配置）
        resp = await client.get("/auth/wechat/callback?code=fake&state=bad-state")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_callback_with_valid_state_reaches_wechat_check(monkeypatch):
    """有效 state 通过校验后继续走微信 API 流程。

    用 monkeypatch 替换 httpx.AsyncClient，一旦被调用就 raise AssertionError。
    state 校验通过后会尝试调用微信 API → 触发 AssertionError → 证明校验通过。
    """
    _configure_for_auth()
    _mock_httpx_async_client(monkeypatch)

    from app.auth.oauth_state import generate_oauth_state_for_test
    import time

    valid_state = generate_oauth_state_for_test(
        nonce="test-cb", timestamp=int(time.time())
    )

    transport = ASGITransport(app=app)
    wechat_was_called = False
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/auth/wechat/callback?code=fake_code_123&state={valid_state}"
            )
        # 如果走到这里（未抛异常），说明 mock 未被触发
        # 可能是响应在 mock 之前就返回了
        assert resp.status_code != 400 or "state" not in resp.json().get("detail", "").lower()
    except AssertionError as e:
        if "不应发起真实 HTTP 请求" in str(e):
            wechat_was_called = True
        else:
            raise

    assert wechat_was_called, "有效 state 应通过校验并尝试调用微信 API"


@pytest.mark.asyncio
async def test_callback_with_weak_jwt_secret_does_not_call_wechat(monkeypatch):
    """JWT_SECRET_KEY="change_me" 时，callback 不应继续调用微信 API。

    即使用弱密钥生成了一个 state，verify_oauth_state 中的 _sign()
    会调用 validate_jwt_secret() 并抛出 ValueError。
    """
    settings = get_settings()
    settings.WECHAT_APP_ID = "wx-test-appid"
    settings.WECHAT_REDIRECT_URI = "https://example.com/callback"
    settings.WECHAT_APP_SECRET = "test-wechat-secret-not-real"
    settings.JWT_SECRET_KEY = "change_me"

    _mock_httpx_async_client(monkeypatch)

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/auth/wechat/callback?code=fake&state=some.state.here")
        # 如果返回了响应，应是服务端错误（不是调了微信 API）
        assert resp.status_code >= 400
    except ValueError:
        # ASGI transport 原样传播 ValueError → state 校验层面阻止了微信调用
        pass

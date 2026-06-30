import pytest
from httpx import ASGITransport, AsyncClient

from config import get_settings
from main import app


@pytest.fixture(autouse=True)
def _restore():
    settings = get_settings()
    old_app_id = settings.WECHAT_APP_ID
    old_redirect = settings.WECHAT_REDIRECT_URI
    yield
    settings.WECHAT_APP_ID = old_app_id
    settings.WECHAT_REDIRECT_URI = old_redirect


@pytest.mark.asyncio
async def test_wechat_login_url_encodes_redirect_uri():
    settings = get_settings()
    settings.WECHAT_APP_ID = "wx-test-appid"
    settings.WECHAT_REDIRECT_URI = "https://example.com/callback?x=1&y=2"

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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/auth/wechat/login-url")
    assert resp.status_code == 503

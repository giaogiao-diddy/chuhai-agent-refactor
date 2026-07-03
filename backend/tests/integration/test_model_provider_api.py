import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import async_session, get_db
from main import app


async def _override_get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


class FakeUser:
    def __init__(self, role="consultant"):
        self.id = uuid.uuid4()
        self.role = role


async def _fake_consultant():
    return FakeUser("consultant")


async def _fake_user():
    return FakeUser("user")


async def _cleanup_created_provider(provider_id: str) -> None:
    from app.db.session import async_session as sess
    from app.models.model_provider import ModelProvider
    from sqlalchemy import delete
    async with sess() as db:
        await db.execute(delete(ModelProvider).where(ModelProvider.id == uuid.UUID(provider_id)))
        await db.commit()


@pytest.fixture(autouse=True)
def _cleanup_deps():
    yield
    app.dependency_overrides.clear()


def _skip_if_no_db():
    from config import get_settings
    s = get_settings()
    if not s.DATABASE_URL or "postgresql" not in s.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")


def _app_instance():
    from app.api.auth_deps import get_current_consultant_required
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_consultant_required] = _fake_consultant
    return app


# ── 权限 ──

@pytest.mark.asyncio
async def test_unauthenticated_returns_401():
    _skip_if_no_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/model-providers")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_user_role_returns_403():
    _skip_if_no_db()
    from app.api.auth_deps import get_current_user_required
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user_required] = _fake_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/model-providers")
    assert resp.status_code == 403


# ── CRUD ──

@pytest.mark.asyncio
async def test_create_provider_masks_api_key_in_response():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    pid = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/model-providers",
                json={"name": "Test", "base_url": "https://x.com", "api_key": "sk-secret-1234abcd", "default_model": "m1"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "api_key" not in data
        assert data["masked_key"] == "sk-s...abcd"
        pid = data["id"]
    finally:
        if pid:
            await _cleanup_created_provider(pid)


@pytest.mark.asyncio
async def test_list_providers_does_not_return_api_key():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    pid = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_resp = await client.post(
                "/model-providers",
                json={"name": "ListTest", "base_url": "https://x.com", "api_key": "sk-list", "default_model": "m"},
            )
            pid = create_resp.json()["id"]
            resp = await client.get("/model-providers")
        assert resp.status_code == 200
        for item in resp.json():
            assert "api_key" not in item
    finally:
        if pid:
            await _cleanup_created_provider(pid)


@pytest.mark.asyncio
async def test_delete_provider():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    pid = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_resp = await client.post(
                "/model-providers",
                json={"name": "ToDelete", "base_url": "https://x.com", "api_key": "sk-del", "default_model": "m"},
            )
            pid = create_resp.json()["id"]
            del_resp = await client.delete(f"/model-providers/{pid}")
            assert del_resp.status_code == 200
            pid = None  # already deleted
    finally:
        if pid:
            await _cleanup_created_provider(pid)


@pytest.mark.asyncio
async def test_update_provider_fields():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    pid = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_resp = await client.post(
                "/model-providers",
                json={"name": "Upd", "base_url": "https://x.com", "api_key": "sk-upd", "default_model": "m"},
            )
            pid = create_resp.json()["id"]
            patch_resp = await client.patch(f"/model-providers/{pid}", json={"default_model": "updated-model", "context_window": 64000})
            assert patch_resp.status_code == 200
            p = patch_resp.json()
            assert p["default_model"] == "updated-model"
    finally:
        if pid:
            await _cleanup_created_provider(pid)


@pytest.mark.asyncio
async def test_test_connection_returns_safe_message():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    pid = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_resp = await client.post(
                "/model-providers",
                json={"name": "TestConn", "base_url": "https://invalid.example.com", "api_key": "sk-bad-key-12345678", "default_model": "m"},
            )
            pid = create_resp.json()["id"]
            test_resp = await client.post(f"/model-providers/{pid}/test")
            data = test_resp.json()
            assert data["success"] is False
            assert "sk-bad-key" not in str(data)
    finally:
        if pid:
            await _cleanup_created_provider(pid)


# ── strip 校验 ──

@pytest.mark.asyncio
async def test_create_provider_rejects_blank_name():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/model-providers",
            json={"name": "   ", "base_url": "https://x.com", "api_key": "sk-x", "default_model": "m"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_provider_rejects_blank_api_key():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/model-providers",
            json={"name": "OK", "base_url": "https://x.com", "api_key": "   ", "default_model": "m"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_provider_rejects_blank_default_model():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    pid = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_resp = await client.post(
                "/model-providers",
                json={"name": "StripUpd", "base_url": "https://x.com", "api_key": "sk-x", "default_model": "m"},
            )
            pid = create_resp.json()["id"]
            patch_resp = await client.patch(f"/model-providers/{pid}", json={"default_model": "   "})
            assert patch_resp.status_code == 422
    finally:
        if pid:
            await _cleanup_created_provider(pid)


@pytest.mark.asyncio
async def test_update_provider_strips_name():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    pid = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_resp = await client.post(
                "/model-providers",
                json={"name": "StripName", "base_url": "https://x.com", "api_key": "sk-x", "default_model": "m"},
            )
            pid = create_resp.json()["id"]
            patch_resp = await client.patch(f"/model-providers/{pid}", json={"name": "  New Name  "})
            assert patch_resp.status_code == 200
            assert patch_resp.json()["name"] == "New Name"
    finally:
        if pid:
            await _cleanup_created_provider(pid)


# ── 非字符串输入 → 422 ──

@pytest.mark.asyncio
async def test_create_provider_rejects_nonstring_name():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/model-providers",
            json={"name": 123, "base_url": "https://x.com", "api_key": "sk-x", "default_model": "m"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_provider_rejects_nonstring_base_url():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/model-providers",
            json={"name": "OK", "base_url": 123, "api_key": "sk-x", "default_model": "m"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_provider_rejects_nonstring_api_key():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    pid = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_resp = await client.post(
                "/model-providers",
                json={"name": "NonStrUpd", "base_url": "https://x.com", "api_key": "sk-x", "default_model": "m"},
            )
            pid = create_resp.json()["id"]
            patch_resp = await client.patch(f"/model-providers/{pid}", json={"api_key": 123})
            assert patch_resp.status_code == 422
    finally:
        if pid:
            await _cleanup_created_provider(pid)


@pytest.mark.asyncio
async def test_update_provider_rejects_nonstring_default_model():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    pid = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_resp = await client.post(
                "/model-providers",
                json={"name": "NonStrUpd2", "base_url": "https://x.com", "api_key": "sk-x", "default_model": "m"},
            )
            pid = create_resp.json()["id"]
            patch_resp = await client.patch(f"/model-providers/{pid}", json={"default_model": 123})
            assert patch_resp.status_code == 422
    finally:
        if pid:
            await _cleanup_created_provider(pid)


# ── URL 拼接 ──

def test_chat_completions_url_handles_v1_suffix():
    from app.api.model_providers import _chat_completions_url
    assert _chat_completions_url("https://api.deepseek.com") == "https://api.deepseek.com/v1/chat/completions"
    assert _chat_completions_url("https://api.deepseek.com/v1") == "https://api.deepseek.com/v1/chat/completions"
    assert _chat_completions_url("https://xxx/compatible-mode/v1") == "https://xxx/compatible-mode/v1/chat/completions"
    assert _chat_completions_url("https://api.openai.com/v1/") == "https://api.openai.com/v1/chat/completions"

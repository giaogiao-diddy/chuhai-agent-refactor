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
    from app.api.auth_deps import get_current_consultant_required, get_current_user_required
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_consultant_required] = _fake_consultant
    return app


# ── 权限 ──

@pytest.mark.asyncio
async def test_knowledge_unauthenticated_returns_401():
    _skip_if_no_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/knowledge")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_knowledge_user_role_returns_403():
    _skip_if_no_db()
    from app.api.auth_deps import get_current_user_required
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user_required] = _fake_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/knowledge")
    assert resp.status_code == 403


# ── CRUD ──

@pytest.mark.asyncio
async def test_create_knowledge_returns_201_and_no_embedding():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    doc_id = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/knowledge", json={
                "title": "Test Doc", "content": "test content for embedding", "source": "test-src",
            })
        assert resp.status_code == 201
        data = resp.json()
        doc_id = data["id"]
        assert "embedding" not in data
        assert "id" in data
        assert data["has_embedding"] is True
    finally:
        if doc_id:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.delete(f"/knowledge/{doc_id}")


@pytest.mark.asyncio
async def test_list_knowledge_does_not_return_embedding():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    doc_id = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/knowledge", json={
                "title": "ListTest", "content": "list test content",
            })
            doc_id = resp.json()["id"]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            list_resp = await client.get("/knowledge")
        assert list_resp.status_code == 200
        for item in list_resp.json():
            assert "embedding" not in item
            assert "has_embedding" in item
    finally:
        if doc_id:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.delete(f"/knowledge/{doc_id}")


@pytest.mark.asyncio
async def test_delete_knowledge_returns_204():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    doc_id = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/knowledge", json={
                "title": "ToDelete", "content": "will be deleted",
            })
            doc_id = resp.json()["id"]
            del_resp = await client.delete(f"/knowledge/{doc_id}")
            assert del_resp.status_code == 204
            doc_id = None
    finally:
        if doc_id:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.delete(f"/knowledge/{doc_id}")


@pytest.mark.asyncio
async def test_get_knowledge_detail_returns_full_content():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    doc_id = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/knowledge", json={
                "title": "DetailTest", "content": "full content for detail endpoint",
            })
            doc_id = resp.json()["id"]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            detail_resp = await client.get(f"/knowledge/{doc_id}")
        assert detail_resp.status_code == 200
        data = detail_resp.json()
        assert data["content"] == "full content for detail endpoint"
        assert "embedding" not in data
        assert data["has_embedding"] is True
    finally:
        if doc_id:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.delete(f"/knowledge/{doc_id}")


@pytest.mark.asyncio
async def test_get_knowledge_404():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/knowledge/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_knowledge_does_not_return_embedding():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    doc_id = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/knowledge", json={
                "title": "SearchTest", "content": "B2B factory export to Southeast Asia market strategy",
            })
            doc_id = resp.json()["id"]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            search_resp = await client.post("/knowledge/search", json={
                "query": "Southeast Asia export", "top_k": 3,
            })
        assert search_resp.status_code == 200
        for item in search_resp.json():
            assert "embedding" not in item
            assert "distance" in item
            assert "content_preview" in item
    finally:
        if doc_id:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.delete(f"/knowledge/{doc_id}")


# ── 校验 ──

@pytest.mark.asyncio
async def test_create_knowledge_rejects_blank_title():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/knowledge", json={"title": "   ", "content": "valid content"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_knowledge_rejects_blank_content():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/knowledge", json={"title": "valid", "content": "   "})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_knowledge_rejects_blank_title():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    doc_id = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/knowledge", json={"title": "orig", "content": "original content"})
            doc_id = resp.json()["id"]
            patch_resp = await client.patch(f"/knowledge/{doc_id}", json={"title": "   "})
            assert patch_resp.status_code == 422
    finally:
        if doc_id:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.delete(f"/knowledge/{doc_id}")


@pytest.mark.asyncio
async def test_update_knowledge_can_clear_source():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    doc_id = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/knowledge", json={"title": "src-test", "content": "c", "source": "old"})
            doc_id = resp.json()["id"]
            await client.patch(f"/knowledge/{doc_id}", json={"source": None})
            detail_resp = await client.get(f"/knowledge/{doc_id}")
            assert detail_resp.json()["source"] is None
    finally:
        if doc_id:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.delete(f"/knowledge/{doc_id}")


@pytest.mark.asyncio
async def test_update_knowledge_blank_source_becomes_none():
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    doc_id = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/knowledge", json={"title": "src-test2", "content": "c", "source": "old"})
            doc_id = resp.json()["id"]
            await client.patch(f"/knowledge/{doc_id}", json={"source": "   "})
            detail_resp = await client.get(f"/knowledge/{doc_id}")
            assert detail_resp.json()["source"] is None
    finally:
        if doc_id:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.delete(f"/knowledge/{doc_id}")

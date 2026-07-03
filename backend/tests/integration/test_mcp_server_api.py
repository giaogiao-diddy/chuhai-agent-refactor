import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, text

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


def _skip_if_no_db():
    from config import get_settings
    s = get_settings()
    if not s.DATABASE_URL or "postgresql" not in s.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")


async def _skip_if_postgres_unreachable():
    _skip_if_no_db()
    try:
        async with async_session() as db:
            await db.execute(text("select 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL 不可达: {type(exc).__name__}")


def _app_instance():
    from app.api.auth_deps import get_current_consultant_required
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_consultant_required] = _fake_consultant
    return app


async def _cleanup_server(server_id: str) -> None:
    from app.models.mcp_server import McpServer
    async with async_session() as db:
        await db.execute(delete(McpServer).where(McpServer.id == uuid.UUID(server_id)))
        await db.commit()


@pytest.fixture(autouse=True)
def _cleanup_deps():
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_mcp_requires_http_url():
    _skip_if_no_db()
    async with AsyncClient(transport=ASGITransport(app=_app_instance()), base_url="http://test") as client:
        resp = await client.post("/mcp-servers", json={"name": "Tariff", "transport": "http"})

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_mcp_rejects_unsupported_transport():
    _skip_if_no_db()
    async with AsyncClient(transport=ASGITransport(app=_app_instance()), base_url="http://test") as client:
        resp = await client.post(
            "/mcp-servers",
            json={"name": "Local", "transport": "stdio", "command": "python server.py"},
        )

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_mcp_response_does_not_expose_headers_or_env():
    await _skip_if_postgres_unreachable()
    server_id = None
    try:
        async with AsyncClient(transport=ASGITransport(app=_app_instance()), base_url="http://test") as client:
            resp = await client.post(
                "/mcp-servers",
                json={
                    "name": "Tariff",
                    "transport": "http",
                    "url": "https://mcp.example.com",
                    "headers": {"Authorization": "Bearer secret"},
                    "env": {"TOKEN": "secret"},
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        server_id = data["id"]
        assert "headers" not in data
        assert "env" not in data
        assert "secret" not in str(data)
    finally:
        if server_id:
            await _cleanup_server(server_id)


@pytest.mark.asyncio
async def test_mcp_test_connection_returns_tools_count(monkeypatch):
    await _skip_if_postgres_unreachable()

    async def fake_list_tools(server_url, headers=None):
        return [{"name": "ping", "description": "ping", "inputSchema": {"properties": {}}}]

    monkeypatch.setattr("app.api.mcp_servers.list_mcp_tools", fake_list_tools)

    server_id = None
    try:
        async with AsyncClient(transport=ASGITransport(app=_app_instance()), base_url="http://test") as client:
            create_resp = await client.post(
                "/mcp-servers",
                json={"name": "Tariff", "transport": "http", "url": "https://mcp.example.com"},
            )
            server_id = create_resp.json()["id"]
            resp = await client.post(f"/mcp-servers/{server_id}/test")

        assert resp.status_code == 200
        data = resp.json()
        assert data["connected"] is True
        assert data["tools_count"] == 1
    finally:
        if server_id:
            await _cleanup_server(server_id)

"""Phase 43 测试：Agent 运行时模型选择"""
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


async def _create_provider(client: AsyncClient, name="TestModel", enabled=True) -> dict:
    resp = await client.post(
        "/model-providers",
        json={"name": name, "base_url": "https://test.example.com", "api_key": "sk-test1234", "default_model": "test-model-v1", "enabled": enabled},
    )
    assert resp.status_code == 200
    return resp.json()


async def _delete_provider(client: AsyncClient, provider_id: str) -> None:
    await client.delete(f"/model-providers/{provider_id}")


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


# ── /start 模型选择 ──

@pytest.mark.asyncio
async def test_start_with_default_provider_locks_model():
    """不传 provider_id 时，/start 使用默认 enabled Provider 并锁定。"""
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    pid = None
    disabled_ids: list[str] = []
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            providers = (await client.get("/model-providers")).json()
            for existing in providers:
                if existing.get("enabled"):
                    await client.patch(f"/model-providers/{existing['id']}", json={"enabled": False})
                    disabled_ids.append(existing["id"])
            p = await _create_provider(client, "StartDefault")
            pid = p["id"]
            resp = await client.post("/conversation/start", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider_id"] == pid
        assert data["model_name"] == "test-model-v1"
        assert data["state"]["provider_id"] == pid
        assert data["state"]["model_name"] == "test-model-v1"
    finally:
        if pid:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await _delete_provider(client, pid)
        if disabled_ids:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                for existing_id in disabled_ids:
                    await client.patch(f"/model-providers/{existing_id}", json={"enabled": True})


@pytest.mark.asyncio
async def test_start_with_specific_provider_locks_model():
    """传 provider_id 时，/start 锁定指定 Provider。"""
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    pid = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            p = await _create_provider(client, "StartSpecific")
            pid = p["id"]
            resp = await client.post("/conversation/start", json={"provider_id": pid, "model_name": "custom-model"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider_id"] == pid
        assert data["model_name"] == "custom-model"
        assert data["state"]["provider_id"] == pid
        assert data["state"]["model_name"] == "custom-model"
    finally:
        if pid:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await _delete_provider(client, pid)


@pytest.mark.asyncio
async def test_start_with_disabled_provider_returns_400():
    """传 disabled Provider → 400。"""
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    pid = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            p = await _create_provider(client, "StartDisabled", enabled=False)
            pid = p["id"]
            resp = await client.post("/conversation/start", json={"provider_id": pid})
        assert resp.status_code == 400
    finally:
        if pid:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await _delete_provider(client, pid)


@pytest.mark.asyncio
async def test_start_with_nonexistent_provider_returns_400():
    """传不存在的 provider_id → 400。"""
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/conversation/start", json={"provider_id": "00000000-0000-0000-0000-000000000000"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_start_invalid_provider_id_returns_400():
    """传无效的 provider_id → 400。"""
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/conversation/start", json={"provider_id": "not-a-uuid"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_start_no_provider_uses_env_fallback():
    """无 enabled DB Provider 时，/start 返回 provider_id/model_name 为 null（env fallback）。"""
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    # 先保存当前 enabled provider 的 ID，临时禁用全部
    disabled_ids: list[str] = []
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        providers = (await client.get("/model-providers")).json()
        for p in providers:
            if p.get("enabled"):
                await client.patch(f"/model-providers/{p['id']}", json={"enabled": False})
                disabled_ids.append(p["id"])

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/conversation/start", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["provider_id"] is None
        assert data["model_name"] is None
        assert data["state"]["provider_id"] is None
        assert data["state"]["model_name"] is None
    finally:
        # 恢复 enabled
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            for pid in disabled_ids:
                await client.patch(f"/model-providers/{pid}", json={"enabled": True})


# ── state 往返 ──

@pytest.mark.asyncio
async def test_conversation_state_roundtrip_preserves_provider():
    """ConversationClientState ↔ AgentState 往返保留 provider_id/model_name。"""
    from app.schemas.conversation import ConversationClientState

    cc = ConversationClientState(
        messages=[], slots={}, answers={}, branch=None, status="active",
        conversation_round=0, ai_failure_count=0, validation_errors=[],
        used_template_report=False, provider_id="pid-1", model_name="m1",
    )
    agent_state = cc.to_agent_state()
    assert agent_state.provider_id == "pid-1"
    assert agent_state.model_name == "m1"

    cc2 = ConversationClientState.from_agent_state(agent_state)
    assert cc2.provider_id == "pid-1"
    assert cc2.model_name == "m1"


# ── Provider API Key 不出现在响应中 ──

@pytest.mark.asyncio
async def test_start_does_not_leak_api_key():
    """/start 响应不泄露 API Key。"""
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    pid = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            p = await _create_provider(client, "LeakTest")
            pid = p["id"]
            resp = await client.post("/conversation/start", json={"provider_id": pid})
        assert resp.status_code == 200
        body = resp.json()
        body_str = str(body)
        assert "sk-test" not in body_str
    finally:
        if pid:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await _delete_provider(client, pid)


# ── 公开 Provider 接口 ──

@pytest.mark.asyncio
async def test_public_provider_list_requires_no_auth():
    """GET /model-providers/enabled-public 无需认证，不返回 401/403。"""
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/model-providers/enabled-public")
    # 不鉴权 → 不返回 401 或 403
    assert resp.status_code not in (401, 403)
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_public_provider_list_filters_disabled():
    """GET /model-providers/enabled-public 只返回 enabled=true 的 Provider。"""
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    pid_enabled = None
    pid_disabled = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            p1 = await _create_provider(client, "PubEnabled", enabled=True)
            pid_enabled = p1["id"]
            p2 = await _create_provider(client, "PubDisabled", enabled=False)
            pid_disabled = p2["id"]
        # 使用公开接口（同一 transport 带 DB override）
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/model-providers/enabled-public")
        assert resp.status_code == 200
        items = resp.json()
        ids = [it["id"] for it in items]
        assert pid_enabled in ids
        assert pid_disabled not in ids
    finally:
        if pid_enabled or pid_disabled:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                if pid_enabled: await _delete_provider(client, pid_enabled)
                if pid_disabled: await _delete_provider(client, pid_disabled)


@pytest.mark.asyncio
async def test_public_provider_list_no_sensitive_fields():
    """GET /model-providers/enabled-public 不泄露 api_key/base_url/masked_key/provider_type。"""
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    pid = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            p = await _create_provider(client, "PubSensitive")
            pid = p["id"]
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/model-providers/enabled-public")
        assert resp.status_code == 200
        for item in resp.json():
            assert "api_key" not in item
            assert "masked_key" not in item
            assert "base_url" not in item
            assert "provider_type" not in item
            assert "created_at" not in item
            assert "updated_at" not in item
            assert "id" in item
            assert "name" in item
            assert "default_model" in item
            assert "context_window" in item
    finally:
        if pid:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await _delete_provider(client, pid)


# ── disabled provider 在 continue/finish 返回错误 ──

@pytest.mark.asyncio
async def test_continue_with_disabled_provider_returns_400():
    """start 锁定 provider 后 provider 被禁用，continue 返回 400。"""
    _skip_if_no_db()
    transport = ASGITransport(app=_app_instance())
    pid = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            p = await _create_provider(client, "ContDisabled")
            pid = p["id"]
            # start with this provider
            start_resp = await client.post("/conversation/start", json={"provider_id": pid})
            assert start_resp.status_code == 200
            state = start_resp.json()["state"]

            # disable the provider
            await client.patch(f"/model-providers/{pid}", json={"enabled": False})

            # continue should fail
            cont_resp = await client.post("/conversation/continue", json={"state": state, "message": "test"})
            assert cont_resp.status_code == 400
    finally:
        if pid:
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await _delete_provider(client, pid)


# ── 报告历史返回 provider_id/model_name ──

@pytest.mark.asyncio
async def test_report_list_returns_model_info():
    """ReportListItem 包含 provider_id / model_name。"""
    _skip_if_no_db()
    from app.schemas.report_history import ReportListItem
    from datetime import datetime, timezone

    item = ReportListItem(
        assessment_id="00000000-0000-0000-0000-000000000001",
        status="completed",
        created_at=datetime.now(timezone.utc),
        provider_id="pid-123",
        model_name="deepseek-v3",
    )
    data = item.model_dump()
    assert data["provider_id"] == "pid-123"
    assert data["model_name"] == "deepseek-v3"


@pytest.mark.asyncio
async def test_report_detail_returns_model_info():
    """ReportDetailResponse 包含 provider_id / model_name。"""
    _skip_if_no_db()
    from app.schemas.report_history import ReportDetailResponse, PublicReportSummary
    from datetime import datetime, timezone

    detail = ReportDetailResponse(
        assessment_id="00000000-0000-0000-0000-000000000001",
        status="completed",
        created_at=datetime.now(timezone.utc),
        report_summary=PublicReportSummary(
            feasibility_score=50, display_score=50, tag="test",
            tag_explanation="x", preliminary_judgment="x",
            strengths=[], risks=[], unlock_hint="x",
        ),
        provider_id="pid-456",
        model_name="gpt-4",
    )
    data = detail.model_dump()
    assert data["provider_id"] == "pid-456"
    assert data["model_name"] == "gpt-4"


# ── AgentState 默认值 ──

@pytest.mark.asyncio
async def test_agent_state_defaults_provider_to_none():
    """AgentState 的 provider_id/model_name 默认为 None。"""
    from app.schemas.agent_state import AgentState
    s = AgentState()
    assert s.provider_id is None
    assert s.model_name is None

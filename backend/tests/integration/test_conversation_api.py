import uuid
from sqlalchemy import delete

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import async_session, get_db
from app.models import Assessment, LeadReport, UserReport
from app.models.message import Message
from app.models.user import User as UserModel
from config import get_settings
from main import app


def _skip_if_no_ai_key():
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY:
        pytest.skip("DEEPSEEK_API_KEY 未配置")


async def _override_get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def _app_with_db():
    app.dependency_overrides[get_db] = _override_get_db
    return app


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    yield
    app.dependency_overrides.clear()


FORBIDDEN_IN_RESPONSE = [
    "raw_report", "lead_report", "scoring_result", "audit_result",
    "scoring_error", "report_error",
    "lead_score", "lead_priority", "sales_followup", "consultant_notes",
    "销售话术", "顾问跟进", "线索优先级", "顾问备注",
]


# ── start ───────────────────────────────────────────────────────

async def test_conversation_start_returns_opening_message():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/conversation/start")
    assert response.status_code == 200
    data = response.json()
    assert data["assistant_message"]
    assert len(data["state"]["messages"]) >= 1
    text = response.text
    assert "lead_report" not in text
    assert "raw_report" not in text
    assert "lead_score" not in text


# ── 空白消息 ────────────────────────────────────────────────────

async def test_continue_blank_message_returns_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = await client.post("/conversation/start")
        state = start.json()["state"]
        resp = await client.post(
            "/conversation/continue",
            json={"state": state, "message": "   "},
        )
    assert resp.status_code == 422


# ── 恶意注入 ────────────────────────────────────────────────────

async def test_continue_malicious_state_no_leak():
    """恶意注入不会泄露顾问字段（ConversationClientState 白名单阻止注入）"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = await client.post("/conversation/start")
        state_data = start.json()["state"]
        # 注入恶意字段 — ConversationClientState 会忽略额外字段
        state_data["lead_report"] = {"lead_score": 99, "lead_priority": "P0", "tag": "x", "sales_followup": "秘密话术", "consultant_notes": "秘密"}
        state_data["raw_report"] = {"summary_conclusion": "x", "positioning_assessment": "x", "content_assessment": "x", "conversion_assessment": "x", "recommended_path": "x", "risk_reminder": "x", "action_plan_30days": ["1","2","3","4"], "consultant_guide": "x", "sales_followup": "秘密", "consultant_notes": "秘密"}

        resp = await client.post(
            "/conversation/continue",
            json={"state": state_data, "message": "test"},
        )
        assert resp.status_code == 200
        text = resp.text
        for word in FORBIDDEN_IN_RESPONSE:
            assert word not in text, f"响应泄露了: {word}"


# ── finish 无身份拒绝 ───────────────────────────────────────────

async def test_finish_without_identity_returns_401():
    """有 user message 但没有 JWT 也没有 anonymous_user_id → 401"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/finish",
            json={
                "state": {
                    "messages": [{"role": "user", "content": "test"}],
                    "conversation_round": 1,
                    "answers": {},
                }
            },
        )
    assert resp.status_code == 401


# ── 空对话 finish 拒绝 ──────────────────────────────────────────

async def test_finish_empty_conversation_returns_400():
    """start 后直接 finish 应拒绝，无 user 消息"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = await client.post("/conversation/start")
        state = start.json()["state"]

        resp = await client.post(
            "/conversation/finish",
            json={"state": state},
        )
    assert resp.status_code == 400
    assert "不足" in resp.text


# ── 对话无轮次上限 ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_continue_after_eight_rounds_still_allowed(monkeypatch):
    from app.agent.state_machine import append_assistant_message
    import app.api.conversation as conversation_api

    async def fake_run_dialogue_graph(state):
        return append_assistant_message(state, "继续补充问题")

    async def fake_extract_answers_node(state):
        return state

    monkeypatch.setattr(conversation_api, "run_dialogue_graph", fake_run_dialogue_graph)
    monkeypatch.setattr(conversation_api, "extract_answers_node", fake_extract_answers_node)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/continue",
            json={
                "state": {
                    "messages": [
                        {"role": "user", "content": "你好"},
                        {"role": "assistant", "content": "你好"},
                    ],
                    "conversation_round": 8,
                    "answers": {},
                },
                "message": "test",
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"]["conversation_round"] == 9
    assert data["should_stop"] is False


# ── wechat_qr_url ──────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.asyncio
async def test_finish_returns_wechat_qr_url_when_configured():
    """branch=None 走模板兜底 + DB 写入，验证 wechat_qr_url 返回配置值"""
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")
    old_qr = settings.WECHAT_QR_URL
    settings.WECHAT_QR_URL = "https://example.com/wechat-qr.png"

    anon_id = f"test-qr-url-{uuid.uuid4().hex[:12]}"
    app_with_db = await _app_with_db()
    transport = ASGITransport(app=app_with_db)
    assessment_id = None
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/conversation/finish",
                json={
                    "state": {
                        "messages": [{"role": "user", "content": "test"}],
                        "conversation_round": 1,
                        "branch": None,
                        "answers": {},
                    },
                    "anonymous_user_id": anon_id,
                },
            )
        assert resp.status_code == 200, f"status={resp.status_code} body={resp.text[:300]}"
        data = resp.json()
        assert data["wechat_qr_url"] == "https://example.com/wechat-qr.png"
        assessment_id = data["assessment_id"]
    finally:
        settings.WECHAT_QR_URL = old_qr
        if assessment_id is not None:
            async with async_session() as _db:
                await _db.execute(delete(LeadReport).where(LeadReport.assessment_id == uuid.UUID(assessment_id)))
                await _db.execute(delete(UserReport).where(UserReport.assessment_id == uuid.UUID(assessment_id)))
                await _db.execute(delete(Message).where(Message.assessment_id == uuid.UUID(assessment_id)))
                await _db.execute(delete(Assessment).where(Assessment.id == uuid.UUID(assessment_id)))
                await _db.execute(delete(UserModel).where(UserModel.wechat_openid == f"anonymous:{anon_id}"))
                await _db.commit()


# ── finish 模板兜底安全扫描 ─────────────────────────────────────

@pytest.mark.ai
@pytest.mark.integration
async def test_finish_template_fallback_response_safe():
    """branch=None → 走模板兜底 → 响应不含敏感字段"""
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    app_with_db = await _app_with_db()
    transport = ASGITransport(app=app_with_db)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/conversation/finish",
            json={
                "state": {
                    "messages": [{"role": "user", "content": "test"}],
                    "conversation_round": 1,
                    "branch": None,
                    "answers": {},
                },
                "anonymous_user_id": "test-safety-user-000000",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["used_template_report"] is True
    assert data["state"]["public_error"] is not None
    text = response.text
    for word in FORBIDDEN_IN_RESPONSE:
        assert word not in text, f"响应泄露了: {word}"


# ── continue AI ─────────────────────────────────────────────────

@pytest.mark.ai
@pytest.mark.integration
async def test_conversation_continue_real_deepseek():
    _skip_if_no_ai_key()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start_resp = await client.post("/conversation/start")
        state = start_resp.json()["state"]

        continue_resp = await client.post(
            "/conversation/continue",
            json={"state": state, "message": "我们是一家做健身器材的源头工厂，有少量东南亚客户。"},
        )
    assert continue_resp.status_code == 200
    data = continue_resp.json()
    assert data["assistant_message"]
    assert data["state"]["conversation_round"] == 1
    assert len(data["state"]["messages"]) >= 3
    assert data["state"]["ai_failure_count"] == 0


# ── finish AI ───────────────────────────────────────────────────

@pytest.mark.ai
@pytest.mark.integration
async def test_conversation_finish_real_pipeline_persists_assessment():
    _skip_if_no_ai_key()
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    app_with_db = await _app_with_db()
    transport = ASGITransport(app=app_with_db)
    import uuid
    anonymous_user_id = f"test-ai-finish-{uuid.uuid4()}"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # start → 长消息 continue → 用长消息 state 调 finish
        start = await client.post("/conversation/start")
        start_state = start.json()["state"]

        long_continue = await client.post(
            "/conversation/continue",
            json={"state": start_state, "message": "我们是成立10年以上的健身器材源头工厂，团队100人左右，销售团队10人，去年营收5000万到1亿，毛利率25%-40%。有少量东南亚客户，主要通过阿里国际站和老客户介绍，想开发东南亚市场，因为已有询盘。单笔海外订单大概10万到40万，有复购。产品有部分认证和英文资料，交付比较稳定。有国内新媒体经验，但海外社媒还没系统做。预算每月2到5万，愿意先看报告再预约咨询。"},
        )
        assert long_continue.status_code == 200
        cont_state = long_continue.json()["state"]

        response = await client.post(
            "/conversation/finish",
            json={"state": cont_state, "anonymous_user_id": anonymous_user_id},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["assessment_id"]
    assert data["report_summary"] is not None
    assert data["report_summary"]["tag"]
    assert data["report_summary"]["display_score"] > 0
    assert data["state"]["status"] == "completed"

    text = response.text
    for word in FORBIDDEN_IN_RESPONSE:
        assert word not in text, f"响应泄露了: {word}"

    # 验证 DB
    from sqlalchemy import select
    assessment_id = data["assessment_id"]
    async with async_session() as db:
        aid = uuid.UUID(assessment_id)
        ur = await db.scalar(
            select(UserReport).where(UserReport.assessment_id == aid)
        )
        lr = await db.scalar(
            select(LeadReport).where(LeadReport.assessment_id == aid)
        )
        assert ur is not None, "user_report 未存入数据库"
        assert lr is not None, "lead_report 未存入数据库"

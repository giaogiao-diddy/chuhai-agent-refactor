import uuid
from sqlalchemy import delete, text

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


async def _skip_if_postgres_unreachable():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")
    try:
        async with async_session() as db:
            await db.execute(text("select 1"))
    except Exception as e:
        pytest.skip(f"PostgreSQL 不可达: {type(e).__name__}")


def _fake_light_scoring():
    from app.schemas.scoring import DimensionScore, ScoringResult
    return ScoringResult(
        feasibility_score=50, lead_score=40, display_score=50,
        tag="轻量试探型", tag_explanation="t", preliminary_judgment="p",
        dimension_scores=[DimensionScore(name="d", raw_score=10, max_score=20, normalized_score=50)],
        strengths=["s"], risks=["r"], lead_priority="P2",
    )


def _fake_light_user_report():
    from app.schemas.report import UserReport
    return UserReport(
        feasibility_score=50, display_score=50, tag="t", tag_explanation="t",
        preliminary_judgment="p", strengths=["s"], risks=["r"],
        summary_conclusion="s", positioning_assessment="p",
        content_assessment="c", conversion_assessment="v",
        dimension_scores=[], recommended_path="r", risk_reminder="rr",
        action_plan_30days=["1","2","3","4"], consultant_guide="g",
    )


def _fake_light_lead_report():
    from app.schemas.report import LeadReport
    return LeadReport(
        lead_score=40, lead_priority="P2", tag="t",
        sales_followup="sf", consultant_notes="cn",
    )


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
    """start 不应调用 DeepSeek，conversation_round == 0，messages 只含 assistant 开场白。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/conversation/start")
    assert response.status_code == 200
    data = response.json()
    assert data["assistant_message"]
    assert len(data["state"]["messages"]) >= 1
    assert data["state"]["conversation_round"] == 0
    # 不应包含 user 消息
    for m in data["state"]["messages"]:
        assert m["role"] != "user", "start 不应包含 user message"
    text = response.text
    assert "lead_report" not in text
    assert "raw_report" not in text
    assert "lead_score" not in text


async def test_conversation_start_does_not_call_runner_or_deepseek(monkeypatch):
    """start 轻量开场白，不调 runner/DeepSeek。monkeypatch 为异常后仍应 200。"""
    async def _fail_runner(*args, **kwargs):
        raise AssertionError("start must not call runner")

    def _fail_deepseek(*args, **kwargs):
        raise AssertionError("start must not init DeepSeek")

    monkeypatch.setattr("app.api.conversation.run_agent_event", _fail_runner)
    monkeypatch.setattr("app.agent.runner.DeepSeekClient", _fail_deepseek)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/conversation/start")
    assert response.status_code == 200
    data = response.json()
    assert data["state"]["conversation_round"] == 0
    for m in data["state"]["messages"]:
        assert m["role"] != "user", "start 不应包含 user message"


# ── 空白消息 ────────────────────────────────────────────────────

async def test_continue_blank_message_returns_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/continue",
            json={
                "state": {
                    "messages": [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好"}],
                    "conversation_round": 1,
                    "answers": {},
                },
                "message": "   ",
            },
        )
    assert resp.status_code == 422


# ── 恶意注入 ────────────────────────────────────────────────────

async def test_continue_malicious_state_no_leak(monkeypatch):
    """恶意注入不会泄露顾问字段（ConversationClientState 白名单阻止注入）"""
    from app.agent.state_machine import append_assistant_message, append_user_message
    from app.schemas.agent_protocol import AgentRunResult, TerminalState

    async def fake_runner(state, event, registry=None, max_steps=16):
        new_state = append_user_message(state, event.message)
        new_state = append_assistant_message(new_state, "好的，继续。")
        return AgentRunResult(
            state=new_state,
            terminal=TerminalState.AWAITING_USER,
            response={"assistant_message": "好的，继续。"},
        )

    monkeypatch.setattr("app.api.conversation.run_agent_event", fake_runner)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        state_data = {
            "messages": [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好"}],
            "conversation_round": 1,
            "answers": {},
            "slots": {},
        }
        # 注入恶意字段 — ConversationClientState 会忽略额外字段
        state_data["lead_report"] = {"lead_score": 99, "lead_priority": "P0", "tag": "x", "sales_followup": "秘密话术", "consultant_notes": "秘密"}
        state_data["raw_report"] = {"summary_conclusion": "x"}

        resp = await client.post(
            "/conversation/continue",
            json={"state": state_data, "message": "test"},
        )
        assert resp.status_code == 200
        text = resp.text
        for word in FORBIDDEN_IN_RESPONSE:
            assert word not in text, f"响应泄露了: {word}"


# ── finish 无身份拒绝 ───────────────────────────────────────────

async def test_finish_without_identity_does_not_call_runner(monkeypatch):
    """无 JWT 无 anonymous_user_id → 401，且 runner 不被调用。"""
    def _fail_runner(*args, **kwargs):
        raise AssertionError("runner must not be called without identity")

    monkeypatch.setattr("app.api.conversation.run_agent_event", _fail_runner)

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


# ── finish missing_info ──────────────────────────────────────────

async def test_finish_missing_info_returns_400_no_template(monkeypatch):
    """信息不足时返回 400，不生成 0 分报告。"""
    from app.schemas.agent_protocol import AgentRunResult, TerminalState

    async def fake_runner(state, event, registry=None, max_steps=16):
        return AgentRunResult(state=state, terminal=TerminalState.MISSING_INFO)

    class FakeUser:
        id = "fake-uuid"
    async def _fake_get_user(db, anon_id):
        return FakeUser()

    monkeypatch.setattr("app.api.conversation.run_agent_event", fake_runner)
    monkeypatch.setattr("app.api.conversation.get_or_create_anonymous_user", _fake_get_user)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/finish",
            json={
                "state": {
                    "messages": [{"role": "user", "content": "test"}],
                    "conversation_round": 1,
                    "answers": {},
                },
                "anonymous_user_id": "test-missing-info-user-000",
            },
        )
    assert resp.status_code == 400
    assert "信息不足" in resp.text


async def test_finish_unsupported_branch_returns_400(monkeypatch):
    """inexperienced 分支返回 400，不评分。"""
    from app.schemas.agent_protocol import AgentRunResult, TerminalState

    async def fake_runner(state, event, registry=None, max_steps=16):
        return AgentRunResult(state=state, terminal=TerminalState.UNSUPPORTED_BRANCH)

    class FakeUser:
        id = "fake-uuid"
    async def _fake_get_user(db, anon_id):
        return FakeUser()

    monkeypatch.setattr("app.api.conversation.run_agent_event", fake_runner)
    monkeypatch.setattr("app.api.conversation.get_or_create_anonymous_user", _fake_get_user)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/finish",
            json={
                "state": {
                    "messages": [{"role": "user", "content": "test"}],
                    "conversation_round": 1,
                    "answers": {"Q5": ["D"]},
                },
                "anonymous_user_id": "test-unsupported-user-000",
            },
        )
    assert resp.status_code == 400


# ── 空对话 finish 拒绝 ──────────────────────────────────────────

async def test_finish_empty_conversation_returns_400():
    """无 user 消息直接 finish 应拒绝"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/finish",
            json={
                "state": {"messages": [], "conversation_round": 0, "answers": {}},
            },
        )
    assert resp.status_code == 400
    assert "不足" in resp.text


# ── 对话无轮次上限 ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_continue_after_eight_rounds_still_allowed(monkeypatch):
    from app.agent.state_machine import append_assistant_message, append_user_message
    from app.schemas.agent_protocol import AgentRunResult, TerminalState

    async def fake_run_agent_event(state, event, registry=None, max_steps=16):
        new_state = append_user_message(state, event.message)
        new_state = append_assistant_message(new_state, "继续补充问题")
        return AgentRunResult(
            state=new_state,
            terminal=TerminalState.AWAITING_USER,
            response={"assistant_message": "继续补充问题"},
        )

    monkeypatch.setattr("app.api.conversation.run_agent_event", fake_run_agent_event)
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


# ── continue failed terminal ─────────────────────────────────────

@pytest.mark.asyncio
async def test_continue_failed_terminal_returns_500(monkeypatch):
    from app.schemas.agent_protocol import AgentRunResult, TerminalState

    async def fake_runner(state, event, registry=None, max_steps=16):
        return AgentRunResult(state=state, terminal=TerminalState.FAILED, response=None)

    monkeypatch.setattr("app.api.conversation.run_agent_event", fake_runner)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/continue",
            json={
                "state": {
                    "messages": [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好"}],
                    "conversation_round": 1,
                    "answers": {},
                },
                "message": "test",
            },
        )
    assert resp.status_code == 500
    text = resp.text
    assert "AI 暂时不可用" in text
    for word in FORBIDDEN_IN_RESPONSE:
        assert word not in text, f"响应泄露了: {word}"


@pytest.mark.asyncio
async def test_continue_missing_assistant_message_returns_500(monkeypatch):
    from app.schemas.agent_protocol import AgentRunResult, TerminalState

    async def fake_runner(state, event, registry=None, max_steps=16):
        return AgentRunResult(state=state, terminal=TerminalState.AWAITING_USER, response={})

    monkeypatch.setattr("app.api.conversation.run_agent_event", fake_runner)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/continue",
            json={
                "state": {
                    "messages": [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好"}],
                    "conversation_round": 1,
                    "answers": {},
                },
                "message": "test",
            },
        )
    assert resp.status_code == 500


# ── wechat_qr_url ──────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.asyncio
async def test_finish_returns_wechat_qr_url_when_configured(monkeypatch):
    """已完成的 finish 返回 wechat_qr_url（mock runner 避免真实 AI）。"""
    await _skip_if_postgres_unreachable()
    from app.agent.state_machine import append_user_message
    from app.schemas.agent_protocol import AgentRunResult, TerminalState

    async def fake_runner(state, event, registry=None, max_steps=16):
        state = state.model_copy(deep=True)
        state.scoring_result = _fake_light_scoring()
        state.user_report = _fake_light_user_report()
        state.lead_report = _fake_light_lead_report()
        state.status = "completed"
        state.used_template_report = False
        return AgentRunResult(state=state, terminal=TerminalState.COMPLETED)

    monkeypatch.setattr("app.api.conversation.run_agent_event", fake_runner)

    settings = get_settings()
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


# ── AgentEvent-only 架构 ────────────────────────────────────────

@pytest.mark.asyncio
async def test_conversation_continue_uses_agent_event_only(monkeypatch):
    """API 层只传 AgentEvent，不直接调 extraction/dialogue。"""
    from app.schemas.agent_protocol import AgentRunResult, TerminalState

    captured_event = None

    async def fake_runner(state, event, registry=None, max_steps=16):
        nonlocal captured_event
        captured_event = event
        state = state.model_copy(deep=True)
        from app.agent.state_machine import append_assistant_message
        state = append_assistant_message(state, "好的，继续。")
        return AgentRunResult(
            state=state, terminal=TerminalState.AWAITING_USER,
            response={"assistant_message": "好的，继续。"},
        )

    monkeypatch.setattr("app.api.conversation.run_agent_event", fake_runner)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/continue",
            json={
                "state": {"messages": [{"role": "user", "content": "你好"}] * 2, "conversation_round": 1, "answers": {}},
                "message": "test",
            },
        )
    assert resp.status_code == 200
    assert captured_event is not None
    assert captured_event.type == "user_message"
    assert captured_event.message == "test"


@pytest.mark.asyncio
async def test_finish_uses_agent_event_only(monkeypatch):
    """API 层只传 finish_requested 事件。mock DB 调用，不连真实 PostgreSQL。"""
    from app.schemas.agent_protocol import AgentRunResult, TerminalState

    captured_event = None

    async def fake_runner(state, event, registry=None, max_steps=16):
        nonlocal captured_event
        captured_event = event
        state = state.model_copy(deep=True)
        state.scoring_result = _fake_light_scoring()
        state.user_report = _fake_light_user_report()
        state.lead_report = _fake_light_lead_report()
        state.status = "completed"
        return AgentRunResult(state=state, terminal=TerminalState.COMPLETED)

    async def _fake_get_or_create_user(db, anon_id):
        class FakeUser:
            id = "fake-user-uuid-12345678"
        return FakeUser()

    async def _fake_save_assessment(db, state, user_id=None):
        class FakeAssessment:
            id = "fake-assessment-uuid-12345678"
        return FakeAssessment()

    monkeypatch.setattr("app.api.conversation.run_agent_event", fake_runner)
    monkeypatch.setattr("app.api.conversation.get_or_create_anonymous_user", _fake_get_or_create_user)
    monkeypatch.setattr("app.api.conversation.save_completed_assessment", _fake_save_assessment)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/finish",
            json={
                "state": {"messages": [{"role": "user", "content": "test"}], "conversation_round": 1, "answers": {}},
                "anonymous_user_id": "test-agent-event-user-000",
            },
        )
    assert resp.status_code == 200
    assert captured_event is not None
    assert captured_event.type == "finish_requested"


@pytest.mark.asyncio
async def test_finish_missing_info_does_not_save_assessment(monkeypatch):
    """MISSING_INFO → 400，不写 DB。"""
    from app.schemas.agent_protocol import AgentRunResult, TerminalState

    async def fake_runner(state, event, registry=None, max_steps=16):
        return AgentRunResult(state=state, terminal=TerminalState.MISSING_INFO)

    class FakeUser:
        id = "fake-uuid"
    async def _fake_get_user(db, anon_id):
        return FakeUser()

    monkeypatch.setattr("app.api.conversation.run_agent_event", fake_runner)
    monkeypatch.setattr("app.api.conversation.get_or_create_anonymous_user", _fake_get_user)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/finish",
            json={
                "state": {"messages": [{"role": "user", "content": "test"}], "conversation_round": 1, "answers": {}},
                "anonymous_user_id": "test-no-save-user-000",
            },
        )
    assert resp.status_code == 400
    assert "信息不足" in resp.text


@pytest.mark.asyncio
async def test_finish_failed_terminal_returns_500(monkeypatch):
    """runner 返回 FAILED → 500 安全文案。"""
    from app.schemas.agent_protocol import AgentRunResult, TerminalState

    async def fake_runner(state, event, registry=None, max_steps=16):
        return AgentRunResult(state=state, terminal=TerminalState.FAILED)

    class FakeUser:
        id = "fake-uuid"
    async def _fake_get_user(db, anon_id):
        return FakeUser()

    monkeypatch.setattr("app.api.conversation.run_agent_event", fake_runner)
    monkeypatch.setattr("app.api.conversation.get_or_create_anonymous_user", _fake_get_user)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/finish",
            json={
                "state": {"messages": [{"role": "user", "content": "test"}], "conversation_round": 1, "answers": {}},
                "anonymous_user_id": "test-fail-user-000",
            },
        )
    assert resp.status_code == 500
    for word in FORBIDDEN_IN_RESPONSE:
        assert word not in resp.text, f"响应泄露了: {word}"


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

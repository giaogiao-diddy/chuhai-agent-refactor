import json

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    yield
    app.dependency_overrides.clear()


# ── 空白消息 ──

async def test_continue_stream_blank_message_returns_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/continue-stream",
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


async def test_stream_response_does_not_accept_get():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/conversation/continue-stream")
    assert resp.status_code in (404, 405)


# ── 错误路径 ──

async def test_continue_stream_reasoning_only_returns_safe_error(monkeypatch):
    """stream 只有 reasoning 无 content → error，不泄露 reasoning_content。"""

    class _FakeReasoningOnlyClient:
        async def stream_chat(self, *args, **kwargs):
            if False:
                yield  # empty — 模拟模型只输出 reasoning 没有 content

    _patch_no_ai_extraction(monkeypatch)
    monkeypatch.setattr("app.agent.runner.DeepSeekClient", lambda: _FakeReasoningOnlyClient())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/continue-stream",
            json={
                "state": {
                    "messages": [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好"}],
                    "conversation_round": 1,
                    "answers": {},
                },
                "message": "test",
            },
        )
    assert resp.status_code == 200
    text = (await resp.aread()).decode()
    assert '"type": "error"' in text
    assert '"type": "done"' not in text
    assert "AI 暂时不可用" in text
    assert "reasoning_content" not in text


# ── 错误路径 ──

async def _fake_extract(*args, **kwargs):
    from app.schemas.extraction import ExtractionResult
    return ExtractionResult()


def _patch_no_ai_extraction(monkeypatch):
    monkeypatch.setattr("app.agent.extraction.extract_from_messages", _fake_extract)


class _FakeStreamFailClient:
    """stream_chat 抛异常 → runner 进入 error 分支。"""
    async def stream_chat(self, *args, **kwargs):
        raise RuntimeError("模拟 stream 失败")
        yield


class _FakeEmptyStreamClient:
    """stream_chat 返回空流 → runner 进入 error 分支。"""
    async def stream_chat(self, *args, **kwargs):
        if False:
            yield "never"


class _FakeSuccessStreamClient:
    """stream_chat 正常返回一个 chunk。"""
    async def stream_chat(self, *args, **kwargs):
        yield "继续提问"


async def test_continue_stream_error_yields_sse_error(monkeypatch):
    """stream 失败 → SSE error + 安全文案, 不发送 done。"""
    _patch_no_ai_extraction(monkeypatch)
    monkeypatch.setattr("app.agent.runner.DeepSeekClient", lambda: _FakeStreamFailClient())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/continue-stream",
            json={
                "state": {
                    "messages": [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好"}],
                    "conversation_round": 1,
                    "answers": {},
                },
                "message": "test",
            },
        )
    assert resp.status_code == 200
    text = (await resp.aread()).decode()
    assert '"type": "error"' in text
    assert '"type": "done"' not in text
    assert '"state"' in text
    assert "模拟" not in text
    assert "AI 暂时不可用" in text


async def test_continue_stream_empty_content_yields_sse_error(monkeypatch):
    """空流 → error + state, 不发送 done。"""
    _patch_no_ai_extraction(monkeypatch)
    monkeypatch.setattr("app.agent.runner.DeepSeekClient", lambda: _FakeEmptyStreamClient())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/continue-stream",
            json={
                "state": {
                    "messages": [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好"}],
                    "conversation_round": 1,
                    "answers": {},
                },
                "message": "test",
            },
        )
    assert resp.status_code == 200
    text = (await resp.aread()).decode()
    assert '"type": "error"' in text
    assert '"type": "done"' not in text
    assert '"state"' in text
    assert "AI 暂时不可用" in text


async def test_continue_stream_client_init_error_yields_safe_sse_error(monkeypatch):
    """DeepSeekClient 构造失败 → 不泄露原始异常。"""
    _patch_no_ai_extraction(monkeypatch)
    def _fail_init(*a, **kw):
        raise RuntimeError("模拟 init 失败 sales_followup 顾问备注")

    monkeypatch.setattr("app.agent.runner.DeepSeekClient", _fail_init)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/continue-stream",
            json={
                "state": {
                    "messages": [{"role": "user", "content": "你好"}, {"role": "assistant", "content": "你好"}],
                    "conversation_round": 1,
                    "answers": {},
                },
                "message": "test",
            },
        )
    assert resp.status_code == 200
    text = (await resp.aread()).decode()
    assert '"type": "error"' in text
    assert "AI 暂时不可用" in text
    assert "模拟" not in text
    assert "sales_followup" not in text
    assert "顾问备注" not in text


# ── AgentEvent-only ──

async def test_continue_stream_uses_runner_stream_only(monkeypatch):
    """API 层只转发 runner stream event，不直接调 DeepSeek。"""
    async def _fake_stream(state, event, registry=None):
        yield {"type": "delta", "content": "test"}
        from app.schemas.conversation import ConversationClientState
        cc = ConversationClientState.from_agent_state(state)
        yield {"type": "done", "state": cc.model_dump()}

    monkeypatch.setattr("app.api.conversation.run_agent_event_stream", _fake_stream)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/continue-stream",
            json={
                "state": {"messages": [{"role": "user", "content": "hi"}], "conversation_round": 0, "answers": {}},
                "message": "test",
            },
        )
    text = (await resp.aread()).decode()
    assert '"type": "delta"' in text
    assert '"type": "done"' in text


# ── 流式：轮次无上限 + 历史不丢失 ──

@pytest.mark.asyncio
async def test_continue_stream_after_eight_rounds_still_allowed(monkeypatch):
    _patch_no_ai_extraction(monkeypatch)
    monkeypatch.setattr("app.agent.runner.DeepSeekClient", lambda: _FakeSuccessStreamClient())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/continue-stream",
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
    text = (await resp.aread()).decode()
    assert '"type": "done"' in text
    assert "继续提问" in text


@pytest.mark.asyncio
async def test_continue_stream_preserves_full_message_history(monkeypatch):
    _patch_no_ai_extraction(monkeypatch)
    monkeypatch.setattr("app.agent.runner.DeepSeekClient", lambda: _FakeSuccessStreamClient())

    messages = []
    for i in range(14):
        messages.append({"role": "user", "content": f"用户消息 {i}"})
        messages.append({"role": "assistant", "content": f"顾问消息 {i}"})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/continue-stream",
            json={
                "state": {"messages": messages, "conversation_round": 14, "answers": {}},
                "message": "继续",
            },
        )
    text = (await resp.aread()).decode()
    lines = [l for l in text.split("\n") if l.startswith("data: ")]
    done = json.loads(lines[-1][6:])
    assert done["state"]["messages"][0]["content"] == "用户消息 0"
    assert len(done["state"]["messages"]) == len(messages) + 2


# ── 真实流式 ──

FORBIDDEN_IN_STREAM = [
    "reasoning_content", "lead_report", "raw_report",
    "sales_followup", "consultant_notes", "lead_score", "lead_priority",
    "scoring_result", "audit_result", "report_error", "scoring_error",
    "销售话术", "顾问跟进", "线索优先级", "顾问备注",
]


@pytest.mark.ai
@pytest.mark.asyncio
async def test_continue_stream_real_deepseek():
    from config import get_settings
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY:
        pytest.skip("DEEPSEEK_API_KEY 未配置")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/conversation/continue-stream",
            json={
                "state": {
                    "messages": [{"role": "user", "content": "你们是做什么的？"}, {"role": "assistant", "content": "我们是出海诊断顾问"}],
                    "conversation_round": 1,
                    "answers": {},
                },
                "message": "我们是一家做健身器材的源头工厂，有少量东南亚客户",
            },
        )
    assert resp.status_code == 200
    text = (await resp.aread()).decode()

    assert '"type": "delta"' in text
    assert '"type": "done"' in text

    lines = [l for l in text.split("\n") if l.startswith("data: ")]
    done_data = None
    for line in lines:
        data = json.loads(line[6:])
        if data.get("type") == "done":
            done_data = data
    assert done_data is not None, "未收到 done event"
    st = done_data["state"]
    assert st["conversation_round"] == 2
    assert len(st["messages"]) >= 3

    for word in FORBIDDEN_IN_STREAM:
        assert word not in text, f"流式响应泄露了: {word}"

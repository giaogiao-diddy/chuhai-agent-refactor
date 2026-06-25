import json

import pytest
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    yield
    app.dependency_overrides.clear()


# ── 空白消息 ────────────────────────────────────────────────────

async def test_continue_stream_blank_message_returns_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = await client.post("/conversation/start")
        state = start.json()["state"]
        resp = await client.post(
            "/conversation/continue-stream",
            json={"state": state, "message": "   "},
        )
    assert resp.status_code == 422


async def test_stream_response_does_not_accept_get():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/conversation/continue-stream")
    assert resp.status_code in (404, 405)


# ── 错误路径 ────────────────────────────────────────────────────

async def test_continue_stream_error_yields_sse_error(monkeypatch):
    async def _fail(*a, **kw):
        raise RuntimeError("模拟 stream 失败")
        yield  # noqa

    monkeypatch.setattr("app.services.deepseek_client.DeepSeekClient.stream_chat", _fail)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = await client.post("/conversation/start")
        state = start.json()["state"]
        resp = await client.post(
            "/conversation/continue-stream",
            json={"state": state, "message": "test"},
        )
    text = await resp.aread()
    text = text.decode()
    assert '"type": "error"' in text
    assert "模拟" not in text  # 不泄露原始异常
    # 断言 ai_failure_count >= 1
    lines = [l for l in text.split("\n") if l.startswith("data: ")]
    last = json.loads(lines[-1][6:])
    assert last["state"]["ai_failure_count"] >= 1


async def test_continue_stream_empty_content_yields_sse_error(monkeypatch):
    """空流不返回 done，返回 error"""
    async def _empty_stream(*args, **kwargs):
        if False:
            yield "never"

    monkeypatch.setattr("app.services.deepseek_client.DeepSeekClient.stream_chat", _empty_stream)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = await client.post("/conversation/start")
        state = start.json()["state"]
        resp = await client.post(
            "/conversation/continue-stream",
            json={"state": state, "message": "test"},
        )
    assert resp.status_code == 200
    text = await resp.aread()
    text = text.decode()
    assert '"type": "error"' in text
    assert '"type": "done"' not in text
    assert "AI 暂时不可用" in text
    assert "模型未返回最终 content" not in text

    lines = [l for l in text.split("\n") if l.startswith("data: ")]
    last = json.loads(lines[-1][6:])
    assert last["state"]["ai_failure_count"] >= 1


async def test_continue_stream_client_init_error_yields_safe_sse_error(monkeypatch):
    """DeepSeekClient 构造失败也不泄露原始异常"""
    def _fail_init(*a, **kw):
        raise RuntimeError("模拟 init 失败 sales_followup 顾问备注")

    monkeypatch.setattr("app.api.conversation.DeepSeekClient", _fail_init)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = await client.post("/conversation/start")
        state = start.json()["state"]
        resp = await client.post(
            "/conversation/continue-stream",
            json={"state": state, "message": "test"},
        )
    assert resp.status_code == 200
    text = await resp.aread()
    text = text.decode()
    assert '"type": "error"' in text
    assert "AI 暂时不可用" in text
    assert "模拟" not in text
    assert "sales_followup" not in text
    assert "顾问备注" not in text

    lines = [l for l in text.split("\n") if l.startswith("data: ")]
    last = json.loads(lines[-1][6:])
    assert last["state"]["ai_failure_count"] >= 1


# ── 真实流式 ────────────────────────────────────────────────────

FORBIDDEN_IN_STREAM = [
    "reasoning_content", "lead_report", "raw_report",
    "sales_followup", "consultant_notes", "lead_score", "lead_priority",
    "scoring_result", "audit_result", "report_error", "scoring_error",
    "销售话术", "顾问跟进", "线索优先级", "顾问备注",
]


@pytest.mark.ai
@pytest.mark.integration
async def test_continue_stream_real_deepseek():
    from config import get_settings
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY:
        pytest.skip("DEEPSEEK_API_KEY 未配置")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = await client.post("/conversation/start")
        state = start.json()["state"]

        resp = await client.post(
            "/conversation/continue-stream",
            json={"state": state, "message": "我们是一家做健身器材的源头工厂，有少量东南亚客户。"},
        )
    assert resp.status_code == 200
    text = await resp.aread()
    text = text.decode()

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
    assert st["conversation_round"] == 1
    assert len(st["messages"]) >= 3

    for word in FORBIDDEN_IN_STREAM:
        assert word not in text, f"流式响应泄露了: {word}"

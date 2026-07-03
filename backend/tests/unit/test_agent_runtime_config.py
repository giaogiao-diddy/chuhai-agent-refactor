import pytest
from pydantic import BaseModel

from app.agent.runner import run_agent_event
from app.agent.tools.external.dialogue import (
    DialogueDeepSeekInput,
    dialogue_deepseek_handler,
)
from app.agent.tools.external.report_generation import (
    ReportGenerateInput,
    report_generate_deepseek_handler,
)
from app.schemas.agent_protocol import AgentEvent, TerminalState
from app.schemas.agent_state import AgentState
from app.schemas.llm import LLMMessage
from app.schemas.report import RawAIReport
from app.schemas.scoring import DimensionScore, ScoringResult


# ── helpers ──

def _fake_scoring_result():
    return ScoringResult(
        feasibility_score=65, lead_score=55, display_score=65,
        tag="基础具备型", tag_explanation="x", preliminary_judgment="x",
        dimension_scores=[DimensionScore(name="d", raw_score=10, max_score=20, normalized_score=50)],
        strengths=["s"], risks=["r"], lead_priority="P1",
    )


# ── MAX_AGENT_STEPS ──

@pytest.mark.asyncio
async def test_run_agent_event_uses_configured_max_steps(monkeypatch):
    """max_steps=None 时使用配置值。"""
    class FakeSettings:
        MAX_AGENT_STEPS = 0

    monkeypatch.setattr("app.agent.runner._default_max_agent_steps", lambda: 0)

    state = AgentState()
    result = await run_agent_event(
        state,
        AgentEvent(type="user_message", message="hello"),
        max_steps=None,
    )
    assert result.terminal == TerminalState.MAX_STEPS_EXCEEDED


# ── dialogue config ──

@pytest.mark.asyncio
async def test_dialogue_tool_uses_configured_tokens_temperature_and_history_window(monkeypatch):
    """dialogue.deepseek 使用配置的 max_tokens / temperature / history window。"""
    class FakeSettings:
        DIALOGUE_MAX_TOKENS = 123
        DIALOGUE_TEMPERATURE = 0.7
        DIALOGUE_HISTORY_WINDOW = 2

    monkeypatch.setattr(
        "app.agent.tools.external.dialogue.get_settings",
        lambda: FakeSettings(),
    )

    recorded = {}
    class FakeDeepSeekClient:
        async def chat(self, messages, max_tokens, temperature):
            recorded["max_tokens"] = max_tokens
            recorded["temperature"] = temperature
            recorded["msg_count"] = len(messages)
            from app.schemas.llm import LLMResponse
            return LLMResponse(content="ok")

    monkeypatch.setattr(
        "app.agent.tools.external.dialogue.DeepSeekClient",
        lambda: FakeDeepSeekClient(),
    )

    from app.schemas.agent_state import AgentMessage
    messages = [
        AgentMessage(role="user", content=f"msg{i}")
        for i in range(10)
    ]
    inp = DialogueDeepSeekInput(messages=messages)
    from app.agent.tools.base import ToolContext
    result = await dialogue_deepseek_handler(inp, ToolContext())

    assert result.error is None
    assert recorded["max_tokens"] == 123
    assert recorded["temperature"] == 0.7
    # system prompt + 2 history messages = 3
    assert recorded["msg_count"] == 3


# ── report generation config ──

@pytest.mark.asyncio
async def test_report_generate_uses_configured_report_tokens(monkeypatch):
    """report.generate.deepseek 使用配置的 REPORT_MAX_TOKENS / REPORT_ESCALATED_MAX_TOKENS。"""
    class FakeSettings:
        REPORT_MAX_TOKENS = 3456
        REPORT_ESCALATED_MAX_TOKENS = 7890

    monkeypatch.setattr(
        "app.agent.tools.external.report_generation.get_settings",
        lambda: FakeSettings(),
    )

    recorded = {}
    class FakeDeepSeekClient:
        async def chat_json(self, messages, response_model, max_tokens, temperature):
            recorded["max_tokens"] = max_tokens
            return RawAIReport(
                summary_conclusion="s", positioning_assessment="p", content_assessment="c",
                conversion_assessment="v", recommended_path="r", risk_reminder="rr",
                action_plan_30days=["1","2","3","4"], consultant_guide="g",
                sales_followup="sf", consultant_notes="cn",
            )

    monkeypatch.setattr(
        "app.agent.tools.external.report_generation.DeepSeekClient",
        lambda: FakeDeepSeekClient(),
    )

    state = AgentState(answers={"Q5": ["A"]}, branch="experienced")
    state.scoring_result = _fake_scoring_result()

    # escalated=False, audit_feedback triggers _build_feedback_prompt path
    from app.agent.tools.base import ToolContext
    inp = ReportGenerateInput(state=state, rag_context=[], audit_feedback=["test"], escalated=False)
    result = await report_generate_deepseek_handler(inp, ToolContext())
    assert result.error is None
    assert recorded["max_tokens"] == 3456

    recorded.clear()
    inp2 = ReportGenerateInput(state=state, rag_context=[], audit_feedback=[], escalated=True)
    result2 = await report_generate_deepseek_handler(inp2, ToolContext())
    assert result2.error is None
    assert recorded["max_tokens"] == 7890


# ── reporting.py generate_raw_report ──

@pytest.mark.asyncio
async def test_generate_raw_report_uses_configured_report_tokens(monkeypatch):
    """generate_raw_report() 使用配置的 REPORT_MAX_TOKENS。"""
    class FakeSettings:
        REPORT_MAX_TOKENS = 3456

    monkeypatch.setattr(
        "app.agent.reporting.get_settings",
        lambda: FakeSettings(),
    )

    recorded = {}
    class FakeDeepSeekClient:
        async def chat_json(self, messages, response_model, max_tokens, temperature):
            recorded["max_tokens"] = max_tokens
            return RawAIReport(
                summary_conclusion="s", positioning_assessment="p", content_assessment="c",
                conversion_assessment="v", recommended_path="r", risk_reminder="rr",
                action_plan_30days=["1","2","3","4"], consultant_guide="g",
                sales_followup="sf", consultant_notes="cn",
            )

    monkeypatch.setattr(
        "app.agent.reporting.DeepSeekClient",
        lambda: FakeDeepSeekClient(),
    )

    from app.agent.reporting import generate_raw_report
    state = AgentState(answers={"Q5": ["A"]}, branch="experienced")
    state.scoring_result = _fake_scoring_result()

    result = await generate_raw_report(state, rag_context=None)
    assert recorded["max_tokens"] == 3456


# ── streaming config ──

@pytest.mark.asyncio
async def test_streaming_uses_configured_dialogue_values(monkeypatch):
    """streaming 使用 DIALOGUE 配置。"""
    class FakeSettings:
        DIALOGUE_MAX_TOKENS = 111
        DIALOGUE_TEMPERATURE = 0.9
        DIALOGUE_HISTORY_WINDOW = 3

    monkeypatch.setattr(
        "app.agent.runner.get_settings",
        lambda: FakeSettings(),
    )

    recorded = {}
    class FakeDeepSeekClient:
        async def stream_chat(self, messages, max_tokens, temperature):
            recorded["max_tokens"] = max_tokens
            recorded["temperature"] = temperature
            recorded["msg_count"] = len(messages)
            yield "ok"

    monkeypatch.setattr(
        "app.agent.runner.DeepSeekClient",
        lambda: FakeDeepSeekClient(),
    )

    async def _fake_extract(inp, ctx):
        from app.agent.tools.base import ToolResult
        from app.schemas.extraction import ExtractionResult
        return ToolResult(data=ExtractionResult())

    monkeypatch.setattr("app.agent.extraction.extract_from_messages", _fake_extract)

    from app.schemas.agent_state import AgentMessage
    state = AgentState(answers={}, branch=None)
    state.messages = [
        AgentMessage(role="user", content=f"msg{i}")
        for i in range(10)
    ]

    from app.agent.runner import run_agent_event_stream
    events = []
    async for ev in run_agent_event_stream(
        state,
        AgentEvent(type="user_message", message="test"),
    ):
        events.append(ev)

    assert recorded["max_tokens"] == 111
    assert recorded["temperature"] == 0.9
    # system prompt + 3 history
    assert recorded["msg_count"] == 4


def test_dialogue_max_tokens_default_is_1024():
    from config import Settings
    s = Settings()
    assert s.DIALOGUE_MAX_TOKENS == 1024

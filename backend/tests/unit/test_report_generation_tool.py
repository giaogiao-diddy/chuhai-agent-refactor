import pytest

from app.agent.tools.base import ToolErrorCode
from app.agent.tools.external.report_generation import (
    ReportGenerateInput,
    report_generate_deepseek_handler,
)
from app.schemas.agent_state import AgentState
from app.schemas.report import RawAIReport
from app.schemas.scoring import DimensionScore, ScoringResult


def _fake_scoring_result():
    return ScoringResult(
        feasibility_score=65, lead_score=55, display_score=65,
        tag="基础具备型", tag_explanation="较完善",
        preliminary_judgment="适合出海",
        dimension_scores=[DimensionScore(name="d", raw_score=10, max_score=20, normalized_score=50)],
        strengths=["s"], risks=["r"], lead_priority="P1",
    )


def _fake_raw_report():
    return RawAIReport(
        summary_conclusion="s", positioning_assessment="p", content_assessment="c",
        conversion_assessment="v", recommended_path="r", risk_reminder="rr",
        action_plan_30days=["1","2","3","4"], consultant_guide="g",
        sales_followup="sf", consultant_notes="cn",
    )


@pytest.mark.asyncio
async def test_report_generate_escalated_without_feedback_uses_8000_tokens(monkeypatch):
    """escalated=True 且 audit_feedback=[] 时，max_tokens=8000 应生效。"""
    recorded_max_tokens = []

    class FakeDeepSeekClient:
        async def chat_json(self, messages, response_model, max_tokens, temperature):
            recorded_max_tokens.append(max_tokens)
            return _fake_raw_report()

    monkeypatch.setattr(
        "app.agent.tools.external.report_generation.DeepSeekClient",
        lambda: FakeDeepSeekClient(),
    )

    state = AgentState(answers={"Q5": ["A"]}, branch="experienced")
    state.scoring_result = _fake_scoring_result()

    inp = ReportGenerateInput(state=state, rag_context=[], audit_feedback=[], escalated=True)
    result = await report_generate_deepseek_handler(inp, None)

    assert result.error is None
    assert recorded_max_tokens == [8000], f"expected 8000, got {recorded_max_tokens}"


@pytest.mark.asyncio
async def test_chat_json_finish_reason_length_maps_to_length_exceeded(monkeypatch):
    """DeepSeekClient.chat_json 抛出 finish_reason=length ValueError → LENGTH_EXCEEDED。"""

    class FakeDeepSeekClient:
        async def chat_json(self, messages, response_model, max_tokens, temperature):
            raise ValueError("finish_reason=length: 模型输出被截断")

    monkeypatch.setattr(
        "app.agent.tools.external.report_generation.DeepSeekClient",
        lambda: FakeDeepSeekClient(),
    )

    state = AgentState(answers={"Q5": ["A"]}, branch="experienced")
    state.scoring_result = _fake_scoring_result()

    inp = ReportGenerateInput(state=state, rag_context=[], audit_feedback=["fix length issue"], escalated=False)
    result = await report_generate_deepseek_handler(inp, None)

    assert result.error is not None
    assert result.error.code == ToolErrorCode.LENGTH_EXCEEDED
    assert result.error.retryable is True

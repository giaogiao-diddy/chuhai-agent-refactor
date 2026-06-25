import pytest

from app.agent.graph import run_report_pipeline
from app.agent.nodes import score_node
from app.reports.guard import assert_user_report_safe
from app.schemas.agent_state import AgentState
from app.schemas.slots import SlotValue
from config import get_settings


@pytest.mark.ai
@pytest.mark.integration
async def test_generate_report_real_deepseek():
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY:
        pytest.skip("DEEPSEEK_API_KEY 未配置")

    state = AgentState(
        branch="experienced",
        slots={
            "industry": SlotValue(value="健身器材", confidence=0.9),
            "main_product": SlotValue(value="力量训练设备", confidence=0.9),
            "target_market": SlotValue(value="东南亚", confidence=0.8),
            "monthly_budget": SlotValue(value="2-5万", confidence=0.7),
            "consultation_intent": SlotValue(value="愿意先看报告再预约", confidence=0.75),
        },
        answers={
            "Q2a": ["A"], "Q2b": ["B"], "Q3a": ["B"], "Q3b": ["B"],
            "Q4": ["A"], "Q5": ["C"], "Q6": ["B", "C"], "Q7": ["C"],
        },
    )
    state = score_node(state)
    assert state.scoring_result is not None

    result = await run_report_pipeline(state)

    assert result.ai_failure_count == 0
    assert result.raw_report is not None
    assert result.user_report is not None
    assert result.lead_report is not None
    assert result.user_report.summary_conclusion
    assert len(result.user_report.action_plan_30days) == 4
    assert result.lead_report.sales_followup
    assert result.report_error is None
    assert_user_report_safe(result.user_report)

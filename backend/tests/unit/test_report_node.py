import asyncio

from app.agent.nodes import report_node
from app.schemas.agent_state import AgentState
from app.schemas.report import RawAIReport, LeadReport, UserReport
from app.schemas.scoring import DimensionScore, ScoringResult
from app.schemas.slots import SlotValue


def test_report_node_clears_old_reports_on_failure():
    scoring = ScoringResult(
        feasibility_score=50, lead_score=40, display_score=50,
        tag="基础具备型", tag_explanation="x", preliminary_judgment="x",
        dimension_scores=[
            DimensionScore(name="x", raw_score=10, max_score=20, normalized_score=50),
        ],
        strengths=["a"], risks=["b"], lead_priority="P2",
    )
    old_raw = RawAIReport(
        summary_conclusion="old", positioning_assessment="old",
        content_assessment="old", conversion_assessment="old",
        recommended_path="old", risk_reminder="old",
        action_plan_30days=["1","2","3","4"],
        consultant_guide="old", sales_followup="old", consultant_notes="old",
    )
    old_user = UserReport(
        feasibility_score=50, display_score=50, tag="a", tag_explanation="a",
        preliminary_judgment="a", strengths=["a"], risks=["a"],
        summary_conclusion="a", positioning_assessment="a",
        content_assessment="a", conversion_assessment="a",
        dimension_scores=[], recommended_path="a", risk_reminder="a",
        action_plan_30days=["1","2","3","4"], consultant_guide="a",
    )
    old_lead = LeadReport(
        lead_score=40, lead_priority="P2", tag="a",
        sales_followup="a", consultant_notes="a",
    )

    # scoring_result is None → must fail
    state = AgentState(
        scoring_result=None,
        raw_report=old_raw,
        user_report=old_user,
        lead_report=old_lead,
    )
    result = asyncio.run(report_node(state))

    assert result.report_error is not None
    assert "模板兜底" in result.report_error
    assert result.raw_report is not None
    assert result.user_report is not None
    assert result.lead_report is not None
    assert result.used_template_report is True

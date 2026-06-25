import pytest

from app.reports.splitter import split_report
from app.schemas.agent_state import AgentState
from app.schemas.report import RawAIReport, UserReport
from app.schemas.scoring import DimensionScore, ScoringResult
from app.schemas.slots import SlotValue


def _raw_report() -> RawAIReport:
    return RawAIReport(
        summary_conclusion="综合结论",
        positioning_assessment="定位分析",
        content_assessment="内容分析",
        conversion_assessment="转化分析",
        recommended_path="推荐路径",
        risk_reminder="风险提醒",
        action_plan_30days=["第一步", "第二步", "第三步", "第四步"],
        consultant_guide="顾问引导",
        sales_followup="销售话术",
        consultant_notes="顾问备注",
    )


def _state() -> AgentState:
    state = AgentState()
    state.scoring_result = ScoringResult(
        feasibility_score=65,
        lead_score=55,
        display_score=65,
        tag="基础具备型",
        tag_explanation="条件较完善",
        preliminary_judgment="适合出海",
        dimension_scores=[
            DimensionScore(name="enterprise_base_feasibility", raw_score=15, max_score=20, normalized_score=75),
        ],
        strengths=["优势A"],
        risks=["风险A"],
        lead_priority="P1",
    )
    state.slots.industry = SlotValue(value="健身器材", confidence=0.9)
    state.slots.main_product = SlotValue(value="力量训练设备", confidence=0.9)
    return state


def test_split_report_produces_bundle():
    bundle = split_report(_raw_report(), _state())
    assert bundle.raw_report is not None
    assert bundle.user_report is not None
    assert bundle.lead_report is not None


def test_user_report_excludes_forbidden_fields():
    bundle = split_report(_raw_report(), _state())
    ur = bundle.user_report.model_dump()
    forbidden = {"lead_score", "lead_priority", "sales_followup", "consultant_notes"}
    for key in forbidden:
        assert key not in ur


def test_lead_report_includes_sales_fields():
    bundle = split_report(_raw_report(), _state())
    assert bundle.lead_report.lead_score == 55
    assert bundle.lead_report.lead_priority == "P1"
    assert bundle.lead_report.sales_followup == "销售话术"


def test_action_plan_is_4_steps():
    bundle = split_report(_raw_report(), _state())
    assert len(bundle.user_report.action_plan_30days) == 4


def test_split_report_requires_scoring_result():
    state = AgentState()
    with pytest.raises(ValueError):
        split_report(_raw_report(), state)


def test_raw_ai_report_rejects_3_items():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        RawAIReport(
            summary_conclusion="x", positioning_assessment="x",
            content_assessment="x", conversion_assessment="x",
            recommended_path="x", risk_reminder="x",
            action_plan_30days=["a", "b", "c"],
            consultant_guide="x", sales_followup="x", consultant_notes="x",
        )


def test_raw_ai_report_rejects_5_items():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        RawAIReport(
            summary_conclusion="x", positioning_assessment="x",
            content_assessment="x", conversion_assessment="x",
            recommended_path="x", risk_reminder="x",
            action_plan_30days=["a", "b", "c", "d", "e"],
            consultant_guide="x", sales_followup="x", consultant_notes="x",
        )


def test_raw_ai_report_accepts_4_items():
    r = _raw_report()
    assert len(r.action_plan_30days) == 4


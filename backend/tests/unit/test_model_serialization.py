import pytest

from app.schemas.agent_state import AgentState
from app.schemas.audit import ReportAuditResult
from app.schemas.report import LeadReport, RawAIReport, UserReport
from app.schemas.scoring import DimensionScore, ScoringResult
from app.schemas.slots import SlotValue
from app.services.assessment_repository import _slots_to_dict, _validate_state


def test_slots_serialize_to_dict():
    state = AgentState()
    state.slots.industry = SlotValue(value="健身器材", confidence=0.9)
    state.slots.main_product = SlotValue(value="力量训练设备", confidence=0.85)
    d = _slots_to_dict(state.slots)
    assert d["industry"] == {"value": "健身器材", "confidence": 0.9}
    assert d["main_product"] == {"value": "力量训练设备", "confidence": 0.85}


def test_scoring_result_serializable():
    sr = ScoringResult(
        feasibility_score=50, lead_score=30, display_score=50,
        tag="基础具备型", tag_explanation="x", preliminary_judgment="x",
        dimension_scores=[DimensionScore(name="x", raw_score=10, max_score=20, normalized_score=50)],
        strengths=["a"], risks=["b"], lead_priority="P2",
    )
    d = sr.model_dump()
    assert isinstance(d, dict)
    assert d["feasibility_score"] == 50


def test_report_models_serializable():
    raw = RawAIReport(
        summary_conclusion="x", positioning_assessment="x",
        content_assessment="x", conversion_assessment="x",
        recommended_path="x", risk_reminder="x",
        action_plan_30days=["1","2","3","4"],
        consultant_guide="x", sales_followup="x", consultant_notes="x",
    )
    user = UserReport(
        feasibility_score=50, display_score=50, tag="x", tag_explanation="x",
        preliminary_judgment="x", strengths=["x"], risks=["x"],
        summary_conclusion="x", positioning_assessment="x",
        content_assessment="x", conversion_assessment="x",
        dimension_scores=[DimensionScore(name="x", raw_score=10, max_score=20, normalized_score=50)],
        recommended_path="x", risk_reminder="x",
        action_plan_30days=["1","2","3","4"], consultant_guide="x",
    )
    lead = LeadReport(
        lead_score=30, lead_priority="P2", tag="x",
        sales_followup="x", consultant_notes="x",
    )
    assert isinstance(raw.model_dump(), dict)
    assert isinstance(user.model_dump(), dict)
    assert isinstance(lead.model_dump(), dict)


def test_audit_result_serializable():
    ar = ReportAuditResult(passed=True, issues=[], rewrite_required=False, severity="pass")
    assert isinstance(ar.model_dump(), dict)


def test_validate_state_rejects_missing_reports():
    state = AgentState()
    with pytest.raises(ValueError, match="scoring_result"):
        _validate_state(state)


def test_assessment_validation_errors_is_list():
    from app.models import Assessment
    a = Assessment(validation_errors=["error 1", "error 2"])
    assert isinstance(a.validation_errors, list)
    assert a.validation_errors == ["error 1", "error 2"]

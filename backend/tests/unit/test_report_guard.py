import pytest

from app.reports.guard import FORBIDDEN_STRINGS, assert_user_report_safe
from app.schemas.report import UserReport
from app.schemas.scoring import DimensionScore


def _safe_user_report(**overrides) -> UserReport:
    data = dict(
        feasibility_score=50,
        display_score=50,
        tag="基础具备型",
        tag_explanation="条件较完善",
        preliminary_judgment="适合出海",
        strengths=["优势"],
        risks=["风险"],
        summary_conclusion="结论",
        positioning_assessment="定位",
        content_assessment="内容",
        conversion_assessment="转化",
        dimension_scores=[
            DimensionScore(name="x", raw_score=10, max_score=20, normalized_score=50),
        ],
        recommended_path="路径",
        risk_reminder="提醒",
        action_plan_30days=["1","2","3","4"],
        consultant_guide="引导",
    )
    data.update(overrides)
    return UserReport(**data)


def test_safe_report_passes():
    assert_user_report_safe(_safe_user_report())


def test_lead_score_in_content_fails():
    report = _safe_user_report(summary_conclusion="此用户 lead_score 较高")
    with pytest.raises(ValueError, match="lead_score"):
        assert_user_report_safe(report)


def test_sales_followup_phrases_fail():
    report = _safe_user_report(risk_reminder="根据销售话术和顾问跟进建议")
    for word in ("销售话术", "顾问跟进"):
        if word in str(report.model_dump()):
            with pytest.raises(ValueError):
                assert_user_report_safe(report)
            return
    pytest.fail("测试数据应包含禁止词")

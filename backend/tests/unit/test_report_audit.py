import pytest

from app.agent.audit import validate_report_bundle_locally
from app.schemas.audit import ReportAuditResult
from app.schemas.report import LeadReport, RawAIReport, ReportBundle, UserReport
from app.schemas.scoring import DimensionScore


def _bundle(**overrides) -> ReportBundle:
    raw = RawAIReport(
        summary_conclusion="结论", positioning_assessment="定位",
        content_assessment="内容", conversion_assessment="转化",
        recommended_path="路径", risk_reminder="提醒",
        action_plan_30days=["1","2","3","4"],
        consultant_guide="引导", sales_followup="话术", consultant_notes="备注",
    )
    user = UserReport(
        feasibility_score=50, display_score=50, tag="x", tag_explanation="x",
        preliminary_judgment="x", strengths=["x"], risks=["x"],
        summary_conclusion="结论", positioning_assessment="定位",
        content_assessment="内容", conversion_assessment="转化",
        dimension_scores=[DimensionScore(name="x", raw_score=10, max_score=20, normalized_score=50)],
        recommended_path="路径", risk_reminder="提醒",
        action_plan_30days=["1","2","3","4"], consultant_guide="引导",
    )
    lead = LeadReport(
        lead_score=40, lead_priority="P2", tag="x",
        sales_followup="话术", consultant_notes="备注",
    )
    return ReportBundle(raw_report=raw, user_report=user, lead_report=lead)


def test_safe_bundle_passes():
    r = validate_report_bundle_locally(_bundle())
    assert r.passed
    assert r.severity == "pass"


def test_forbidden_word_in_user_report_fails():
    bundle = _bundle()
    bundle.user_report.summary_conclusion = "这是销售话术建议"
    r = validate_report_bundle_locally(bundle)
    assert not r.passed
    assert r.severity == "fail"


def test_action_plan_not_4_fails():
    bundle = _bundle()
    bundle.user_report.action_plan_30days = ["1","2","3"]
    r = validate_report_bundle_locally(bundle)
    assert not r.passed


def test_empty_sales_followup_fails():
    bundle = _bundle()
    bundle.lead_report.sales_followup = ""
    r = validate_report_bundle_locally(bundle)
    assert not r.passed


def test_report_audit_result_severity_literal():
    r = ReportAuditResult(passed=True, issues=[], rewrite_required=False, severity="pass")
    assert r.severity == "pass"
    with pytest.raises(Exception):
        ReportAuditResult(passed=True, issues=[], rewrite_required=False, severity="invalid")


def test_audit_passed_with_fail_severity_rejected():
    with pytest.raises(ValueError):
        ReportAuditResult(passed=True, rewrite_required=False, issues=[], severity="fail")


def test_audit_passed_with_rewrite_required_rejected():
    with pytest.raises(ValueError):
        ReportAuditResult(passed=True, rewrite_required=True, issues=[], severity="pass")


def test_audit_failed_no_rewrite_rejected():
    with pytest.raises(ValueError):
        ReportAuditResult(passed=False, rewrite_required=False, issues=["x"], severity="fail")

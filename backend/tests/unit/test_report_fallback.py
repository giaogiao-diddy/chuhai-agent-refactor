import asyncio

from app.agent.nodes import report_node
from app.reports.guard import assert_user_report_safe
from app.reports.splitter import split_report
from app.reports.template_report import build_template_raw_report
from app.schemas.agent_state import AgentState
from app.schemas.scoring import DimensionScore, ScoringResult
from app.schemas.slots import SlotValue


def test_template_raw_report_has_4_action_plans():
    state = AgentState()
    raw = build_template_raw_report(state)
    assert len(raw.action_plan_30days) == 4


def test_template_report_splits_and_passes_guard():
    state = AgentState()
    state.scoring_result = ScoringResult(
        feasibility_score=30, lead_score=20, display_score=30,
        tag="轻量试探型", tag_explanation="x", preliminary_judgment="x",
        dimension_scores=[
            DimensionScore(name="x", raw_score=5, max_score=20, normalized_score=25),
        ],
        strengths=["x"], risks=["x"], lead_priority="P3",
    )
    raw = build_template_raw_report(state)
    bundle = split_report(raw, state)
    assert_user_report_safe(bundle.user_report)


def test_report_node_fallback_when_no_scoring_result():
    state = AgentState()
    result = asyncio.run(report_node(state))
    assert result.status == "completed"
    assert result.used_template_report is True
    assert result.report_error is not None
    assert result.raw_report is not None
    assert result.user_report is not None
    assert result.lead_report is not None


def test_report_node_fallback_after_repeated_failures(monkeypatch):
    async def _fail(*args, **kwargs):
        raise RuntimeError("模拟失败")

    monkeypatch.setattr("app.agent.nodes.generate_raw_report", _fail)

    state = AgentState()
    state.scoring_result = ScoringResult(
        feasibility_score=30, lead_score=20, display_score=30,
        tag="轻量试探型", tag_explanation="x", preliminary_judgment="x",
        dimension_scores=[
            DimensionScore(name="x", raw_score=5, max_score=20, normalized_score=25),
        ],
        strengths=["x"], risks=["x"], lead_priority="P3",
    )
    result = asyncio.run(report_node(state))
    assert result.status == "completed"
    assert result.used_template_report is True
    assert result.raw_report is not None
    assert result.report_error is not None


def test_template_fallback_sets_warning_audit_result(monkeypatch):
    """模板兜底成功时 audit_result.severity == 'warning'，不是旧 fail 残留"""
    async def _fail_audit(*args, **kwargs):
        from app.schemas.audit import ReportAuditResult
        return ReportAuditResult(
            passed=False, issues=["审计失败"], rewrite_required=True, severity="fail",
        )
    monkeypatch.setattr("app.agent.nodes.audit_report_bundle", _fail_audit)

    state = AgentState()
    state.scoring_result = ScoringResult(
        feasibility_score=30, lead_score=20, display_score=30,
        tag="轻量试探型", tag_explanation="x", preliminary_judgment="x",
        dimension_scores=[
            DimensionScore(name="x", raw_score=5, max_score=20, normalized_score=25),
        ],
        strengths=["x"], risks=["x"], lead_priority="P3",
    )
    state.max_report_retries = 0  # 尝试 1 次后即 fallback

    result = asyncio.run(report_node(state))
    assert result.used_template_report is True
    assert result.audit_result is not None
    assert result.audit_result.severity == "warning"
    assert result.audit_result.issues == ["使用模板兜底"]

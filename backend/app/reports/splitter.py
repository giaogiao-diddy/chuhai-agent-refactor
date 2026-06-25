from app.schemas.agent_state import AgentState
from app.schemas.report import LeadReport, RawAIReport, ReportBundle, UserReport


def build_user_report(raw_report: RawAIReport, state: AgentState) -> UserReport:
    scoring = state.scoring_result
    return UserReport(
        feasibility_score=scoring.feasibility_score,
        display_score=scoring.feasibility_score,
        tag=scoring.tag,
        tag_explanation=scoring.tag_explanation,
        preliminary_judgment=scoring.preliminary_judgment,
        strengths=scoring.strengths,
        risks=scoring.risks,
        summary_conclusion=raw_report.summary_conclusion,
        positioning_assessment=raw_report.positioning_assessment,
        content_assessment=raw_report.content_assessment,
        conversion_assessment=raw_report.conversion_assessment,
        dimension_scores=scoring.dimension_scores,
        recommended_path=raw_report.recommended_path,
        risk_reminder=raw_report.risk_reminder,
        action_plan_30days=raw_report.action_plan_30days,
        consultant_guide=raw_report.consultant_guide,
    )


def build_lead_report(raw_report: RawAIReport, state: AgentState) -> LeadReport:
    scoring = state.scoring_result
    slots = state.slots
    return LeadReport(
        lead_score=scoring.lead_score,
        lead_priority=scoring.lead_priority,
        tag=scoring.tag,
        company_name=slots.company_name.value if slots.company_name else None,
        industry=slots.industry.value if slots.industry else None,
        product=slots.main_product.value if slots.main_product else None,
        target_market=slots.target_market.value if slots.target_market else None,
        summary_conclusion=raw_report.summary_conclusion,
        sales_followup=raw_report.sales_followup,
        consultant_notes=raw_report.consultant_notes,
        recommended_next_action=raw_report.action_plan_30days[0] if raw_report.action_plan_30days else "",
    )


def split_report(raw_report: RawAIReport, state: AgentState) -> ReportBundle:
    if state.scoring_result is None:
        raise ValueError("state.scoring_result 缺失，无法拆分报告")
    return ReportBundle(
        raw_report=raw_report,
        user_report=build_user_report(raw_report, state),
        lead_report=build_lead_report(raw_report, state),
    )

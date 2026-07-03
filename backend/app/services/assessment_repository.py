# Repository does not commit/rollback; transaction is owned by the caller (FastAPI dependency / test fixture).
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Assessment, LeadReport, Message, UserReport
from app.schemas.agent_state import AgentState
from app.schemas.slots import CompanySlots


def _slots_to_dict(slots: CompanySlots) -> dict:
    result = {}
    for field in CompanySlots.model_fields:
        val = getattr(slots, field)
        if val is not None:
            result[field] = {"value": val.value, "confidence": val.confidence}
    return result


def _validate_state(state: AgentState) -> None:
    if state.scoring_result is None:
        raise ValueError("state.scoring_result 缺失")
    if state.user_report is None:
        raise ValueError("state.user_report 缺失")
    if state.lead_report is None:
        raise ValueError("state.lead_report 缺失")


async def save_completed_assessment(
    db: AsyncSession,
    state: AgentState,
    user_id: uuid.UUID | None = None,
) -> Assessment:
    _validate_state(state)

    now = datetime.now(timezone.utc)
    assessment = Assessment(
        user_id=user_id,
        branch=state.branch,
        status=state.status,
        conversation_round=state.conversation_round,
        ai_failure_count=state.ai_failure_count,
        validation_errors=state.validation_errors,
        slots=_slots_to_dict(state.slots),
        answers=state.answers,
        scoring_result=state.scoring_result.model_dump(),
        feasibility_score=state.scoring_result.feasibility_score,
        lead_score=state.scoring_result.lead_score,
        display_score=state.scoring_result.display_score,
        tag=state.scoring_result.tag,
        lead_priority=state.scoring_result.lead_priority,
        audit_result=state.audit_result.model_dump() if state.audit_result else None,
        report_retry_count=state.report_retry_count,
        used_template_report=state.used_template_report,
        report_error=state.report_error,
        scoring_error=state.scoring_error,
        provider_id=state.provider_id,
        model_name=state.model_name,
        rag_matches=state.rag_matches,
        completed_at=now if state.status == "completed" else None,
    )

    db.add(assessment)
    await db.flush()

    for msg in state.messages:
        db.add(Message(
            assessment_id=assessment.id,
            role=msg.role,
            content=msg.content,
        ))

    db.add(UserReport(
        assessment_id=assessment.id,
        report_json=state.user_report.model_dump(),
    ))
    db.add(LeadReport(
        assessment_id=assessment.id,
        report_json=state.lead_report.model_dump(),
    ))

    await db.flush()
    await db.refresh(assessment)
    return assessment

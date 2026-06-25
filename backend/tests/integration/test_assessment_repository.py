import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session
from app.models import LeadReport, Message, UserReport
from app.schemas.agent_state import AgentMessage, AgentState
from app.schemas.audit import ReportAuditResult
from app.schemas.report import LeadReport as LeadReportSchema
from app.schemas.report import UserReport as UserReportSchema
from app.schemas.scoring import DimensionScore, ScoringResult
from app.schemas.slots import SlotValue
from app.services.assessment_repository import save_completed_assessment
from config import get_settings


@pytest.fixture
async def db() -> AsyncSession:
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")
    from sqlalchemy import text
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
            yield session
    except Exception:
        pytest.skip("PostgreSQL 不可达")


@pytest.mark.asyncio
async def test_save_completed_assessment(db):
    state = AgentState(
        branch="experienced",
        status="completed",
        conversation_round=8,
        ai_failure_count=0,
        validation_errors=[],
        report_retry_count=0,
        used_template_report=False,
        answers={"Q2a": ["A"], "Q5": ["C"], "Q6": ["B", "C"], "Q7": ["C"], "Q8": ["B"]},
    )
    state.slots.industry = SlotValue(value="健身器材", confidence=0.9)
    state.slots.main_product = SlotValue(value="力量训练设备", confidence=0.85)
    state.messages = [
        AgentMessage(role="user", content="你好"),
        AgentMessage(role="assistant", content="你好，我是顾问"),
    ]
    state.scoring_result = ScoringResult(
        feasibility_score=50, lead_score=30, display_score=50,
        tag="基础具备型", tag_explanation="x", preliminary_judgment="x",
        dimension_scores=[DimensionScore(name="x", raw_score=10, max_score=20, normalized_score=50)],
        strengths=["a"], risks=["b"], lead_priority="P2",
    )
    state.user_report = UserReportSchema(
        feasibility_score=50, display_score=50, tag="x", tag_explanation="x",
        preliminary_judgment="x", strengths=["a"], risks=["b"],
        summary_conclusion="conclusion text", positioning_assessment="x",
        content_assessment="x", conversion_assessment="x",
        dimension_scores=[DimensionScore(name="x", raw_score=10, max_score=20, normalized_score=50)],
        recommended_path="x", risk_reminder="x",
        action_plan_30days=["1","2","3","4"], consultant_guide="x",
    )
    state.lead_report = LeadReportSchema(
        lead_score=30, lead_priority="P2", tag="x",
        sales_followup="followup text", consultant_notes="x",
    )
    state.audit_result = ReportAuditResult(passed=True, issues=[], rewrite_required=False, severity="pass")

    assessment = await save_completed_assessment(db, state)
    await db.commit()

    assert assessment.id is not None
    assert assessment.status == "completed"
    assert assessment.feasibility_score == 50
    assert assessment.lead_score == 30
    assert assessment.used_template_report is False
    assert assessment.completed_at is not None
    assert isinstance(assessment.slots, dict)
    assert isinstance(assessment.answers, dict)
    assert assessment.slots["industry"]["value"] == "健身器材"
    assert assessment.answers["Q5"] == ["C"]

    msg_count = await db.scalar(
        select(func.count()).select_from(Message).where(Message.assessment_id == assessment.id)
    )
    assert msg_count == len(state.messages)

    user_r = await db.scalar(
        select(UserReport).where(UserReport.assessment_id == assessment.id)
    )
    lead_r = await db.scalar(
        select(LeadReport).where(LeadReport.assessment_id == assessment.id)
    )
    assert user_r is not None
    assert user_r.report_json["summary_conclusion"] == "conclusion text"
    assert lead_r is not None
    assert lead_r.report_json["sales_followup"] == "followup text"

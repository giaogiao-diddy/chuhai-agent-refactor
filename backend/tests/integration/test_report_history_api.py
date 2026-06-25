import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.db.session import async_session, get_db
from app.models import Assessment
from app.models.report import LeadReport as LeadReportModel
from app.models.report import UserReport as UserReportModel
from app.models.message import Message
from app.schemas.agent_state import AgentState
from app.schemas.audit import ReportAuditResult
from app.schemas.report import LeadReport as LeadReportSchema
from app.schemas.report import UserReport as UserReportSchema
from app.schemas.scoring import DimensionScore, ScoringResult
from app.services.assessment_repository import save_completed_assessment
from config import get_settings
from main import app


async def _override_get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest.fixture(autouse=True)
async def _cleanup():
    yield
    app.dependency_overrides.clear()


async def _app_with_db():
    app.dependency_overrides[get_db] = _override_get_db
    return app


async def _save_report():
    state = AgentState(branch="experienced", status="completed", answers={"Q5": ["C"]})
    state.scoring_result = ScoringResult(
        feasibility_score=50, lead_score=30, display_score=50,
        tag="基础具备型", tag_explanation="x", preliminary_judgment="x",
        dimension_scores=[DimensionScore(name="x", raw_score=10, max_score=20, normalized_score=50)],
        strengths=["a"], risks=["b"], lead_priority="P2",
    )
    state.user_report = UserReportSchema(
        feasibility_score=50, display_score=50, tag="基础具备型", tag_explanation="x",
        preliminary_judgment="x", strengths=["a"], risks=["b"],
        summary_conclusion="结论", positioning_assessment="x", content_assessment="x",
        conversion_assessment="x", dimension_scores=[DimensionScore(name="x", raw_score=10, max_score=20, normalized_score=50)],
        recommended_path="x", risk_reminder="x", action_plan_30days=["1","2","3","4"], consultant_guide="x",
    )
    state.lead_report = LeadReportSchema(lead_score=30, lead_priority="P2", tag="x", sales_followup="x", consultant_notes="x")
    state.audit_result = ReportAuditResult(passed=True, issues=[], rewrite_required=False, severity="pass")

    async with async_session() as db:
        assessment = await save_completed_assessment(db, state)
        await db.commit()
        return assessment


async def _delete_assessment_tree(assessment_id):
    async with async_session() as db:
        await db.execute(delete(UserReportModel).where(UserReportModel.assessment_id == assessment_id))
        await db.execute(delete(LeadReportModel).where(LeadReportModel.assessment_id == assessment_id))
        await db.execute(delete(Message).where(Message.assessment_id == assessment_id))
        await db.execute(delete(Assessment).where(Assessment.id == assessment_id))
        await db.commit()


FORBIDDEN = ["lead_report", "raw_report", "sales_followup", "consultant_notes", "lead_score", "lead_priority"]


@pytest.mark.asyncio
async def test_list_reports_returns_user_reports_only():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    assessment = await _save_report()
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/reports")
        assert resp.status_code == 200
        data = resp.json()
        ids = [item["assessment_id"] for item in data]
        assert str(assessment.id) in ids, f"列表中未找到 {assessment.id}"

        mine = next(item for item in data if item["assessment_id"] == str(assessment.id))
        assert mine["status"] == "completed"
        assert mine["branch"] == "experienced"
        assert mine["used_template_report"] is False
        assert mine["tag"] == "基础具备型"
        assert mine["feasibility_score"] == 50
        assert mine["display_score"] == 50

        text = resp.text
        for word in FORBIDDEN:
            assert word not in text, f"泄露: {word}"
    finally:
        await _delete_assessment_tree(assessment.id)


@pytest.mark.asyncio
async def test_get_report_detail_returns_user_report():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    assessment = await _save_report()
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/reports/{assessment.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["assessment_id"] == str(assessment.id)
        assert data["status"] == "completed"
        assert data["branch"] == "experienced"
        assert data["used_template_report"] is False
        assert data["user_report"]["tag"] == "基础具备型"
        assert data["user_report"]["summary_conclusion"]
        assert len(data["user_report"]["action_plan_30days"]) == 4
        text = resp.text
        for word in FORBIDDEN:
            assert word not in text, f"泄露: {word}"
    finally:
        await _delete_assessment_tree(assessment.id)


@pytest.mark.asyncio
async def test_get_report_detail_404():
    app_with_db = await _app_with_db()
    transport = ASGITransport(app=app_with_db)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/reports/{uuid.uuid4()}")
    assert resp.status_code == 404

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.db.session import async_session, get_db
from app.models import Assessment, LeadSubmission, User
from app.models.report import LeadReport as LeadReportModel
from app.models.report import UserReport as UserReportModel
from app.models.message import Message
from app.schemas.agent_state import AgentState
from app.schemas.audit import ReportAuditResult
from app.schemas.report import LeadReport as LeadReportSchema
from app.schemas.report import UserReport as UserReportSchema
from app.schemas.scoring import DimensionScore, ScoringResult
from app.services.assessment_repository import save_completed_assessment
from app.services.user_repository import get_or_create_anonymous_user
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


def _build_state():
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
    return state


async def _save_report(anon_id: str):
    state = _build_state()
    async with async_session() as db:
        user = await get_or_create_anonymous_user(db, anon_id)
        assessment = await save_completed_assessment(db, state, user_id=user.id)
        await db.commit()
        return assessment


async def _delete_assessment_tree(assessment_id):
    async with async_session() as db:
        await db.execute(delete(UserReportModel).where(UserReportModel.assessment_id == assessment_id))
        await db.execute(delete(LeadReportModel).where(LeadReportModel.assessment_id == assessment_id))
        await db.execute(delete(Message).where(Message.assessment_id == assessment_id))
        await db.execute(delete(LeadSubmission).where(LeadSubmission.assessment_id == assessment_id))
        await db.execute(delete(Assessment).where(Assessment.id == assessment_id))
        await db.commit()


async def _delete_anon_user(anon_id: str):
    async with async_session() as db:
        await db.execute(
            delete(User).where(User.wechat_openid == f"anonymous:{anon_id}")
        )
        await db.commit()


FORBIDDEN = [
    "lead_report", "raw_report", "scoring_result", "audit_result",
    "lead_score", "lead_priority", "sales_followup", "consultant_notes",
    "销售话术", "顾问跟进", "线索优先级", "顾问备注",
]


# ── 成功提交 ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_lead_submission_success():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_id = f"test-lead-ok-{uuid.uuid4().hex[:12]}"
    assessment = await _save_report(anon_id)
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/reports/{assessment.id}/lead-submission",
                json={
                    "anonymous_user_id": anon_id,
                    "contact_name": "张三",
                    "phone": "13800138000",
                },
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["submitted"] is True
        assert data["submission_id"]

        # DB 确认
        async with async_session() as db:
            sub = await db.scalar(
                select(LeadSubmission).where(LeadSubmission.assessment_id == assessment.id)
            )
            assert sub is not None
            assert sub.contact_name == "张三"
            assert sub.phone == "13800138000"
    finally:
        await _delete_assessment_tree(assessment.id)
        await _delete_anon_user(anon_id)


# ── 跨用户拒绝 ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_lead_submission_rejects_other_user_report():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_a = f"test-lead-a-{uuid.uuid4().hex[:12]}"
    anon_b = f"test-lead-b-{uuid.uuid4().hex[:12]}"
    assessment_b = await _save_report(anon_b)
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/reports/{assessment_b.id}/lead-submission",
                json={
                    "anonymous_user_id": anon_a,
                    "contact_name": "李四",
                    "phone": "13900139000",
                },
            )
        assert resp.status_code == 404

        # DB 无记录
        async with async_session() as db:
            sub = await db.scalar(
                select(LeadSubmission).where(LeadSubmission.assessment_id == assessment_b.id)
            )
            assert sub is None
    finally:
        await _delete_assessment_tree(assessment_b.id)
        await _delete_anon_user(anon_a)  # 可能不存在，但不影响
        await _delete_anon_user(anon_b)


# ── 幂等 ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_lead_submission_is_idempotent():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_id = f"test-lead-idem-{uuid.uuid4().hex[:12]}"
    assessment = await _save_report(anon_id)
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)

        # 第一次
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp1 = await client.post(
                f"/reports/{assessment.id}/lead-submission",
                json={
                    "anonymous_user_id": anon_id,
                    "contact_name": "王五",
                    "phone": "13700137000",
                },
            )
        assert resp1.status_code == 200
        sid1 = resp1.json()["submission_id"]

        # 第二次（不同联系方式）
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp2 = await client.post(
                f"/reports/{assessment.id}/lead-submission",
                json={
                    "anonymous_user_id": anon_id,
                    "contact_name": "赵六",
                    "phone": "13600136000",
                },
            )
        assert resp2.status_code == 200
        sid2 = resp2.json()["submission_id"]
        assert sid1 == sid2, f"幂等提交应返回同一 submission_id: {sid1} != {sid2}"

        # DB 仍只有一条，不覆盖
        async with async_session() as db:
            subs = (await db.execute(
                select(LeadSubmission).where(LeadSubmission.assessment_id == assessment.id)
            )).scalars().all()
            assert len(subs) == 1
            assert subs[0].contact_name == "王五"
    finally:
        await _delete_assessment_tree(assessment.id)
        await _delete_anon_user(anon_id)


# ── 非法 anonymous_user_id → 422 ──────────────────────────────────

@pytest.mark.asyncio
async def test_create_lead_submission_invalid_anonymous_id_returns_422():
    app_with_db = await _app_with_db()
    transport = ASGITransport(app=app_with_db)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/reports/{uuid.uuid4()}/lead-submission",
            json={
                "anonymous_user_id": "bad:id",
                "contact_name": "test",
                "phone": "12345678",
            },
        )
    assert resp.status_code == 422


# ── 安全响应 ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_lead_submission_response_has_no_sensitive_fields():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_id = f"test-lead-safe-{uuid.uuid4().hex[:12]}"
    assessment = await _save_report(anon_id)
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/reports/{assessment.id}/lead-submission",
                json={
                    "anonymous_user_id": anon_id,
                    "contact_name": "测试",
                    "phone": "13800001111",
                },
            )
        assert resp.status_code == 200
        text = resp.text
        for word in FORBIDDEN:
            assert word not in text, f"泄露: {word}"
    finally:
        await _delete_assessment_tree(assessment.id)
        await _delete_anon_user(anon_id)


# ── 报告解锁 ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_report_detail_locked_before_lead_submission():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")
    anon_id = f"test-locked-{uuid.uuid4().hex[:12]}"
    assessment = await _save_report(anon_id)
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/reports/{assessment.id}?anonymous_user_id={anon_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_unlocked"] is False
        assert data["user_report"] is None
        assert data["report_summary"]["tag"] == "基础具备型"
        for word in FORBIDDEN:
            assert word not in resp.text, f"泄露: {word}"
    finally:
        await _delete_assessment_tree(assessment.id)
        await _delete_anon_user(anon_id)


@pytest.mark.asyncio
async def test_report_detail_unlocked_after_lead_submission():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")
    anon_id = f"test-unlocked-{uuid.uuid4().hex[:12]}"
    assessment = await _save_report(anon_id)
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            await client.post(
                f"/reports/{assessment.id}/lead-submission",
                json={"anonymous_user_id": anon_id, "contact_name": "张三", "phone": "13800138000"},
            )
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/reports/{assessment.id}?anonymous_user_id={anon_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_unlocked"] is True
        assert data["user_report"] is not None
        assert data["user_report"]["summary_conclusion"]
        for word in FORBIDDEN:
            assert word not in resp.text, f"泄露: {word}"
    finally:
        await _delete_assessment_tree(assessment.id)
        await _delete_anon_user(anon_id)


# ── JWT 留资 ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_lead_submission_with_jwt_user_unlocks_report():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")
    from app.auth.jwt import create_access_token
    get_settings().JWT_SECRET_KEY = "test-jwt-lead-key"

    anon_id = f"test-jwt-lead-{uuid.uuid4().hex[:12]}"
    assessment = await _save_report(anon_id)
    try:
        async with async_session() as db:
            user = await get_or_create_anonymous_user(db, anon_id)
            token = create_access_token(str(user.id), "user")
            await db.commit()

        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/reports/{assessment.id}/lead-submission",
                json={"contact_name": "张三", "phone": "13800138000"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200

        # 验证解锁
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp2 = await client.get(
                f"/reports/{assessment.id}",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp2.status_code == 200
        assert resp2.json()["is_unlocked"] is True
        assert resp2.json()["user_report"] is not None
    finally:
        await _delete_assessment_tree(assessment.id)
        await _delete_anon_user(anon_id)


@pytest.mark.asyncio
async def test_create_lead_submission_with_jwt_rejects_other_user_report():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")
    from app.auth.jwt import create_access_token
    get_settings().JWT_SECRET_KEY = "test-jwt-lead-key-2"

    anon_a = f"test-jwt-a-{uuid.uuid4().hex[:12]}"
    anon_b = f"test-jwt-b-{uuid.uuid4().hex[:12]}"
    assessment_b = await _save_report(anon_b)
    try:
        async with async_session() as db:
            user_a = await get_or_create_anonymous_user(db, anon_a)
            token_a = create_access_token(str(user_a.id), "user")
            await db.commit()

        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/reports/{assessment_b.id}/lead-submission",
                json={"contact_name": "李四", "phone": "13900139000"},
                headers={"Authorization": f"Bearer {token_a}"},
            )
        assert resp.status_code == 404
    finally:
        await _delete_assessment_tree(assessment_b.id)
        await _delete_anon_user(anon_a)
        await _delete_anon_user(anon_b)


# ── strip 后长度校验 ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_contact_name_strip_too_short_rejected():
    """contact_name=" a " strip 后只有1位，应被拒绝"""
    app_with_db = await _app_with_db()
    transport = ASGITransport(app=app_with_db)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/reports/{uuid.uuid4()}/lead-submission",
            json={
                "anonymous_user_id": "valid-test-00000000",
                "contact_name": " a ",
                "phone": "12345678",
            },
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_phone_strip_too_short_rejected():
    """phone=" 1234 " strip 后只有4位，应被拒绝"""
    app_with_db = await _app_with_db()
    transport = ASGITransport(app=app_with_db)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/reports/{uuid.uuid4()}/lead-submission",
            json={
                "anonymous_user_id": "valid-test-00000000",
                "contact_name": "张三",
                "phone": " 1234 ",
            },
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_company_name_strip_too_short_rejected():
    """company_name=" a " strip 后只有1位，应被拒绝"""
    app_with_db = await _app_with_db()
    transport = ASGITransport(app=app_with_db)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/reports/{uuid.uuid4()}/lead-submission",
            json={
                "anonymous_user_id": "valid-test-00000000",
                "contact_name": "张三",
                "phone": "12345678",
                "company_name": " a ",
            },
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_wechat_id_strip_too_short_rejected():
    """wechat_id=" a " strip 后只有1位，应被拒绝"""
    app_with_db = await _app_with_db()
    transport = ASGITransport(app=app_with_db)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            f"/reports/{uuid.uuid4()}/lead-submission",
            json={
                "anonymous_user_id": "valid-test-00000000",
                "contact_name": "张三",
                "phone": "12345678",
                "wechat_id": " a ",
            },
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_whitespace_only_note_accepted():
    """note="   " strip 后为空，应被接受并保存为 None"""
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_id = f"test-note-sp-{uuid.uuid4().hex[:12]}"
    assessment = await _save_report(anon_id)
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/reports/{assessment.id}/lead-submission",
                json={
                    "anonymous_user_id": anon_id,
                    "contact_name": "张三",
                    "phone": "12345678",
                    "note": "   ",
                },
            )
        assert resp.status_code == 200
        async with async_session() as db:
            sub = await db.scalar(
                select(LeadSubmission).where(LeadSubmission.assessment_id == assessment.id)
            )
            assert sub is not None
            assert not sub.note
    finally:
        await _delete_assessment_tree(assessment.id)
        await _delete_anon_user(anon_id)

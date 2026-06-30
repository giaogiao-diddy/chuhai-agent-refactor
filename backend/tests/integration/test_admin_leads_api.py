import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

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
from app.services.lead_submission_repository import create_lead_submission
from app.services.user_repository import get_or_create_anonymous_user
from config import get_settings
from main import app

TEST_JWT_SECRET = "test-admin-leads-jwt-secret-key-32-bytes!"


@pytest.fixture(autouse=True)
async def _cleanup():
    settings = get_settings()
    old_secret = settings.JWT_SECRET_KEY
    settings.JWT_SECRET_KEY = TEST_JWT_SECRET
    try:
        yield
    finally:
        settings.JWT_SECRET_KEY = old_secret
        app.dependency_overrides.clear()


async def _app_with_db():
    app.dependency_overrides[get_db] = _override_get_db
    return app


async def _override_get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


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


async def _save_report_with_lead(anon_id: str):
    state = _build_state()
    async with async_session() as db:
        user = await get_or_create_anonymous_user(db, anon_id)
        assessment = await save_completed_assessment(db, state, user_id=user.id)
        submission = await create_lead_submission(
            db, assessment_id=assessment.id, anonymous_user_id=anon_id,
            contact_name="张三", phone="13800138000", company_name="测试公司",
        )
        await db.commit()
        return assessment, submission


async def _delete_all(assessment_id, anon_id):
    async with async_session() as db:
        await db.execute(delete(LeadSubmission).where(LeadSubmission.assessment_id == assessment_id))
        await db.execute(delete(UserReportModel).where(UserReportModel.assessment_id == assessment_id))
        await db.execute(delete(LeadReportModel).where(LeadReportModel.assessment_id == assessment_id))
        await db.execute(delete(Message).where(Message.assessment_id == assessment_id))
        await db.execute(delete(Assessment).where(Assessment.id == assessment_id))
        await db.execute(delete(User).where(User.wechat_openid == f"anonymous:{anon_id}"))
        await db.commit()


async def _make_token(user_id: str, role: str) -> str:
    from app.auth.jwt import create_access_token
    return create_access_token(user_id, role)


async def _create_user_and_token(anon_id: str, role: str = "user") -> tuple[str, str]:
    """返回 (user_id_str, token)"""
    async with async_session() as db:
        user = await get_or_create_anonymous_user(db, anon_id)
        if role != "user":
            user.role = role
        await db.commit()
        return str(user.id), await _make_token(str(user.id), user.role)


FORBIDDEN = [
    "lead_report", "raw_report", "scoring_result", "audit_result",
    "sales_followup", "consultant_notes",
]


# ── 无 Authorization → 401 ────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_leads_no_auth_returns_401():
    app_with_db = await _app_with_db()
    transport = ASGITransport(app=app_with_db)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/admin/leads")
    assert resp.status_code == 401


# ── 无效 token → 401 ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_leads_invalid_token_returns_401():
    app_with_db = await _app_with_db()
    transport = ASGITransport(app=app_with_db)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/admin/leads", headers={"Authorization": "Bearer bad.token.here"})
    assert resp.status_code == 401


# ── role="user" → 403 ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_leads_user_role_returns_403():
    anon_id = f"test-adm-user-{uuid.uuid4().hex[:12]}"
    uid, token = await _create_user_and_token(anon_id, "user")
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/leads", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403
    finally:
        async with async_session() as db:
            await db.execute(delete(User).where(User.id == uuid.UUID(uid)))
            await db.commit()


# ── role="consultant" → 200 ────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_leads_consultant_role_returns_200():
    settings_obj = get_settings()
    if not settings_obj.DATABASE_URL or "postgresql" not in settings_obj.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_id = f"test-adm-cons-{uuid.uuid4().hex[:12]}"
    assessment, submission = await _save_report_with_lead(anon_id)
    uid, token = await _create_user_and_token(anon_id, "consultant")
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/leads", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        text = resp.text
        for word in FORBIDDEN:
            assert word not in text, f"泄露: {word}"
    finally:
        await _delete_all(assessment.id, anon_id)


# ── role="admin" → 200 ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_leads_admin_role_returns_200():
    settings_obj = get_settings()
    if not settings_obj.DATABASE_URL or "postgresql" not in settings_obj.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_id = f"test-adm-admin-{uuid.uuid4().hex[:12]}"
    uid, token = await _create_user_and_token(anon_id, "admin")
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/leads", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
    finally:
        async with async_session() as db:
            await db.execute(delete(User).where(User.id == uuid.UUID(uid)))
            await db.commit()


# ── lead_report 顾问字段 ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_leads_detail_returns_lead_report():
    settings_obj = get_settings()
    if not settings_obj.DATABASE_URL or "postgresql" not in settings_obj.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_id = f"test-adm-lr-{uuid.uuid4().hex[:12]}"
    assessment, submission = await _save_report_with_lead(anon_id)
    uid, token = await _create_user_and_token(anon_id, "consultant")
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/admin/leads/{submission.id}",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["lead_report"] is not None
        assert data["lead_report"]["sales_followup"] is not None
        assert data["lead_report"]["consultant_notes"] is not None
    finally:
        await _delete_all(assessment.id, anon_id)


# ── followup 更新 ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_leads_patch_followup_success():
    settings_obj = get_settings()
    if not settings_obj.DATABASE_URL or "postgresql" not in settings_obj.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_id = f"test-adm-fu-{uuid.uuid4().hex[:12]}"
    assessment, submission = await _save_report_with_lead(anon_id)
    uid, token = await _create_user_and_token(anon_id, "consultant")
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.patch(
                f"/admin/leads/{submission.id}/followup",
                json={"followup_status": "已联系", "followup_note": "已电话沟通"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["followup_status"] == "已联系"
        assert data["followup_note"] == "已电话沟通"
    finally:
        await _delete_all(assessment.id, anon_id)


@pytest.mark.asyncio
async def test_admin_leads_patch_followup_user_403():
    anon_id = f"test-adm-fu403-{uuid.uuid4().hex[:12]}"
    uid, token = await _create_user_and_token(anon_id, "user")
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.patch(
                f"/admin/leads/{uuid.uuid4()}/followup",
                json={"followup_status": "已联系"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 403
    finally:
        async with async_session() as db:
            await db.execute(delete(User).where(User.id == uuid.UUID(uid)))
            await db.commit()


@pytest.mark.asyncio
async def test_admin_leads_patch_followup_invalid_status_422():
    anon_id = f"test-adm-fu422-{uuid.uuid4().hex[:12]}"
    uid, token = await _create_user_and_token(anon_id, "consultant")
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.patch(
                f"/admin/leads/{uuid.uuid4()}/followup",
                json={"followup_status": "invalid"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 422
    finally:
        async with async_session() as db:
            await db.execute(delete(User).where(User.id == uuid.UUID(uid)))
            await db.commit()


# ── PATCH 404 ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_leads_patch_followup_404():
    anon_id = f"test-adm-fu404-{uuid.uuid4().hex[:12]}"
    uid, token = await _create_user_and_token(anon_id, "consultant")
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.patch(
                f"/admin/leads/{uuid.uuid4()}/followup",
                json={"followup_status": "已联系"},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 404
    finally:
        async with async_session() as db:
            await db.execute(delete(User).where(User.id == uuid.UUID(uid)))
            await db.commit()


# ── 排序 ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_leads_sorted_by_priority_then_created_at():
    settings_obj = get_settings()
    if not settings_obj.DATABASE_URL or "postgresql" not in settings_obj.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    # 插入顺序不等于期望排序：P2, P0, P3, P1 → 期望 P0, P1, P2, P3
    priorities_in_order = ["P2", "P0", "P3", "P1"]
    expected_order = ["P0", "P1", "P2", "P3"]
    anon_ids: list[str] = []
    assessment_ids: list = []
    submission_ids: list[str] = []
    try:
        for pri in priorities_in_order:
            anon_id = f"test-sort-{pri}-{uuid.uuid4().hex[:8]}"
            anon_ids.append(anon_id)
            assessment, submission = await _save_report_with_lead(anon_id)
            assessment_ids.append(assessment.id)
            submission_ids.append(str(submission.id))
            async with async_session() as db:
                a = await db.get(Assessment, assessment.id)
                a.lead_priority = pri
                await db.commit()

        _, token = await _create_user_and_token(anon_ids[0], "consultant")
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/leads", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()

        # 只取本次创建的 submission，排除历史数据干扰
        created_ids = set(submission_ids)
        actual = [
            (d["submission_id"], d["lead_priority"])
            for d in data
            if d["submission_id"] in created_ids
        ]
        # 严格按业务顺序断言 P0 → P1 → P2 → P3
        priorities = [row[1] for row in actual]
        assert priorities == expected_order, f"排序错误: 期望 {expected_order}, 实际 {priorities}"
    finally:
        for aid in assessment_ids:
            async with async_session() as db:
                await db.execute(delete(LeadSubmission).where(LeadSubmission.assessment_id == aid))
                await db.execute(delete(UserReportModel).where(UserReportModel.assessment_id == aid))
                await db.execute(delete(LeadReportModel).where(LeadReportModel.assessment_id == aid))
                await db.execute(delete(Message).where(Message.assessment_id == aid))
                await db.execute(delete(Assessment).where(Assessment.id == aid))
                await db.commit()
        for anon_id in anon_ids:
            await _delete_anon_user(anon_id)


@pytest.mark.asyncio
async def test_admin_leads_same_priority_sorted_by_created_at_desc():
    """同优先级内按 created_at 倒序：后创建的在前面"""
    import asyncio

    settings_obj = get_settings()
    if not settings_obj.DATABASE_URL or "postgresql" not in settings_obj.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_ids: list[str] = []
    assessment_ids: list = []
    submission_ids: list[str] = []
    try:
        for i in range(2):
            anon_id = f"test-samepri-{i}-{uuid.uuid4().hex[:8]}"
            anon_ids.append(anon_id)
            assessment, submission = await _save_report_with_lead(anon_id)
            assessment_ids.append(assessment.id)
            submission_ids.append(str(submission.id))
            async with async_session() as db:
                a = await db.get(Assessment, assessment.id)
                a.lead_priority = "P1"
                await db.commit()
            if i == 0:
                await asyncio.sleep(0.02)  # 确保时间差

        _, token = await _create_user_and_token(anon_ids[0], "consultant")
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin/leads", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()

        created_ids = set(submission_ids)
        actual_ids = [d["submission_id"] for d in data if d["submission_id"] in created_ids]
        # 第二条（后创建）应在第一条前面
        assert actual_ids == [submission_ids[1], submission_ids[0]], (
            f"同优先级时间倒序错误: 期望 [{submission_ids[1]}, {submission_ids[0]}], 实际 {actual_ids}"
        )
    finally:
        for aid in assessment_ids:
            async with async_session() as db:
                await db.execute(delete(LeadSubmission).where(LeadSubmission.assessment_id == aid))
                await db.execute(delete(UserReportModel).where(UserReportModel.assessment_id == aid))
                await db.execute(delete(LeadReportModel).where(LeadReportModel.assessment_id == aid))
                await db.execute(delete(Message).where(Message.assessment_id == aid))
                await db.execute(delete(Assessment).where(Assessment.id == aid))
                await db.commit()
        for anon_id in anon_ids:
            await _delete_anon_user(anon_id)


# ── 筛选 ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_leads_filter_by_followup_status():
    settings_obj = get_settings()
    if not settings_obj.DATABASE_URL or "postgresql" not in settings_obj.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_a = f"test-flt-a-{uuid.uuid4().hex[:8]}"
    anon_b = f"test-flt-b-{uuid.uuid4().hex[:8]}"
    assessment_a, sub_a = await _save_report_with_lead(anon_a)
    assessment_b, sub_b = await _save_report_with_lead(anon_b)
    try:
        # 更新 sub_a 为已联系
        async with async_session() as db:
            s = await db.get(LeadSubmission, sub_a.id)
            s.followup_status = "已联系"
            await db.commit()

        _, token = await _create_user_and_token(anon_a, "consultant")
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/admin/leads?followup_status=已联系",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        data = resp.json()
        sids = {d["submission_id"] for d in data}
        assert str(sub_a.id) in sids
        assert str(sub_b.id) not in sids
    finally:
        for aid in [assessment_a.id, assessment_b.id]:
            async with async_session() as db:
                await db.execute(delete(LeadSubmission).where(LeadSubmission.assessment_id == aid))
                await db.execute(delete(UserReportModel).where(UserReportModel.assessment_id == aid))
                await db.execute(delete(LeadReportModel).where(LeadReportModel.assessment_id == aid))
                await db.execute(delete(Message).where(Message.assessment_id == aid))
                await db.execute(delete(Assessment).where(Assessment.id == aid))
                await db.commit()
        for anon_id in [anon_a, anon_b]:
            await _delete_anon_user(anon_id)


@pytest.mark.asyncio
async def test_admin_leads_bad_followup_status_returns_422():
    anon_id = f"test-badfs-{uuid.uuid4().hex[:12]}"
    _, token = await _create_user_and_token(anon_id, "consultant")
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/admin/leads?followup_status=invalid",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 422
    finally:
        async with async_session() as db:
            await db.execute(delete(User).where(User.wechat_openid == f"anonymous:{anon_id}"))
            await db.commit()

async def _delete_anon_user(anon_id: str):
    async with async_session() as db:
        await db.execute(delete(User).where(User.wechat_openid == f"anonymous:{anon_id}"))
        await db.commit()


# ── 详情 404 ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_leads_detail_404():
    anon_id = f"test-adm-404-{uuid.uuid4().hex[:12]}"
    uid, token = await _create_user_and_token(anon_id, "consultant")
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/admin/leads/{uuid.uuid4()}",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 404
    finally:
        async with async_session() as db:
            await db.execute(delete(User).where(User.id == uuid.UUID(uid)))
            await db.commit()

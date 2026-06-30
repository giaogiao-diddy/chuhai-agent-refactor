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
        await db.execute(delete(LeadSubmission).where(LeadSubmission.assessment_id == assessment_id))
        await db.execute(delete(UserReportModel).where(UserReportModel.assessment_id == assessment_id))
        await db.execute(delete(LeadReportModel).where(LeadReportModel.assessment_id == assessment_id))
        await db.execute(delete(Message).where(Message.assessment_id == assessment_id))
        await db.execute(delete(Assessment).where(Assessment.id == assessment_id))
        await db.commit()


async def _delete_anon_user(anon_id: str):
    async with async_session() as db:
        await db.execute(
            delete(User).where(User.wechat_openid == f"anonymous:{anon_id}")
        )
        await db.commit()


FORBIDDEN = ["lead_report", "raw_report", "sales_followup", "consultant_notes", "lead_score", "lead_priority"]


# ── 带 anonymous_user_id 的 list ──────────────────────────────────

@pytest.mark.asyncio
async def test_list_reports_returns_user_reports_only():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_id = f"test-list-{uuid.uuid4().hex[:12]}"
    assessment = await _save_report(anon_id)
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/reports?anonymous_user_id={anon_id}")
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
        await _delete_anon_user(anon_id)


# ── 带 anonymous_user_id 的 detail ────────────────────────────────

@pytest.mark.asyncio
async def test_get_report_detail_returns_user_report():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_id = f"test-detail-{uuid.uuid4().hex[:12]}"
    assessment = await _save_report(anon_id)
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/reports/{assessment.id}?anonymous_user_id={anon_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["assessment_id"] == str(assessment.id)
        assert data["status"] == "completed"
        assert data["branch"] == "experienced"
        assert data["used_template_report"] is False
        assert data["report_summary"]["tag"] == "基础具备型"
        assert data["report_summary"]["strengths"]
        text = resp.text
        for word in FORBIDDEN:
            assert word not in text, f"泄露: {word}"
    finally:
        await _delete_assessment_tree(assessment.id)
        await _delete_anon_user(anon_id)


# ── 404 ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_report_detail_404():
    app_with_db = await _app_with_db()
    transport = ASGITransport(app=app_with_db)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/reports/{uuid.uuid4()}?anonymous_user_id=nonexistent")
    assert resp.status_code == 404


# ── 不带 anonymous_user_id 返回空 ─────────────────────────────────

@pytest.mark.asyncio
async def test_reports_without_anonymous_user_returns_empty():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_id = f"test-empty-{uuid.uuid4().hex[:12]}"
    assessment = await _save_report(anon_id)
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/reports")
        assert resp.status_code == 200
        assert resp.json() == []

        # detail 也 404
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/reports/{assessment.id}")
        assert resp.status_code == 404
    finally:
        await _delete_assessment_tree(assessment.id)
        await _delete_anon_user(anon_id)


# ── A/B 用户隔离 ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reports_are_filtered_by_anonymous_user():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_a = f"test-iso-a-{uuid.uuid4().hex[:12]}"
    anon_b = f"test-iso-b-{uuid.uuid4().hex[:12]}"
    assessment_a = await _save_report(anon_a)
    assessment_b = await _save_report(anon_b)
    try:
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)

        # A 只能看到自己的
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/reports?anonymous_user_id={anon_a}")
        assert resp.status_code == 200
        data = resp.json()
        ids = [item["assessment_id"] for item in data]
        assert str(assessment_a.id) in ids
        assert str(assessment_b.id) not in ids

        # A 看 B 的详情 → 404
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/reports/{assessment_b.id}?anonymous_user_id={anon_a}")
        assert resp.status_code == 404

        # B 只能看到自己的
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/reports?anonymous_user_id={anon_b}")
        assert resp.status_code == 200
        data = resp.json()
        ids = [item["assessment_id"] for item in data]
        assert str(assessment_b.id) in ids
        assert str(assessment_a.id) not in ids
    finally:
        await _delete_assessment_tree(assessment_a.id)
        await _delete_assessment_tree(assessment_b.id)
        await _delete_anon_user(anon_a)
        await _delete_anon_user(anon_b)


# ── anonymous_user_id query 参数校验 ───────────────────────────────

@pytest.mark.asyncio
async def test_list_reports_bad_anonymous_user_id_returns_422():
    app_with_db = await _app_with_db()
    transport = ASGITransport(app=app_with_db)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/reports?anonymous_user_id=bad:id")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_report_detail_bad_anonymous_user_id_returns_422():
    app_with_db = await _app_with_db()
    transport = ASGITransport(app=app_with_db)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/reports/{uuid.uuid4()}?anonymous_user_id=bad:id")
    assert resp.status_code == 422


# ── wechat_qr_url ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_report_detail_returns_wechat_qr_url_when_configured():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")
    old_qr = settings.WECHAT_QR_URL
    settings.WECHAT_QR_URL = "https://example.com/wechat-qr.png"
    assessment = None
    try:
        anon_id = f"test-qr-{uuid.uuid4().hex[:12]}"
        assessment = await _save_report(anon_id)
        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/reports/{assessment.id}?anonymous_user_id={anon_id}"
            )
        assert resp.status_code == 200
        assert resp.json()["wechat_qr_url"] == "https://example.com/wechat-qr.png"
    finally:
        settings.WECHAT_QR_URL = old_qr
        if assessment is not None:
            await _delete_assessment_tree(assessment.id)
            await _delete_anon_user(anon_id)


# ── get_or_create_anonymous_user 并发安全 ──────────────────────────

@pytest.mark.asyncio
async def test_get_or_create_anonymous_user_idempotent():
    """两次独立调用（模拟并发场景）返回同一用户，数据库中只有一条记录。"""
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_id = f"test-idempotent-{uuid.uuid4().hex[:12]}"
    try:
        # 第一次：创建
        async with async_session() as db1:
            user_a = await get_or_create_anonymous_user(db1, anon_id)
            await db1.commit()

        # 第二次：应返回同一用户（走 on_conflict_do_nothing → select 已有记录）
        async with async_session() as db2:
            user_b = await get_or_create_anonymous_user(db2, anon_id)
            await db2.commit()

        assert user_a.id == user_b.id, f"两次调用应返回同一用户: {user_a.id} != {user_b.id}"

        # 验证数据库中该 wechat_openid 只有一条
        async with async_session() as db:
            result = await db.execute(
                select(User).where(User.wechat_openid == f"anonymous:{anon_id}")
            )
            users = result.scalars().all()
            assert len(users) == 1
    finally:
        await _delete_anon_user(anon_id)


# ── JWT 用户隔离 ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reports_with_jwt_return_current_user_reports():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    from app.auth.jwt import create_access_token

    _set_jwt_secret("test-jwt-secret-key-for-isolation")
    anon_a = f"test-jwt-a-{uuid.uuid4().hex[:12]}"
    anon_b = f"test-jwt-b-{uuid.uuid4().hex[:12]}"
    assessment_a = await _save_report(anon_a)
    assessment_b = await _save_report(anon_b)
    try:
        # 获取 user A 的 UUID，签发 JWT
        async with async_session() as db:
            user_a = await get_or_create_anonymous_user(db, anon_a)
            token_a = create_access_token(str(user_a.id), "user")

        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/reports",
                headers={"Authorization": f"Bearer {token_a}"},
            )
        assert resp.status_code == 200
        data = resp.json()
        ids = [item["assessment_id"] for item in data]
        assert str(assessment_a.id) in ids
        assert str(assessment_b.id) not in ids
    finally:
        await _delete_assessment_tree(assessment_a.id)
        await _delete_assessment_tree(assessment_b.id)
        await _delete_anon_user(anon_a)
        await _delete_anon_user(anon_b)


@pytest.mark.asyncio
async def test_report_detail_with_jwt_rejects_other_user():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    from app.auth.jwt import create_access_token

    _set_jwt_secret("test-jwt-secret-key-for-isolation-2")
    anon_a = f"test-jwt-det-a-{uuid.uuid4().hex[:12]}"
    anon_b = f"test-jwt-det-b-{uuid.uuid4().hex[:12]}"
    assessment_a = await _save_report(anon_a)
    assessment_b = await _save_report(anon_b)
    try:
        async with async_session() as db:
            user_a = await get_or_create_anonymous_user(db, anon_a)
            token_a = create_access_token(str(user_a.id), "user")

        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        # A token 查 B 的 detail → 404
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                f"/reports/{assessment_b.id}",
                headers={"Authorization": f"Bearer {token_a}"},
            )
        assert resp.status_code == 404
    finally:
        await _delete_assessment_tree(assessment_a.id)
        await _delete_assessment_tree(assessment_b.id)
        await _delete_anon_user(anon_a)
        await _delete_anon_user(anon_b)


def _set_jwt_secret(key: str):
    get_settings().JWT_SECRET_KEY = key


# ── followup_status ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_report_list_returns_followup_status_after_submission():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_id = f"test-fu-list-{uuid.uuid4().hex[:12]}"
    assessment = await _save_report(anon_id)
    try:
        # 创建 lead submission
        async with async_session() as db:
            sub = LeadSubmission(
                assessment_id=assessment.id,
                user_id=(await get_or_create_anonymous_user(db, anon_id)).id,
                contact_name="张三", phone="13800138000",
                followup_status="已联系",
            )
            db.add(sub)
            await db.commit()

        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/reports?anonymous_user_id={anon_id}")
        assert resp.status_code == 200
        data = resp.json()
        mine = next(item for item in data if item["assessment_id"] == str(assessment.id))
        assert mine["followup_status"] == "已联系"
        assert "followup_note" not in resp.text
    finally:
        await _delete_assessment_tree(assessment.id)
        await _delete_anon_user(anon_id)


@pytest.mark.asyncio
async def test_report_detail_returns_followup_status_after_submission():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    anon_id = f"test-fu-det-{uuid.uuid4().hex[:12]}"
    assessment = await _save_report(anon_id)
    try:
        async with async_session() as db:
            sub = LeadSubmission(
                assessment_id=assessment.id,
                user_id=(await get_or_create_anonymous_user(db, anon_id)).id,
                contact_name="李四", phone="13900139000",
                followup_status="已预约",
            )
            db.add(sub)
            await db.commit()

        app_with_db = await _app_with_db()
        transport = ASGITransport(app=app_with_db)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(f"/reports/{assessment.id}?anonymous_user_id={anon_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["followup_status"] == "已预约"
        # 不应暴露顾问字段
        for word in ["lead_report", "sales_followup", "consultant_notes", "lead_score", "lead_priority", "followup_note"]:
            assert word not in resp.text, f"泄露: {word}"
    finally:
        await _delete_assessment_tree(assessment.id)
        await _delete_anon_user(anon_id)

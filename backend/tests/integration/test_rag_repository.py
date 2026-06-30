import pytest
from sqlalchemy import delete, select

from app.db.session import async_session
from app.models.rag_document import RagDocument
from app.schemas.rag import RagDocumentMatch
from app.services.rag_repository import SEED_DOCUMENTS, search_rag_context, upsert_seed_documents
from config import get_settings

SEED_TITLES = [d["title"] for d in SEED_DOCUMENTS]


async def _cleanup_all_seeds():
    async with async_session() as db:
        for title in SEED_TITLES:
            await db.execute(delete(RagDocument).where(RagDocument.title == title))
        await db.commit()


def _skip_if_no_ai_key():
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY:
        pytest.skip("DEEPSEEK_API_KEY 未配置")


@pytest.mark.integration
@pytest.mark.ai
@pytest.mark.asyncio
async def test_seed_and_search_rag_real_embedding():
    _skip_if_no_ai_key()
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    await _cleanup_all_seeds()

    try:
        async with async_session() as db:
            count = await upsert_seed_documents(db)
            await db.commit()
        assert count == 8

        async with async_session() as db:
            matches = await search_rag_context(db, "健身器材工厂 东南亚 TikTok 获客", top_k=3)
        assert len(matches) >= 1
        assert matches[0].title
        assert matches[0].content
        assert matches[0].score > 0
    finally:
        await _cleanup_all_seeds()


@pytest.mark.integration
@pytest.mark.ai
@pytest.mark.asyncio
async def test_report_generation_with_rag_context_real_deepseek():
    _skip_if_no_ai_key()

    from app.agent.reporting import generate_raw_report
    from app.schemas.agent_state import AgentState
    from app.schemas.scoring import DimensionScore, ScoringResult
    from app.schemas.slots import SlotValue

    state = AgentState(branch="experienced")
    state.slots.industry = SlotValue(value="健身器材", confidence=0.9)
    state.slots.main_product = SlotValue(value="力量训练设备", confidence=0.85)
    state.scoring_result = ScoringResult(
        feasibility_score=50, lead_score=30, display_score=50,
        tag="基础具备型", tag_explanation="具备出海基础",
        preliminary_judgment="初步具备出海条件",
        dimension_scores=[DimensionScore(name="enterprise_base", raw_score=15, max_score=20, normalized_score=75)],
        strengths=["源头工厂价格优势"], risks=["海外社媒经验不足"],
        lead_priority="P2",
    )

    rag_ctx = [
        RagDocumentMatch(title="TikTok短视频B2B获客策略",
                         content="TikTok已成为B2B工厂获客新渠道。工厂车间、生产流程等场景拍摄内容能展示真实制造能力。",
                         source="test", score=0.9),
    ]

    report = await generate_raw_report(state, rag_context=rag_ctx)
    assert report.summary_conclusion
    assert len(report.action_plan_30days) == 4
    assert report.sales_followup


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rag_document_match_schema_serializable():
    """非 AI 测试：RagDocumentMatch 可正常序列化"""
    m = RagDocumentMatch(title="测试", content="内容", source="src", score=0.5)
    d = m.model_dump()
    assert d["title"] == "测试"
    assert d["score"] == 0.5


@pytest.mark.integration
@pytest.mark.ai
@pytest.mark.asyncio
async def test_upsert_seed_documents_is_idempotent():
    _skip_if_no_ai_key()
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    await _cleanup_all_seeds()
    try:
        # 第一次：插入 8 条
        async with async_session() as db:
            count1 = await upsert_seed_documents(db)
            await db.commit()
        assert count1 == 8

        # 第二次：幂等，返回 0
        async with async_session() as db:
            count2 = await upsert_seed_documents(db)
            await db.commit()
        assert count2 == 0

        # DB 中仍只有 8 条
        async with async_session() as db:
            from sqlalchemy import func
            cnt = await db.scalar(
                select(func.count()).select_from(RagDocument).where(
                    RagDocument.title.in_(SEED_TITLES)
                )
            )
            assert cnt == 8
    finally:
        await _cleanup_all_seeds()

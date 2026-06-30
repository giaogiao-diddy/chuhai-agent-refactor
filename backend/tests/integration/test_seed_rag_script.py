import os
import subprocess
import sys

import pytest
from sqlalchemy import delete, func, select

from app.db.session import async_session
from app.models.rag_document import RagDocument
from app.services.rag_repository import SEED_DOCUMENTS
from config import get_settings

SEED_TITLES = [d["title"] for d in SEED_DOCUMENTS]
SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "seed_rag.py")


async def _cleanup_all_seeds():
    async with async_session() as db:
        for title in SEED_TITLES:
            await db.execute(delete(RagDocument).where(RagDocument.title == title))
        await db.commit()


@pytest.mark.integration
@pytest.mark.ai
@pytest.mark.asyncio
async def test_seed_rag_script_runs_real_embedding():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")
    emb_key = settings.EMBEDDING_API_KEY or settings.DEEPSEEK_API_KEY
    emb_url = settings.EMBEDDING_BASE_URL or settings.DEEPSEEK_BASE_URL
    if not emb_key or not emb_url:
        pytest.skip("EMBEDDING_API_KEY 或 EMBEDDING_BASE_URL 未配置")

    await _cleanup_all_seeds()
    try:
        # 第一次运行：应新增 8 条
        result1 = subprocess.run(
            [sys.executable, SCRIPT_PATH],
            capture_output=True, text=True, timeout=60,
        )
        assert result1.returncode == 0, f"stdout: {result1.stdout}\nstderr: {result1.stderr}"
        assert "新增" in result1.stdout
        assert "8" in result1.stdout

        # DB 验证
        async with async_session() as db:
            cnt = await db.scalar(
                select(func.count()).select_from(RagDocument).where(
                    RagDocument.title.in_(SEED_TITLES)
                )
            )
            assert cnt == 8

        # 第二次运行：幂等，新增 0 条
        result2 = subprocess.run(
            [sys.executable, SCRIPT_PATH],
            capture_output=True, text=True, timeout=60,
        )
        assert result2.returncode == 0
        assert "0" in result2.stdout or "新增 0" in result2.stdout
    finally:
        await _cleanup_all_seeds()

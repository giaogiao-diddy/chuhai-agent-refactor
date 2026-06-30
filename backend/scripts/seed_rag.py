# RAG 种子知识初始化脚本: cd backend && python scripts/seed_rag.py

import asyncio
import os
import sys

# 确保 backend/ 在 sys.path 中，支持从任意目录运行
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from app.db.session import async_session
from app.services.rag_repository import upsert_seed_documents


async def main() -> None:
    async with async_session() as db:
        try:
            count = await upsert_seed_documents(db)
            await db.commit()
            print(f"新增 {count} 条种子知识")
        except Exception:
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())

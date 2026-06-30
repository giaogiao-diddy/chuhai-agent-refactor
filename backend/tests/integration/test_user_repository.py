import uuid

import pytest

from app.db.session import async_session
from app.models import User
from app.services.user_repository import get_or_create_wechat_user
from config import get_settings


@pytest.mark.asyncio
async def test_get_or_create_wechat_user_reuses_existing_and_preserves_role():
    settings = get_settings()
    if not settings.DATABASE_URL or "postgresql" not in settings.DATABASE_URL:
        pytest.skip("DATABASE_URL 未配置 PostgreSQL")

    openid = f"test-openid-{uuid.uuid4().hex[:12]}"
    try:
        # 首次创建
        async with async_session() as db:
            user1 = await get_or_create_wechat_user(db, openid=openid, nickname="张三", avatar_url="http://x.img")
            await db.commit()
        assert user1.role == "user"

        # 手动改 role
        async with async_session() as db:
            u = await db.get(User, user1.id)
            u.role = "consultant"
            await db.commit()

        # 再次调用，传新 nickname/avatar，role 不变
        async with async_session() as db:
            user2 = await get_or_create_wechat_user(db, openid=openid, nickname="李四", avatar_url="http://y.img")
            await db.commit()

        assert user2.id == user1.id
        assert user2.role == "consultant"
        assert user2.nickname == "李四"
        assert user2.avatar_url == "http://y.img"
    finally:
        async with async_session() as db:
            from sqlalchemy import delete
            await db.execute(delete(User).where(User.id == user1.id))
            await db.commit()

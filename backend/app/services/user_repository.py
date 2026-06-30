from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_or_create_anonymous_user(
    db: AsyncSession,
    anonymous_user_id: str,
) -> User:
    wechat_openid = f"anonymous:{anonymous_user_id}"

    stmt = (
        insert(User)
        .values(wechat_openid=wechat_openid, role="user")
        .on_conflict_do_nothing(index_elements=[User.wechat_openid])
        .returning(User.id)
    )
    result = await db.execute(stmt)
    created_id = result.scalar_one_or_none()

    if created_id is not None:
        user = await db.get(User, created_id)
        if user is None:
            raise ValueError("anonymous user create failed")
        return user

    result = await db.execute(
        select(User).where(User.wechat_openid == wechat_openid)
    )
    return result.scalar_one()


async def get_or_create_wechat_user(
    db: AsyncSession,
    openid: str,
    unionid: str | None = None,
    nickname: str | None = None,
    avatar_url: str | None = None,
) -> User:
    wechat_openid = f"wechat_union:{unionid}" if unionid else f"wechat_openid:{openid}"

    stmt = (
        insert(User)
        .values(wechat_openid=wechat_openid, nickname=nickname, avatar_url=avatar_url, role="user")
        .on_conflict_do_nothing(index_elements=[User.wechat_openid])
        .returning(User.id)
    )
    result = await db.execute(stmt)
    created_id = result.scalar_one_or_none()

    if created_id is not None:
        user = await db.get(User, created_id)
        if user is None:
            raise ValueError("wechat user create failed")
        return user

    user = (
        await db.execute(select(User).where(User.wechat_openid == wechat_openid))
    ).scalar_one()
    if nickname:
        user.nickname = nickname
    if avatar_url:
        user.avatar_url = avatar_url
    return user

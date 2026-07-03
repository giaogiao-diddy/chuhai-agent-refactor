import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.model_provider import ModelProvider


async def list_providers(db: AsyncSession) -> list[ModelProvider]:
    result = await db.execute(select(ModelProvider).order_by(ModelProvider.name))
    return list(result.scalars().all())


async def create_provider(db: AsyncSession, data: dict) -> ModelProvider:
    p = ModelProvider(**data)
    db.add(p)
    await db.flush()
    return p


async def update_provider(db: AsyncSession, provider_id: uuid.UUID, data: dict) -> ModelProvider | None:
    p = await db.get(ModelProvider, provider_id)
    if p is None:
        return None
    for key, val in data.items():
        if val is not None:
            setattr(p, key, val)
    await db.flush()
    return p


async def delete_provider(db: AsyncSession, provider_id: uuid.UUID) -> bool:
    p = await db.get(ModelProvider, provider_id)
    if p is None:
        return False
    await db.delete(p)
    await db.flush()
    return True


async def get_provider(db: AsyncSession, provider_id: uuid.UUID) -> ModelProvider | None:
    return await db.get(ModelProvider, provider_id)


async def get_default_provider(db: AsyncSession) -> ModelProvider | None:
    result = await db.execute(
        select(ModelProvider).where(ModelProvider.enabled == True).order_by(ModelProvider.name).limit(1)
    )
    return result.scalar()

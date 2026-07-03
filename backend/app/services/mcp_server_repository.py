import uuid as _uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.mcp_server import McpServer


async def list_servers(db: AsyncSession) -> list[McpServer]:
    result = await db.execute(select(McpServer).order_by(McpServer.name))
    return list(result.scalars().all())


async def list_enabled_http_servers(db: AsyncSession) -> list[McpServer]:
    result = await db.execute(
        select(McpServer)
        .where(McpServer.enabled.is_(True))
        .where(McpServer.transport == "http")
        .where(McpServer.url.isnot(None))
        .order_by(McpServer.name)
    )
    return list(result.scalars().all())


async def get_server(db: AsyncSession, sid: _uuid.UUID) -> McpServer | None:
    return await db.get(McpServer, sid)


async def create_server(db: AsyncSession, data: dict) -> McpServer:
    s = McpServer(**data)
    db.add(s)
    await db.flush()
    return s


async def update_server(db: AsyncSession, sid: _uuid.UUID, data: dict) -> McpServer | None:
    s = await db.get(McpServer, sid)
    if s is None: return None
    for k, v in data.items():
        if v is not None:
            setattr(s, k, v)
    await db.flush()
    return s


async def delete_server(db: AsyncSession, sid: _uuid.UUID) -> bool:
    s = await db.get(McpServer, sid)
    if s is None: return False
    await db.delete(s)
    await db.flush()
    return True

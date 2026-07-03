import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import get_current_consultant_required
from app.db.session import get_db
from app.models import User
from app.agent.mcp.adapter import list_mcp_tools
from app.schemas.mcp_server import McpServerCreate, McpServerResponse, McpServerUpdate
from app.services.mcp_server_repository import (
    create_server, delete_server, get_server, list_servers, update_server,
)

router = APIRouter(prefix="/mcp-servers", tags=["mcp-servers"])


@router.get("", response_model=list[McpServerResponse])
async def api_list(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    servers = await list_servers(db)
    return [McpServerResponse.from_orm_model(s) for s in servers]


@router.post("", response_model=McpServerResponse, status_code=201)
async def api_create(
    body: McpServerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    s = await create_server(db, body.model_dump())
    return McpServerResponse.from_orm_model(s)


@router.patch("/{server_id}", response_model=McpServerResponse)
async def api_update(
    server_id: _uuid.UUID,
    body: McpServerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    s = await update_server(db, server_id, body.model_dump(exclude_none=True))
    if s is None:
        raise HTTPException(status_code=404, detail="MCP Server 不存在")
    return McpServerResponse.from_orm_model(s)


@router.post("/{server_id}/test", response_model=McpServerResponse)
async def api_test(
    server_id: _uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    s = await get_server(db, server_id)
    if s is None:
        raise HTTPException(status_code=404, detail="MCP Server 不存在")
    if not s.url:
        raise HTTPException(status_code=400, detail="MCP Server 未配置 URL")

    response = McpServerResponse.from_orm_model(s)
    try:
        tools = await list_mcp_tools(s.url, s.headers or {})
        response.connected = True
        response.tools_count = len(tools)
        response.error_message = None
    except Exception:
        response.connected = False
        response.tools_count = 0
        response.error_message = "连接失败"
    return response


@router.delete("/{server_id}", status_code=204)
async def api_delete(
    server_id: _uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    ok = await delete_server(db, server_id)
    if not ok:
        raise HTTPException(status_code=404, detail="MCP Server 不存在")

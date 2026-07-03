import uuid
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import get_current_consultant_required
from app.db.session import get_db
from app.models import User
from app.schemas.model_provider import (
    ModelProviderCreate,
    ModelProviderPublicItem,
    ModelProviderResponse,
    ModelProviderTestResponse,
    ModelProviderUpdate,
)
from app.services.model_provider_repository import (
    create_provider,
    delete_provider,
    get_provider,
    list_providers,
    update_provider,
)

router = APIRouter(prefix="/model-providers", tags=["model-providers"])


def _chat_completions_url(base_url: str) -> str:
    u = base_url.rstrip("/")
    if u.endswith("/v1"):
        return u + "/chat/completions"
    return u + "/v1/chat/completions"


@router.get("", response_model=list[ModelProviderResponse])
async def api_list_providers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    providers = await list_providers(db)
    return [ModelProviderResponse.from_orm_model(p) for p in providers]


@router.get("/enabled-public", response_model=list[ModelProviderPublicItem])
async def api_list_public_providers(
    db: AsyncSession = Depends(get_db),
):
    """公开只读接口：返回 enabled 的 Provider 列表，仅暴露 id/name/default_model/context_window。"""
    providers = await list_providers(db)
    return [ModelProviderPublicItem.from_orm_model(p) for p in providers if p.enabled]


@router.post("", response_model=ModelProviderResponse)
async def api_create_provider(
    body: ModelProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    p = await create_provider(db, body.model_dump())
    return ModelProviderResponse.from_orm_model(p)


@router.patch("/{provider_id}", response_model=ModelProviderResponse)
async def api_update_provider(
    provider_id: uuid.UUID,
    body: ModelProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    p = await update_provider(db, provider_id, body.model_dump(exclude_none=True))
    if p is None:
        raise HTTPException(status_code=404, detail="Provider 不存在")
    return ModelProviderResponse.from_orm_model(p)


@router.delete("/{provider_id}")
async def api_delete_provider(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    ok = await delete_provider(db, provider_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Provider 不存在")
    return {"ok": True}


@router.post("/{provider_id}/test", response_model=ModelProviderTestResponse)
async def api_test_provider(
    provider_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    p = await get_provider(db, provider_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Provider 不存在")

    url = _chat_completions_url(p.base_url)
    payload: dict[str, Any] = {
        "model": p.default_model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 5,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {p.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        if resp.status_code == 200:
            return ModelProviderTestResponse(success=True, message="连接成功", model_used=p.default_model)
        return ModelProviderTestResponse(success=False, message=f"模型 API 返回 {resp.status_code}")
    except httpx.HTTPError as e:
        return ModelProviderTestResponse(success=False, message=f"连接失败: {type(e).__name__}")

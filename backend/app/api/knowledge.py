import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth_deps import get_current_consultant_required
from app.db.session import get_db
from app.models import User
from app.schemas.rag import (
    KnowledgeCreate,
    KnowledgeDetail,
    KnowledgeItem,
    KnowledgeSearchRequest,
    KnowledgeSearchResult,
    KnowledgeUpdate,
)
from app.services.rag_repository import (
    create_knowledge,
    delete_knowledge,
    get_knowledge,
    list_knowledge,
    re_embed_knowledge,
    search_knowledge,
    update_knowledge,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeItem])
async def api_list_knowledge(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    rows = await list_knowledge(db)
    return [KnowledgeItem.from_row(r) for r in rows]


@router.post("", response_model=KnowledgeItem, status_code=201)
async def api_create_knowledge(
    body: KnowledgeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    doc = await create_knowledge(db, title=body.title, content=body.content, source=body.source)
    return KnowledgeItem.from_orm_model(doc)


@router.get("/{doc_id}", response_model=KnowledgeDetail)
async def api_get_knowledge(
    doc_id: _uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    doc = await get_knowledge(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="知识不存在")
    return KnowledgeDetail.from_orm_model(doc)


@router.patch("/{doc_id}", response_model=KnowledgeItem)
async def api_update_knowledge(
    doc_id: _uuid.UUID,
    body: KnowledgeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    update_source = "source" in body.model_fields_set
    doc = await update_knowledge(
        db, doc_id,
        title=body.title, content=body.content, source=body.source,
        update_source=update_source,
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="知识不存在")
    return KnowledgeItem.from_orm_model(doc)


@router.delete("/{doc_id}", status_code=204)
async def api_delete_knowledge(
    doc_id: _uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    ok = await delete_knowledge(db, doc_id)
    if not ok:
        raise HTTPException(status_code=404, detail="知识不存在")


@router.post("/{doc_id}/re-embed", response_model=KnowledgeItem)
async def api_re_embed_knowledge(
    doc_id: _uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    doc = await re_embed_knowledge(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="知识不存在")
    return KnowledgeItem.from_orm_model(doc)


@router.post("/search", response_model=list[KnowledgeSearchResult])
async def api_search_knowledge(
    body: KnowledgeSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    return await search_knowledge(db, query=body.query, top_k=body.top_k)

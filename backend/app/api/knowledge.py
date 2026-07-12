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


@router.get("/eval")
async def api_eval_rag(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_consultant_required),
):
    """RAG 离线评估：recall@3, precision@3, MRR, Hit@3"""
    import asyncio
    from app.services.rag_eval import EVAL_QUERIES
    from app.services.rag_repository import search_rag_context

    sem = asyncio.Semaphore(5)
    async def search_one(query: str, top_k: int = 3):
        async with sem:
            return await search_rag_context(db, query, top_k)

    K = 3; total = len(EVAL_QUERIES)
    recall_sum = precision_sum = mrr_sum = hit_count = 0.0
    per_query: list[dict] = []

    for item in EVAL_QUERIES:
        query = item["query"]; relevant = set(item["relevant_titles"])
        matches = await search_one(query, K)
        titles = [m.title for m in matches]
        rel_retrieved = [t for t in titles if t in relevant]
        recall = len(rel_retrieved) / len(relevant) if relevant else 0.0
        precision = len(rel_retrieved) / K if K > 0 else 0.0
        rr = 0.0
        for rank, t in enumerate(titles, 1):
            if t in relevant: rr = 1.0 / rank; break
        recall_sum += recall; precision_sum += precision; mrr_sum += rr
        hit_count += 1 if rel_retrieved else 0
        per_query.append({
            "query": query, "expected": sorted(relevant),
            "retrieved": [(t, round(m.score, 4)) for t, m in zip(titles, matches)],
            "recall": round(recall, 4), "precision": round(precision, 4),
            "reciprocal_rank": round(rr, 4),
        })

    return {
        "summary": {
            "total_queries": total, "top_k": K,
            "recall_at_k": round(recall_sum / total, 4),
            "precision_at_k": round(precision_sum / total, 4),
            "mrr": round(mrr_sum / total, 4),
            "hit_rate_at_k": round(hit_count / total, 4),
        }, "details": per_query,
    }


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


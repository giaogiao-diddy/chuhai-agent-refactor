from pydantic import BaseModel, Field


class RagDocumentMatch(BaseModel):
    title: str
    content: str
    source: str | None = None
    score: float


class RagMatchSafe(BaseModel):
    """返回给前端的安全 RAG 引用，不包含完整正文和 embedding。"""
    title: str
    source: str | None = None
    distance: float | None = None
    content_preview: str = ""

    @classmethod
    def from_match(cls, m: RagDocumentMatch) -> "RagMatchSafe":
        preview = m.content[:200] + "..." if len(m.content) > 200 else m.content
        return cls(title=m.title, source=m.source, distance=round(1.0 - m.score, 4), content_preview=preview)


class KnowledgeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    source: str | None = None


class KnowledgeUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    content: str | None = None
    source: str | None = None


class KnowledgeItem(BaseModel):
    id: str
    title: str
    source: str | None = None
    content_preview: str
    has_embedding: bool
    created_at: str | None = None

    @classmethod
    def from_row(cls, row) -> "KnowledgeItem":
        preview = row.content[:200] + "..." if len(row.content) > 200 else row.content
        return cls(
            id=str(row.id),
            title=row.title,
            source=row.source,
            content_preview=preview,
            has_embedding=bool(row.has_embedding),
            created_at=row.created_at.isoformat() if row.created_at else None,
        )

    @classmethod
    def from_orm_model(cls, doc) -> "KnowledgeItem":
        preview = doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
        return cls(
            id=str(doc.id),
            title=doc.title,
            source=doc.source,
            content_preview=preview,
            has_embedding=doc.embedding is not None,
            created_at=doc.created_at.isoformat() if doc.created_at else None,
        )


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class KnowledgeDetail(BaseModel):
    id: str
    title: str
    source: str | None = None
    content: str
    has_embedding: bool
    created_at: str | None = None

    @classmethod
    def from_orm_model(cls, doc) -> "KnowledgeDetail":
        return cls(
            id=str(doc.id),
            title=doc.title,
            source=doc.source,
            content=doc.content,
            has_embedding=doc.embedding is not None,
            created_at=doc.created_at.isoformat() if doc.created_at else None,
        )


class KnowledgeSearchResult(BaseModel):
    title: str
    source: str | None = None
    content_preview: str
    distance: float

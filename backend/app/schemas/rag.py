from pydantic import BaseModel, Field, field_validator


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


def _strip_not_blank(v: str | None) -> str | None:
    """strip 后为空 → None，否则返回 strip 值。"""
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError("必须是字符串")
    s = v.strip()
    return s if s else None


def _strip_required(v: str) -> str:
    """strip 后必须非空。"""
    if not isinstance(v, str):
        raise ValueError("必须是字符串")
    s = v.strip()
    if not s:
        raise ValueError("不能为空")
    return s


class KnowledgeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content: str = Field(min_length=1)
    source: str | None = None

    @field_validator("title", "content", mode="before")
    @classmethod
    def _strip_required_fields(cls, v: str) -> str:
        return _strip_required(v)

    @field_validator("source", mode="before")
    @classmethod
    def _strip_source_create(cls, v: str | None) -> str | None:
        return _strip_not_blank(v)


class KnowledgeUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    content: str | None = None
    source: str | None = None

    @field_validator("title", "content", mode="before")
    @classmethod
    def _strip_update_fields(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("必须是字符串")
        s = v.strip()
        if not s:
            raise ValueError("不能为空")
        return s

    @field_validator("source", mode="before")
    @classmethod
    def _strip_source_update(cls, v: str | None) -> str | None:
        return _strip_not_blank(v)


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

    @field_validator("query", mode="before")
    @classmethod
    def _strip_query(cls, v: str) -> str:
        return _strip_required(v)


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

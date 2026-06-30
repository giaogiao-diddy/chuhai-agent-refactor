from pydantic import BaseModel


class RagDocumentMatch(BaseModel):
    title: str
    content: str
    source: str | None = None
    score: float

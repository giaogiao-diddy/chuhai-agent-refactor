from pydantic import BaseModel, Field


class ExtractedSlot(BaseModel):
    value: str | int | float | bool | list[str] | None
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractedAnswer(BaseModel):
    question_id: str
    option_ids: list[str]
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractionResult(BaseModel):
    slots: dict[str, ExtractedSlot | None] = Field(default_factory=dict)
    answers: list[ExtractedAnswer] = Field(default_factory=list)
    reasoning_summary: str | None = None

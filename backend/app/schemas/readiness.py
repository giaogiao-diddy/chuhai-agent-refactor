from pydantic import BaseModel, Field


class MissingItem(BaseModel):
    question_id: str
    label: str
    reason: str
    ask: str | None = None


class ReadinessResult(BaseModel):
    ready: bool
    score_ready: bool = False
    report_ready: bool = False
    missing_items: list[MissingItem] = Field(default_factory=list)
    report_missing_items: list[MissingItem] = Field(default_factory=list)
    next_questions: list[str] = Field(default_factory=list)
    unsupported_branch: bool = False

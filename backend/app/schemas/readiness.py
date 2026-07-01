from pydantic import BaseModel


class MissingItem(BaseModel):
    question_id: str
    label: str
    reason: str


class ReadinessResult(BaseModel):
    ready: bool
    missing_items: list[MissingItem] = []
    next_questions: list[str] = []
    unsupported_branch: bool = False

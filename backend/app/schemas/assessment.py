from __future__ import annotations
"""测评请求/响应模型"""

from pydantic import BaseModel, Field


class AnswerSubmit(BaseModel):
    question_id: int = Field(..., gt=0, strict=True)
    option_id: int | None = Field(default=None, gt=0)
    answer_text: str | None = Field(default=None, max_length=200)


class AssessmentComplete(BaseModel):
    """完成测评请求 — 答案已在 answers 表中，完成时只需校验数量"""
    pass


class AssessmentCreateResponse(BaseModel):
    id: int
    status: str


class AssessmentResponse(BaseModel):
    id: int
    total_score: int | None = None
    tag: str | None = None
    status: str
    benefit_minutes: int = 45
    completed_at: str | None = None

    class Config:
        from_attributes = True


class CompleteResponse(BaseModel):
    assessment_id: int
    total_score: int
    display_score: int
    tag: str
    tag_explanation: str
    status: str


class ReportStatusResponse(BaseModel):
    status: str
    generation_type: str | None = None
    has_summary: bool = False
    has_full: bool = False
    elapsed_seconds: int | None = None

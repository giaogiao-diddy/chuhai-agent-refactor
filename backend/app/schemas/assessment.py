from __future__ import annotations
"""测评请求/响应模型"""

from pydantic import BaseModel


class AnswerSubmit(BaseModel):
    question_id: int
    option_id: int


class AssessmentComplete(BaseModel):
    """完成测评请求 — 15 题答案已在 answers 表中，完成时只需校验数量"""
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
    tag: str
    status: str


class ReportStatusResponse(BaseModel):
    status: str
    generation_type: str | None = None
    has_summary: bool = False
    has_full: bool = False
    elapsed_seconds: int | None = None

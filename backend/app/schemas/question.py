from __future__ import annotations
"""题库响应模型"""

from pydantic import BaseModel


class OptionResponse(BaseModel):
    id: int
    text: str
    score: int
    sort_order: int

    class Config:
        from_attributes = True


class QuestionResponse(BaseModel):
    id: int
    title: str
    description: str = ""
    dimension: str
    sort_order: int
    options: list[OptionResponse] = []

    class Config:
        from_attributes = True


class QuestionListResponse(BaseModel):
    questions: list[QuestionResponse]
    total: int

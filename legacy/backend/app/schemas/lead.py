from __future__ import annotations
"""留资请求/响应模型"""

from pydantic import BaseModel, Field


class LeadCreate(BaseModel):
    assessment_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=32)
    contact: str = Field(..., min_length=2)
    company: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)


class LeadResponse(BaseModel):
    lead_id: int
    unlocked: bool
    benefit_minutes: int

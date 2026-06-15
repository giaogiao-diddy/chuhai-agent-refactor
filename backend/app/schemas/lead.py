from __future__ import annotations
"""留资请求/响应模型"""

from pydantic import BaseModel


class LeadCreate(BaseModel):
    name: str
    contact: str
    company: str
    role: str


class LeadResponse(BaseModel):
    lead_id: int
    unlocked: bool
    benefit_minutes: int

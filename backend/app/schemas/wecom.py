from __future__ import annotations
"""企业微信解锁相关 Schema"""

from pydantic import BaseModel, Field


class WeComUnlockSessionCreate(BaseModel):
    assessment_id: int = Field(..., gt=0)


class WeComUnlockSessionResponse(BaseModel):
    assessment_id: int
    is_unlocked: bool
    qr_code_url: str | None = None
    consultant_name: str | None = None
    polling_interval: float = 2.0
    message: str
    enable_mock_unlock: bool = False


class WeComUnlockStatusResponse(BaseModel):
    assessment_id: int
    is_unlocked: bool
    full_report_available: bool
    message: str


class WeComCustomerAddedRequest(BaseModel):
    assessment_id: int = Field(..., gt=0)
    external_user_id: str | None = None
    unionid: str | None = None
    openid: str | None = None
    event: str = "customer_added"


class MockUnlockRequest(BaseModel):
    assessment_id: int = Field(..., gt=0)

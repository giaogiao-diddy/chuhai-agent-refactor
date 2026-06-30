import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.anonymous import validate_anonymous_user_id

PHONE_PATTERN = r"^[0-9 +()\-]+$"
PHONE_ERROR = "phone 只能包含数字、空格、+、-、括号"


class LeadSubmissionCreate(BaseModel):
    anonymous_user_id: str | None = Field(default=None)
    contact_name: str
    phone: str
    wechat_id: str | None = Field(default=None)
    company_name: str | None = Field(default=None)
    note: str | None = Field(default=None)

    # ── anonymous_user_id ──

    @field_validator("anonymous_user_id")
    @classmethod
    def validate_anon_id(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_anonymous_user_id(v)

    # ── 字符串 strip (mode="before": 在类型校验后、长度校验前 strip) ──

    @field_validator("contact_name", "phone", mode="before")
    @classmethod
    def strip_before_validate(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("wechat_id", "company_name", "note", mode="before")
    @classmethod
    def strip_optional_before(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            stripped = v.strip()
            return stripped if stripped else None
        return v

    # ── contact_name ──

    @field_validator("contact_name")
    @classmethod
    def validate_contact_name(cls, v: str) -> str:
        if len(v) < 2:
            raise ValueError("contact_name 长度须至少为2")
        if len(v) > 50:
            raise ValueError("contact_name 长度须至多为50")
        return v

    # ── phone ──

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("phone 长度须至少为6")
        if len(v) > 30:
            raise ValueError("phone 长度须至多为30")
        if not re.fullmatch(PHONE_PATTERN, v):
            raise ValueError(PHONE_ERROR)
        return v

    # ── wechat_id ──

    @field_validator("wechat_id")
    @classmethod
    def validate_wechat_id(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) < 3 or len(v) > 80:
            raise ValueError("wechat_id 长度须为3-80位")
        return v

    # ── company_name ──

    @field_validator("company_name")
    @classmethod
    def validate_company_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) < 2 or len(v) > 100:
            raise ValueError("company_name 长度须为2-100位")
        return v

    # ── note ──

    @field_validator("note")
    @classmethod
    def validate_note(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) > 500:
            raise ValueError("note 长度须至多为500")
        return v


class LeadSubmissionResponse(BaseModel):
    submission_id: str
    assessment_id: str
    submitted: bool = True
    created_at: datetime

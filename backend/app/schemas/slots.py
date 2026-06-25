from pydantic import BaseModel, Field


class SlotValue(BaseModel):
    value: str | int | float | bool | list[str] | None
    confidence: float = Field(ge=0.0, le=1.0)
    source: str | None = None


class CompanySlots(BaseModel):
    company_name: SlotValue | None = None
    industry: SlotValue | None = None
    main_product: SlotValue | None = None
    target_market: SlotValue | None = None
    overseas_experience: SlotValue | None = None
    annual_revenue: SlotValue | None = None
    team_size: SlotValue | None = None
    sales_team_size: SlotValue | None = None
    overseas_order_ratio: SlotValue | None = None
    content_capability: SlotValue | None = None
    conversion_channel: SlotValue | None = None
    monthly_budget: SlotValue | None = None
    consultation_intent: SlotValue | None = None


class SlotMergeResult(BaseModel):
    slots: CompanySlots
    updated_fields: list[str]
    low_confidence_fields: list[str]
    ignored_fields: list[str]

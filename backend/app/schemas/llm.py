from typing import Literal

from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMResponse(BaseModel):
    content: str
    raw: dict | None = None


class SlotExtractionResult(BaseModel):
    industry: str | None = None
    main_product: str | None = None
    confidence: float

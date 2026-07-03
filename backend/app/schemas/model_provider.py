from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _mask_key(key: str) -> str:
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


def _validate_string(v: str | None) -> str | None:
    if v is None:
        return None
    if not isinstance(v, str):
        raise ValueError("必须是字符串")
    s = v.strip()
    if not s:
        raise ValueError("不能为空")
    return s


class ModelProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    base_url: str = Field(min_length=1, max_length=512)
    api_key: str = Field(min_length=1)
    default_model: str = Field(min_length=1, max_length=128)
    context_window: int = Field(default=128000, ge=1)
    enabled: bool = True

    @field_validator("name", "base_url", "default_model", "api_key", mode="before")
    @classmethod
    def _strip_fields(cls, v: str) -> str:
        return _validate_string(v)  # type: ignore


class ModelProviderUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    base_url: str | None = Field(default=None, max_length=512)
    api_key: str | None = None
    default_model: str | None = Field(default=None, max_length=128)
    context_window: int | None = Field(default=None, ge=1)
    enabled: bool | None = None

    @field_validator("name", "base_url", "default_model", "api_key", mode="before")
    @classmethod
    def _strip_optional_fields(cls, v: str | None) -> str | None:
        return _validate_string(v)


class ModelProviderResponse(BaseModel):
    id: str
    name: str
    provider_type: str
    base_url: str
    masked_key: str
    default_model: str
    enabled: bool
    context_window: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_orm_model(cls, p) -> "ModelProviderResponse":
        return cls(
            id=str(p.id),
            name=p.name,
            provider_type=p.provider_type,
            base_url=p.base_url,
            masked_key=_mask_key(p.api_key),
            default_model=p.default_model,
            enabled=p.enabled,
            context_window=p.context_window,
            created_at=p.created_at,
            updated_at=p.updated_at,
        )


class ModelProviderTestResponse(BaseModel):
    success: bool
    message: str
    model_used: str | None = None

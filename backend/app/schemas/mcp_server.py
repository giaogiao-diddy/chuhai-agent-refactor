from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class McpServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    transport: Literal["http"] = "http"
    url: str | None = None
    command: str | None = None
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    headers: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True

    @field_validator("name", "url", "command", mode="before")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        if v is None: return None
        if not isinstance(v, str): raise ValueError("必须是字符串")
        s = v.strip()
        return s if s else None

    @model_validator(mode="after")
    def _validate_http_url(self) -> "McpServerCreate":
        if self.transport == "http" and not self.url:
            raise ValueError("HTTP MCP Server 必须配置 url")
        return self


class McpServerUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    transport: Literal["http"] | None = None
    url: str | None = None
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    headers: dict[str, str] | None = None
    enabled: bool | None = None

    @field_validator("name", "url", "command", mode="before")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        if v is None: return None
        if not isinstance(v, str): raise ValueError("必须是字符串")
        s = v.strip()
        return s if s else None


class McpServerResponse(BaseModel):
    id: str
    name: str
    transport: str
    url: str | None = None
    command: str | None = None
    enabled: bool
    tools_count: int = 0
    connected: bool = False
    error_message: str | None = None
    created_at: str | None = None

    @classmethod
    def from_orm_model(cls, p) -> "McpServerResponse":
        return cls(
            id=str(p.id), name=p.name, transport=p.transport,
            url=p.url, command=p.command, enabled=p.enabled,
            created_at=p.created_at.isoformat() if p.created_at else None,
        )

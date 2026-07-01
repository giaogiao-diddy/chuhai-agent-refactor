from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class ToolErrorCode(StrEnum):
    TRANSIENT = "TRANSIENT"
    RATE_LIMITED = "RATE_LIMITED"
    AUTH_FAILED = "AUTH_FAILED"
    LENGTH_EXCEEDED = "LENGTH_EXCEEDED"
    STRUCTURED_OUTPUT_ERROR = "STRUCTURED_OUTPUT_ERROR"
    PERMANENT = "PERMANENT"


class ToolError(BaseModel):
    code: ToolErrorCode
    message: str
    retryable: bool


class ToolResult(BaseModel):
    data: Any | None = None
    error: ToolError | None = None


class ToolContext(BaseModel):
    assessment_id: str | None = None
    user_id: str | None = None
    db_session: Any | None = None
    abort_signal: Any | None = None

    model_config = {"arbitrary_types_allowed": True}


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_model: type[BaseModel]
    handler: Any = field(repr=False)
    output_model: type[BaseModel] | None = None
    is_read_only: bool = False
    is_concurrency_safe: bool = False
    is_destructive: bool = False
    max_retries: int = 0
    retry_delay_seconds: float = 0.5
    timeout_seconds: float = 60.0

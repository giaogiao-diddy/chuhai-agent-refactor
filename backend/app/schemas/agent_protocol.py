from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, model_validator

from app.schemas.agent_state import AgentState


class TerminalState(StrEnum):
    AWAITING_USER = "awaiting_user"
    MISSING_INFO = "missing_info"
    UNSUPPORTED_BRANCH = "unsupported_branch"
    COMPLETED = "completed"
    COMPLETED_WITH_TEMPLATE = "completed_with_template"
    FAILED = "failed"
    ABORTED = "aborted"
    MAX_STEPS_EXCEEDED = "max_steps_exceeded"


class AgentEvent(BaseModel):
    type: Literal["user_message", "finish_requested"]
    message: str | None = None

    @model_validator(mode="after")
    def _validate_message(self) -> "AgentEvent":
        if self.type == "user_message":
            if not self.message or not self.message.strip():
                raise ValueError("user_message 的 message 不能为空")
            stripped = self.message.strip()
            if len(stripped) < 1 or len(stripped) > 500:
                raise ValueError("消息长度需在 1-500 字符之间")
            self.message = stripped
        return self


class AgentRunResult(BaseModel):
    state: AgentState
    terminal: TerminalState
    response: dict[str, Any] | None = None

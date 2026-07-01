import app.agent.extraction as extraction_module
from pydantic import BaseModel

from app.agent.tools.base import ToolContext, ToolError, ToolErrorCode, ToolResult
from app.schemas.agent_state import AgentMessage
from app.schemas.extraction import ExtractionResult


class ExtractAnswersDeepSeekInput(BaseModel):
    messages: list[AgentMessage]


async def extract_answers_deepseek_handler(
    inp: ExtractAnswersDeepSeekInput,
    ctx: ToolContext,
) -> ToolResult:
    try:
        extraction = await extraction_module.extract_from_messages(inp.messages)
        return ToolResult(data=extraction)
    except Exception as e:
        return ToolResult(error=ToolError(
            code=ToolErrorCode.TRANSIENT,
            message=f"提取失败: {e}",
            retryable=True,
        ))

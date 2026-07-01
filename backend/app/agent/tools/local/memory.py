from pydantic import ValidationError

from app.agent.tools.base import ToolContext, ToolError, ToolErrorCode, ToolResult
from app.schemas.memory import (
    MemoryRecallInput,
    MemoryRecallOutput,
    MemorySaveInput,
    MemorySaveOutput,
)
from app.services.memory_store import recall_memory, save_memory


def memory_recall_handler(
    inp: MemoryRecallInput,
    ctx: ToolContext,
) -> ToolResult:
    entries = recall_memory(inp.query, inp.limit)
    return ToolResult(data=MemoryRecallOutput(entries=entries))


def memory_save_handler(
    inp: MemorySaveInput,
    ctx: ToolContext,
) -> ToolResult:
    try:
        rel_path = save_memory(
            name=inp.name,
            description=inp.description,
            mtype=inp.type,
            content=inp.content,
        )
        return ToolResult(data=MemorySaveOutput(
            path=rel_path,
            index_updated=True,
        ))
    except (ValueError, ValidationError) as e:
        return ToolResult(error=ToolError(
            code=ToolErrorCode.PERMANENT,
            message=str(e),
            retryable=False,
        ))

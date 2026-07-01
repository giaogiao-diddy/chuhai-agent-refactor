import asyncio
import inspect
from typing import Any

from pydantic import BaseModel

from app.agent.tools.base import ToolContext, ToolError, ToolErrorCode, ToolResult
from app.agent.tools.registry import ToolRegistry


class ToolCall(BaseModel):
    name: str
    input_data: dict[str, Any] | BaseModel


def _timeout_error() -> ToolError:
    return ToolError(
        code=ToolErrorCode.TRANSIENT,
        message="tool timeout",
        retryable=True,
    )


class ToolExecutor:
    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    async def execute(
        self,
        name: str,
        input_data: dict[str, Any] | BaseModel,
        context: ToolContext | None = None,
    ) -> ToolResult:
        tool = self._registry.get(name)
        validated = tool.input_model.model_validate(input_data)
        ctx = context or ToolContext()

        retries_left = tool.max_retries
        while True:
            result = await self._call_handler(tool, validated, ctx)
            if result.error is None:
                return self._validate_output(tool, result)
            if not self._should_retry(result.error, retries_left):
                return result
            retries_left -= 1
            await asyncio.sleep(tool.retry_delay_seconds)

    async def _call_handler(
        self,
        tool: Any,
        validated: BaseModel,
        context: ToolContext,
    ) -> ToolResult:
        is_async = inspect.iscoroutinefunction(tool.handler)
        try:
            if is_async:
                result = await asyncio.wait_for(
                    tool.handler(validated, context),
                    timeout=tool.timeout_seconds,
                )
            else:
                result = tool.handler(validated, context)
        except asyncio.TimeoutError:
            return ToolResult(error=_timeout_error())
        except Exception:
            raise

        if not isinstance(result, ToolResult):
            raise TypeError(
                f"Handler for tool '{tool.name}' must return ToolResult, "
                f"got {type(result).__name__}"
            )
        return result

    @staticmethod
    def _validate_output(tool: Any, result: ToolResult) -> ToolResult:
        if tool.output_model is not None and result.data is not None:
            validated_data = tool.output_model.model_validate(result.data)
            return ToolResult(data=validated_data)
        return result

    @staticmethod
    def _should_retry(error: Any, retries_left: int) -> bool:
        if retries_left <= 0:
            return False
        if error.code in (ToolErrorCode.AUTH_FAILED, ToolErrorCode.PERMANENT):
            return False
        if not error.retryable:
            return False
        return True

    async def execute_many(
        self,
        calls: list[ToolCall],
        context: ToolContext | None = None,
    ) -> list[ToolResult]:
        ctx = context or ToolContext()

        results: list[ToolResult | None] = [None] * len(calls)

        i = 0
        while i < len(calls):
            tool = self._registry.get(calls[i].name)

            if tool.is_read_only and tool.is_concurrency_safe:
                batch_indices = []
                j = i
                while j < len(calls):
                    t = self._registry.get(calls[j].name)
                    if t.is_read_only and t.is_concurrency_safe:
                        batch_indices.append(j)
                        j += 1
                    else:
                        break

                async def _run_one(idx: int) -> None:
                    results[idx] = await self.execute(
                        calls[idx].name,
                        calls[idx].input_data,
                        ctx,
                    )

                await asyncio.gather(*(_run_one(idx) for idx in batch_indices))
                i = j
            else:
                results[i] = await self.execute(
                    calls[i].name,
                    calls[i].input_data,
                    ctx,
                )
                i += 1

        return [r for r in results if r is not None]

import asyncio
import time

import pytest
from pydantic import BaseModel

from app.agent.tools.base import (
    ToolContext,
    ToolDefinition,
    ToolError,
    ToolErrorCode,
    ToolResult,
)
from app.agent.tools.executor import ToolCall, ToolExecutor
from app.agent.tools.registry import ToolRegistry


# ── 测试用 fake model ──

class FakeInput(BaseModel):
    text: str
    count: int = 1


class FakeOutput(BaseModel):
    result: str


class WrongInput(BaseModel):
    other: str


# ── 测试用 fake handler ──

def _ok_handler(inp: FakeInput, ctx: ToolContext) -> ToolResult:
    return ToolResult(data={"echo": inp.text, "count": inp.count})


def _fail_transient_handler(inp: FakeInput, ctx: ToolContext) -> ToolResult:
    return ToolResult(
        error=ToolError(
            code=ToolErrorCode.TRANSIENT,
            message="timeout",
            retryable=True,
        )
    )


def _fail_auth_handler(inp: FakeInput, ctx: ToolContext) -> ToolResult:
    return ToolResult(
        error=ToolError(
            code=ToolErrorCode.AUTH_FAILED,
            message="unauthorized",
            retryable=False,
        )
    )


def _fail_permanent_handler(inp: FakeInput, ctx: ToolContext) -> ToolResult:
    return ToolResult(
        error=ToolError(
            code=ToolErrorCode.PERMANENT,
            message="bad schema",
            retryable=False,
        )
    )


def _non_result_handler(inp: FakeInput, ctx: ToolContext) -> str:
    return "not a ToolResult"


def _crash_handler(inp: FakeInput, ctx: ToolContext) -> ToolResult:
    raise RuntimeError("boom")


async def _async_ok_handler(inp: FakeInput, ctx: ToolContext) -> ToolResult:
    await asyncio.sleep(0)
    return ToolResult(data={"async": True})


def _slow_safe_handler(inp: FakeInput, ctx: ToolContext) -> ToolResult:
    # 用一段小 sleep 让并发测试能观测到重叠
    time.sleep(0.05)
    return ToolResult(data={"done": True})


# ── 工厂 ──

def _make_tool(
    name="test",
    handler=_ok_handler,
    is_read_only=False,
    is_concurrency_safe=False,
    is_destructive=False,
    max_retries=0,
    retry_delay_seconds=0.01,
) -> ToolDefinition:
    return ToolDefinition(
        name=name,
        description=f"Tool {name}",
        input_model=FakeInput,
        handler=handler,
        is_read_only=is_read_only,
        is_concurrency_safe=is_concurrency_safe,
        is_destructive=is_destructive,
        max_retries=max_retries,
        retry_delay_seconds=retry_delay_seconds,
    )


# ═══════════════════════════════════════════════
# Registry
# ═══════════════════════════════════════════════

def test_registry_registers_and_gets_tool():
    r = ToolRegistry()
    t = _make_tool(name="my_tool")
    r.register(t)
    assert r.get("my_tool") is t


def test_registry_rejects_duplicate_tool_name():
    r = ToolRegistry()
    r.register(_make_tool(name="dup"))
    with pytest.raises(ValueError, match="dup"):
        r.register(_make_tool(name="dup"))


def test_registry_missing_tool_raises():
    r = ToolRegistry()
    with pytest.raises(KeyError, match="no_such"):
        r.get("no_such")


def test_registry_lists_all_tools_in_order():
    r = ToolRegistry()
    r.register(_make_tool(name="a"))
    r.register(_make_tool(name="b"))
    assert [t.name for t in r.list_all()] == ["a", "b"]


def test_registry_lists_read_only_tools():
    r = ToolRegistry()
    r.register(_make_tool(name="rw"))
    r.register(_make_tool(name="ro", is_read_only=True))
    ro_list = r.list_read_only()
    assert len(ro_list) == 1
    assert ro_list[0].name == "ro"


# ═══════════════════════════════════════════════
# ToolDefinition defaults
# ═══════════════════════════════════════════════

def test_tool_definition_defaults_fail_closed():
    t = ToolDefinition(
        name="t",
        description="d",
        input_model=FakeInput,
        handler=_ok_handler,
    )
    assert t.is_read_only is False
    assert t.is_concurrency_safe is False
    assert t.is_destructive is False
    assert t.max_retries == 0


# ═══════════════════════════════════════════════
# Execute
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_executor_validates_input_model():
    r = ToolRegistry()
    r.register(_make_tool())
    ex = ToolExecutor(r)
    with pytest.raises(Exception):  # Pydantic validation
        await ex.execute("test", {"bad_field": 1})


@pytest.mark.asyncio
async def test_executor_runs_sync_handler():
    r = ToolRegistry()
    r.register(_make_tool())
    ex = ToolExecutor(r)
    result = await ex.execute("test", {"text": "hello", "count": 2})
    assert result.data == {"echo": "hello", "count": 2}
    assert result.error is None


@pytest.mark.asyncio
async def test_executor_runs_async_handler():
    r = ToolRegistry()
    r.register(_make_tool(handler=_async_ok_handler))
    ex = ToolExecutor(r)
    result = await ex.execute("test", {"text": "x"})
    assert result.data == {"async": True}


@pytest.mark.asyncio
async def test_executor_accepts_pydantic_input():
    r = ToolRegistry()
    r.register(_make_tool())
    ex = ToolExecutor(r)
    result = await ex.execute("test", FakeInput(text="direct", count=3))
    assert result.data == {"echo": "direct", "count": 3}


@pytest.mark.asyncio
async def test_executor_rejects_non_tool_result():
    r = ToolRegistry()
    r.register(_make_tool(handler=_non_result_handler))
    ex = ToolExecutor(r)
    with pytest.raises(TypeError, match="ToolResult"):
        await ex.execute("test", {"text": "x"})


@pytest.mark.asyncio
async def test_executor_propagates_programming_error():
    r = ToolRegistry()
    r.register(_make_tool(handler=_crash_handler))
    ex = ToolExecutor(r)
    with pytest.raises(RuntimeError, match="boom"):
        await ex.execute("test", {"text": "x"})


# ═══════════════════════════════════════════════
# Retry
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_executor_does_not_retry_auth_failed():
    call_count = 0

    def counting_auth(inp: FakeInput, ctx: ToolContext) -> ToolResult:
        nonlocal call_count
        call_count += 1
        return ToolResult(
            error=ToolError(
                code=ToolErrorCode.AUTH_FAILED,
                message="unauthorized",
                retryable=False,
            )
        )

    r = ToolRegistry()
    r.register(_make_tool(handler=counting_auth, max_retries=3, retry_delay_seconds=0))
    ex = ToolExecutor(r)
    result = await ex.execute("test", {"text": "x"})
    assert result.error is not None
    assert result.error.code == ToolErrorCode.AUTH_FAILED
    assert call_count == 1


@pytest.mark.asyncio
async def test_executor_does_not_retry_permanent_error():
    call_count = 0

    def counting(inp: FakeInput, ctx: ToolContext) -> ToolResult:
        nonlocal call_count
        call_count += 1
        return ToolResult(
            error=ToolError(
                code=ToolErrorCode.PERMANENT,
                message="bad",
                retryable=False,
            )
        )

    r = ToolRegistry()
    r.register(_make_tool(handler=counting, max_retries=3, retry_delay_seconds=0))
    ex = ToolExecutor(r)
    result = await ex.execute("test", {"text": "x"})
    assert result.error.code == ToolErrorCode.PERMANENT
    assert call_count == 1


@pytest.mark.asyncio
async def test_executor_retries_retryable_error():
    call_count = 0

    def flaky(inp: FakeInput, ctx: ToolContext) -> ToolResult:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            return ToolResult(
                error=ToolError(
                    code=ToolErrorCode.TRANSIENT,
                    message="fail",
                    retryable=True,
                )
            )
        return ToolResult(data={"success": True})

    r = ToolRegistry()
    r.register(_make_tool(handler=flaky, max_retries=2, retry_delay_seconds=0))
    ex = ToolExecutor(r)
    result = await ex.execute("test", {"text": "x"})
    assert result.data == {"success": True}
    assert call_count == 3  # 2 failures + 1 success


@pytest.mark.asyncio
async def test_executor_stops_after_successful_retry():
    call_count = 0

    def flaky2(inp: FakeInput, ctx: ToolContext) -> ToolResult:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            return ToolResult(
                error=ToolError(
                    code=ToolErrorCode.TRANSIENT,
                    message="fail",
                    retryable=True,
                )
            )
        return ToolResult(data={"ok": True})

    r = ToolRegistry()
    r.register(_make_tool(handler=flaky2, max_retries=3, retry_delay_seconds=0))
    ex = ToolExecutor(r)
    result = await ex.execute("test", {"text": "x"})
    assert result.data == {"ok": True}
    assert call_count == 2  # 1 failure + 1 success (not 4)


@pytest.mark.asyncio
async def test_executor_exhausts_retries():
    call_count = 0

    def always_fail(inp: FakeInput, ctx: ToolContext) -> ToolResult:
        nonlocal call_count
        call_count += 1
        return ToolResult(
            error=ToolError(
                code=ToolErrorCode.TRANSIENT,
                message="fail",
                retryable=True,
            )
        )

    r = ToolRegistry()
    r.register(_make_tool(handler=always_fail, max_retries=2, retry_delay_seconds=0))
    ex = ToolExecutor(r)
    result = await ex.execute("test", {"text": "x"})
    assert result.error is not None
    assert call_count == 3  # 1 initial + 2 retries


# ═══════════════════════════════════════════════
# execute_many 并发与顺序
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_execute_many_parallelizes_read_only_concurrency_safe_tools():
    """两个只读并发安全工具应该同时进入执行。"""
    started: list[str] = []
    concurrency_observed = False

    async def concurrent_handler(inp: FakeInput, ctx: ToolContext) -> ToolResult:
        nonlocal concurrency_observed
        started.append(inp.text)
        if len(started) >= 2:
            concurrency_observed = True  # 第二个进入时第一个还没完成
        await asyncio.sleep(0.05)
        started.remove(inp.text)
        return ToolResult(data={"ok": True})

    r = ToolRegistry()
    r.register(ToolDefinition(
        name="safe_a",
        description="safe a",
        input_model=FakeInput,
        handler=concurrent_handler,
        is_read_only=True,
        is_concurrency_safe=True,
    ))
    r.register(ToolDefinition(
        name="safe_b",
        description="safe b",
        input_model=FakeInput,
        handler=concurrent_handler,
        is_read_only=True,
        is_concurrency_safe=True,
    ))

    ex = ToolExecutor(r)
    calls = [
        ToolCall(name="safe_a", input_data={"text": "a"}),
        ToolCall(name="safe_b", input_data={"text": "b"}),
    ]
    results = await ex.execute_many(calls)
    assert len(results) == 2
    assert concurrency_observed, "两个并发安全工具应同时进入执行"


@pytest.mark.asyncio
async def test_execute_many_runs_write_tools_serially():
    """非并发安全工具必须按顺序执行。"""
    execution_order: list[str] = []
    active = 0

    async def serial_handler(inp: FakeInput, ctx: ToolContext) -> ToolResult:
        nonlocal active
        execution_order.append(inp.text)
        active += 1
        assert active == 1, f"串行工具不应并发执行，当前活跃数: {active}"
        await asyncio.sleep(0.03)
        active -= 1
        return ToolResult(data={"ok": True})

    r = ToolRegistry()
    r.register(ToolDefinition(
        name="write_a",
        description="write a",
        input_model=FakeInput,
        handler=serial_handler,
        is_read_only=False,
    ))
    r.register(ToolDefinition(
        name="write_b",
        description="write b",
        input_model=FakeInput,
        handler=serial_handler,
        is_read_only=False,
    ))

    ex = ToolExecutor(r)
    calls = [
        ToolCall(name="write_a", input_data={"text": "a"}),
        ToolCall(name="write_b", input_data={"text": "b"}),
    ]
    results = await ex.execute_many(calls)
    assert len(results) == 2
    assert execution_order == ["a", "b"], f"串行工具应按顺序执行，实际: {execution_order}"


@pytest.mark.asyncio
async def test_execute_many_preserves_result_order():
    """结果顺序必须与 calls 顺序一致。"""
    async def make_handler(label: str):
        async def h(inp: FakeInput, ctx: ToolContext) -> ToolResult:
            await asyncio.sleep(0.02)
            return ToolResult(data={"label": label})
        return h

    r = ToolRegistry()
    for name in ["first", "second", "third"]:
        r.register(ToolDefinition(
            name=name,
            description=name,
            input_model=FakeInput,
            handler=await make_handler(name),
            is_read_only=True,
            is_concurrency_safe=True,
        ))

    ex = ToolExecutor(r)
    calls = [
        ToolCall(name="first", input_data={"text": "x"}),
        ToolCall(name="second", input_data={"text": "x"}),
        ToolCall(name="third", input_data={"text": "x"}),
    ]
    results = await ex.execute_many(calls)
    labels = [r.data["label"] for r in results]
    assert labels == ["first", "second", "third"]


@pytest.mark.asyncio
async def test_execute_many_mixed_batch_handles_serially_after_concurrent():
    """混合场景：并发 batch → 串行工具 → 恢复。"""
    execution_order: list[str] = []

    async def record_handler(inp: FakeInput, ctx: ToolContext) -> ToolResult:
        execution_order.append(inp.text)
        await asyncio.sleep(0.02)
        return ToolResult(data={"ok": True})

    r = ToolRegistry()
    r.register(ToolDefinition(
        name="safe", description="s",
        input_model=FakeInput, handler=record_handler,
        is_read_only=True, is_concurrency_safe=True,
    ))
    r.register(ToolDefinition(
        name="write", description="w",
        input_model=FakeInput, handler=record_handler,
        is_read_only=False,
    ))

    ex = ToolExecutor(r)
    calls = [
        ToolCall(name="safe", input_data={"text": "s1"}),
        ToolCall(name="safe", input_data={"text": "s2"}),
        ToolCall(name="write", input_data={"text": "w1"}),
        ToolCall(name="safe", input_data={"text": "s3"}),
    ]
    results = await ex.execute_many(calls)
    assert len(results) == 4
    # s1 和 s2 并发跑，w1 在它们之后串行，s3 在 w1 之后
    w_idx = execution_order.index("w1")
    s3_idx = execution_order.index("s3")
    assert w_idx < s3_idx, f"write 应在 s3 之前执行，实际: {execution_order}"


@pytest.mark.asyncio
async def test_execute_many_handles_empty_calls():
    r = ToolRegistry()
    ex = ToolExecutor(r)
    results = await ex.execute_many([])
    assert results == []


# ═══════════════════════════════════════════════
# timeout_seconds
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_executor_async_handler_timeout_returns_transient_error():
    async def slow_handler(inp: FakeInput, ctx: ToolContext) -> ToolResult:
        await asyncio.sleep(0.5)
        return ToolResult(data={"ok": True})

    r = ToolRegistry()
    r.register(ToolDefinition(
        name="slow",
        description="slow tool",
        input_model=FakeInput,
        handler=slow_handler,
        timeout_seconds=0.05,
    ))
    ex = ToolExecutor(r)
    result = await ex.execute("slow", {"text": "x"})
    assert result.error is not None
    assert result.error.code == ToolErrorCode.TRANSIENT
    assert result.error.message == "tool timeout"
    assert result.error.retryable is True


@pytest.mark.asyncio
async def test_executor_timeout_can_retry_and_succeed():
    call_count = 0

    async def timeout_then_ok(inp: FakeInput, ctx: ToolContext) -> ToolResult:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            await asyncio.sleep(0.3)  # 第一次超时
            return ToolResult(data={"ok": True})
        return ToolResult(data={"ok": True})  # 第二次快速返回

    r = ToolRegistry()
    r.register(ToolDefinition(
        name="flaky_slow",
        description="flaky",
        input_model=FakeInput,
        handler=timeout_then_ok,
        max_retries=1,
        retry_delay_seconds=0,
        timeout_seconds=0.05,
    ))
    ex = ToolExecutor(r)
    result = await ex.execute("flaky_slow", {"text": "x"})
    assert result.data == {"ok": True}
    assert call_count == 2


# ═══════════════════════════════════════════════
# output_model 校验
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_executor_validates_output_model():
    def ok_output_handler(inp: FakeInput, ctx: ToolContext) -> ToolResult:
        return ToolResult(data={"result": "valid"})

    r = ToolRegistry()
    r.register(ToolDefinition(
        name="with_output",
        description="has output model",
        input_model=FakeInput,
        handler=ok_output_handler,
        output_model=FakeOutput,
    ))
    ex = ToolExecutor(r)
    result = await ex.execute("with_output", {"text": "x"})
    assert result.error is None
    assert isinstance(result.data, FakeOutput)
    assert result.data.result == "valid"


@pytest.mark.asyncio
async def test_executor_output_model_validation_error_propagates():
    def bad_output_handler(inp: FakeInput, ctx: ToolContext) -> ToolResult:
        return ToolResult(data={"wrong_field": 123})

    r = ToolRegistry()
    r.register(ToolDefinition(
        name="bad_output",
        description="bad output",
        input_model=FakeInput,
        handler=bad_output_handler,
        output_model=FakeOutput,
    ))
    ex = ToolExecutor(r)
    with pytest.raises(Exception):
        await ex.execute("bad_output", {"text": "x"})


@pytest.mark.asyncio
async def test_executor_does_not_validate_output_when_error_present():
    def error_with_data(inp: FakeInput, ctx: ToolContext) -> ToolResult:
        return ToolResult(
            data={"result": "ignored"},
            error=ToolError(code=ToolErrorCode.PERMANENT, message="fail", retryable=False),
        )

    r = ToolRegistry()
    r.register(ToolDefinition(
        name="error_tool",
        description="returns error",
        input_model=FakeInput,
        handler=error_with_data,
        output_model=FakeOutput,
    ))
    ex = ToolExecutor(r)
    result = await ex.execute("error_tool", {"text": "x"})
    # error 存在时不校验 output，原样返回
    assert result.error is not None
    assert result.error.code == ToolErrorCode.PERMANENT
    assert result.data == {"result": "ignored"}  # 不经过 model_validate


# ═══════════════════════════════════════════════
# Pydantic input 校验
# ═══════════════════════════════════════════════

@pytest.mark.asyncio
async def test_executor_validates_pydantic_input_against_tool_model():
    """同类型的 BaseModel input 应正常通过 model_validate。"""
    r = ToolRegistry()
    r.register(_make_tool())
    ex = ToolExecutor(r)
    result = await ex.execute("test", FakeInput(text="valid", count=5))
    assert result.data == {"echo": "valid", "count": 5}


@pytest.mark.asyncio
async def test_executor_rejects_wrong_pydantic_input_model():
    """不同 schema 的 BaseModel input 应抛 ValidationError。"""
    r = ToolRegistry()
    r.register(_make_tool())
    ex = ToolExecutor(r)
    with pytest.raises(Exception):
        await ex.execute("test", WrongInput(other="wrong schema"))

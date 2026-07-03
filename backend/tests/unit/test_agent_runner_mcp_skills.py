import pytest

from app.agent.runner import _build_tool_registry, run_agent_event
from app.agent.tools.base import ToolContext, ToolDefinition, ToolResult
from app.agent.tools.external.rag import RagSearchInput, RagSearchOutput
from app.agent.tools.registry import ToolRegistry
from app.schemas.agent_protocol import AgentEvent, TerminalState
from app.schemas.agent_state import AgentState
from app.schemas.rag import RagDocumentMatch
from app.schemas.slots import SlotValue


@pytest.mark.asyncio
async def test_build_tool_registry_registers_enabled_mcp_tools(monkeypatch):
    async def fake_register(registry, db_session):
        registry.register(
            ToolDefinition(
                name="mcp__tariff__query_rate",
                description="query tariff",
                input_model=RagSearchInput,
                handler=lambda inp, ctx: ToolResult(data={"ok": True}),
            )
        )
        return 1

    monkeypatch.setattr("app.agent.runner.register_enabled_mcp_tools", fake_register)

    registry = await _build_tool_registry(db_session=object())

    assert registry.get("mcp__tariff__query_rate").name == "mcp__tariff__query_rate"


@pytest.mark.asyncio
async def test_user_message_slash_market_access_invokes_skill():
    captured_queries = []

    def fake_rag(inp: RagSearchInput, ctx: ToolContext) -> ToolResult:
        captured_queries.append(inp.query)
        return ToolResult(
            data=RagSearchOutput(
                matches=[
                    RagDocumentMatch(
                        title="泰国服装市场准入",
                        content="泰国服装进口需要关注标签、质检和平台规则。",
                        source="test",
                        score=0.9,
                    )
                ]
            )
        )

    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="rag.search",
            description="search rag",
            input_model=RagSearchInput,
            handler=fake_rag,
        )
    )
    state = AgentState()
    state.slots.main_product = SlotValue(value="女装", confidence=1.0)
    state.slots.target_market = SlotValue(value="泰国", confidence=1.0)

    result = await run_agent_event(
        state,
        AgentEvent(type="user_message", message="/market-access"),
        registry=registry,
    )

    assert result.terminal == TerminalState.AWAITING_USER
    assert "市场准入分析" in result.response["assistant_message"]
    assert captured_queries == ["女装 泰国 出口认证 关税 合规"]

import pytest
from pydantic import ValidationError

from app.agent.mcp.adapter import build_mcp_tool_def
from app.agent.mcp.naming import build_mcp_tool_name, mcp_info_from_string
from app.agent.tools.executor import ToolExecutor
from app.agent.tools.registry import ToolRegistry


def test_mcp_tool_name_normalizes_server_and_tool_names():
    name = build_mcp_tool_name("Tariff Lookup", "get rate")

    assert name == "mcp__tariff_lookup__get_rate"
    assert mcp_info_from_string(name) == {
        "server_name": "tariff_lookup",
        "tool_name": "get_rate",
    }


@pytest.mark.asyncio
async def test_mcp_tool_required_fields_are_required():
    tool = build_mcp_tool_def(
        "tariff",
        "https://mcp.example.com",
        {
            "name": "query_rate",
            "inputSchema": {
                "type": "object",
                "required": ["country", "hs_code"],
                "properties": {
                    "country": {"type": "string"},
                    "hs_code": {"type": "string"},
                    "top_k": {"type": "integer", "default": 3},
                },
            },
        },
    )
    registry = ToolRegistry()
    registry.register(tool)

    with pytest.raises(ValidationError):
        await ToolExecutor(registry).execute(
            "mcp__tariff__query_rate",
            {"country": "TH"},
        )


@pytest.mark.asyncio
async def test_mcp_tool_optional_fields_default_to_none(monkeypatch):
    captured = {}

    async def fake_call(server_url, tool_name, params, headers=None):
        captured["params"] = params
        return {"content": [{"type": "text", "text": "ok"}]}

    monkeypatch.setattr("app.agent.mcp.adapter._call_mcp_tool", fake_call)

    tool = build_mcp_tool_def(
        "tariff",
        "https://mcp.example.com",
        {
            "name": "query_rate",
            "inputSchema": {
                "type": "object",
                "required": ["country"],
                "properties": {
                    "country": {"type": "string"},
                    "note": {"type": "string"},
                },
            },
        },
    )
    registry = ToolRegistry()
    registry.register(tool)

    result = await ToolExecutor(registry).execute(
        "mcp__tariff__query_rate",
        {"country": "TH"},
    )

    assert result.error is None
    assert captured["params"] == {"country": "TH", "note": None}

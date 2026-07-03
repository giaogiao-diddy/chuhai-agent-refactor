import asyncio
import logging
from typing import Any

import httpx
from pydantic import BaseModel, Field, create_model

from app.agent.mcp.naming import build_mcp_tool_name
from app.agent.tools.base import ToolContext, ToolDefinition, ToolError, ToolErrorCode, ToolResult
from app.agent.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class McpCallError(Exception):
    def __init__(self, code: ToolErrorCode, message: str, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def _http_error(status_code: int, text: str = "") -> McpCallError:
    if status_code in (401, 403):
        return McpCallError(ToolErrorCode.AUTH_FAILED, f"MCP server returned {status_code}", False)
    if status_code == 429:
        return McpCallError(ToolErrorCode.RATE_LIMITED, "MCP server rate limited", True)
    if 400 <= status_code < 500:
        return McpCallError(ToolErrorCode.PERMANENT, f"MCP server returned {status_code}", False)
    return McpCallError(ToolErrorCode.TRANSIENT, f"MCP server returned {status_code}", True)


async def _call_mcp_tool(server_url: str, tool_name: str, params: dict, headers: dict | None = None) -> dict:
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": params},
        "id": 1,
    }
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(server_url, json=payload, headers=h)
    if resp.status_code != 200:
        raise _http_error(resp.status_code, resp.text[:200])
    data = resp.json()
    if "error" in data:
        raise McpCallError(ToolErrorCode.PERMANENT, "MCP tool returned error", False)
    return data.get("result", {})


def _json_schema_type(prop_info: dict) -> Any:
    prop_type = prop_info.get("type", "string")
    if prop_type == "string":
        return str
    if prop_type == "number":
        return float
    if prop_type == "integer":
        return int
    if prop_type == "boolean":
        return bool
    if prop_type == "array":
        return list[Any]
    if prop_type == "object":
        return dict[str, Any]
    return Any


def build_mcp_tool_def(server_name: str, server_url: str, tool_schema: dict, headers: dict | None = None) -> ToolDefinition:
    tool_name = tool_schema["name"]
    full_name = build_mcp_tool_name(server_name, tool_name)
    desc = tool_schema.get("description", "")[:2048]  # Claude Code: MAX_MCP_DESCRIPTION_LENGTH

    input_schema = tool_schema.get("inputSchema", {})
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    fields: dict = {}
    for prop_name, prop_info in properties.items():
        desc_text = prop_info.get("description", "")
        py_type = _json_schema_type(prop_info)
        if prop_name in required:
            fields[prop_name] = (py_type, Field(default=..., description=desc_text))
        elif "default" in prop_info:
            fields[prop_name] = (py_type, Field(default=prop_info["default"], description=desc_text))
        else:
            fields[prop_name] = (py_type | None, Field(default=None, description=desc_text))

    DynamicInput = create_model(f"MCP_{full_name}_Input", **fields) if fields else BaseModel

    async def handler(inp, ctx: ToolContext) -> ToolResult:
        try:
            params = inp.model_dump() if hasattr(inp, "model_dump") else {}
            result = await _call_mcp_tool(server_url, tool_name, params, headers)
            content = result.get("content", [])
            text_parts = [c.get("text", "") for c in content if isinstance(c, dict)]
            return ToolResult(data={"result": "\n".join(text_parts) or str(result)})
        except McpCallError as e:
            return ToolResult(error=ToolError(code=e.code, message=str(e)[:500], retryable=e.retryable))
        except Exception as e:
            return ToolResult(error=ToolError(code=ToolErrorCode.TRANSIENT, message=str(e)[:500], retryable=True))

    return ToolDefinition(
        name=full_name,
        description=desc,
        input_model=DynamicInput,
        handler=handler,
        is_read_only=True,
        is_concurrency_safe=False,
        max_retries=1,
        timeout_seconds=30.0,
    )


async def list_mcp_tools(server_url: str, headers: dict | None = None) -> list[dict]:
    payload = {"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}
    h = {"Content-Type": "application/json"}
    if headers: h.update(headers)
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(server_url, json=payload, headers=h)
    if resp.status_code != 200:
        raise _http_error(resp.status_code, resp.text[:200])
    data = resp.json()
    return data.get("result", {}).get("tools", [])


async def register_mcp_tools(registry, server_name: str, server_url: str, headers: dict | None = None) -> int:
    try:
        tools = await list_mcp_tools(server_url, headers)
    except Exception as e:
        logger.warning("Failed to list MCP tools from %s: %s", server_name, e)
        return 0

    count = 0
    for tool_schema in tools:
        try:
            tool_def = build_mcp_tool_def(server_name, server_url, tool_schema, headers)
            registry.register(tool_def)
            count += 1
        except Exception as e:
            logger.warning("Failed to register MCP tool %s: %s", tool_schema.get("name"), e)

    return count


async def register_enabled_mcp_tools(registry: ToolRegistry, db_session) -> int:
    from app.services.mcp_server_repository import list_enabled_http_servers

    count = 0
    try:
        servers = await list_enabled_http_servers(db_session)
    except Exception as e:
        logger.warning("Failed to load enabled MCP servers: %s", e)
        return 0

    for server in servers:
        if server.url:
            count += await register_mcp_tools(
                registry,
                server.name,
                server.url,
                server.headers or {},
            )
    return count

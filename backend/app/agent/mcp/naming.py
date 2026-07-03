"""MCP tool naming helpers."""

import re


def normalize_mcp_name(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    if "__" in normalized:
        normalized = normalized.replace("__", "_")
    if not normalized:
        raise ValueError("invalid MCP name")
    return normalized


def build_mcp_tool_name(server_name: str, tool_name: str) -> str:
    return f"mcp__{normalize_mcp_name(server_name)}__{normalize_mcp_name(tool_name)}"


def mcp_info_from_string(tool_name: str) -> dict | None:
    parts = tool_name.split("__")
    if parts[0] != "mcp" or len(parts) < 3:
        return None
    return {
        "server_name": parts[1],
        "tool_name": "__".join(parts[2:]),
    }


def get_mcp_prefix(server_name: str) -> str:
    return f"mcp__{normalize_mcp_name(server_name)}__"

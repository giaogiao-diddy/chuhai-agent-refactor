from app.agent.skills.discovery import _parse_frontmatter


def test_parse_frontmatter_without_yaml_dependency():
    fm = _parse_frontmatter(
        """---
name: market-access
description: 市场准入
user_invocable: true
allowed_tools:
  - rag.search
  - mcp__tariff__query_rate
---

body
"""
    )

    assert fm["name"] == "market-access"
    assert fm["description"] == "市场准入"
    assert fm["user_invocable"] is True
    assert fm["allowed_tools"] == ["rag.search", "mcp__tariff__query_rate"]

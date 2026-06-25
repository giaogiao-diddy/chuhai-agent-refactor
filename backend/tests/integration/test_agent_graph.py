import asyncio

import pytest

from app.agent.graph import run_dialogue_graph
from app.agent.nodes import dialogue_node, opening_node
from app.agent.state_machine import (
    append_assistant_message,
    append_user_message,
)
from app.schemas.agent_state import AgentState
from config import get_settings


def _new_state(**kwargs) -> AgentState:
    return AgentState(**kwargs)


# ── 空 state：只返回开场白，不调用 DeepSeek ─────────────────────

def test_opening_node_adds_opening_message():
    state = _new_state()
    result = asyncio.run(opening_node(state))
    assert len(result.messages) == 1
    assert result.messages[0].role == "assistant"
    assert result.messages[0].content != ""


def test_dialogue_graph_empty_state_only_returns_opening_message():
    state = _new_state()
    result = asyncio.run(run_dialogue_graph(state))
    assert len(result.messages) == 1
    assert result.messages[0].role == "assistant"


# ── dialogue_node 前置条件 ──────────────────────────────────────

def test_dialogue_node_skips_when_last_message_not_user():
    state = _new_state()
    state = append_assistant_message(state, "你好，我是顾问。")
    result = asyncio.run(dialogue_node(state))
    assert result == state  # 未修改，跳过 AI 调用


# ── 路由：assistant + user → dialogue ───────────────────────────

@pytest.mark.ai
@pytest.mark.integration
async def test_dialogue_graph_routes_user_after_assistant_to_dialogue():
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY:
        pytest.skip("DEEPSEEK_API_KEY 未配置")

    state = append_assistant_message(
        _new_state(),
        "你好，我是深度未来的企业出海诊断顾问。先从最关键的开始：你们主要做什么产品？目前有没有海外客户或外贸经验？",
    )
    state = append_user_message(state, "我们做健身器材，有少量东南亚客户。")
    result = await run_dialogue_graph(state)

    assert len(result.messages) >= 3  # opening + user + ai reply
    assert result.messages[-1].role == "assistant"


# ── dialogue_node 不初始化 DeepSeekClient 当不需要调用时 ─────────

def test_dialogue_node_skip_does_not_initialize_deepseek(monkeypatch):
    def _fail(*args, **kwargs):
        raise RuntimeError("DeepSeekClient 不应被初始化")

    monkeypatch.setattr(
        "app.agent.nodes.DeepSeekClient",
        lambda: _fail(),
    )

    state = _new_state()
    state = append_assistant_message(state, "你好，我是顾问。")
    # 不应抛错——最后一条是 assistant，跳过 AI
    result = asyncio.run(dialogue_node(state))
    assert result == state


# ── 真实 DeepSeek ──────────────────────────────────────────────

@pytest.mark.ai
@pytest.mark.integration
async def test_dialogue_node_real_deepseek():
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY:
        pytest.skip("DEEPSEEK_API_KEY 未配置")

    state = _new_state()
    state = append_user_message(state, "我们是一家做健身器材的工厂，有少量东南亚客户。")
    result = await dialogue_node(state)

    assert result.messages[-1].role == "assistant"
    assert result.messages[-1].content
    assert result.ai_failure_count == 0


@pytest.mark.ai
@pytest.mark.integration
async def test_dialogue_graph_real_deepseek():
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY:
        pytest.skip("DEEPSEEK_API_KEY 未配置")

    state = _new_state()
    state = append_user_message(state, "我们是一家做健身器材的工厂。")
    result = await run_dialogue_graph(state)

    assert len(result.messages) >= 2
    assert result.messages[-1].role == "assistant"
    assert result.messages[-1].content
    assert len(result.messages) <= 12

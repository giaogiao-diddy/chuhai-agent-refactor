import pytest

from app.agent.runner import run_agent_event
from app.agent.tools.external import register_external_tools
from app.agent.tools.local import register_local_tools
from app.agent.tools.registry import ToolRegistry
from app.schemas.agent_protocol import AgentEvent, TerminalState
from app.schemas.agent_state import AgentState


def _build_registry() -> ToolRegistry:
    r = ToolRegistry()
    register_local_tools(r)
    register_external_tools(r)
    return r


# ── AI tests ──

@pytest.mark.ai
@pytest.mark.asyncio
async def test_agent_runner_continue_real_deepseek():
    """真实 DeepSeek: user_message 路径应生成追问。"""
    state = AgentState()
    result = await run_agent_event(
        state,
        AgentEvent(type="user_message",
                   message="我们是做女装上衣的工厂，有少量泰国 Shopee 订单，预算每月5万"),
        _build_registry(),
    )
    assert result.terminal == TerminalState.AWAITING_USER
    assert len(result.state.messages) >= 2
    has_assistant = any(m.role == "assistant" for m in result.state.messages)
    assert has_assistant, "应有 assistant 回复"
    # readiness_result 应有值
    assert result.state.readiness_result is not None
    # assistant 回复应包含追问，不应输出详细投放计划
    assistant_text = ""
    for m in reversed(result.state.messages):
        if m.role == "assistant":
            assistant_text = m.content
            break
    assert len(assistant_text) > 0
    # 不应输出详细投放计划（预算分配/广告投放/KOC等）
    plan_keywords = ["预算分配", "广告投放方案", "KOC", "KOL执行"]
    for kw in plan_keywords:
        assert kw not in assistant_text, f"不应输出 '{kw}' 等执行建议"

    # 响应不泄露内部字段
    if result.response:
        resp_str = str(result.response)
        for forbidden in ["lead_score", "lead_priority", "sales_followup", "consultant_notes"]:
            assert forbidden not in resp_str, f"response 不应包含 {forbidden}"


@pytest.mark.ai
@pytest.mark.asyncio
async def test_agent_runner_continue_extracts_answers():
    """真实 DeepSeek: 提取应产出 slots 或 answers。"""
    state = AgentState()
    result = await run_agent_event(
        state,
        AgentEvent(type="user_message",
                   message="我们是深圳的3C配件源头工厂，成立8年，去年营收8000万，主要做手机壳和充电器"),
        _build_registry(),
    )
    has_answers = len(result.state.answers) > 0
    has_slots = bool(
        (result.state.slots.industry and result.state.slots.industry.value) or
        (result.state.slots.main_product and result.state.slots.main_product.value)
    )
    assert has_answers or has_slots, "至少应有 answers 或 slots 被提取"

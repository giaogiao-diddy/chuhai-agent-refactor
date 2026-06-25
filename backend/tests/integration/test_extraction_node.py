import pytest

from app.agent.extraction import extract_from_messages
from app.agent.nodes import extract_answers_node
from app.agent.state_machine import append_user_message
from app.scoring.answer_scoring import build_scoring_input
from app.scoring.engine import calculate_scoring
from app.schemas.agent_state import AgentMessage, AgentState
from config import get_settings


def _skip_if_no_key():
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY:
        pytest.skip("DEEPSEEK_API_KEY 未配置")


# ── 基础提取 ───────────────────────────────────────────────────

@pytest.mark.ai
@pytest.mark.integration
async def test_extract_from_messages_real_deepseek_basic():
    _skip_if_no_key()

    messages = [
        AgentMessage(role="user", content="我们是一家做健身器材的工厂，有少量东南亚客户，主要卖家用力量训练设备。")
    ]
    result = await extract_from_messages(messages)

    industry_slot = result.slots.get("industry")
    product_slot = result.slots.get("main_product")
    assert (industry_slot and industry_slot.value) or (product_slot and product_slot.value)
    assert 0.0 <= (industry_slot.confidence if industry_slot else 0) <= 1.0
    assert len(result.answers) > 0, f"预期至少一个答案，实际 {result.answers}"
    q5_ids = next((ea.option_ids for ea in result.answers if ea.question_id == "Q5"), [])
    assert "C" in q5_ids, f"预期 Q5 包含 C，实际 {q5_ids}"


# ── 节点合并 ───────────────────────────────────────────────────

@pytest.mark.ai
@pytest.mark.integration
async def test_extract_answers_node_merges_slots_and_answers():
    _skip_if_no_key()

    state = AgentState()
    state = append_user_message(state, "我们是一家做健身器材的工厂，有少量东南亚客户，主要卖家用力量训练设备。")
    result = await extract_answers_node(state)

    assert "Q5" in result.answers
    assert result.branch == "experienced"
    assert result.ai_failure_count == 0


# ── 完整打分管道 ───────────────────────────────────────────────

@pytest.mark.ai
@pytest.mark.integration
async def test_extract_answers_can_feed_scoring_when_enough_answers():
    _skip_if_no_key()

    state = AgentState()
    state = append_user_message(
        state,
        "我们是成立10年以上的健身器材源头工厂，团队100人左右，去年营收5000万到1亿，"
        "有少量东南亚客户，主要通过阿里国际站和老客户介绍，想开发东南亚市场，"
        "预算每月2到5万，愿意先看报告再预约咨询。"
    )
    result = await extract_answers_node(state)

    assert len(result.answers) >= 8, (
        f"预期至少提取8个答案，实际 {len(result.answers)}: {list(result.answers.keys())}"
    )

    si = build_scoring_input(
        result.answers, branch=result.branch, q1_slots=result.slots,
    )
    scoring = calculate_scoring(si)

    assert scoring.tag
    assert scoring.lead_priority

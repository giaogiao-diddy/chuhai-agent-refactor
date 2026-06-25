import pytest

from app.agent.graph import run_scoring_pipeline
from app.agent.state_machine import append_user_message
from app.schemas.agent_state import AgentState
from config import get_settings


@pytest.mark.ai
@pytest.mark.integration
async def test_run_scoring_pipeline_real_deepseek():
    settings = get_settings()
    if not settings.DEEPSEEK_API_KEY:
        pytest.skip("DEEPSEEK_API_KEY 未配置")

    state = AgentState()
    state = append_user_message(
        state,
        "我们是成立10年以上的健身器材源头工厂，团队100人左右，销售团队10人，"
        "去年营收5000万到1亿，毛利率25%-40%。有少量东南亚客户，"
        "主要通过阿里国际站和老客户介绍，想开发东南亚市场，因为已有询盘。"
        "单笔海外订单大概10万到40万，有复购。产品有部分认证和英文资料，"
        "交付比较稳定。有国内新媒体经验，但海外社媒还没系统做。"
        "预算每月2到5万，愿意先看报告再预约咨询。",
    )
    result = await run_scoring_pipeline(state)

    assert result.ai_failure_count == 0
    assert "Q5" in result.answers
    assert result.branch == "experienced"
    assert len(result.answers) >= 8, f"预期 >=8 个答案，实际 {len(result.answers)}: {list(result.answers.keys())}"
    assert result.scoring_result is not None
    assert 0 <= result.scoring_result.feasibility_score <= 100
    assert 0 <= result.scoring_result.lead_score <= 100
    assert result.scoring_result.tag
    assert result.scoring_result.lead_priority
    assert result.scoring_error is None

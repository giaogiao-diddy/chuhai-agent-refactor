from app.agent.prompts import build_dialogue_system_prompt
from app.schemas.agent_state import AgentState


def test_dialogue_prompt_includes_missing_question_hints():
    state = AgentState(answers={"Q5": ["C"]})

    prompt = build_dialogue_system_prompt(state)

    assert "当前已收集题号: Q5" in prompt
    assert "下一轮优先补齐" in prompt
    assert "Q1 行业和主营产品" in prompt


def test_dialogue_prompt_prevents_consulting_before_intake():
    prompt = build_dialogue_system_prompt(AgentState())

    assert "不要直接给广告投放方案" in prompt
    assert "先完成信息采集" in prompt

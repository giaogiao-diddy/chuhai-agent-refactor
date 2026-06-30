from app.agent.prompts import (
    REPORT_KEY_QUESTION_HINTS,
    build_dialogue_system_prompt,
    get_missing_report_question_hints,
)
from app.schemas.agent_state import AgentState
from app.schemas.slots import SlotValue


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


def test_report_key_questions_cover_report_dimensions():
    question_ids = [item["id"] for item in REPORT_KEY_QUESTION_HINTS]

    assert question_ids == [
        "Q1", "Q2a", "Q2b", "Q3a", "Q5", "Q8", "Q11",
        "Q15", "Q19", "Q22", "Q23", "Q28", "Q30", "Q31",
    ]


def test_missing_report_questions_skip_collected_answers_and_slots():
    state = AgentState(
        answers={
            "Q2a": ["A"],
            "Q2b": ["B"],
            "Q3a": ["B"],
            "Q5": ["C"],
        }
    )
    state.slots.industry = SlotValue(value="女装", confidence=0.9)
    state.slots.main_product = SlotValue(value="上衣", confidence=0.9)

    missing = get_missing_report_question_hints(state)
    missing_ids = [item["id"] for item in missing]

    assert "Q1" not in missing_ids
    assert "Q2a" not in missing_ids
    assert missing_ids[:3] == ["Q8", "Q11", "Q15"]


def test_dialogue_prompt_forces_next_key_questions_before_advice():
    state = AgentState(answers={"Q5": ["C"]})
    state.slots.industry = SlotValue(value="女装", confidence=0.9)
    state.slots.main_product = SlotValue(value="上衣", confidence=0.9)

    prompt = build_dialogue_system_prompt(state)

    assert "报告生成关键问题尚未收集完整" in prompt
    assert "下一轮必须优先追问" in prompt
    assert "Q2a 成立年限" in prompt
    assert "Q2b 团队人数" in prompt
    assert "不要继续给平台投放、预算分配或运营执行建议" in prompt

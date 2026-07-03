import pytest

from app.agent.tools.external.dialogue import (
    DialogueDeepSeekInput,
    _build_dialogue_prompt,
    dialogue_deepseek_handler,
)
from app.schemas.agent_state import AgentMessage
from app.schemas.memory import MemoryEntry, MemoryFrontmatter


def _make_entry(name="memory-name", desc="memory desc", content="memory content"):
    return MemoryEntry(
        path=".claude/memory/test.md",
        frontmatter=MemoryFrontmatter(name=name, description=desc, type="user"),
        content=content,
    )


def test_dialogue_prompt_includes_memory_entries():
    inp = DialogueDeepSeekInput(
        messages=[AgentMessage(role="user", content="hello")],
        memory_entries=[_make_entry()],
    )
    prompt = _build_dialogue_prompt(inp)
    assert "已知长期记忆" in prompt
    assert "memory-name" in prompt
    assert "memory desc" in prompt
    assert "memory content" in prompt


def test_dialogue_prompt_omits_memory_section_when_empty():
    inp = DialogueDeepSeekInput(
        messages=[AgentMessage(role="user", content="hello")],
        memory_entries=[],
    )
    prompt = _build_dialogue_prompt(inp)
    assert "已知长期记忆" not in prompt


def test_dialogue_prompt_truncates_memory_content_at_300():
    long_content = "x" * 500
    inp = DialogueDeepSeekInput(
        messages=[AgentMessage(role="user", content="hello")],
        memory_entries=[_make_entry(content=long_content)],
    )
    prompt = _build_dialogue_prompt(inp)
    snippet = "x" * 300
    assert snippet in prompt
    assert long_content not in prompt


def test_dialogue_prompt_limits_to_3_memories():
    entries = [_make_entry(name=f"mem{i}") for i in range(5)]
    inp = DialogueDeepSeekInput(
        messages=[AgentMessage(role="user", content="hello")],
        memory_entries=entries,
    )
    prompt = _build_dialogue_prompt(inp)
    assert "mem0" in prompt
    assert "mem2" in prompt
    assert "mem3" not in prompt


def test_dialogue_input_defaults_are_independent():
    """Field(default_factory=list) 确保实例间不共享可变默认值。"""
    from app.schemas.agent_state import AgentMessage
    a = DialogueDeepSeekInput(messages=[AgentMessage(role="user", content="hi")])
    b = DialogueDeepSeekInput(messages=[AgentMessage(role="user", content="hi")])
    a.memory_entries.append(_make_entry())
    assert len(a.memory_entries) == 1
    assert len(b.memory_entries) == 0


def test_dialogue_prompt_missing_items_priority_above_memory():
    """missing_items 应在 memory 之后输出，且追问优先级不变。"""
    inp = DialogueDeepSeekInput(
        messages=[AgentMessage(role="user", content="hello")],
        missing_items=[{"label": "目标市场", "question_id": "Q8"}],
        memory_entries=[_make_entry()],
    )
    prompt = _build_dialogue_prompt(inp)
    mem_pos = prompt.index("已知长期记忆")
    missing_pos = prompt.index("当前缺失关键信息")
    assert mem_pos < missing_pos  # memory 在前, missing 在后
    assert "优先追问" in prompt


# ── Phase 43 fix: structured state injection + premature closure prevention ──

def test_dialogue_prompt_includes_slots_summary():
    inp = DialogueDeepSeekInput(
        messages=[AgentMessage(role="user", content="hi")],
        slots_summary={"行业": "健身器材", "主营产品": "哑铃", "目标市场": "东南亚"},
    )
    prompt = _build_dialogue_prompt(inp)
    assert "健身器材" in prompt
    assert "东南亚" in prompt
    assert "当前企业画像" in prompt


def test_dialogue_prompt_forbids_completion_when_missing_items_exist():
    inp = DialogueDeepSeekInput(
        messages=[AgentMessage(role="user", content="hi")],
        missing_items=[{"label": "目标市场", "question_id": "Q8", "ask": "目标市场是?"}],
    )
    prompt = _build_dialogue_prompt(inp)
    assert "当前缺失关键信息" in prompt
    # 禁止声明中包含了这些词作为反面示例，确认禁止语义存在
    assert "禁止声明" in prompt
    assert "可以引导用户点击'生成报告'" not in prompt


def test_dialogue_prompt_uses_next_question_priority():
    inp = DialogueDeepSeekInput(
        messages=[AgentMessage(role="user", content="hi")],
        missing_items=[{"label": "目标市场", "question_id": "Q8"}],
        next_questions=["目标市场是?", "预算是?"],
    )
    prompt = _build_dialogue_prompt(inp)
    assert "本轮优先追问" in prompt
    assert "目标市场是?" in prompt


def test_shared_input_builder_stream_and_non_stream():
    from app.agent.tools.external.dialogue import _build_dialogue_input
    from app.schemas.readiness import MissingItem, ReadinessResult
    from app.schemas.agent_state import AgentState
    from app.schemas.slots import CompanySlots, SlotValue

    readiness = ReadinessResult(
        ready=False, score_ready=False, report_ready=False,
        missing_items=[MissingItem(question_id="Q8", label="目标市场", reason="x", ask="目标市场是?")],
        next_questions=["目标市场是?"],
    )
    mem = [_make_entry()]
    state = AgentState(
        messages=[AgentMessage(role="user", content="东南亚市场怎样")],
        answers={"Q5": ["C"]},
        slots=CompanySlots(industry=SlotValue(value="健身", confidence=0.9)),
        branch="experienced",
    )
    inp = _build_dialogue_input(state, readiness, mem)
    assert inp.score_ready is False
    assert len(inp.missing_items) == 1
    assert inp.slots_summary.get("行业") == "健身"
    assert "Q5" in inp.answered_question_ids

    prompt = _build_dialogue_prompt(inp)
    assert "健身" in prompt
    assert "当前缺失关键信息" in prompt


def test_dialogue_prompt_continues_when_score_ready_but_report_not():
    inp = DialogueDeepSeekInput(
        messages=[AgentMessage(role="user", content="hi")],
        score_ready=True,
        report_ready=False,
        report_missing_items=[{"label": "成立年限", "question_id": "Q2a", "ask": "公司成立多久?"}],
    )
    prompt = _build_dialogue_prompt(inp)
    assert "诊断质量还需要补充" in prompt
    assert "可以引导用户点击'生成报告'" not in prompt


def test_dialogue_prompt_allows_report_when_fully_ready():
    inp = DialogueDeepSeekInput(
        messages=[AgentMessage(role="user", content="hi")],
        score_ready=True,
        report_ready=True,
    )
    prompt = _build_dialogue_prompt(inp)
    assert "可以引导用户点击'生成报告'" in prompt
    assert "当前缺失关键信息" not in prompt

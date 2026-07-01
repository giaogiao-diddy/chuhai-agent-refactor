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
    assert "必须优先追问" in prompt

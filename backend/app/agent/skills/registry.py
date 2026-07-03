"""Skill 注册中心 — 直接翻译自 Claude Code src/skills/bundledSkills.ts"""
from dataclasses import dataclass, field
from typing import Any, Callable

from app.schemas.agent_state import AgentState


@dataclass
class BundledSkill:
    name: str
    description: str
    when_to_use: str | None = None
    allowed_tools: list[str] = field(default_factory=list)
    user_invocable: bool = True
    _execute: Callable | None = field(default=None, repr=False)

    async def execute(self, state: AgentState, tool_executor: Any, **kwargs) -> str:
        if self._execute:
            return await self._execute(state, tool_executor, **kwargs)
        return f"Skill '{self.name}' has no execute implementation."


# ── Global registry ──

_skills: dict[str, BundledSkill] = {}


def register_bundled_skill(skill: BundledSkill) -> None:
    """注册一个内建 skill。重复注册同名 skill 会覆盖旧定义。"""
    _skills[skill.name] = skill


def get_bundled_skills() -> list[BundledSkill]:
    return list(_skills.values())


def get_skill(name: str) -> BundledSkill | None:
    return _skills.get(name)


def clear_skills() -> None:
    _skills.clear()

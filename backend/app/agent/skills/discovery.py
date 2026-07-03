import logging
from pathlib import Path

from app.agent.skills.registry import BundledSkill, register_bundled_skill

logger = logging.getLogger(__name__)


def _parse_frontmatter(content: str) -> dict:
    if not content.startswith("---"):
        return {}
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}

    result: dict = {}
    current_key: str | None = None
    for raw_line in parts[1].splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            continue
        stripped = line.strip()
        if stripped.startswith("- ") and current_key:
            result.setdefault(current_key, []).append(stripped[2:].strip())
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        current_key = key
        if value == "":
            result[key] = []
        elif value.lower() == "true":
            result[key] = True
        elif value.lower() == "false":
            result[key] = False
        else:
            result[key] = value.strip("\"'")
    return result


def _load_skill_from_markdown(filepath: Path) -> BundledSkill | None:
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return None

    fm = _parse_frontmatter(content)
    name = fm.get("name")
    if not name:
        return None

    body = content.split("---", 2)[-1].strip() if content.count("---") >= 2 else content

    return BundledSkill(
        name=name,
        description=fm.get("description", ""),
        when_to_use=fm.get("when_to_use"),
        allowed_tools=fm.get("allowed_tools", []),
        user_invocable=fm.get("user_invocable", True),
    )


def discover_file_skills(base_dir: str | Path) -> int:
    base = Path(base_dir)
    if not base.is_dir():
        return 0

    count = 0
    for skill_file in base.rglob("SKILL.md"):
        skill = _load_skill_from_markdown(skill_file)
        if skill:
            register_bundled_skill(skill)
            count += 1

    return count

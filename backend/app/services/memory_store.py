import re
from pathlib import Path

from app.schemas.memory import MemoryEntry, MemoryFrontmatter, MemorySaveInput, MemoryType

_MEMORY_DIR = ".claude/memory"
_INDEX_FILE = "MEMORY.md"

_SECRET_PATTERNS = [
    "sk-",
    "Bearer ",
    "DEEPSEEK_API_KEY",
    "EMBEDDING_API_KEY",
    "JWT_SECRET_KEY",
]


def _repo_root() -> Path:
    """Derive repo root from this file's location: .../backend/app/services/memory_store.py → ../../.."""
    return Path(__file__).resolve().parent.parent.parent.parent


def get_memory_root() -> Path:
    return _repo_root() / _MEMORY_DIR


def _relative_memory_path(absolute: Path) -> str:
    try:
        return str(absolute.relative_to(_repo_root())).replace("\\", "/")
    except ValueError:
        # absolute is not under repo root (e.g. test tmp_path) — fallback with .claude/memory/ prefix
        return f"{_MEMORY_DIR}/{absolute.name}"


def ensure_memory_store() -> None:
    root = get_memory_root()
    root.mkdir(parents=True, exist_ok=True)
    index = root / _INDEX_FILE
    if not index.exists():
        index.write_text("# Memory Index\n\n> Agent memory index. Do not store secrets, API keys, or tokens.\n", encoding="utf-8")


def parse_memory_file(path: Path) -> MemoryEntry:
    text = path.read_text(encoding="utf-8").strip()
    if not text.startswith("---"):
        raise ValueError(f"Memory file missing frontmatter: {path}")

    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"Memory file frontmatter incomplete: {path}")

    fm_lines = parts[1].strip().split("\n")
    fm: dict[str, str] = {}
    for line in fm_lines:
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()

    name = fm.get("name", "")
    description = fm.get("description", "")
    mtype = fm.get("type", "reference")
    if mtype not in ("user", "feedback", "project", "reference"):
        mtype = "reference"
    if not name:
        raise ValueError(f"Memory file missing 'name' in frontmatter: {path}")

    content = parts[2].strip()

    return MemoryEntry(
        path=_relative_memory_path(path),
        frontmatter=MemoryFrontmatter(
            name=name,
            description=description,
            type=mtype,  # type: ignore
        ),
        content=content,
    )


def list_memory_entries() -> list[MemoryEntry]:
    root = get_memory_root()
    entries: list[MemoryEntry] = []
    for f in sorted(root.glob("*.md")):
        if f.name == _INDEX_FILE:
            continue
        entries.append(parse_memory_file(f))
    return entries


def recall_memory(query: str, limit: int = 5) -> list[MemoryEntry]:
    all_entries = list_memory_entries()
    if not query.strip():
        return all_entries[:limit]

    tokens = query.lower().split()
    scored: list[tuple[int, MemoryEntry]] = []
    for e in all_entries:
        text = (e.frontmatter.name + " " + e.frontmatter.description + " " + e.content).lower()
        score = sum(1 for t in tokens if t in text)
        if score > 0:
            scored.append((score, e))

    scored.sort(key=lambda x: -x[0])
    return [e for _, e in scored[:limit]]


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w一-鿿\-]", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    if not slug:
        raise ValueError("Memory name 无法生成有效文件名")
    return slug


def _scan_secrets(text: str) -> str | None:
    for pattern in _SECRET_PATTERNS:
        if pattern in text:
            return pattern
    return None


def save_memory(
    name: str,
    description: str,
    mtype: MemoryType,
    content: str,
) -> str:
    # Validate via MemorySaveInput (Pydantic field_validator)
    validated = MemorySaveInput(name=name, description=description, type=mtype, content=content)

    secret = _scan_secrets(validated.name + " " + validated.description + " " + validated.content)
    if secret:
        raise ValueError(f"Memory 内容包含疑似密钥: {secret}")

    ensure_memory_store()
    root = get_memory_root()
    slug = _slugify(validated.name)
    filename = f"{slug}.md"
    filepath = root / filename

    frontmatter = f"---\nname: {validated.name}\ndescription: {validated.description}\ntype: {validated.type}\n---"
    filepath.write_text(f"{frontmatter}\n\n{validated.content}\n", encoding="utf-8")

    # Update MEMORY.md index
    index_path = root / _INDEX_FILE
    index_text = index_path.read_text(encoding="utf-8")
    line = f"- [{validated.name}]({filename}) — {validated.description}"

    if filename in index_text:
        lines = index_text.split("\n")
        new_lines = []
        for l in lines:
            if filename in l:
                new_lines.append(line)
            else:
                new_lines.append(l)
        index_text = "\n".join(new_lines)
    else:
        index_text = index_text.rstrip() + "\n" + line + "\n"

    index_path.write_text(index_text, encoding="utf-8")
    return _relative_memory_path(filepath)

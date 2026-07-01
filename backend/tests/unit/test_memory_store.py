import pytest
from pydantic import ValidationError

from app.services import memory_store


def _patch_root(monkeypatch, tmp_path):
    root = tmp_path / "memory"
    monkeypatch.setattr(memory_store, "get_memory_root", lambda: root)
    return root


def test_ensure_memory_store_creates_index(monkeypatch, tmp_path):
    root = _patch_root(monkeypatch, tmp_path)
    memory_store.ensure_memory_store()
    assert (root / "MEMORY.md").exists()


def test_get_memory_root_is_project_based(monkeypatch, tmp_path):
    """get_memory_root == _repo_root() / .claude/memory，不依赖 cwd。"""
    expected = memory_store._repo_root() / ".claude/memory"
    assert memory_store.get_memory_root() == expected

    # 切换 cwd 后仍不变
    monkeypatch.chdir(tmp_path)
    assert memory_store.get_memory_root() == expected


def test_save_memory_creates_markdown_with_frontmatter(monkeypatch, tmp_path):
    root = _patch_root(monkeypatch, tmp_path)
    rel = memory_store.save_memory("test-memory", "测试记忆", "project", "正文内容")
    assert "test-memory" in rel
    assert (root / "test-memory.md").exists()


def test_save_memory_updates_existing_file(monkeypatch, tmp_path):
    root = _patch_root(monkeypatch, tmp_path)
    memory_store.save_memory("same-name", "first", "user", "old content")
    memory_store.save_memory("same-name", "updated", "user", "new content")
    text = (root / "same-name.md").read_text(encoding="utf-8")
    assert "new content" in text
    assert "old content" not in text


def test_memory_index_appends_entry(monkeypatch, tmp_path):
    root = _patch_root(monkeypatch, tmp_path)
    memory_store.save_memory("item-a", "desc a", "user", "content a")
    memory_store.save_memory("item-b", "desc b", "project", "content b")
    index = (root / "MEMORY.md").read_text(encoding="utf-8")
    assert "item-a" in index
    assert "item-b" in index


def test_parse_memory_file_reads_frontmatter_and_content(monkeypatch, tmp_path):
    root = _patch_root(monkeypatch, tmp_path)
    memory_store.save_memory("parse-test", "parsed", "reference", "the body")
    path = root / "parse-test.md"
    entry = memory_store.parse_memory_file(path)
    assert entry.frontmatter.name == "parse-test"
    assert entry.content == "the body"


def test_recall_memory_matches_name_description_content(monkeypatch, tmp_path):
    root = _patch_root(monkeypatch, tmp_path)
    memory_store.save_memory("alpha", "first entry", "user", "apple banana")
    memory_store.save_memory("beta", "second item", "project", "orange grape")
    results = memory_store.recall_memory("apple", limit=5)
    assert any(e.frontmatter.name == "alpha" for e in results)
    results2 = memory_store.recall_memory("nonexistent-xyz", limit=5)
    assert len(results2) == 0


def test_save_memory_rejects_secret_like_content(monkeypatch, tmp_path):
    _patch_root(monkeypatch, tmp_path)
    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        memory_store.save_memory("secret", "desc", "user", "my key is DEEPSEEK_API_KEY=abc123")


def test_save_memory_rejects_newline_in_name():
    from app.schemas.memory import MemorySaveInput
    with pytest.raises(ValidationError):
        MemorySaveInput(name="bad\nname", description="x", type="user", content="ok")
    with pytest.raises(ValidationError):
        MemorySaveInput(name="ok", description="x", type="user", content="")


def test_memory_recall_limit_range():
    from app.schemas.memory import MemoryRecallInput
    with pytest.raises(ValidationError):
        MemoryRecallInput(query="x", limit=0)
    with pytest.raises(ValidationError):
        MemoryRecallInput(query="x", limit=21)


def test_save_memory_path_is_relative(monkeypatch, tmp_path):
    _patch_root(monkeypatch, tmp_path)
    rel = memory_store.save_memory("rel-path", "desc", "user", "body")
    assert ":" not in rel
    assert not rel.startswith("/")


def test_save_memory_returns_repo_relative_path():
    """save_memory 返回以 .claude/memory/ 开头的相对路径。"""
    rel = memory_store._relative_memory_path(
        memory_store._repo_root() / ".claude/memory/foo.md"
    )
    assert rel == ".claude/memory/foo.md"


def test_save_memory_service_validates_input(monkeypatch, tmp_path):
    """直接调用 save_memory 也会经过 MemorySaveInput 校验。"""
    _patch_root(monkeypatch, tmp_path)
    with pytest.raises(ValidationError):
        memory_store.save_memory("bad\nname", "desc", "user", "content")
    with pytest.raises(ValidationError):
        memory_store.save_memory("ok", "desc", "user", "")


def test_relative_memory_path_fallback_keeps_claude_prefix(tmp_path):
    """不在 repo root 下的 path 回退为 .claude/memory/<filename>。"""
    path = tmp_path / "foo.md"
    rel = memory_store._relative_memory_path(path)
    assert rel == ".claude/memory/foo.md"


def test_save_memory_index_uses_validated_fields(monkeypatch, tmp_path):
    root = _patch_root(monkeypatch, tmp_path)
    memory_store.save_memory("  trim-name  ", "  trim desc  ", "user", " body ")

    # 文件名使用 strip 后的值
    filepath = root / "trim-name.md"
    assert filepath.exists()
    text = filepath.read_text(encoding="utf-8")

    # frontmatter 值已 strip
    assert "name: trim-name" in text
    assert "description: trim desc" in text

    # index 文件中 name/description 已 strip
    index_text = (root / "MEMORY.md").read_text(encoding="utf-8")
    assert "[trim-name](trim-name.md)" in index_text
    assert "trim desc" in index_text
    assert "  trim-name  " not in index_text

import pytest

from app.agent.tools.base import ToolErrorCode
from app.agent.tools.executor import ToolExecutor
from app.agent.tools.local import register_local_tools
from app.agent.tools.registry import ToolRegistry
from app.schemas.memory import MemoryRecallInput, MemorySaveInput
from app.services import memory_store


def _patch_root(monkeypatch, tmp_path):
    root = tmp_path / "memory"
    monkeypatch.setattr(memory_store, "get_memory_root", lambda: root)
    return root


def test_memory_tools_registered():
    r = ToolRegistry()
    register_local_tools(r)
    names = {t.name for t in r.list_all()}
    assert "memory.recall" in names
    assert "memory.save" in names


@pytest.mark.asyncio
async def test_memory_recall_tool_returns_entries(monkeypatch, tmp_path):
    _patch_root(monkeypatch, tmp_path)
    memory_store.save_memory("pref-name", "name desc", "user", "name content")

    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    result = await ex.execute("memory.recall", MemoryRecallInput(query="name", limit=5))
    assert result.error is None
    assert len(result.data.entries) >= 1


@pytest.mark.asyncio
async def test_memory_save_tool_writes_entry(monkeypatch, tmp_path):
    _patch_root(monkeypatch, tmp_path)
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    result = await ex.execute("memory.save", MemorySaveInput(
        name="tool-test", description="tool desc", type="project", content="tool content",
    ))
    assert result.error is None
    assert result.data.index_updated is True
    assert "tool-test" in str(result.data.path)


@pytest.mark.asyncio
async def test_memory_save_tool_rejects_secret_as_permanent_error(monkeypatch, tmp_path):
    _patch_root(monkeypatch, tmp_path)
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    result = await ex.execute("memory.save", MemorySaveInput(
        name="bad", description="x", type="user", content="contains sk-abcd12345ef",
    ))
    assert result.error is not None
    assert result.error.code == ToolErrorCode.PERMANENT


@pytest.mark.asyncio
async def test_memory_save_tool_path_no_absolute_local_path(monkeypatch, tmp_path):
    _patch_root(monkeypatch, tmp_path)
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    result = await ex.execute("memory.save", MemorySaveInput(
        name="path-test", description="path desc", type="user", content="path content",
    ))
    assert result.error is None
    p = result.data.path
    assert ":" not in p, f"path 不应包含盘符: {p}"
    assert not p.startswith("/"), f"path 不应是绝对路径: {p}"


@pytest.mark.asyncio
async def test_memory_save_tool_path_is_repo_relative(monkeypatch, tmp_path):
    """path 必须以 .claude/memory/ 开头。"""
    _patch_root(monkeypatch, tmp_path)
    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    result = await ex.execute("memory.save", MemorySaveInput(
        name="repo-test", description="repo desc", type="user", content="repo content",
    ))
    assert result.error is None
    p = result.data.path
    assert p.startswith(".claude/memory/")
    assert ":" not in p
    assert not p.startswith("/")


@pytest.mark.asyncio
async def test_memory_save_tool_wraps_validation_error(monkeypatch, tmp_path):
    """service 层抛出的 ValueError/ValidationError 被 tool 包装为 PERMANENT。"""
    _patch_root(monkeypatch, tmp_path)

    # 绕过 Pydantic input 校验：直接注入一个不验证 service 的 fake save_memory
    import app.agent.tools.local.memory as mem_tool

    def _fail_save(name, description, mtype, content):
        from pydantic import ValidationError
        raise ValidationError.from_exception_data("test", [])

    monkeypatch.setattr(mem_tool, "save_memory", _fail_save)

    r = ToolRegistry()
    register_local_tools(r)
    ex = ToolExecutor(r)
    result = await ex.execute("memory.save", MemorySaveInput(
        name="ok", description="ok desc", type="user", content="valid",
    ))
    assert result.error is not None
    assert result.error.code == ToolErrorCode.PERMANENT

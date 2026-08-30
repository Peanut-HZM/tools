"""文件工具单元测试（P2-③）"""
import uuid

import pytest

from app.services.harness.tool_protocol import ToolContext
from app.services.harness.tools.file_list import FileListTool
from app.services.harness.tools.file_read import FileReadTool
from app.services.harness.tools.file_write import FileWriteTool

AID = uuid.UUID("00000000-0000-0000-0000-000000000002")
UID = uuid.UUID("00000000-0000-0000-0000-000000000003")


def _ctx(db) -> ToolContext:
    return ToolContext(
        user_id=str(UID), conversation_id="c1", agent_id=str(AID), session=None, db=db
    )


@pytest.fixture
def enable_sandbox(test_db, tmp_path, monkeypatch):
    """创建启用沙箱的 Agent 行；WORKSPACE_ROOT 指向临时目录隔离测试"""
    monkeypatch.setenv("WORKSPACE_ROOT", str(tmp_path))
    from app.models.agent import Agent

    agent = Agent(id=AID, name="sb", description="", system_prompt="")
    agent.sandbox_enabled = True
    test_db.add(agent)
    test_db.commit()
    return test_db


@pytest.mark.asyncio
async def test_file_write_read_list(enable_sandbox):
    ctx = _ctx(enable_sandbox)

    r = await FileWriteTool().execute({"path": "docs/note.txt", "content": "hello"}, ctx)
    assert r.success is True, r

    r2 = await FileReadTool().execute({"path": "docs/note.txt"}, ctx)
    assert r2.success is True
    assert r2.content["content"] == "hello"
    assert r2.content["truncated"] is False

    r3 = await FileListTool().execute({}, ctx)
    assert r3.success is True
    assert r3.content["count"] == 1
    assert r3.content["files"][0]["path"] == "docs/note.txt"


@pytest.mark.asyncio
async def test_file_read_missing(enable_sandbox):
    ctx = _ctx(enable_sandbox)
    r = await FileReadTool().execute({"path": "nope.txt"}, ctx)
    assert r.success is False


@pytest.mark.asyncio
async def test_file_write_escape_rejected(enable_sandbox):
    ctx = _ctx(enable_sandbox)
    r = await FileWriteTool().execute({"path": "../evil.txt", "content": "x"}, ctx)
    assert r.success is False
    assert "工作区" in str(r)


@pytest.mark.asyncio
async def test_file_tools_gated(test_db):
    """未启用 sandbox 的 Agent：门控 False"""
    from app.models.agent import Agent

    agent = Agent(id=AID, name="g2", description="", system_prompt="")
    agent.sandbox_enabled = False
    test_db.add(agent)
    test_db.commit()
    ctx = _ctx(test_db)
    assert FileReadTool().is_available(ctx) is False
    assert FileWriteTool().is_available(ctx) is False
    assert FileListTool().is_available(ctx) is False

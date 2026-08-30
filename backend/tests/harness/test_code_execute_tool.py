"""code_execute 工具单元测试（P2-③，真实子进程）"""
import uuid

import pytest

from app.services.harness.tool_protocol import ToolContext
from app.services.harness.tools.code_execute import CodeExecuteTool
from app.services.harness.tools.file_write import FileWriteTool
from app.services.harness.workspace import WorkspaceService

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

    agent = Agent(id=AID, name="sb2", description="", system_prompt="")
    agent.sandbox_enabled = True
    test_db.add(agent)
    test_db.commit()
    return test_db


@pytest.mark.asyncio
async def test_execute_print(enable_sandbox):
    ctx = _ctx(enable_sandbox)
    r = await CodeExecuteTool().execute({"code": 'print("hi")'}, ctx)
    assert r.success is True, r
    assert r.content["stdout"].strip() == "hi"
    assert r.content["exit_code"] == 0
    assert r.content["timed_out"] is False


@pytest.mark.asyncio
async def test_execute_nonzero_exit(enable_sandbox):
    """非零退出码是正常返回（LLM 需要 stderr 自我修正），不是 error"""
    ctx = _ctx(enable_sandbox)
    r = await CodeExecuteTool().execute(
        {"code": "import sys; sys.exit(3)"}, ctx
    )
    assert r.success is True
    assert r.content["exit_code"] == 3


@pytest.mark.asyncio
async def test_execute_timeout(enable_sandbox):
    ctx = _ctx(enable_sandbox)
    r = await CodeExecuteTool().execute(
        {"code": "import time; time.sleep(10)", "timeout_seconds": 1}, ctx
    )
    assert r.success is True
    assert r.content["timed_out"] is True


@pytest.mark.asyncio
async def test_execute_cwd_is_workspace(enable_sandbox):
    """cwd=工作区：代码可用相对路径读写工作文件"""
    ctx = _ctx(enable_sandbox)
    # 先写一个工作区文件
    await FileWriteTool().execute({"path": "data.csv", "content": "a,b\n1,2"}, ctx)
    r = await CodeExecuteTool().execute(
        {"code": "print(open('data.csv').read())"}, ctx
    )
    assert r.success is True
    assert "a,b" in r.content["stdout"]


@pytest.mark.asyncio
async def test_execute_stdout_truncated(enable_sandbox):
    ctx = _ctx(enable_sandbox)
    r = await CodeExecuteTool().execute(
        {"code": "print('x' * 100000)"}, ctx
    )
    assert r.success is True
    assert len(r.content["stdout"]) <= 10 * 1024 + 20  # 10KB 截断 + 尾注余量
    assert "truncated" in r.content["stdout"]


@pytest.mark.asyncio
async def test_execute_rejects_non_python(enable_sandbox):
    ctx = _ctx(enable_sandbox)
    r = await CodeExecuteTool().execute({"code": "1", "language": "javascript"}, ctx)
    assert r.success is False


@pytest.mark.asyncio
async def test_execute_timeout_cap(enable_sandbox):
    """timeout_seconds 上限 30：传 999 被钳制（不应真的执行 999 秒）"""
    ctx = _ctx(enable_sandbox)
    r = await CodeExecuteTool().execute(
        {"code": "print('ok')", "timeout_seconds": 999}, ctx
    )
    assert r.success is True


@pytest.mark.asyncio
async def test_code_execute_gated(test_db):
    from app.models.agent import Agent

    agent = Agent(id=AID, name="g3", description="", system_prompt="")
    agent.sandbox_enabled = False
    test_db.add(agent)
    test_db.commit()
    assert CodeExecuteTool().is_available(_ctx(test_db)) is False

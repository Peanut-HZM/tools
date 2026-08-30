"""技能工具单元测试（P2-②）"""
import uuid

import pytest

from app.services.harness.skill_service import SkillService
from app.services.harness.tool_protocol import ToolContext
from app.services.harness.tools.skill_delete import SkillDeleteTool
from app.services.harness.tools.skill_read import SkillReadTool
from app.services.harness.tools.skill_save import SkillSaveTool, _check_procedural_enabled

AID = uuid.UUID("00000000-0000-0000-0000-000000000002")
UID = uuid.UUID("00000000-0000-0000-0000-000000000003")


def _ctx(db) -> ToolContext:
    """构造最小 ToolContext"""
    return ToolContext(
        user_id=str(UID),
        conversation_id="c1",
        agent_id=str(AID),
        session=None,
        db=db,
    )


@pytest.fixture
def enable_procedural(test_db):
    """创建启用了 procedural 记忆的 Agent 行，并注册 (agent_id, user_id) 隔离"""
    from app.models.agent import Agent

    agent = Agent(id=AID, name="test-agent", description="", system_prompt="")
    agent.memory_procedural_enabled = True
    test_db.add(agent)
    test_db.commit()
    return test_db


@pytest.mark.asyncio
async def test_skill_save_and_read_roundtrip(enable_procedural):
    db = enable_procedural
    ctx = _ctx(db)
    r = await SkillSaveTool().execute(
        {"name": "deploy", "trigger": "部署前", "content": "1. 测试"}, ctx
    )
    assert r.success is True, r

    r2 = await SkillReadTool().execute({"name": "deploy"}, ctx)
    assert r2.success is True, r2
    assert "1. 测试" in str(r2.content.get("content"))


@pytest.mark.asyncio
async def test_skill_read_index_and_use_count(enable_procedural):
    db = enable_procedural
    ctx = _ctx(db)
    await SkillSaveTool().execute({"name": "s", "trigger": "t", "content": "c"}, ctx)

    read = SkillReadTool()
    idx = await read.execute({}, ctx)
    assert idx.success is True
    assert idx.content["records"][0]["name"] == "s"

    # 读完整内容 → use_count 递增
    await read.execute({"name": "s"}, ctx)
    svc = SkillService(db)
    row = await svc.get(AID, UID, "s")
    assert row.use_count == 1


@pytest.mark.asyncio
async def test_skill_delete_missing(enable_procedural):
    ctx = _ctx(enable_procedural)
    r = await SkillDeleteTool().execute({"name": "nope"}, ctx)
    assert r.success is False


@pytest.mark.asyncio
async def test_skill_save_requires_name(enable_procedural):
    ctx = _ctx(enable_procedural)
    r = await SkillSaveTool().execute({"trigger": "t", "content": "c"}, ctx)
    assert r.success is False


@pytest.mark.asyncio
async def test_skill_read_disabled_skill_rejected(enable_procedural):
    db = enable_procedural
    ctx = _ctx(db)
    await SkillSaveTool().execute({"name": "off", "trigger": "t", "content": "c"}, ctx)
    svc = SkillService(db)
    row = await svc.get(AID, UID, "off")
    row.is_enabled = False
    db.commit()

    r = await SkillReadTool().execute({"name": "off"}, ctx)
    assert r.success is False
    assert "禁用" in str(r)


@pytest.mark.asyncio
async def test_skill_tools_gated_by_agent_flag(test_db):
    """未启用 procedural 的 Agent：门控返回 False"""
    from app.models.agent import Agent

    agent = Agent(id=AID, name="gated", description="", system_prompt="")
    agent.memory_procedural_enabled = False
    test_db.add(agent)
    test_db.commit()

    ctx = _ctx(test_db)
    assert _check_procedural_enabled(ctx) is False
    assert SkillSaveTool().is_available(ctx) is False
    assert SkillReadTool().is_available(ctx) is False
    assert SkillDeleteTool().is_available(ctx) is False


@pytest.mark.asyncio
async def test_skill_tools_available_when_enabled(enable_procedural):
    ctx = _ctx(enable_procedural)
    assert SkillSaveTool().is_available(ctx) is True
    assert SkillReadTool().is_available(ctx) is True
    assert SkillDeleteTool().is_available(ctx) is True

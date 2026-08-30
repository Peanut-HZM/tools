"""Runtime 技能索引注入测试（P2-②）"""
import uuid
from unittest.mock import MagicMock

import pytest

from app.services.harness.agent_runtime import AgentRuntime


def _runtime(agent, db) -> AgentRuntime:
    """最小 runtime 构造（不跑 run()，只测块构建）"""
    ctx = MagicMock()
    ctx.db = db
    ctx.user_id = str(uuid.uuid4())
    ctx.agent_id = agent.id
    rt = AgentRuntime.__new__(AgentRuntime)
    rt._current_agent = agent
    rt.ctx = ctx
    rt._cached_memory_block = ""
    rt._cached_skill_block = ""
    return rt


def _agent(procedural_enabled=True):
    a = MagicMock()
    a.id = uuid.uuid4()
    a.memory_procedural_enabled = procedural_enabled
    a.system_prompt = "You are a test agent."
    return a


@pytest.mark.asyncio
async def test_skill_block_injected(test_db):
    from app.services.harness.skill_service import SkillService

    aid, uid = uuid.uuid4(), uuid.uuid4()
    await SkillService(test_db).save(aid, uid, "deploy", "部署前检查", "步骤")
    rt = _runtime(_agent(True), test_db)
    rt.ctx.user_id = str(uid)
    block = await rt._build_skill_block()
    assert "<procedural_memory>" in block
    assert "deploy" in block
    assert "skill_read" in block


@pytest.mark.asyncio
async def test_skill_block_empty_when_disabled(test_db):
    rt = _runtime(_agent(False), test_db)
    assert await rt._build_skill_block() == ""


@pytest.mark.asyncio
async def test_skill_block_empty_when_no_skills(test_db):
    rt = _runtime(_agent(True), test_db)
    assert await rt._build_skill_block() == ""


@pytest.mark.asyncio
async def test_skill_block_in_messages(test_db):
    """_build_messages_for_llm 应把技能块拼进 system 消息"""
    from app.services.harness.skill_service import SkillService

    aid, uid = uuid.uuid4(), uuid.uuid4()
    await SkillService(test_db).save(aid, uid, "deploy", "部署前检查", "步骤")

    rt = _runtime(_agent(True), test_db)
    rt.ctx.user_id = str(uid)
    rt._cached_skill_block = await rt._build_skill_block()
    # session.messages 为空列表时也要能组装
    rt.session = MagicMock()
    rt.session.messages = []
    rt._current_agent.memory_short_term_policy = "full"
    rt._current_agent.memory_short_term_window = 20

    msgs = rt._build_messages_for_llm()
    assert msgs[0]["role"] == "system"
    assert "<procedural_memory>" in msgs[0]["content"]

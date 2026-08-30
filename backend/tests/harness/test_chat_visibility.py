"""聊天入口 Agent 可见性校验测试（P2-④）"""
import uuid

import pytest

from app.api.routes.chat_stream import _can_use_agent
from app.models.agent import Agent

AID = uuid.uuid4()
OWNER_ID = uuid.uuid4()
OTHER_ID = uuid.uuid4()


def _agent(visibility="public", owner_id=OWNER_ID) -> Agent:
    a = Agent(id=AID, name="v", description="", system_prompt="")
    a.visibility = visibility
    a.owner_id = owner_id
    return a


def test_public_agent_usable_by_anyone():
    assert _can_use_agent(_agent("public"), {"id": str(OTHER_ID), "role": "user"}) is True


def test_unlisted_agent_usable_by_anyone():
    assert _can_use_agent(_agent("unlisted"), {"id": str(OTHER_ID), "role": "user"}) is True


def test_private_agent_usable_by_owner():
    assert _can_use_agent(_agent("private"), {"id": str(OWNER_ID), "role": "user"}) is True


def test_private_agent_usable_by_admin():
    assert _can_use_agent(_agent("private"), {"id": str(OTHER_ID), "role": "admin"}) is True


def test_private_agent_denied_for_others():
    assert _can_use_agent(_agent("private"), {"id": str(OTHER_ID), "role": "user"}) is False


def test_private_agent_without_owner_denied_for_users():
    """owner_id 为 None 的 private agent：仅 admin 可用"""
    a = _agent("private", owner_id=None)
    assert _can_use_agent(a, {"id": str(OTHER_ID), "role": "user"}) is False
    assert _can_use_agent(a, {"id": str(OTHER_ID), "role": "admin"}) is True

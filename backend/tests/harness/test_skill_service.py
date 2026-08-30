"""SkillService 单元测试（P2-②）"""
import uuid

import pytest

from app.services.harness.skill_service import SkillService

AID = uuid.UUID("00000000-0000-0000-0000-000000000002")
UID = uuid.UUID("00000000-0000-0000-0000-000000000003")
UID2 = uuid.UUID("00000000-0000-0000-0000-000000000004")


@pytest.mark.asyncio
async def test_save_creates(test_db):
    svc = SkillService(test_db)
    s = await svc.save(AID, UID, "s1", "触发条件", "步骤")
    assert s.name == "s1"
    assert s.use_count == 0


@pytest.mark.asyncio
async def test_save_upsert_preserves_use_count(test_db):
    svc = SkillService(test_db)
    await svc.save(AID, UID, "s1", "旧触发", "旧内容")
    await svc.increment_use_count(AID, UID, "s1")
    await svc.save(AID, UID, "s1", "新触发", "新内容", importance=0.9)
    s = await svc.get(AID, UID, "s1")
    assert s.trigger == "新触发"
    assert s.importance == 0.9
    assert s.use_count == 1  # UPSERT 保留使用计数


@pytest.mark.asyncio
async def test_isolation_by_agent_and_user(test_db):
    svc = SkillService(test_db)
    await svc.save(AID, UID, "s1", "t", "c")
    assert await svc.get(AID, UID2, "s1") is None
    assert await svc.delete(AID, UID2, "s1") is False


@pytest.mark.asyncio
async def test_list_enabled_filters_disabled(test_db):
    svc = SkillService(test_db)
    await svc.save(AID, UID, "on", "t", "c")
    off = await svc.save(AID, UID, "off", "t", "c")
    off.is_enabled = False
    test_db.commit()
    names = [s.name for s in await svc.list_enabled(AID, UID)]
    assert names == ["on"]


@pytest.mark.asyncio
async def test_list_enabled_cap_20(test_db):
    svc = SkillService(test_db)
    for i in range(25):
        await svc.save(AID, UID, f"s{i}", "t", "c")
    assert len(await svc.list_enabled(AID, UID)) == 20
    assert len(await svc.list_all(AID, UID)) == 25


@pytest.mark.asyncio
async def test_delete(test_db):
    svc = SkillService(test_db)
    await svc.save(AID, UID, "s1", "t", "c")
    assert await svc.delete(AID, UID, "s1") is True
    assert await svc.get(AID, UID, "s1") is None

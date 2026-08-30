"""SkillService — 程序性记忆（技能）CRUD

P2-② Memory procedural
无向量检索：技能索引直接注入 system prompt（见 spec §3.1）。
"""
import logging
import uuid
from typing import List, Optional

from sqlalchemy.orm import Session as DBSession

logger = logging.getLogger(__name__)

# 索引注入上限（spec §3.4：超过按 updated_at 截断）
_MAX_INDEX_SIZE = 20


class SkillService:
    """技能服务：save/get/list/delete + 使用计数"""

    def __init__(self, db: DBSession):
        self._db = db

    async def save(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        name: str,
        trigger: str,
        content: str,
        importance: float = 0.5,
    ):
        """按 name UPSERT 技能（use_count 保留）"""
        from app.models.agent_procedural_memory import AgentProceduralMemory

        row = (
            self._db.query(AgentProceduralMemory)
            .filter(
                AgentProceduralMemory.agent_id == agent_id,
                AgentProceduralMemory.user_id == user_id,
                AgentProceduralMemory.name == name,
            )
            .first()
        )
        if row:
            row.trigger = trigger
            row.content = content
            row.importance = importance
        else:
            row = AgentProceduralMemory(
                agent_id=agent_id,
                user_id=user_id,
                name=name,
                trigger=trigger,
                content=content,
                importance=importance,
            )
            self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row

    async def get(
        self, agent_id: uuid.UUID, user_id: uuid.UUID, name: str
    ) -> Optional[object]:
        """按 name 精确查询（隔离在 (agent_id, user_id) 内）"""
        from app.models.agent_procedural_memory import AgentProceduralMemory

        return (
            self._db.query(AgentProceduralMemory)
            .filter(
                AgentProceduralMemory.agent_id == agent_id,
                AgentProceduralMemory.user_id == user_id,
                AgentProceduralMemory.name == name,
            )
            .first()
        )

    async def list_enabled(self, agent_id: uuid.UUID, user_id: uuid.UUID) -> List:
        """启用技能（updated_at 倒序，上限 _MAX_INDEX_SIZE）"""
        from app.models.agent_procedural_memory import AgentProceduralMemory

        return (
            self._db.query(AgentProceduralMemory)
            .filter(
                AgentProceduralMemory.agent_id == agent_id,
                AgentProceduralMemory.user_id == user_id,
                AgentProceduralMemory.is_enabled == True,  # noqa: E712
            )
            .order_by(AgentProceduralMemory.updated_at.desc())
            .limit(_MAX_INDEX_SIZE)
            .all()
        )

    async def list_all(self, agent_id: uuid.UUID, user_id: uuid.UUID) -> List:
        """全部技能（含禁用，管理用）"""
        from app.models.agent_procedural_memory import AgentProceduralMemory

        return (
            self._db.query(AgentProceduralMemory)
            .filter(
                AgentProceduralMemory.agent_id == agent_id,
                AgentProceduralMemory.user_id == user_id,
            )
            .order_by(AgentProceduralMemory.updated_at.desc())
            .all()
        )

    async def delete(self, agent_id: uuid.UUID, user_id: uuid.UUID, name: str) -> bool:
        """删除技能，返回是否删除成功"""
        row = await self.get(agent_id, user_id, name)
        if row is None:
            return False
        self._db.delete(row)
        self._db.commit()
        return True

    async def increment_use_count(
        self, agent_id: uuid.UUID, user_id: uuid.UUID, name: str
    ) -> None:
        """读即计数（best-effort，失败不阻塞对话）"""
        try:
            row = await self.get(agent_id, user_id, name)
            if row:
                row.use_count = (row.use_count or 0) + 1
                self._db.commit()
        except Exception as e:
            logger.warning("increment_use_count 失败: %s", type(e).__name__)

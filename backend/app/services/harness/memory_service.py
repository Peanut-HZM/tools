"""MemoryService — 记忆读写 + 向量检索"""
import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session as DBSession

from app.services.harness.embeddings.provider import EmbeddingProvider

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """记忆检索结果"""
    key: str
    value: Any
    score: float = 0.0
    importance: float = 0.5
    access_count: int = 0
    summary: Optional[str] = None
    has_embedding: bool = False


class MemoryService:
    """记忆服务：封装 KV 读写 + 向量检索 + 降级逻辑"""

    def __init__(
        self,
        db: DBSession,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ):
        self._db = db
        self._provider = embedding_provider

    async def store(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        key: str,
        value: Dict[str, Any],
        importance: float = 0.5,
        summary: Optional[str] = None,
    ) -> None:
        """写入记忆：生成 embedding + UPSERT"""
        from app.models.agent_memory import AgentMemoryLongTerm

        # 生成 embedding（从 value 中提取文本）
        embedding_str = None
        if self._provider:
            try:
                text = self._extract_text(value)
                vectors = await self._provider.embed([text])
                embedding_str = json.dumps(vectors[0])
            except Exception as e:
                logger.warning("embedding 生成失败，KV 仍保存: %s", type(e).__name__)

        # UPSERT
        existing = (
            self._db.query(AgentMemoryLongTerm)
            .filter(
                AgentMemoryLongTerm.agent_id == agent_id,
                AgentMemoryLongTerm.user_id == user_id,
                AgentMemoryLongTerm.key == key,
            )
            .first()
        )

        if existing:
            existing.value = value
            existing.summary = summary
            existing.importance = importance
            if embedding_str:
                existing.embedding = embedding_str
        else:
            record = AgentMemoryLongTerm(
                agent_id=agent_id,
                user_id=user_id,
                key=key,
                value=value,
                summary=summary,
                importance=importance,
                embedding=embedding_str,
            )
            self._db.add(record)

        self._db.commit()

    async def search(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        threshold: float = 0.7,
        timeout_seconds: float = 5.0,
    ) -> List[MemoryEntry]:
        """向量检索 + 降级"""
        # 空 / 空白 query：跳过向量与关键词两条路径
        # 关键词 LIKE 会用 "%%" 匹配所有行，等同于返回任意 5 条
        if not query or not query.strip():
            return []

        # 没有 embedding provider 时直接走关键词（带兜底异常保护）
        if not self._provider:
            return await self._safe_keyword_search(agent_id, user_id, query, top_k)

        try:
            results = await asyncio.wait_for(
                self._vector_search(agent_id, user_id, query, top_k, threshold),
                timeout=timeout_seconds,
            )
            if results:
                return results
        except asyncio.TimeoutError:
            logger.warning("向量检索超时，降级为关键词搜索")
        except Exception as e:
            logger.warning("向量检索失败: %s，降级为关键词搜索", type(e).__name__)

        return await self._safe_keyword_search(agent_id, user_id, query, top_k)

    async def _safe_keyword_search(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        query: str,
        top_k: int,
    ) -> List[MemoryEntry]:
        """关键词降级搜索（带异常保护，避免阻塞对话）"""
        try:
            return await self._keyword_search(agent_id, user_id, query, top_k)
        except Exception as e:
            logger.warning("关键词检索失败: %s", type(e).__name__)
            return []

    async def _vector_search(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        query: str,
        top_k: int,
        threshold: float,
    ) -> List[MemoryEntry]:
        """向量检索实现"""
        from app.models.agent_memory import AgentMemoryLongTerm
        from sqlalchemy import text as sa_text

        # 生成 query embedding
        vectors = await self._provider.embed([query])
        query_vec = json.dumps(vectors[0])

        # SQL 查询（cosine distance）
        sql = sa_text("""
            SELECT key, value, importance, access_count, summary,
                   1 - (embedding <=> :query_vec::vector) AS similarity
            FROM agent_memory_long_term
            WHERE agent_id = :agent_id
              AND user_id = :user_id
              AND embedding IS NOT NULL
            ORDER BY embedding <=> :query_vec::vector
            LIMIT :top_k
        """)

        rows = self._db.execute(sql, {
            "query_vec": query_vec,
            "agent_id": str(agent_id),
            "user_id": str(user_id),
            "top_k": top_k,
        }).fetchall()

        results = []
        hit_keys = []
        for row in rows:
            score = float(row.similarity) * float(row.importance)
            if score >= threshold:
                results.append(MemoryEntry(
                    key=row.key,
                    value=row.value,
                    score=score,
                    importance=float(row.importance),
                    access_count=row.access_count,
                    summary=row.summary,
                ))
                hit_keys.append(row.key)

        # 更新 access_count
        if hit_keys:
            self._db.execute(
                sa_text("""
                    UPDATE agent_memory_long_term
                    SET access_count = access_count + 1
                    WHERE agent_id = :agent_id
                      AND user_id = :user_id
                      AND key = ANY(:keys)
                """),
                {"agent_id": str(agent_id), "user_id": str(user_id), "keys": hit_keys},
            )
            self._db.commit()

        return results

    async def _keyword_search(
        self,
        agent_id: uuid.UUID,
        user_id: uuid.UUID,
        query: str,
        top_k: int,
    ) -> List[MemoryEntry]:
        """关键词降级搜索"""
        from app.models.agent_memory import AgentMemoryLongTerm

        pattern = f"%{query}%"
        rows = (
            self._db.query(AgentMemoryLongTerm)
            .filter(
                AgentMemoryLongTerm.agent_id == agent_id,
                AgentMemoryLongTerm.user_id == user_id,
            )
            .filter(
                (AgentMemoryLongTerm.key.ilike(pattern))
                | (AgentMemoryLongTerm.summary.ilike(pattern))
            )
            .limit(top_k)
            .all()
        )
        return [
            MemoryEntry(
                key=r.key, value=r.value, score=0.5,
                importance=r.importance, access_count=r.access_count,
                summary=r.summary,
            )
            for r in rows
        ]

    async def get_by_key(
        self, agent_id: uuid.UUID, user_id: uuid.UUID, key: str
    ) -> Optional[MemoryEntry]:
        """按 key 精确查询"""
        from app.models.agent_memory import AgentMemoryLongTerm

        row = (
            self._db.query(AgentMemoryLongTerm)
            .filter(
                AgentMemoryLongTerm.agent_id == agent_id,
                AgentMemoryLongTerm.user_id == user_id,
                AgentMemoryLongTerm.key == key,
            )
            .first()
        )
        if row is None:
            return None
        return MemoryEntry(
            key=row.key, value=row.value, importance=row.importance,
            access_count=row.access_count, summary=row.summary,
        )

    async def list_all(
        self, agent_id: uuid.UUID, user_id: uuid.UUID
    ) -> List[MemoryEntry]:
        """列出所有记忆"""
        from app.models.agent_memory import AgentMemoryLongTerm

        rows = (
            self._db.query(AgentMemoryLongTerm)
            .filter(
                AgentMemoryLongTerm.agent_id == agent_id,
                AgentMemoryLongTerm.user_id == user_id,
            )
            .order_by(AgentMemoryLongTerm.updated_at.desc())
            .all()
        )
        return [
            MemoryEntry(
                key=r.key, value=r.value, importance=r.importance,
                access_count=r.access_count, summary=r.summary,
                has_embedding=r.embedding is not None,
            )
            for r in rows
        ]

    async def delete(
        self, agent_id: uuid.UUID, user_id: uuid.UUID, key: str
    ) -> bool:
        """删除记忆"""
        from app.models.agent_memory import AgentMemoryLongTerm

        row = (
            self._db.query(AgentMemoryLongTerm)
            .filter(
                AgentMemoryLongTerm.agent_id == agent_id,
                AgentMemoryLongTerm.user_id == user_id,
                AgentMemoryLongTerm.key == key,
            )
            .first()
        )
        if row is None:
            return False
        self._db.delete(row)
        self._db.commit()
        return True

    @staticmethod
    def _extract_text(value: Any) -> str:
        """从 JSONB value 中提取用于 embedding 的文本"""
        # 优先用 "text" 字段，否则 JSON dump
        if isinstance(value, dict) and "text" in value:
            return str(value["text"])[:2000]
        return json.dumps(value, ensure_ascii=False)[:2000]

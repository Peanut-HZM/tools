"""Agent 记忆管理 API

Phase 3 Plan-1B / Task 6
参考 spec §6.2: docs/superpowers/specs/2026-08-29-agent-harness-phase3-plan1b-memory-vector-design.md

提供 3 个 REST 端点用于从前端浏览/管理长期记忆：
- GET    /api/v1/harness/agents/{agent_id}/memories           列出当前用户的所有记忆
- DELETE /api/v1/harness/agents/{agent_id}/memories/{key}     删除指定记忆
- POST   /api/v1/harness/agents/{agent_id}/memories/search    向量检索（调试用）

所有端点要求认证；非认证调用返回 401。
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/harness/agents/{agent_id}/memories",
    tags=["harness-memories"],
)


def _parse_uuid(value: str, field: str) -> uuid.UUID:
    """解析路径参数为 UUID，失败时抛 400"""
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"{field} 不是合法的 UUID")


@router.get("")
async def list_memories(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """列出当前用户对指定 Agent 的所有记忆"""
    from app.services.harness.memory_service import MemoryService

    svc = MemoryService(db=db, embedding_provider=None)
    agent_uuid = _parse_uuid(agent_id, "agent_id")
    user_uuid = _parse_uuid(str(current_user["id"]), "user_id")

    try:
        entries = await svc.list_all(agent_uuid, user_uuid)
    except Exception as e:
        logger.warning("list_memories 失败: %s", type(e).__name__)
        raise HTTPException(status_code=500, detail="查询记忆失败")

    return {
        "records": [
            {
                "key": e.key,
                "value": e.value,
                "importance": e.importance,
                "access_count": e.access_count,
                "summary": e.summary,
                "has_embedding": True,  # 列表场景不读 embedding 列，避免加载 1536 维向量
            }
            for e in entries
        ],
        "count": len(entries),
    }


@router.delete("/{key}")
async def delete_memory(
    agent_id: str,
    key: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """删除指定记忆"""
    from app.services.harness.memory_service import MemoryService

    svc = MemoryService(db=db, embedding_provider=None)
    agent_uuid = _parse_uuid(agent_id, "agent_id")
    user_uuid = _parse_uuid(str(current_user["id"]), "user_id")

    try:
        deleted = await svc.delete(agent_uuid, user_uuid, key)
    except Exception as e:
        logger.warning("delete_memory 失败: %s", type(e).__name__)
        raise HTTPException(status_code=500, detail="删除记忆失败")

    if not deleted:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {"deleted": True, "key": key}


@router.post("/search")
async def search_memories(
    agent_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """向量检索记忆（调试用）

    body 格式:
    {
        "query": "<自然语言/关键词>",
        "top_k": 5  # 可选
    }

    由于本端点为调试接口，使用 embedding_provider=None（仅关键词 LIKE）。
    生产语义检索由 memory_search tool + AgentRuntime 自动注入承担。
    """
    from app.services.harness.memory_service import MemoryService

    query = (body or {}).get("query", "")
    top_k = (body or {}).get("top_k", 5)
    if not isinstance(top_k, int) or top_k < 1:
        top_k = 5

    svc = MemoryService(db=db, embedding_provider=None)
    agent_uuid = _parse_uuid(agent_id, "agent_id")
    user_uuid = _parse_uuid(str(current_user["id"]), "user_id")

    try:
        results = await svc.search(agent_uuid, user_uuid, query, top_k=top_k)
    except Exception as e:
        logger.warning("search_memories 失败: %s", type(e).__name__)
        raise HTTPException(status_code=500, detail="检索失败")

    return {
        "records": [
            {"key": r.key, "value": r.value, "score": round(r.score, 4)}
            for r in results
        ],
        "count": len(results),
    }
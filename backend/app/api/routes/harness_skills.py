"""Agent 技能（程序性记忆）管理 API

P2-② Memory procedural
- GET    /api/v1/harness/agents/{agent_id}/skills           列出全部技能（含禁用）
- POST   /api/v1/harness/agents/{agent_id}/skills           创建/更新技能
- DELETE /api/v1/harness/agents/{agent_id}/skills/{name}    删除技能
所有端点要求认证；按 (agent_id, current_user.id) 隔离。
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/harness/agents/{agent_id}/skills",
    tags=["harness-skills"],
)


class SkillCreateRequest(BaseModel):
    """创建/更新技能请求体"""
    name: str = Field(..., min_length=1, max_length=100)
    trigger: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    is_enabled: bool = True


def _parse_uuid(value: str, field: str) -> uuid.UUID:
    """解析路径参数为 UUID，失败时抛 400"""
    try:
        return uuid.UUID(value)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail=f"{field} 不是合法的 UUID")


def _serialize(row) -> dict:
    """ORM 行序列化"""
    return {
        "name": row.name,
        "trigger": row.trigger,
        "content": row.content,
        "importance": row.importance,
        "use_count": row.use_count,
        "is_enabled": row.is_enabled,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


@router.get("")
async def list_skills(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """列出当前用户对指定 Agent 的全部技能（含禁用）"""
    from app.services.harness.skill_service import SkillService

    svc = SkillService(db)
    try:
        records = await svc.list_all(
            _parse_uuid(agent_id, "agent_id"),
            _parse_uuid(str(current_user["id"]), "user_id"),
        )
    except Exception as e:
        logger.warning("list_skills 失败: %s", type(e).__name__)
        raise HTTPException(status_code=500, detail="查询技能失败")

    return {"records": [_serialize(r) for r in records], "count": len(records)}


@router.post("", status_code=201)
async def create_skill(
    agent_id: str,
    data: SkillCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """创建/更新技能（按 name UPSERT）"""
    from app.services.harness.skill_service import SkillService

    svc = SkillService(db)
    try:
        row = await svc.save(
            _parse_uuid(agent_id, "agent_id"),
            _parse_uuid(str(current_user["id"]), "user_id"),
            data.name.strip(),
            data.trigger.strip(),
            data.content,
            importance=data.importance,
        )
        row.is_enabled = data.is_enabled
        db.commit()
    except Exception as e:
        logger.warning("create_skill 失败: %s", type(e).__name__)
        raise HTTPException(status_code=500, detail="保存技能失败")

    logger.info("技能已保存: agent=%s name=%s", agent_id, data.name)
    return _serialize(row)


@router.delete("/{name}", status_code=204)
async def delete_skill(
    agent_id: str,
    name: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """删除指定技能"""
    from app.services.harness.skill_service import SkillService

    svc = SkillService(db)
    ok = await svc.delete(
        _parse_uuid(agent_id, "agent_id"),
        _parse_uuid(str(current_user["id"]), "user_id"),
        name,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="技能不存在")
    logger.info("技能已删除: agent=%s name=%s", agent_id, name)

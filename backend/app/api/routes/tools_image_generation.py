"""图像生成工具页面支撑 API

- GET /api/v1/tools/image-generation/agent   获取（并确保存在）图像生成助手 Agent

普通登录用户可访问：页面需要 agent_id 来驱动 harness 聊天流
（Agent 列表接口是 admin-only，普通用户无法自行发现该 Agent）。
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.api.dependencies import get_db, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tools/image-generation", tags=["tools-image-generation"])


@router.get("/agent")
def get_image_gen_agent(
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取（幂等创建）图像生成助手 Agent"""
    from app.services.image_gen_agent import ensure_image_gen_agent

    agent = ensure_image_gen_agent(db)
    return {"agent_id": str(agent.id), "name": agent.name}

"""视频生成工具页面支撑 API

- GET /api/v1/tools/video-generation/agent   获取（并确保存在）视频生成助手 Agent
"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession

from app.api.dependencies import get_db, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/tools/video-generation", tags=["tools-video-generation"])


@router.get("/agent")
def get_video_gen_agent(
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取（幂等创建）视频生成助手 Agent"""
    from app.services.video_gen_agent import ensure_video_gen_agent

    agent = ensure_video_gen_agent(db)
    return {"agent_id": str(agent.id), "name": agent.name}

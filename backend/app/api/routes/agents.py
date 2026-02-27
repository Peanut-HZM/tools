"""
Agent管理路由
用于管理AI Agent配置
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.services.agent_management_service import AgentService

router = APIRouter(prefix="/admin/agents", tags=["admin-agents"])


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1)
    system_prompt: str = Field(..., min_length=1)
    icon: str = Field(default="fa-robot")
    icon_color: str = Field(default="bg-blue-500")
    category: str = Field(default="AI工具")


class AgentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    icon: Optional[str] = None
    icon_color: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    description: str
    system_prompt: str
    icon: str
    icon_color: str
    category: str
    is_active: bool
    is_default: bool
    created_at: str
    updated_at: Optional[str] = None


class AgentStats(BaseModel):
    total: int
    active: int
    inactive: int


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """获取Agent列表（管理员）"""
    service = AgentService(db)
    agents = service.list_agents(skip=skip, limit=limit, is_active=is_active)

    return [
        {
            "id": str(agent.id),
            "name": agent.name,
            "description": agent.description,
            "system_prompt": agent.system_prompt,
            "icon": agent.icon,
            "icon_color": agent.icon_color,
            "category": agent.category,
            "is_active": agent.is_active,
            "is_default": agent.is_default,
            "created_at": agent.created_at.isoformat() if agent.created_at else None,
            "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
        }
        for agent in agents
    ]


@router.post("", response_model=AgentResponse)
async def create_agent(
    data: AgentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """创建Agent（管理员）"""
    service = AgentService(db)
    agent = service.create_agent(
        name=data.name,
        description=data.description,
        system_prompt=data.system_prompt,
        icon=data.icon,
        icon_color=data.icon_color,
        category=data.category,
    )

    return {
        "id": str(agent.id),
        "name": agent.name,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "icon": agent.icon,
        "icon_color": agent.icon_color,
        "category": agent.category,
        "is_active": agent.is_active,
        "is_default": agent.is_default,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """获取Agent详情（管理员）"""
    service = AgentService(db)
    agent = service.get_agent(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")

    return {
        "id": str(agent.id),
        "name": agent.name,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "icon": agent.icon,
        "icon_color": agent.icon_color,
        "category": agent.category,
        "is_active": agent.is_active,
        "is_default": agent.is_default,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    data: AgentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """更新Agent（管理员）"""
    service = AgentService(db)

    update_data = {k: v for k, v in data.dict().items() if v is not None}
    agent = service.update_agent(agent_id, **update_data)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")

    return {
        "id": str(agent.id),
        "name": agent.name,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "icon": agent.icon,
        "icon_color": agent.icon_color,
        "category": agent.category,
        "is_active": agent.is_active,
        "is_default": agent.is_default,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """删除Agent（管理员）"""
    service = AgentService(db)
    success = service.delete_agent(agent_id)

    if not success:
        raise HTTPException(status_code=404, detail="Agent不存在")

    return {"message": "Agent已删除"}


@router.post("/{agent_id}/default", response_model=AgentResponse)
async def set_default_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """设置默认Agent（管理员）"""
    service = AgentService(db)
    agent = service.set_default_agent(agent_id)

    if not agent:
        raise HTTPException(status_code=404, detail="Agent不存在")

    return {
        "id": str(agent.id),
        "name": agent.name,
        "description": agent.description,
        "system_prompt": agent.system_prompt,
        "icon": agent.icon,
        "icon_color": agent.icon_color,
        "category": agent.category,
        "is_active": agent.is_active,
        "is_default": agent.is_default,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


@router.get("/stats/overview", response_model=AgentStats)
async def get_agent_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    """获取Agent统计（管理员）"""
    service = AgentService(db)
    stats = service.get_agent_stats()
    return stats

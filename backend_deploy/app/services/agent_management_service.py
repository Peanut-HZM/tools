"""
Agent管理服务
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
import uuid

from app.models.agent import Agent


class AgentService:
    """Agent管理服务"""

    def __init__(self, db: Session):
        self.db = db

    def list_agents(
        self, skip: int = 0, limit: int = 100, is_active: Optional[bool] = None
    ) -> List[Agent]:
        """获取Agent列表"""
        query = self.db.query(Agent)

        if is_active is not None:
            query = query.filter(Agent.is_active == is_active)

        return query.order_by(desc(Agent.created_at)).offset(skip).limit(limit).all()

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """获取单个Agent"""
        return self.db.query(Agent).filter(Agent.id == agent_id).first()

    def get_default_agent(self) -> Optional[Agent]:
        """获取默认Agent"""
        return self.db.query(Agent).filter(Agent.is_default == True).first()

    def create_agent(
        self,
        name: str,
        description: str,
        system_prompt: str,
        icon: str = "fa-robot",
        icon_color: str = "bg-blue-500",
        category: str = "AI工具",
    ) -> Agent:
        """创建Agent"""
        agent = Agent(
            name=name,
            description=description,
            system_prompt=system_prompt,
            icon=icon,
            icon_color=icon_color,
            category=category,
            is_active=True,
            is_default=False,
        )
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def update_agent(
        self,
        agent_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        system_prompt: Optional[str] = None,
        icon: Optional[str] = None,
        icon_color: Optional[str] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Agent]:
        """更新Agent"""
        agent = self.get_agent(agent_id)
        if not agent:
            return None

        if name is not None:
            agent.name = name
        if description is not None:
            agent.description = description
        if system_prompt is not None:
            agent.system_prompt = system_prompt
        if icon is not None:
            agent.icon = icon
        if icon_color is not None:
            agent.icon_color = icon_color
        if category is not None:
            agent.category = category
        if is_active is not None:
            agent.is_active = is_active

        self.db.commit()
        self.db.refresh(agent)
        return agent

    def delete_agent(self, agent_id: str) -> bool:
        """删除Agent"""
        agent = self.get_agent(agent_id)
        if not agent:
            return False

        self.db.delete(agent)
        self.db.commit()
        return True

    def set_default_agent(self, agent_id: str) -> Optional[Agent]:
        """设置默认Agent"""
        # 先取消所有默认
        self.db.query(Agent).update({Agent.is_default: False})

        # 设置新的默认
        agent = self.get_agent(agent_id)
        if not agent:
            return None

        agent.is_default = True
        self.db.commit()
        self.db.refresh(agent)
        return agent

    def get_agent_stats(self) -> Dict[str, Any]:
        """获取Agent统计信息"""
        total = self.db.query(Agent).count()
        active = self.db.query(Agent).filter(Agent.is_active == True).count()

        return {
            "total": total,
            "active": active,
            "inactive": total - active,
        }

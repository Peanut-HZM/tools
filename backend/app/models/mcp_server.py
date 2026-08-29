"""McpServer — MCP Server 配置表

Phase 3-Plan-1A: MCP 工具支持核心骨架
存储 MCP server 的连接信息、状态缓存、工具计数。
"""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class McpServer(Base):
    """MCP Server 配置

    存储 MCP server 的连接信息、状态缓存、工具计数。
    """

    __tablename__ = "mcp_servers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True, index=True)
    server_url = Column(String(500), nullable=False)
    transport = Column(String(20), nullable=False, default="sse")  # sse / stdio / http
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    headers_json = Column(Text, nullable=True)  # JSON 字符串，鉴权用
    timeout_seconds = Column(Integer, nullable=False, default=30)

    # 状态缓存（由最近一次 test/sync 更新）
    last_connected_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    tools_count = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<McpServer {self.name} url={self.server_url} active={self.is_active}>"

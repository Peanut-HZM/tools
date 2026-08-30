"""MCP Server Pydantic schemas

Phase 3-Plan-1A: MCP 工具支持核心骨架
"""
from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class McpServerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    server_url: str = Field(..., min_length=1, max_length=500)
    # P2-①c: 扩展 stdio / streamable http（原有 sse 保持不变）
    transport: Literal["sse", "http", "stdio"] = "sse"
    headers: Optional[dict[str, str]] = None
    # stdio 启动配置：{"command": str, "args": [str], "env": {str: str}}；sse/http 时忽略
    command: Optional[dict] = None
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class McpServerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    server_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    headers: Optional[dict[str, str]] = None
    command: Optional[dict] = None  # 非 None 时整体替换 command_json
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=300)
    is_active: Optional[bool] = None


class McpServerResponse(BaseModel):
    id: UUID
    name: str
    server_url: str
    transport: str
    command_json: Optional[str] = None  # P2-①c: stdio 启动配置（JSON 字符串）
    is_active: bool
    timeout_seconds: int
    last_connected_at: Optional[datetime] = None
    last_error: Optional[str] = None
    tools_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class McpServerTestResponse(BaseModel):
    success: bool
    tools: list[dict]
    error: Optional[str] = None

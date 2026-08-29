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
    transport: Literal["sse"] = "sse"  # 本期仅支持 sse
    headers: Optional[dict[str, str]] = None
    timeout_seconds: int = Field(default=30, ge=1, le=300)


class McpServerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    server_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    headers: Optional[dict[str, str]] = None
    timeout_seconds: Optional[int] = Field(default=None, ge=1, le=300)
    is_active: Optional[bool] = None


class McpServerResponse(BaseModel):
    id: UUID
    name: str
    server_url: str
    transport: str
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

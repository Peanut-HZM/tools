"""Harness Phase 1 Pydantic schemas

参考 spec §8
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ToolCreate(BaseModel):
    """创建工具请求体"""

    name: str = Field(..., max_length=100)
    display_name: str = Field(..., max_length=100)
    description: str
    type: str = Field(..., pattern="^(builtin|http|mcp|plugin)$")
    config: Dict[str, Any] = Field(default_factory=dict)
    parameters_schema: Dict[str, Any]
    returns_schema: Optional[Dict[str, Any]] = None
    is_available_condition: Dict[str, Any] = Field(default_factory=dict)
    rate_limit_per_minute: Optional[int] = None
    metadata_: Optional[Dict[str, Any]] = Field(default_factory=dict, alias="metadata")


class ToolUpdate(BaseModel):
    """更新工具请求体"""

    display_name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    parameters_schema: Optional[Dict[str, Any]] = None
    returns_schema: Optional[Dict[str, Any]] = None
    is_available_condition: Optional[Dict[str, Any]] = None
    rate_limit_per_minute: Optional[int] = None
    metadata_: Optional[Dict[str, Any]] = Field(default=None, alias="metadata")
    is_active: Optional[bool] = None


class ToolView(BaseModel):
    """工具视图（响应体）"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    display_name: str
    description: str
    type: str
    config: Dict[str, Any]
    parameters_schema: Dict[str, Any]
    returns_schema: Optional[Dict[str, Any]]
    is_available_condition: Dict[str, Any]
    rate_limit_per_minute: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ToolListView(BaseModel):
    """工具列表响应体"""

    items: List[ToolView]
    total: int

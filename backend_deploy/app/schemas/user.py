"""
用户 Schema
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名 (3-50 字符)")
    email: str = Field(..., description="邮箱地址")


class UserCreate(BaseModel):
    """创建用户请求"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(...)
    password: str = Field(..., min_length=8, max_length=128, description="密码 (8-128 字符)")


class UserUpdate(BaseModel):
    """更新用户请求"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """用户响应"""
    id: str
    username: str
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

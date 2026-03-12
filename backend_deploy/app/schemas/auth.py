"""
用户认证相关的 Schemas
"""
from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional
from datetime import datetime
import uuid


# ============ 用户相关 Schemas ============

class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名 (3-50 字符)")
    email: str = Field(..., description="邮箱地址")

    @validator('email')
    def validate_email(cls, v):
        if '@' not in v or '.' not in v.split('@')[-1]:
            raise ValueError('无效的邮箱格式')
        return v


class UserCreate(UserBase):
    """创建用户请求"""
    password: str = Field(..., min_length=8, max_length=128, description="密码 (8-128 字符)")


class UserUpdate(BaseModel):
    """更新用户请求"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """用户响应"""
    id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============ 认证相关 Schemas ============

class LoginRequest(BaseModel):
    """登录请求"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class LoginResponse(BaseModel):
    """登录响应"""
    user: UserResponse
    token: str
    expires_at: datetime


class RegisterRequest(UserCreate):
    """注册请求"""
    pass


class RegisterResponse(BaseModel):
    """注册响应"""
    user: UserResponse
    token: str
    expires_at: datetime


class TokenRefresh(BaseModel):
    """Token 刷新请求"""
    token: str


class TokenResponse(BaseModel):
    """Token 响应"""
    token: str
    expires_at: datetime


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    old_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码 (8-128 字符)")

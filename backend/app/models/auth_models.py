"""
Authentication Models - Pydantic models for user authentication
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

EMAIL_PATTERN = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"


class UserBase(BaseModel):
    """Base user model"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=EMAIL_PATTERN)
    phone: Optional[str] = None


class UserCreate(BaseModel):
    """User registration request model"""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=EMAIL_PATTERN)
    password: str = Field(..., min_length=6, max_length=100)
    phone: Optional[str] = None
    email_code: Optional[str] = None
    phone_code: Optional[str] = None


class UserLogin(BaseModel):
    """User login request model"""
    username: str
    password: str


class User(UserBase):
    """User model with ID"""
    user_id: str
    role: str = "user"
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserInDB(User):
    """User model stored in database with hashed password"""
    hashed_password: str


class Token(BaseModel):
    """JWT Token response model"""
    access_token: str
    token_type: str = "bearer"
    role: str = "user"


class TokenData(BaseModel):
    """Token payload data"""
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[datetime] = None


class AuthResponse(BaseModel):
    """Authentication response model"""
    user_id: str
    username: str
    email: str
    role: str
    token: str
    phone: Optional[str] = None


class UserResponse(BaseModel):
    """User info response model"""
    user_id: str
    username: str
    email: str
    role: str
    created_at: datetime
    phone: Optional[str] = None


class UserRoleUpdate(BaseModel):
    """User role update request model"""
    role: str = Field(..., pattern="^(user|admin)$")



class PasswordChange(BaseModel):
    """Password change request model"""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


class UserListResponse(BaseModel):
    """Paginated user list response"""
    total: int
    page: int
    page_size: int
    total_pages: int
    users: List[UserResponse]


class UserBatchDeleteRequest(BaseModel):
    """Batch delete users request"""
    user_ids: List[str]


class UserBatchUpdateRoleRequest(BaseModel):
    """Batch update user role request"""
    user_ids: List[str]
    role: str = Field(..., pattern="^(user|admin)$")


class AdminPasswordReset(BaseModel):
    """管理员重置密码请求"""
    mode: str = Field(..., pattern="^(direct|random)$", description="重置模式：direct=直接设置，random=随机生成")
    new_password: Optional[str] = Field(None, min_length=8, max_length=100, description="新密码（mode=direct 时必填）")


class AdminPasswordResetResponse(BaseModel):
    """管理员重置密码响应"""
    success: bool
    new_password: str
    message: str


class UserPasswordChange(BaseModel):
    """用户修改密码请求"""
    old_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, max_length=100, description="新密码")


class UserPasswordChangeResponse(BaseModel):
    """用户修改密码响应"""
    success: bool
    message: str

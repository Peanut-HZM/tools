"""
Authentication Models - Pydantic models for user authentication
"""
from pydantic import BaseModel, Field
from typing import Optional
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

"""
Authentication Models - Pydantic models for user authentication
"""
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """Base user model"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(BaseModel):
    """User registration request model"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)


class UserLogin(BaseModel):
    """User login request model"""
    username: str
    password: str


class User(UserBase):
    """User model with ID"""
    user_id: str
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


class TokenData(BaseModel):
    """Token payload data"""
    user_id: Optional[str] = None
    username: Optional[str] = None
    exp: Optional[datetime] = None


class AuthResponse(BaseModel):
    """Authentication response model"""
    user_id: str
    username: str
    email: str
    token: str


class UserResponse(BaseModel):
    """User info response model"""
    user_id: str
    username: str
    email: str
    created_at: datetime


class PasswordChange(BaseModel):
    """Password change request model"""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=100)

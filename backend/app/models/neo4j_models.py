"""Neo4j 连接配置模型（SQLAlchemy + Pydantic）。

密码 Fernet 加密后存 encrypted_password，响应永不回传。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, Boolean, DateTime, func

from app.models.base import Base


class Neo4jConnection(Base):
    __tablename__ = "neo4j_connections"

    id = Column(String(36), primary_key=True)  # UUID 字符串
    user_id = Column(String(64), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    uri = Column(String(512), nullable=False)
    username = Column(String(128), nullable=False)
    encrypted_password = Column(String(1024), nullable=False)
    database = Column(String(128), nullable=False, default="neo4j")
    readonly = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Neo4jConnectionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    uri: str = Field(..., min_length=1, max_length=512)
    username: str = Field(..., min_length=1, max_length=128)
    password: str = Field(..., min_length=1)
    database: str = Field("neo4j", max_length=128)


class Neo4jConnectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    uri: Optional[str] = Field(None, min_length=1, max_length=512)
    username: Optional[str] = Field(None, min_length=1, max_length=128)
    password: Optional[str] = Field(None, min_length=1)  # 留空表示不变
    database: Optional[str] = Field(None, max_length=128)


class Neo4jConnectionResponse(BaseModel):
    id: str
    user_id: str
    name: str
    uri: str
    username: str
    database: str
    readonly: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

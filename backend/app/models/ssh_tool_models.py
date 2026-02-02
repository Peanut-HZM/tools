from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class CreateSSHRequest(BaseModel):
    alias: str = Field(..., min_length=1, max_length=64)
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(22, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=128)
    password: Optional[str] = Field(None, max_length=512)
    private_key: Optional[str] = Field(None, max_length=8000)
    passphrase: Optional[str] = Field(None, max_length=512)
    group_name: Optional[str] = Field(None, max_length=64)

class UpdateSSHRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)
    alias: Optional[str] = Field(None, min_length=1, max_length=64)
    host: Optional[str] = Field(None, min_length=1, max_length=255)
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = Field(None, min_length=1, max_length=128)
    password: Optional[str] = Field(None, max_length=512)
    private_key: Optional[str] = Field(None, max_length=8000)
    passphrase: Optional[str] = Field(None, max_length=512)
    group_name: Optional[str] = Field(None, max_length=64)
    is_active: Optional[bool] = None

class DeleteSSHRequest(BaseModel):
    id: str = Field(..., min_length=1, max_length=64)

class TestSSHConnectionRequest(BaseModel):
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(22, ge=1, le=65535)
    username: str = Field(..., min_length=1, max_length=128)
    password: Optional[str] = Field(None, max_length=512)
    private_key: Optional[str] = Field(None, max_length=8000)
    passphrase: Optional[str] = Field(None, max_length=512)

class TestSSHConnectionResponse(BaseModel):
    success: bool
    message: Optional[str] = None

class SSHConfigResponse(BaseModel):
    id: str
    user_id: str
    alias: str
    host: str
    port: int
    username: str
    password: Optional[str] = None
    private_key: Optional[str] = None
    passphrase: Optional[str] = None
    group_name: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class TerminalResizeRequest(BaseModel):
    cols: int
    rows: int

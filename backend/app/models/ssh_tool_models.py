from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

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

# ============ SFTP 相关模型 ============

class SFTPFileInfo(BaseModel):
    name: str
    path: str
    size: int
    modified_time: datetime
    is_directory: bool
    permissions: Optional[str] = None

class SFTPListRequest(BaseModel):
    path: str = Field("/", description="远程目录路径")

class SFTPListResponse(BaseModel):
    files: List[SFTPFileInfo]
    current_path: str

class SFTPDownloadRequest(BaseModel):
    remote_path: str
    local_path: Optional[str] = None

class SFTPDownloadResponse(BaseModel):
    file_name: str
    file_size: int
    content: Optional[str] = None  # 文本内容（如果是文本文件）
    download_url: Optional[str] = None  # 二进制文件的下载 URL

class SFTPUploadRequest(BaseModel):
    remote_path: str
    content: str  # Base64 编码的文件内容
    is_base64: bool = True

class SFTPUploadResponse(BaseModel):
    success: bool
    remote_path: str
    file_size: int

class SFTPDeleteRequest(BaseModel):
    remote_path: str

class SFTPDeleteResponse(BaseModel):
    success: bool
    message: str

class SFTPMkdirRequest(BaseModel):
    remote_path: str
    mode: int = Field(0o755, description="目录权限")

class SFTPMkdirResponse(BaseModel):
    success: bool
    remote_path: str

class SFTPRenameRequest(BaseModel):
    old_path: str
    new_path: str

class SFTPRenameResponse(BaseModel):
    success: bool
    old_path: str
    new_path: str

# ============ SSH 隧道相关模型 ============

class TunnelProtocol(str, Enum):
    TCP = "tcp"
    LOCAL = "local"
    REMOTE = "remote"

class SSHTunnelRequest(BaseModel):
    tunnel_type: TunnelProtocol = Field(TunnelProtocol.LOCAL, description="隧道类型")
    local_port: int = Field(..., ge=1, le=65535, description="本地端口")
    remote_host: str = Field(..., description="远程主机")
    remote_port: int = Field(..., ge=1, le=65535, description="远程端口")

class SSHTunnelResponse(BaseModel):
    tunnel_id: str
    status: str
    message: str

class SSHTunnelInfo(BaseModel):
    tunnel_id: str
    tunnel_type: str
    local_port: int
    remote_host: str
    remote_port: int
    created_at: datetime

class SSHTunnelListResponse(BaseModel):
    tunnels: List[SSHTunnelInfo]

class SSHTunnelStopRequest(BaseModel):
    tunnel_id: str

# ============ 批量命令执行模型 ============

class BatchCommandRequest(BaseModel):
    commands: List[str]
    timeout: int = Field(30, ge=1, le=300, description="超时时间（秒）")

class BatchCommandResult(BaseModel):
    command: str
    stdout: str
    stderr: str
    exit_code: int
    execution_time_ms: float
    error: Optional[str] = None

class BatchCommandResponse(BaseModel):
    results: List[BatchCommandResult]
    total_count: int
    success_count: int
    failed_count: int

# ============ 会话录制模型 ============

class SSHSessionRecord(BaseModel):
    session_id: str
    config_id: str
    config_alias: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    commands_executed: int = 0
    recording_url: Optional[str] = None

class SSHSessionListResponse(BaseModel):
    sessions: List[SSHSessionRecord]
    total: int

# ============ 密钥对管理模型 ============

class SSHKeyPair(BaseModel):
    id: str
    user_id: str
    name: str
    key_type: str  # rsa, ed25519, ecdsa
    public_key: str
    fingerprint: str
    created_at: datetime

class CreateKeyPairRequest(BaseModel):
    name: str
    key_type: str = Field("ed25519", description="密钥类型：rsa, ed25519, ecdsa")
    key_size: int = Field(4096, ge=2048, le=8192, description="RSA 密钥大小")

class CreateKeyPairResponse(BaseModel):
    id: str
    name: str
    key_type: str
    public_key: str
    private_key: str
    fingerprint: str

class DeleteKeyPairRequest(BaseModel):
    key_id: str

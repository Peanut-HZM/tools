"""Checkpoint 时间旅行 Pydantic schemas"""
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class MessageSnapshotItem(BaseModel):
    """快照中单条消息"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    sender_type: str
    role: str
    content: str = Field(max_length=32000)
    message_type: Optional[str] = "text"
    sent_at: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class CheckpointResponse(BaseModel):
    """单个 checkpoint 响应"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    branch_id: UUID
    parent_checkpoint_id: Optional[UUID]
    step_index: int
    phase: str
    checkpoint_kind: str
    label: Optional[str]
    merge_parents: Optional[List[UUID]]
    is_head: bool
    messages_snapshot: List[MessageSnapshotItem]
    agent_state: Dict[str, Any]
    created_at: str


class BranchResponse(BaseModel):
    """分支响应"""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conversation_id: UUID
    name: str
    parent_branch_id: Optional[UUID]
    head_checkpoint_id: Optional[UUID]
    is_archived: bool
    created_at: str
    closed_at: Optional[str]


# ---- Request ----

class CreateBranchRequest(BaseModel):
    source_checkpoint_id: UUID
    name: str = Field(min_length=1, max_length=100)
    start_with_messages: bool = True


class MergeRequest(BaseModel):
    picked_checkpoint_ids: List[UUID] = Field(min_length=2)
    new_branch_name: str = Field(min_length=1, max_length=100)


class UpdateBranchRequest(BaseModel):
    """PATCH /branches/{id} 请求体（改名 / 归档）"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    is_archived: Optional[bool] = None


class WriteCheckpointRequest(BaseModel):
    """POST /checkpoints 请求体（手动写入 checkpoint）"""
    step_index: int
    phase: str
    messages: List[MessageSnapshotItem] = Field(max_length=200)
    scratch_state: Dict[str, Any] = Field(default_factory=dict)
    label: Optional[str] = None


class RollbackResponse(BaseModel):
    conversation_head_checkpoint_id: UUID
    detached_checkpoint_count: int
    target_checkpoint: CheckpointResponse


class CreateBranchResponse(BaseModel):
    """POST /branches 响应：新建分支 + 首个 checkpoint"""
    model_config = ConfigDict(from_attributes=True)

    branch: BranchResponse
    first_checkpoint: CheckpointResponse


class MergeResponse(BaseModel):
    """POST /branches/{id}/merge 响应：新分支 + merge commit"""
    model_config = ConfigDict(from_attributes=True)

    branch: BranchResponse
    merge_commit: CheckpointResponse
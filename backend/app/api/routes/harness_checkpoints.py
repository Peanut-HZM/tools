"""Checkpoint 时间旅行 REST API

Phase 3-Plan-1D / Task 4
"""
import json
import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from app.api.dependencies import get_current_user, get_db
from app.api.schemas.harness_checkpoint import (
    BranchResponse,
    CheckpointResponse,
    CreateBranchRequest,
    CreateBranchResponse,
    MergeRequest,
    MergeResponse,
    RollbackResponse,
)
from app.models.conversation import Conversation
from app.models.harness_models import Branch, SessionCheckpoint
from app.services.harness.checkpoint_service import CheckpointService

logger = logging.getLogger(__name__)

# 资源上限（防 Pydantic-外大对象撑爆 JSONB / 内存）
MAX_MESSAGES_PER_CHECKPOINT = 200
MAX_CONTENT_CHARS = 32000
MAX_SCRATCH_STATE_BYTES = 65536  # 64 KB

router = APIRouter(
    prefix="/api/v1/harness/conversations/{conversation_id}",
    tags=["harness-checkpoints"],
)


# ---- ORM datetime → str 适配 ----

def _datetime_to_str(v):
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.isoformat()
    return v


def _format_checkpoint(cp: SessionCheckpoint) -> dict:
    """把 ORM SessionCheckpoint 转成 dict（datetime → ISO 字符串）"""
    return {
        "id": cp.id,
        "conversation_id": cp.conversation_id,
        "branch_id": cp.branch_id,
        "parent_checkpoint_id": cp.parent_checkpoint_id,
        "step_index": cp.step_index,
        "phase": cp.phase,
        "checkpoint_kind": cp.checkpoint_kind,
        "label": cp.label,
        "merge_parents": cp.merge_parents,
        "is_head": cp.is_head,
        "messages_snapshot": cp.messages_snapshot or [],
        "agent_state": cp.agent_state or {},
        "created_at": _datetime_to_str(getattr(cp, "created_at", None)),
    }


def _format_branch(branch: Branch) -> dict:
    """把 ORM Branch 转成 dict"""
    return {
        "id": branch.id,
        "conversation_id": branch.conversation_id,
        "name": branch.name,
        "parent_branch_id": branch.parent_branch_id,
        "head_checkpoint_id": branch.head_checkpoint_id,
        "is_archived": branch.is_archived,
        "created_at": _datetime_to_str(getattr(branch, "created_at", None)),
        "closed_at": _datetime_to_str(getattr(branch, "closed_at", None)),
    }


def _get_service(db: DBSession = Depends(get_db)) -> CheckpointService:
    return CheckpointService(db)


def _check_tenant(db: DBSession, conversation_id: UUID, current_user: dict) -> Conversation:
    """租户隔离校验：current_user 必须拥有 conversation；否则 404（不泄漏存在性）

    返回 Conversation 对象供后续 handler 复用。
    """
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv is None or conv.user_id != current_user["id"]:
        raise HTTPException(status_code=404, detail="会话不存在")
    return conv


# ---- 分支 ----

@router.get("/branches", response_model=List[BranchResponse])
async def list_branches(
    conversation_id: UUID,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """列出会话的所有分支"""
    _check_tenant(db, conversation_id, current_user)
    cs = CheckpointService(db)
    branches = cs.list_branches(conversation_id)
    logger.info(
        "list_branches conversation_id=%s user_id=%s count=%d",
        conversation_id,
        current_user.get("id"),
        len(branches),
    )
    return [_format_branch(b) for b in branches]


@router.post("/branches", status_code=status.HTTP_201_CREATED, response_model=CreateBranchResponse)
async def create_branch(
    conversation_id: UUID,
    req: CreateBranchRequest,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """从某个 checkpoint 创建新分支"""
    _check_tenant(db, conversation_id, current_user)
    cs = CheckpointService(db)
    try:
        branch, first_cp = cs.branch_from(
            conversation_id=conversation_id,
            source_checkpoint_id=req.source_checkpoint_id,
            branch_name=req.name,
        )
    except ValueError as e:
        logger.warning(
            "create_branch failed conversation_id=%s error_type=%s",
            conversation_id, type(e).__name__,
        )
        raise HTTPException(status_code=400, detail=str(e))

    logger.info(
        "create_branch conversation_id=%s branch_id=%s user_id=%s",
        conversation_id, branch.id, current_user.get("id"),
    )
    return {
        "branch": _format_branch(branch),
        "first_checkpoint": _format_checkpoint(first_cp),
    }


@router.get("/branches/{branch_id}", response_model=BranchResponse)
async def get_branch(
    conversation_id: UUID,
    branch_id: UUID,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取分支详情"""
    _check_tenant(db, conversation_id, current_user)
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if branch is None or branch.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="分支不存在")
    return _format_branch(branch)


@router.patch("/branches/{branch_id}", response_model=BranchResponse)
async def update_branch(
    conversation_id: UUID,
    branch_id: UUID,
    name: Optional[str] = None,
    is_archived: Optional[bool] = None,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """更新分支（改名 / 归档）"""
    _check_tenant(db, conversation_id, current_user)
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if branch is None or branch.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="分支不存在")
    if name is not None:
        branch.name = name
    if is_archived is not None:
        branch.is_archived = is_archived
        if is_archived:
            branch.closed_at = datetime.utcnow()
    db.commit()
    logger.info(
        "update_branch branch_id=%s name_len=%s is_archived=%s user_id=%s",
        branch_id,
        len(name) if isinstance(name, str) else 0,
        is_archived,
        current_user.get("id"),
    )
    return _format_branch(branch)


@router.delete("/branches/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch(
    conversation_id: UUID,
    branch_id: UUID,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """删除分支（checkpoint 保留）"""
    _check_tenant(db, conversation_id, current_user)
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if branch is None or branch.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="分支不存在")
    db.delete(branch)
    db.commit()
    logger.info(
        "delete_branch branch_id=%s user_id=%s",
        branch_id, current_user.get("id"),
    )
    return None


@router.get("/branches/{branch_id}/checkpoints", response_model=List[CheckpointResponse])
async def list_checkpoints(
    conversation_id: UUID,
    branch_id: UUID,
    include_detached: bool = False,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """列出分支 checkpoint"""
    _check_tenant(db, conversation_id, current_user)
    # IDOR 防护：branch_id 必须属于 conversation_id
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if branch is None or branch.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="分支不存在")
    cs = CheckpointService(db)
    cps = cs.list_checkpoints(branch_id, include_detached=include_detached)
    return [_format_checkpoint(c) for c in cps]


# ---- Checkpoint ----

@router.get("/checkpoints/{checkpoint_id}", response_model=CheckpointResponse)
async def get_checkpoint(
    conversation_id: UUID,
    checkpoint_id: UUID,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取单个 checkpoint"""
    _check_tenant(db, conversation_id, current_user)
    cs = CheckpointService(db)
    cp = cs.get_checkpoint(checkpoint_id)
    if cp is None or cp.conversation_id != conversation_id:
        raise HTTPException(status_code=404, detail="checkpoint 不存在")
    return _format_checkpoint(cp)


@router.post("/checkpoints", status_code=status.HTTP_201_CREATED, response_model=CheckpointResponse)
async def write_checkpoint_manual(
    conversation_id: UUID,
    step_index: int,
    phase: str,
    messages: List[dict],
    scratch_state: dict = {},
    label: Optional[str] = None,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """手动写入 checkpoint"""
    conv = _check_tenant(db, conversation_id, current_user)
    cs = CheckpointService(db)

    # 资源上限校验（防 JSONB / 内存膨胀）
    if len(messages) > MAX_MESSAGES_PER_CHECKPOINT:
        raise HTTPException(
            status_code=400,
            detail=f"messages 数量超限 (max={MAX_MESSAGES_PER_CHECKPOINT})",
        )
    scratch_bytes = len(
        json.dumps(scratch_state, ensure_ascii=False).encode("utf-8")
    )
    if scratch_bytes > MAX_SCRATCH_STATE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"scratch_state 过大 (max={MAX_SCRATCH_STATE_BYTES} bytes)",
        )

    if not conv.main_branch_id:
        branch = Branch(conversation_id=conversation_id, name="主线")
        db.add(branch)
        db.flush()
        conv.main_branch_id = branch.id
        db.commit()

    # 把 messages dict 转回伪 Message 对象
    class _FakeMsg:
        def __init__(self, d):
            self.id = d.get("id")
            self.sender_type = d.get("sender_type", "user")
            self.role = d.get("role", self.sender_type)
            content = d.get("content", "")
            # 截断过长的 content
            if isinstance(content, str) and len(content) > MAX_CONTENT_CHARS:
                content = content[:MAX_CONTENT_CHARS]
            self.content = content
            self.message_type = d.get("message_type", "text")
            self.sent_at = None
            self.tool_calls = d.get("tool_calls")
            self.tool_call_id = d.get("tool_call_id")
            self.tool_name = d.get("tool_name")
            self.attachments = d.get("attachments")
            self.prompt_tokens = d.get("prompt_tokens", 0)
            self.completion_tokens = d.get("completion_tokens", 0)
            self.total_tokens = d.get("total_tokens", 0)

    msgs = [_FakeMsg(m) for m in messages]
    cp = cs.write_checkpoint(
        conversation_id=conversation_id,
        step_index=step_index,
        phase=phase,
        messages=msgs,
        scratch_state=scratch_state,
        branch_id=conv.main_branch_id,
        checkpoint_kind="manual",
        label=label,
    )
    logger.info(
        "write_checkpoint_manual conversation_id=%s step=%s phase=%s messages=%d user_id=%s",
        conversation_id, step_index, phase, len(messages), current_user.get("id"),
    )
    return _format_checkpoint(cp)


@router.post("/checkpoints/{checkpoint_id}/rollback", response_model=RollbackResponse)
async def rollback(
    conversation_id: UUID,
    checkpoint_id: UUID,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """回滚到该 checkpoint"""
    _check_tenant(db, conversation_id, current_user)
    cs = CheckpointService(db)
    try:
        target, detached_n = cs.rollback(
            conversation_id=conversation_id,
            target_checkpoint_id=checkpoint_id,
        )
    except ValueError as e:
        logger.warning(
            "rollback failed conversation_id=%s target=%s error_type=%s",
            conversation_id, checkpoint_id, type(e).__name__,
        )
        raise HTTPException(status_code=400, detail=str(e))
    logger.info(
        "rollback conversation_id=%s target=%s detached=%d user_id=%s",
        conversation_id, checkpoint_id, detached_n, current_user.get("id"),
    )
    return {
        "conversation_head_checkpoint_id": target.id,
        "detached_checkpoint_count": detached_n,
        "target_checkpoint": _format_checkpoint(target),
    }


@router.post("/branches/{branch_id}/merge", status_code=status.HTTP_201_CREATED, response_model=MergeResponse)
async def merge(
    conversation_id: UUID,
    branch_id: UUID,
    req: MergeRequest,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Pick-from 合并"""
    _check_tenant(db, conversation_id, current_user)
    cs = CheckpointService(db)
    try:
        new_branch, merge_commit = cs.merge_branches(
            conversation_id=conversation_id,
            picked_checkpoint_ids=req.picked_checkpoint_ids,
            new_branch_name=req.new_branch_name,
        )
    except ValueError as e:
        logger.warning(
            "merge failed conversation_id=%s error_type=%s",
            conversation_id, type(e).__name__,
        )
        raise HTTPException(status_code=400, detail=str(e))
    logger.info(
        "merge conversation_id=%s new_branch=%s merge_commit=%s user_id=%s",
        conversation_id, new_branch.id, merge_commit.id, current_user.get("id"),
    )
    return {
        "branch": _format_branch(new_branch),
        "merge_commit": _format_checkpoint(merge_commit),
    }
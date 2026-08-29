"""CheckpointService — Checkpoint 时间旅行核心服务

Phase 3-Plan-1D / Task 2

职责：写入 checkpoint / 查询 / 回滚 / 分支 / 合并（单一职责）。

参考 spec: docs/superpowers/specs/2026-08-29-agent-harness-phase3-plan1d-checkpoint-time-travel-design.md §5
"""
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_
from sqlalchemy.orm import Session as DBSession

from app.models.conversation import Conversation
from app.models.harness_models import Branch, SessionCheckpoint
from app.models.message import Message

logger = logging.getLogger(__name__)


class CheckpointService:
    """Checkpoint 时间旅行服务

    所有方法均接受 db session（已开启事务的会话）。
    """

    def __init__(self, db: DBSession):
        self.db = db

    # ---- 序列化 ----

    @staticmethod
    def _serialize_message(msg: Message) -> dict:
        """把 Message ORM 序列化为 JSONB dict"""
        return {
            "id": str(msg.id),
            "sender_type": msg.sender_type,
            "role": getattr(msg, "role", msg.sender_type),
            "content": msg.content,
            "message_type": msg.message_type,
            "sent_at": msg.sent_at.isoformat() if msg.sent_at else None,
            "tool_calls": msg.tool_calls,
            "tool_call_id": msg.tool_call_id,
            "tool_name": msg.tool_name,
            "attachments": msg.attachments,
            "prompt_tokens": msg.prompt_tokens,
            "completion_tokens": msg.completion_tokens,
            "total_tokens": msg.total_tokens,
        }

    # ---- 写入 ----

    def write_checkpoint(
        self,
        conversation_id: uuid.UUID,
        step_index: int,
        phase: str,
        messages: List[Message],
        scratch_state: Dict[str, Any],
        branch_id: uuid.UUID,
        parent_checkpoint_id: Optional[uuid.UUID] = None,
        checkpoint_kind: str = "auto",
        label: Optional[str] = None,
    ) -> SessionCheckpoint:
        """写一条 checkpoint（完整快照）"""
        snapshot = [self._serialize_message(m) for m in messages]
        cp = SessionCheckpoint(
            conversation_id=conversation_id,
            step_index=step_index,
            phase=phase,
            branch_id=branch_id,
            parent_checkpoint_id=parent_checkpoint_id,
            messages_snapshot=snapshot,
            agent_state=scratch_state,
            checkpoint_kind=checkpoint_kind,
            label=label,
        )
        self.db.add(cp)
        self.db.commit()
        logger.info(
            "write_checkpoint conv=%s step=%s phase=%s branch=%s snapshot_len=%d",
            conversation_id,
            step_index,
            phase,
            branch_id,
            len(snapshot),
        )
        return cp

    # ---- 查询 ----

    def list_branches(self, conversation_id: uuid.UUID) -> List[Branch]:
        """列出会话的所有分支（含 archived）"""
        return (
            self.db.query(Branch)
            .filter(Branch.conversation_id == conversation_id)
            .order_by(Branch.created_at)
            .all()
        )

    def list_checkpoints(
        self,
        branch_id: uuid.UUID,
        include_detached: bool = False,
    ) -> List[SessionCheckpoint]:
        """列出一个分支的所有 checkpoint（DAG 顺序）"""
        q = self.db.query(SessionCheckpoint).filter(
            SessionCheckpoint.branch_id == branch_id
        )
        if not include_detached:
            q = q.filter(SessionCheckpoint.is_head.is_(True))
        return q.order_by(SessionCheckpoint.created_at).all()

    def get_checkpoint(self, checkpoint_id: uuid.UUID) -> Optional[SessionCheckpoint]:
        """获取单个 checkpoint"""
        return (
            self.db.query(SessionCheckpoint)
            .filter(SessionCheckpoint.id == checkpoint_id)
            .first()
        )

    # ---- 回滚 ----

    def rollback(
        self,
        conversation_id: uuid.UUID,
        target_checkpoint_id: uuid.UUID,
    ) -> Tuple[SessionCheckpoint, int]:
        """回滚到某个 checkpoint

        返回 (target_checkpoint, detached_count)。
        语义：将 conversation.head_checkpoint_id 指向 target，
        并将该分支上 is_head=True 的 checkpoint 标记为 False（即 detached）。
        不物理删除任何数据。
        """
        conv = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )
        if conv is None:
            raise ValueError(f"conversation {conversation_id} 不存在")

        target = self.get_checkpoint(target_checkpoint_id)
        if target is None:
            raise ValueError(f"checkpoint {target_checkpoint_id} 不存在")
        if target.conversation_id != conversation_id:
            raise ValueError("checkpoint 不属于该 conversation")

        # 找到当前分支上所有 is_head=True 的 checkpoint（理论上同一分支只有一个）
        branch_id = target.branch_id
        current_heads = (
            self.db.query(SessionCheckpoint)
            .filter(
                SessionCheckpoint.branch_id == branch_id,
                SessionCheckpoint.is_head.is_(True),
            )
            .all()
        )
        for h in current_heads:
            h.is_head = False

        # 标记 target 为新 head
        target.is_head = True
        conv.head_checkpoint_id = target.id

        self.db.commit()
        logger.info(
            "rollback conv=%s target=%s detached=%d",
            conversation_id,
            target_checkpoint_id,
            len(current_heads),
        )
        return target, len(current_heads)

    # ---- 分支 ----

    def branch_from(
        self,
        conversation_id: uuid.UUID,
        source_checkpoint_id: uuid.UUID,
        branch_name: str,
    ) -> Tuple[Branch, SessionCheckpoint]:
        """从某个 checkpoint 创建新分支"""
        source = self.get_checkpoint(source_checkpoint_id)
        if source is None:
            raise ValueError(f"checkpoint {source_checkpoint_id} 不存在")
        if source.conversation_id != conversation_id:
            raise ValueError("checkpoint 不属于该 conversation")

        new_branch = Branch(
            conversation_id=conversation_id,
            name=branch_name,
            parent_branch_id=None,
        )
        self.db.add(new_branch)
        self.db.flush()  # 拿到 new_branch.id

        # 第一个 checkpoint 复制 source 的 snapshot
        first_cp = SessionCheckpoint(
            conversation_id=conversation_id,
            step_index=source.step_index,
            phase="branch_point",
            branch_id=new_branch.id,
            parent_checkpoint_id=source.id,
            messages_snapshot=list(source.messages_snapshot or []),
            agent_state=dict(source.agent_state or {}),
            checkpoint_kind="branch_point",
            label=f"branched from {source_checkpoint_id}",
            is_head=True,
        )
        self.db.add(first_cp)
        self.db.flush()

        new_branch.head_checkpoint_id = first_cp.id
        self.db.commit()

        logger.info(
            "branch_from conv=%s source=%s new_branch=%s first_cp=%s",
            conversation_id,
            source_checkpoint_id,
            new_branch.id,
            first_cp.id,
        )
        return new_branch, first_cp

    # ---- 合并 ----

    def merge_branches(
        self,
        conversation_id: uuid.UUID,
        picked_checkpoint_ids: List[uuid.UUID],
        new_branch_name: str,
    ) -> Tuple[Branch, SessionCheckpoint]:
        """Pick-from 合并

        按用户勾选的 checkpoint 顺序拼接 messages_snapshot，
        创建新分支 + merge commit。
        """
        if len(picked_checkpoint_ids) < 2:
            raise ValueError("merge 至少需要 2 个 checkpoint")

        picked = []
        for cp_id in picked_checkpoint_ids:
            cp = self.get_checkpoint(cp_id)
            if cp is None:
                raise ValueError(f"checkpoint {cp_id} 不存在")
            if cp.conversation_id != conversation_id:
                raise ValueError("checkpoint 不属于该 conversation")
            picked.append(cp)

        new_branch = Branch(
            conversation_id=conversation_id,
            name=new_branch_name,
            parent_branch_id=None,
        )
        self.db.add(new_branch)
        self.db.flush()

        # 拼接 messages_snapshot（按 picked 顺序，去重保留最后出现）
        seen_msg_ids = set()
        merged_snapshot = []
        for cp in picked:
            for msg in (cp.messages_snapshot or []):
                mid = msg.get("id")
                if mid and mid in seen_msg_ids:
                    continue
                if mid:
                    seen_msg_ids.add(mid)
                merged_snapshot.append(msg)

        merge_commit = SessionCheckpoint(
            conversation_id=conversation_id,
            step_index=max(cp.step_index for cp in picked) + 1,
            phase="merge_commit",
            branch_id=new_branch.id,
            parent_checkpoint_id=None,  # merge commit 无单父
            messages_snapshot=merged_snapshot,
            agent_state={},
            checkpoint_kind="merge_commit",
            label=f"merge of {len(picked)} branches",
            merge_parents=[str(cp.id) for cp in picked],
            is_head=True,
        )
        self.db.add(merge_commit)
        self.db.flush()

        new_branch.head_checkpoint_id = merge_commit.id
        self.db.commit()

        logger.info(
            "merge_branches conv=%s picked=%d new_branch=%s merge_commit=%s",
            conversation_id,
            len(picked),
            new_branch.id,
            merge_commit.id,
        )
        return new_branch, merge_commit

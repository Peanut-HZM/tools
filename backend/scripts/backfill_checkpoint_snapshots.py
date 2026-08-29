"""Checkpoint 快照回填脚本

Phase 3-Plan-1D / Task 1

扫描 `session_checkpoints` 表中 messages_snapshot 为空的旧 checkpoint，
从 messages 表按 conversation_id + sent_at <= checkpoint.created_at 顺序组装快照并写入。

幂等：可重复运行，已回填的 checkpoint 自动跳过。

CLI 用法：
    cd backend
    python -m scripts.backfill_checkpoint_snapshots [--batch-size 50]
"""
import argparse
import json
import logging
import sys
from typing import List

from sqlalchemy import text as sa_text
from sqlalchemy.orm import Session as DBSession

from app.database import SessionLocal
from app.models.harness_models import SessionCheckpoint
from app.models.message import Message

logger = logging.getLogger(__name__)

BATCH_SIZE_DEFAULT = 50


def _serialize_message(msg: Message) -> dict:
    """把 Message ORM 序列化为 JSONB dict 列表元素"""
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


def backfill_checkpoint_snapshots(
    db: DBSession,
    batch_size: int = BATCH_SIZE_DEFAULT,
) -> int:
    """回填缺失 messages_snapshot 的 checkpoint

    返回成功回填的行数。best-effort：失败仅 log。
    """
    try:
        # 找出 messages_snapshot 为空的 checkpoint
        pending_query = db.query(SessionCheckpoint).filter(
            (SessionCheckpoint.messages_snapshot.is_(None))
            | (SessionCheckpoint.messages_snapshot == "[]")
        )
        total = pending_query.count()
    except Exception as e:
        logger.warning("checkpoint 快照回填：统计失败: %s", type(e).__name__)
        return 0

    if total == 0:
        logger.info("checkpoint 快照回填：无需回填")
        return 0

    logger.info("checkpoint 快照回填：发现 %d 条待处理记录", total)
    filled = 0

    while True:
        try:
            pending = (
                db.query(SessionCheckpoint)
                .filter(
                    (SessionCheckpoint.messages_snapshot.is_(None))
                    | (SessionCheckpoint.messages_snapshot == "[]")
                )
                .limit(batch_size)
                .all()
            )
        except Exception as e:
            logger.warning("checkpoint 快照回填：查询失败: %s", type(e).__name__)
            break

        if not pending:
            break

        for cp in pending:
            try:
                # 查询该 checkpoint 之前的所有消息
                msgs: List[Message] = (
                    db.query(Message)
                    .filter(
                        Message.conversation_id == cp.conversation_id,
                        Message.sent_at <= cp.created_at,
                    )
                    .order_by(Message.sent_at)
                    .all()
                )
                cp.messages_snapshot = [_serialize_message(m) for m in msgs]
                filled += 1
            except Exception as e:
                logger.warning(
                    "checkpoint 快照回填：cp=%s 失败: %s",
                    getattr(cp, "id", "?"),
                    type(e).__name__,
                )

        try:
            db.commit()
        except Exception as e:
            logger.warning("checkpoint 快照回填：commit 失败: %s", type(e).__name__)
            db.rollback()
            break

    logger.info("checkpoint 快照回填：完成，共回填 %d 条", filled)
    return filled


def main():
    parser = argparse.ArgumentParser(description="Checkpoint 快照回填")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE_DEFAULT)
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    db = SessionLocal()
    try:
        filled = backfill_checkpoint_snapshots(db, batch_size=args.batch_size)
        logger.info("回填完成，共 %d 条", filled)
        sys.exit(0)
    finally:
        db.close()


if __name__ == "__main__":
    main()
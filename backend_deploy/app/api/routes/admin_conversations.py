"""
对话管理路由（管理员）
用于查看所有用户的对话记录和Token消耗统计
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.config.database import get_db_connection

router = APIRouter(prefix="/admin/conversations", tags=["admin-conversations"])


def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


@router.get("/list")
async def list_all_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: dict = Depends(require_admin),
):
    """获取所有对话列表（管理员）"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            conditions = []
            params = []

            if user_id:
                conditions.append("c.user_id = %s")
                params.append(user_id)

            if start_date:
                conditions.append("c.created_at >= %s")
                params.append(start_date)

            if end_date:
                conditions.append("c.created_at < %s")
                params.append(
                    datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
                )

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

            cur.execute(
                f"""
                SELECT 
                    c.id, c.user_id, c.title, c.current_stage, 
                    c.created_at, c.updated_at,
                    u.username
                FROM conversations c
                JOIN users u ON c.user_id = u.user_id
                {where_clause}
                ORDER BY c.created_at DESC
                LIMIT %s OFFSET %s
            """,
                params + [limit, skip],
            )

            conversations = []
            for row in cur.fetchall():
                cur.execute(
                    """
                    SELECT 
                        COUNT(*) as message_count,
                        COALESCE(SUM(total_tokens), 0) as total_tokens
                    FROM messages
                    WHERE conversation_id = %s
                """,
                    (row["id"],),
                )
                stats = cur.fetchone()

                conversations.append(
                    {
                        "id": str(row["id"]),
                        "user_id": row["user_id"],
                        "username": row["username"],
                        "title": row["title"],
                        "current_stage": row["current_stage"],
                        "message_count": stats["message_count"],
                        "total_tokens": int(stats["total_tokens"]),
                        "created_at": row["created_at"].isoformat()
                        if row["created_at"]
                        else None,
                        "updated_at": row["updated_at"].isoformat()
                        if row["updated_at"]
                        else None,
                    }
                )

            return conversations
    finally:
        conn.close()


@router.get("/{conversation_id}/detail")
async def get_conversation_detail(
    conversation_id: str,
    current_user: dict = Depends(require_admin),
):
    """获取对话详情（管理员）"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.*, u.username, u.email
                FROM conversations c
                JOIN users u ON c.user_id = u.user_id
                WHERE c.id = %s
            """,
                (conversation_id,),
            )

            conv = cur.fetchone()
            if not conv:
                raise HTTPException(status_code=404, detail="对话不存在")

            cur.execute(
                """
                SELECT id, sender_type, content, sent_at,
                       prompt_tokens, completion_tokens, total_tokens, llm_model_name
                FROM messages
                WHERE conversation_id = %s
                ORDER BY sent_at
            """,
                (conversation_id,),
            )

            messages = []
            for msg in cur.fetchall():
                messages.append(
                    {
                        "id": str(msg["id"]),
                        "sender_type": msg["sender_type"],
                        "content": msg["content"][:200] + "..."
                        if len(msg["content"]) > 200
                        else msg["content"],
                        "sent_at": msg["sent_at"].isoformat()
                        if msg["sent_at"]
                        else None,
                        "prompt_tokens": msg["prompt_tokens"] or 0,
                        "completion_tokens": msg["completion_tokens"] or 0,
                        "total_tokens": msg["total_tokens"] or 0,
                        "llm_model_name": msg["llm_model_name"],
                    }
                )

            return {
                "id": str(conv["id"]),
                "user_id": conv["user_id"],
                "username": conv["username"],
                "email": conv["email"],
                "title": conv["title"],
                "current_stage": conv["current_stage"],
                "created_at": conv["created_at"].isoformat()
                if conv["created_at"]
                else None,
                "updated_at": conv["updated_at"].isoformat()
                if conv["updated_at"]
                else None,
                "messages": messages,
            }
    finally:
        conn.close()


@router.get("/stats/overview")
async def get_conversation_stats(
    current_user: dict = Depends(require_admin),
):
    """获取对话统计概览"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COUNT(DISTINCT c.id) as total_conversations,
                    COUNT(m.id) as total_messages,
                    COALESCE(SUM(m.total_tokens), 0) as total_tokens
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
            """)
            total_stats = cur.fetchone()

            today = datetime.now().date()
            today_start = datetime.combine(today, datetime.min.time())

            cur.execute(
                """
                SELECT 
                    COUNT(DISTINCT c.id) as today_conversations,
                    COALESCE(SUM(m.total_tokens), 0) as today_tokens
                FROM conversations c
                LEFT JOIN messages m ON c.id = m.conversation_id
                WHERE c.created_at >= %s
            """,
                (today_start,),
            )
            today_stats = cur.fetchone()

            total_conv = total_stats["total_conversations"] or 0
            total_tok = int(total_stats["total_tokens"] or 0)

            return {
                "total_conversations": total_conv,
                "total_messages": total_stats["total_messages"] or 0,
                "total_tokens": total_tok,
                "today_conversations": today_stats["today_conversations"] or 0,
                "today_tokens": int(today_stats["today_tokens"] or 0),
                "avg_tokens_per_conversation": round(total_tok / total_conv, 2)
                if total_conv > 0
                else 0,
            }
    finally:
        conn.close()


@router.get("/stats/models")
async def get_model_usage_stats(
    current_user: dict = Depends(require_admin),
):
    """获取模型使用统计"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COALESCE(llm_model_name, '未知模型') as model_name,
                    COUNT(*) as usage_count,
                    COALESCE(SUM(total_tokens), 0) as total_tokens
                FROM messages
                WHERE sender_type = 'agent' AND llm_model_name IS NOT NULL
                GROUP BY llm_model_name
                ORDER BY usage_count DESC
            """)

            results = cur.fetchall()
            total_usage = sum(r["usage_count"] for r in results)

            return [
                {
                    "model_name": r["model_name"],
                    "usage_count": r["usage_count"],
                    "total_tokens": int(r["total_tokens"]),
                    "percentage": round((r["usage_count"] / total_usage) * 100, 2)
                    if total_usage > 0
                    else 0,
                }
                for r in results
            ]
    finally:
        conn.close()


@router.get("/stats/users")
async def get_user_conversation_stats(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(require_admin),
):
    """获取用户对话统计排行"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 
                    u.user_id,
                    u.username,
                    u.email,
                    COUNT(DISTINCT c.id) as conversation_count,
                    COALESCE(SUM(m.total_tokens), 0) as total_tokens
                FROM users u
                LEFT JOIN conversations c ON u.user_id = c.user_id
                LEFT JOIN messages m ON c.id = m.conversation_id
                GROUP BY u.user_id, u.username, u.email
                ORDER BY conversation_count DESC
                LIMIT %s OFFSET %s
            """,
                (limit, skip),
            )

            return [
                {
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "email": row["email"],
                    "conversation_count": row["conversation_count"] or 0,
                    "total_tokens": int(row["total_tokens"] or 0),
                }
                for row in cur.fetchall()
            ]
    finally:
        conn.close()


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(require_admin),
):
    """删除对话（管理员）"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM conversations WHERE id = %s", (conversation_id,)
            )
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="对话不存在")

            cur.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
            conn.commit()

            return {"message": "对话已删除"}
    finally:
        conn.close()

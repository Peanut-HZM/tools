"""个人 API Token 服务

遵循项目模式：psycopg2 原生 SQL + Pydantic DTO + 静态方法。
安全设计：明文只在 generate_token 返回值中出现一次；DB 只存 SHA-256 哈希；
支持过期与撤销；校验通过时刷新 last_used_at。
"""
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from app.config.database import get_pooled_db_connection, release_db_connection
from app.models.user_api_token_models import (
    UserTokenCreatedResponse,
    UserTokenResponse,
)

logger = logging.getLogger(__name__)

TOKEN_PREFIX = "pat_"
TOKEN_RANDOM_BYTES = 32

# 进程内建表标记：validate 高频调用，避免每个请求都跑 4 条幂等 DDL
_table_ready = False


class UserTokenService:
    """个人 API Token 服务（所有方法 @staticmethod）"""

    @staticmethod
    def _hash_token(plain: str) -> str:
        """SHA-256 哈希（DB 只存此值）"""
        return hashlib.sha256(plain.encode("utf-8")).hexdigest()

    @staticmethod
    def _ensure_table():
        """创建 user_api_tokens 表（幂等）"""
        global _table_ready
        if _table_ready:
            return
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_api_tokens (
                    id VARCHAR(64) PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    token_hash CHAR(64) NOT NULL,
                    token_prefix VARCHAR(12) NOT NULL,
                    scopes VARCHAR(200) NOT NULL DEFAULT 'k8s:read',
                    created_at TIMESTAMP NOT NULL,
                    last_used_at TIMESTAMP,
                    expires_at TIMESTAMP,
                    revoked_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)
            cursor.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_tokens_hash "
                "ON user_api_tokens(token_hash)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_user_tokens_user "
                "ON user_api_tokens(user_id)"
            )
            conn.commit()
            _table_ready = True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def generate_token(user_id: str, name: str,
                       expires_days: Optional[int] = None) -> Tuple[UserTokenCreatedResponse, str]:
        """生成 Token；明文仅在返回值中出现一次"""
        UserTokenService._ensure_table()
        plain = TOKEN_PREFIX + secrets.token_urlsafe(TOKEN_RANDOM_BYTES)
        token_id = uuid.uuid4().hex
        now = datetime.now()
        expires_at = now + timedelta(days=expires_days) if expires_days else None
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO user_api_tokens
                    (id, user_id, name, token_hash, token_prefix, scopes, created_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING created_at
                """,
                (token_id, user_id, name, UserTokenService._hash_token(plain),
                 plain[:12], "k8s:read", now, expires_at),
            )
            row = cursor.fetchone()
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            release_db_connection(conn)
        logger.info("用户 %s 创建了 API Token %s（前缀 %s）", user_id, token_id, plain[:12])
        resp = UserTokenCreatedResponse(
            id=token_id, name=name, token_prefix=plain[:12],
            created_at=row["created_at"], last_used_at=None,
            expires_at=expires_at, revoked=False, token=plain,
        )
        return resp, plain

    @staticmethod
    def validate_token(plain: str) -> Optional[str]:
        """校验 token：有效返回 user_id；不存在/过期/已撤销/格式错误返回 None"""
        if not plain or not plain.startswith(TOKEN_PREFIX):
            return None
        UserTokenService._ensure_table()
        token_hash = UserTokenService._hash_token(plain)
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT user_id, expires_at, revoked_at FROM user_api_tokens "
                "WHERE token_hash = %s",
                (token_hash,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            if row["revoked_at"] is not None:
                return None
            if row["expires_at"] is not None and row["expires_at"] < datetime.now():
                return None
            cursor.execute(
                "UPDATE user_api_tokens SET last_used_at = %s WHERE token_hash = %s",
                (datetime.now(), token_hash),
            )
            conn.commit()
            return row["user_id"]
        finally:
            cursor.close()
            release_db_connection(conn)

    @staticmethod
    def list_tokens(user_id: str) -> List[UserTokenResponse]:
        """列出当前用户的 Token（脱敏）"""
        UserTokenService._ensure_table()
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, name, token_prefix, created_at, last_used_at,
                       expires_at, revoked_at IS NOT NULL AS revoked
                FROM user_api_tokens WHERE user_id = %s ORDER BY created_at DESC
                """,
                (user_id,),
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()
            release_db_connection(conn)
        return [UserTokenResponse(**r) for r in rows]

    @staticmethod
    def revoke_token(user_id: str, token_id: str) -> bool:
        """撤销 Token（仅限本人）"""
        UserTokenService._ensure_table()
        conn = get_pooled_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE user_api_tokens SET revoked_at = %s "
                "WHERE id = %s AND user_id = %s AND revoked_at IS NULL",
                (datetime.now(), token_id, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            release_db_connection(conn)

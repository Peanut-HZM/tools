"""订阅额度账号存储（用户自助添加供应商 + API Key）

* API Key 用 AES-256-GCM 加密入库（复用 app.core.security）
* 所有读取接口只返回掩码，明文仅在服务端内存中短暂存在
* 表自动创建（与项目既有服务一致：首次访问时 CREATE TABLE IF NOT EXISTS）
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text

from app.core.security import decrypt_api_key, encrypt_api_key
from app.models.base import engine

logger = logging.getLogger(__name__)

TABLE_NAME = "subscription_quota_accounts"

_CREATE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id            VARCHAR(36) PRIMARY KEY,
    user_id       VARCHAR(64) NOT NULL,
    provider_id   VARCHAR(64) NOT NULL,
    label         VARCHAR(120) NOT NULL DEFAULT '',
    api_key_enc   TEXT,
    extra_json    TEXT NOT NULL DEFAULT '{{}}',
    enabled       BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

_INDEX_SQL = (
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_user ON {TABLE_NAME} (user_id, sort_order)"
)

_schema_ready = False


def ensure_schema() -> None:
    """幂等建表（进程内只做一次）。"""
    global _schema_ready
    if _schema_ready:
        return
    try:
        with engine.begin() as conn:
            conn.execute(text(_CREATE_SQL))
            conn.execute(text(_INDEX_SQL))
        _schema_ready = True
    except Exception as exc:  # 建表失败不静默：让调用方看到真实错误
        logger.error("创建 %s 表失败: %s", TABLE_NAME, exc, exc_info=True)
        raise


@dataclass
class QuotaAccount:
    """一条供应商账号配置（api_key 字段为明文，仅服务端内部使用）"""

    id: str
    user_id: str
    provider_id: str
    label: str = ""
    api_key: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    sort_order: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def masked_key(self) -> Optional[str]:
        """返回掩码后的 Key（前端展示用）。"""
        if not self.api_key:
            return None
        key = self.api_key
        if len(key) <= 8:
            return "*" * len(key)
        return f"{key[:4]}{'*' * 8}{key[-4:]}"

    def to_public_dict(self) -> dict:
        """对外序列化：**绝不包含明文 Key**"""
        return {
            "id": self.id,
            "providerId": self.provider_id,
            "label": self.label,
            "maskedKey": self.masked_key(),
            "hasKey": bool(self.api_key),
            "extra": {
                k: ("***" if any(s in k.lower() for s in ("secret", "key", "token")) else v)
                for k, v in (self.extra or {}).items()
            },
            "enabled": self.enabled,
            "sortOrder": self.sort_order,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }


def _row_to_account(row) -> QuotaAccount:
    mapping = row._mapping if hasattr(row, "_mapping") else row
    raw_key = mapping.get("api_key_enc")
    plain: Optional[str] = None
    if raw_key:
        try:
            plain = decrypt_api_key(raw_key)
        except Exception as exc:
            logger.error("解密账号 %s 的 API Key 失败: %s", mapping.get("id"), exc)
            plain = None
    try:
        extra = json.loads(mapping.get("extra_json") or "{}")
    except json.JSONDecodeError:
        extra = {}
    created = mapping.get("created_at")
    updated = mapping.get("updated_at")
    return QuotaAccount(
        id=mapping["id"],
        user_id=mapping["user_id"],
        provider_id=mapping["provider_id"],
        label=mapping.get("label") or "",
        api_key=plain,
        extra=extra if isinstance(extra, dict) else {},
        enabled=bool(mapping.get("enabled")),
        sort_order=int(mapping.get("sort_order") or 0),
        created_at=created.isoformat() if isinstance(created, datetime) else created,
        updated_at=updated.isoformat() if isinstance(updated, datetime) else updated,
    )


def list_accounts(user_id: str, *, only_enabled: bool = False) -> list[QuotaAccount]:
    ensure_schema()
    sql = f"SELECT * FROM {TABLE_NAME} WHERE user_id = :uid"
    if only_enabled:
        sql += " AND enabled = TRUE"
    sql += " ORDER BY sort_order ASC, created_at ASC"
    with engine.connect() as conn:
        rows = conn.execute(text(sql), {"uid": user_id}).fetchall()
    return [_row_to_account(row) for row in rows]


def get_account(user_id: str, account_id: str) -> Optional[QuotaAccount]:
    ensure_schema()
    with engine.connect() as conn:
        row = conn.execute(
            text(f"SELECT * FROM {TABLE_NAME} WHERE user_id = :uid AND id = :aid"),
            {"uid": user_id, "aid": account_id},
        ).fetchone()
    return _row_to_account(row) if row else None


def create_account(
    user_id: str,
    provider_id: str,
    *,
    label: str = "",
    api_key: Optional[str] = None,
    extra: Optional[dict] = None,
) -> QuotaAccount:
    ensure_schema()
    account_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with engine.begin() as conn:
        next_order = conn.execute(
            text(f"SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM {TABLE_NAME} WHERE user_id = :uid"),
            {"uid": user_id},
        ).scalar()
        conn.execute(
            text(
                f"INSERT INTO {TABLE_NAME} "
                "(id, user_id, provider_id, label, api_key_enc, extra_json, enabled, sort_order, created_at, updated_at) "
                "VALUES (:id, :uid, :pid, :label, :key, :extra, TRUE, :order, :now, :now)"
            ),
            {
                "id": account_id,
                "uid": user_id,
                "pid": provider_id,
                "label": label or "",
                "key": encrypt_api_key(api_key) if api_key else None,
                "extra": json.dumps(extra or {}, ensure_ascii=False),
                "order": int(next_order or 0),
                "now": now,
            },
        )
    logger.info("新增订阅额度账号: user=%s provider=%s id=%s", user_id, provider_id, account_id)
    created = get_account(user_id, account_id)
    if created is None:
        raise RuntimeError("账号创建后读取失败")
    return created


def update_account(
    user_id: str,
    account_id: str,
    *,
    label: Optional[str] = None,
    api_key: Optional[str] = None,
    extra: Optional[dict] = None,
    enabled: Optional[bool] = None,
) -> Optional[QuotaAccount]:
    ensure_schema()
    sets: list[str] = []
    params: dict[str, Any] = {"uid": user_id, "aid": account_id}

    if label is not None:
        sets.append("label = :label")
        params["label"] = label
    if api_key is not None:
        sets.append("api_key_enc = :key")
        params["key"] = encrypt_api_key(api_key) if api_key else None
    if extra is not None:
        sets.append("extra_json = :extra")
        params["extra"] = json.dumps(extra, ensure_ascii=False)
    if enabled is not None:
        sets.append("enabled = :enabled")
        params["enabled"] = bool(enabled)

    if not sets:
        return get_account(user_id, account_id)

    sets.append("updated_at = :now")
    params["now"] = datetime.now(timezone.utc).replace(tzinfo=None)

    with engine.begin() as conn:
        conn.execute(
            text(f"UPDATE {TABLE_NAME} SET {', '.join(sets)} WHERE user_id = :uid AND id = :aid"),
            params,
        )
    logger.info("更新订阅额度账号: user=%s id=%s 字段=%s", user_id, account_id, list(sets))
    return get_account(user_id, account_id)


def delete_account(user_id: str, account_id: str) -> bool:
    ensure_schema()
    with engine.begin() as conn:
        result = conn.execute(
            text(f"DELETE FROM {TABLE_NAME} WHERE user_id = :uid AND id = :aid"),
            {"uid": user_id, "aid": account_id},
        )
    deleted = result.rowcount > 0
    if deleted:
        logger.info("删除订阅额度账号: user=%s id=%s", user_id, account_id)
    return deleted

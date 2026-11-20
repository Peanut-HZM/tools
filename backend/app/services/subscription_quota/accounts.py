"""订阅额度账号存储（用户自助添加供应商 + API Key）

* API Key 加密入库（本机库用本机文件密钥，远程库用服务器主密钥）
* 所有读取接口只返回掩码，明文仅在服务端内存中短暂存在
* 表自动创建（与项目既有服务一致：首次访问时 CREATE TABLE IF NOT EXISTS）

## 存储位置：默认本机，不外泄到远程库

订阅额度数据（供应商、API Key、切换指针）是**每台设备各不相同**的本机状态：
同一账号在办公机和家里电脑登录的 CLI、配置的供应商、看到的余额都不一样。
因此默认存本机 SQLite（``~/.toolbox/toolbox.db``），与 k8s/ssh/redis/db 配置
的「本机 / 服务器」双层模型保持一致；也可用 ``QUOTA_STORAGE=server`` 切回
远程主库（多端共享场景）。
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text

from app.models.base import engine
from app.storage.crypto import LocalEncryption
from app.storage.local_db import get_local_engine, init_local_tables

logger = logging.getLogger(__name__)

TABLE_NAME = "subscription_quota_accounts"

#: 存储位置开关：local（默认，本机 SQLite）| server（远程主库）
STORAGE_ENV = "QUOTA_STORAGE"


def _storage_location() -> str:
    """当前订阅额度数据的存储位置。

    默认 ``local``：这类数据是「本机状态」，不同设备的供应商/凭据/余额都不同，
    存到远程库会互相覆盖。显式设 ``QUOTA_STORAGE=server`` 才走远程主库。
    """
    return (os.environ.get(STORAGE_ENV) or "local").strip().lower()


def _use_local() -> bool:
    return _storage_location() != "server"


def _get_engine():
    """按存储位置返回 engine。

    本地模式走 ``~/.toolbox/toolbox.db``（延迟创建），
    远程模式走 ``app.models.base.engine``（主应用库）。
    """
    if _use_local():
        local_engine = get_local_engine()
        init_local_tables(local_engine)
        return local_engine
    return engine


def _encrypt_key(plain: str) -> str:
    """按存储位置加密 API Key（两侧密钥物理隔离）"""
    if _use_local():
        return LocalEncryption.encrypt(plain)
    from app.core.security import encrypt_api_key

    return encrypt_api_key(plain)


def _decrypt_key(cipher: str) -> str:
    """按存储位置解密 API Key"""
    if _use_local():
        return LocalEncryption.decrypt(cipher)
    from app.core.security import decrypt_api_key

    return decrypt_api_key(cipher)

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

#: 合并 agent-hub 后新增的列（幂等 ADD COLUMN，全部有默认值 → 老数据零影响）
_EXTRA_COLUMNS: tuple[tuple[str, str], ...] = (
    # 供应商分类：official / aggregator / third_party / custom / manual
    ("category", "VARCHAR(32) NOT NULL DEFAULT 'official'"),
    # 作用对象 agent（写入本机配置时用）
    ("app", "VARCHAR(32) NOT NULL DEFAULT ''"),
    ("notes", "TEXT NOT NULL DEFAULT ''"),
    ("website_url", "VARCHAR(500) NOT NULL DEFAULT ''"),
    # manual 模式的额度（支持手动增加）
    ("manual_total", "DOUBLE PRECISION NOT NULL DEFAULT 0"),
    ("manual_used", "DOUBLE PRECISION NOT NULL DEFAULT 0"),    ("quota_unit", "VARCHAR(20) NOT NULL DEFAULT 'credits'"),
    ("window_type", "VARCHAR(20) NOT NULL DEFAULT 'none'"),
    ("window_reset_at", "VARCHAR(40) NOT NULL DEFAULT ''"),
    # keep-last-good：最近一次成功查询结果（失败时前端显示上次数据）
    ("last_good_json", "TEXT NOT NULL DEFAULT ''"),
    # 明文 API Key 的 SHA-256（hex）：订阅同步的幂等去重键（agent-subscription-sync）
    # 存量行为空串；同步命中明文相同的存量行时会顺手回填（仅此一列，不动其他字段）
    ("api_key_hash", "VARCHAR(64) NOT NULL DEFAULT ''"),
)

_INDEX_SQL = (
    f"CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_user ON {TABLE_NAME} (user_id, sort_order)"
)

_schema_ready_by_location: set[str] = set()


def _sqlite_columns(conn) -> set[str]:
    """读取 SQLite 表现有列名（SQLite 不支持 ADD COLUMN IF NOT EXISTS）"""
    rows = conn.execute(text(f"PRAGMA table_info({TABLE_NAME})")).fetchall()
    return {row[1] for row in rows}


def ensure_schema() -> None:
    """幂等建表 + 幂等补列（按存储位置分别只做一次）。"""
    location = _storage_location()
    if location in _schema_ready_by_location:
        return
    try:
        target = _get_engine()
        with target.begin() as conn:
            conn.execute(text(_CREATE_SQL))
            conn.execute(text(_INDEX_SQL))
            if _use_local():
                # SQLite 不支持 ADD COLUMN IF NOT EXISTS，先查已有列再补
                existing = _sqlite_columns(conn)
                for column, ddl in _EXTRA_COLUMNS:
                    if column not in existing:
                        conn.execute(text(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {column} {ddl}"))
            else:
                # 合并 agent-hub 后新增的列：ADD COLUMN IF NOT EXISTS 幂等
                for column, ddl in _EXTRA_COLUMNS:
                    conn.execute(
                        text(f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS {column} {ddl}")
                    )
        _schema_ready_by_location.add(location)
    except Exception as exc:  # 建表失败不静默：让调用方看到真实错误
        logger.error("创建 %s 表失败（storage=%s）: %s", TABLE_NAME, location, exc, exc_info=True)
        raise


@dataclass
class QuotaAccount:
    """一条供应商账号配置（api_key 字段为明文，仅服务端内部使用）

    合并 agent-hub 后新增：category / app / notes / website_url /
    manual_total / manual_used / quota_unit / window_type / window_reset_at /
    last_good（keep-last-good 缓存）。全部有默认值，老数据零影响。
    """

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

    # ---- 合并 agent-hub 新增字段 ----
    category: str = "official"
    app: str = ""
    notes: str = ""
    website_url: str = ""
    manual_total: float = 0.0
    manual_used: float = 0.0
    quota_unit: str = "credits"
    window_type: str = "none"
    window_reset_at: str = ""
    last_good: dict[str, Any] = field(default_factory=dict)

    @property
    def is_manual(self) -> bool:
        """手动额度订阅（不查网络，额度由用户维护）"""
        return self.provider_id == "manual" or self.extra.get("kind") == "manual"

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
            # ---- 合并 agent-hub 新增字段 ----
            "category": self.category,
            "app": self.app,
            "notes": self.notes,
            "websiteUrl": self.website_url,
            "manualTotal": self.manual_total,
            "manualUsed": self.manual_used,
            "quotaUnit": self.quota_unit,
            "windowType": self.window_type,
            "windowResetAt": self.window_reset_at,
            "isManual": self.is_manual,
            "lastGood": self.last_good or None,
        }


def _row_to_account(row) -> QuotaAccount:
    mapping = row._mapping if hasattr(row, "_mapping") else row
    raw_key = mapping.get("api_key_enc")
    plain: Optional[str] = None
    if raw_key:
        try:
            plain = _decrypt_key(raw_key)
        except Exception as exc:
            logger.error("解密账号 %s 的 API Key 失败: %s", mapping.get("id"), exc)
            plain = None
    try:
        extra = json.loads(mapping.get("extra_json") or "{}")
    except json.JSONDecodeError:
        extra = {}
    try:
        last_good = json.loads(mapping.get("last_good_json") or "{}")
    except (json.JSONDecodeError, TypeError):
        last_good = {}
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
        category=mapping.get("category") or "official",
        app=mapping.get("app") or "",
        notes=mapping.get("notes") or "",
        website_url=mapping.get("website_url") or "",
        manual_total=float(mapping.get("manual_total") or 0.0),
        manual_used=float(mapping.get("manual_used") or 0.0),
        quota_unit=mapping.get("quota_unit") or "credits",
        window_type=mapping.get("window_type") or "none",
        window_reset_at=mapping.get("window_reset_at") or "",
        last_good=last_good if isinstance(last_good, dict) else {},
    )


def list_accounts(user_id: str, *, only_enabled: bool = False) -> list[QuotaAccount]:
    ensure_schema()
    sql = f"SELECT * FROM {TABLE_NAME} WHERE user_id = :uid"
    if only_enabled:
        sql += " AND enabled = TRUE"
    sql += " ORDER BY sort_order ASC, created_at ASC"
    with _get_engine().connect() as conn:
        rows = conn.execute(text(sql), {"uid": user_id}).fetchall()
    return [_row_to_account(row) for row in rows]


def get_account(user_id: str, account_id: str) -> Optional[QuotaAccount]:
    ensure_schema()
    with _get_engine().connect() as conn:
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
    category: str = "official",
    app: str = "",
    notes: str = "",
    website_url: str = "",
    manual_total: float = 0.0,
    manual_used: float = 0.0,
    quota_unit: str = "credits",
    window_type: str = "none",
    window_reset_at: str = "",
) -> QuotaAccount:
    ensure_schema()
    account_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    with _get_engine().begin() as conn:
        next_order = conn.execute(
            text(f"SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM {TABLE_NAME} WHERE user_id = :uid"),
            {"uid": user_id},
        ).scalar()
        conn.execute(
            text(
                f"INSERT INTO {TABLE_NAME} "
                "(id, user_id, provider_id, label, api_key_enc, extra_json, enabled, sort_order, created_at, updated_at, "
                " category, app, notes, website_url, manual_total, manual_used, quota_unit, window_type, window_reset_at) "
                "VALUES (:id, :uid, :pid, :label, :key, :extra, TRUE, :order, :now, :now, "
                " :category, :app, :notes, :website, :mtotal, :mused, :unit, :wtype, :wreset)"
            ),
            {
                "id": account_id,
                "uid": user_id,
                "pid": provider_id,
                "label": label or "",
                "key": _encrypt_key(api_key) if api_key else None,
                "extra": json.dumps(extra or {}, ensure_ascii=False),
                "order": int(next_order or 0),
                "now": now,
                "category": category or "official",
                "app": app or "",
                "notes": notes or "",
                "website": website_url or "",
                "mtotal": float(manual_total or 0),
                "mused": float(manual_used or 0),
                "unit": quota_unit or "credits",
                "wtype": window_type or "none",
                "wreset": window_reset_at or "",
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
    category: Optional[str] = None,
    app: Optional[str] = None,
    notes: Optional[str] = None,
    website_url: Optional[str] = None,
    manual_total: Optional[float] = None,
    manual_used: Optional[float] = None,
    quota_unit: Optional[str] = None,
    window_type: Optional[str] = None,
    window_reset_at: Optional[str] = None,
    last_good: Optional[dict] = None,
) -> Optional[QuotaAccount]:
    ensure_schema()
    sets: list[str] = []
    params: dict[str, Any] = {"uid": user_id, "aid": account_id}

    if label is not None:
        sets.append("label = :label")
        params["label"] = label
    if api_key is not None:
        sets.append("api_key_enc = :key")
        params["key"] = _encrypt_key(api_key) if api_key else None
    if extra is not None:
        sets.append("extra_json = :extra")
        params["extra"] = json.dumps(extra, ensure_ascii=False)
    if enabled is not None:
        sets.append("enabled = :enabled")
        params["enabled"] = bool(enabled)
    if category is not None:
        sets.append("category = :category")
        params["category"] = category
    if app is not None:
        sets.append("app = :app")
        params["app"] = app
    if notes is not None:
        sets.append("notes = :notes")
        params["notes"] = notes
    if website_url is not None:
        sets.append("website_url = :website")
        params["website"] = website_url
    if manual_total is not None:
        sets.append("manual_total = :mtotal")
        params["mtotal"] = float(manual_total)
    if manual_used is not None:
        sets.append("manual_used = :mused")
        params["mused"] = float(manual_used)
    if quota_unit is not None:
        sets.append("quota_unit = :unit")
        params["unit"] = quota_unit
    if window_type is not None:
        sets.append("window_type = :wtype")
        params["wtype"] = window_type
    if window_reset_at is not None:
        sets.append("window_reset_at = :wreset")
        params["wreset"] = window_reset_at
    if last_good is not None:
        sets.append("last_good_json = :lastgood")
        params["lastgood"] = json.dumps(last_good, ensure_ascii=False)

    if not sets:
        return get_account(user_id, account_id)

    sets.append("updated_at = :now")
    params["now"] = datetime.now(timezone.utc).replace(tzinfo=None)

    with _get_engine().begin() as conn:
        conn.execute(
            text(f"UPDATE {TABLE_NAME} SET {', '.join(sets)} WHERE user_id = :uid AND id = :aid"),
            params,
        )
    logger.info("更新订阅额度账号: user=%s id=%s 字段=%s", user_id, account_id, list(sets))
    return get_account(user_id, account_id)


def delete_account(user_id: str, account_id: str) -> bool:
    ensure_schema()
    with _get_engine().begin() as conn:
        result = conn.execute(
            text(f"DELETE FROM {TABLE_NAME} WHERE user_id = :uid AND id = :aid"),
            {"uid": user_id, "aid": account_id},
        )
    deleted = result.rowcount > 0
    if deleted:
        logger.info("删除订阅额度账号: user=%s id=%s", user_id, account_id)
    return deleted

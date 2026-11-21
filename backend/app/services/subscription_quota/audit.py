"""订阅同步审计（只记掩码与哈希，绝不记明文 Key / 完整深链）

设计依据：``specs/agent-subscription-bridge-design.md`` §9 / §11

表 ``subscription_sync_audit``：每次导出深链、每次入库裁决写一行。
写入失败只记 WARN，不影响主流程（审计不能反过来阻断业务）。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text

from app.services.subscription_quota.accounts import _get_engine

logger = logging.getLogger(__name__)

TABLE_NAME = "subscription_sync_audit"

_CREATE_PG = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id BIGSERIAL PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    account_id VARCHAR(64),
    target VARCHAR(16) NOT NULL,
    action VARCHAR(16) NOT NULL,
    masked_key VARCHAR(32),
    url_hash VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

_CREATE_SQLITE = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(64) NOT NULL,
    account_id VARCHAR(64),
    target VARCHAR(16) NOT NULL,
    action VARCHAR(16) NOT NULL,
    masked_key VARCHAR(32),
    url_hash VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

_INDEX_SQL = (
    f"CREATE INDEX IF NOT EXISTS idx_ssa_user_time ON {TABLE_NAME} (user_id, created_at)"
)

_ready_locations: set[str] = set()


def ensure_table() -> None:
    """幂等建表（按引擎区分方言；失败只记 WARN）"""
    eng = _get_engine()
    key = f"{eng.url.drivername}:{eng.url.database}"
    if key in _ready_locations:
        return
    ddl = _CREATE_SQLITE if eng.dialect.name == "sqlite" else _CREATE_PG
    try:
        with eng.begin() as conn:
            conn.execute(text(ddl))
            conn.execute(text(_INDEX_SQL))
        _ready_locations.add(key)
    except Exception as exc:  # 审计失败不阻断业务
        logger.warning("创建审计表 %s 失败: %s", TABLE_NAME, exc)


def record(
    *,
    user_id: str,
    target: str,
    action: str,
    account_id: Optional[str] = None,
    masked_key: Optional[str] = None,
    url_hash: Optional[str] = None,
) -> None:
    """写一条审计（字段均为脱敏值）"""
    ensure_table()
    try:
        with _get_engine().begin() as conn:
            conn.execute(
                text(
                    f"INSERT INTO {TABLE_NAME} "
                    "(user_id, account_id, target, action, masked_key, url_hash, created_at) "
                    "VALUES (:uid, :aid, :target, :action, :masked, :hash, :now)"
                ),
                {
                    "uid": user_id,
                    "aid": account_id,
                    "target": target,
                    "action": action,
                    "masked": masked_key,
                    "hash": url_hash,
                    "now": datetime.now(timezone.utc).replace(tzinfo=None),
                },
            )
    except Exception as exc:  # 审计失败不阻断业务
        logger.warning("写审计失败（%s/%s）: %s", target, action, exc)
"""本机 Agent 订阅信息同步到远程主库（agent-subscription-sync）

目标恒为**远程数据库**（``app.models.base.engine``，即部署环境 PostgreSQL 主库），
不随 ``QUOTA_STORAGE`` 开关走——同步是用户显式发起的「写远程」动作。

去重规则（设计 §5，台账见 docs/reviews/2026-11-20-agent-subscription-sync-review.md）：
* 规则 1：同 (provider_id, sha256(api_key)) 已存在 → 跳过，任何字段不覆盖不更新；
  命中的存量行 api_key_hash 为空时顺手回填（仅此一列，幂等；dry_run 不回填）
* 规则 2：同 (provider_id, 渠道) 已存在但 Key 不同 → 新增一行，label 以
  ``·Key后4位`` 消歧，仍冲突则 ``-2``/``-3`` 递增，保证渠道命名互不相同

安全约束：明文 Key 仅在服务端内存中短暂存在（扫描 → sha256 → 加密入库）；
日志与响应只出现 provider / agent / 数量 / 掩码，绝不出现明文。
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text

from app.services.subscription_quota.accounts import (
    _CREATE_SQL,
    _EXTRA_COLUMNS,
    _INDEX_SQL,
    _sqlite_columns,
)
from app.services.subscription_quota.agent_subscription_scan import (
    ScanReport,
    ScannedSubscription,
    classify_channel,
    host_of,
    scan_local_subscriptions,
)

logger = logging.getLogger(__name__)

TABLE_NAME = "subscription_quota_accounts"

#: 批内多来源重叠时的保留优先级（元数据完整度从高到低）
_SOURCE_PRIORITY: tuple[str, ...] = ("cc-switch", "zcode", "opencode", "codex", "claude")

_schema_ready = False


def _server_engine():
    """远程主库 engine（独立函数便于测试 patch 为临时 SQLite）。"""
    from app.models.base import engine

    return engine


def _ensure_schema() -> None:
    """在远程主库幂等建表/补列（DDL 复用 accounts，防两处漂移）。"""
    global _schema_ready
    if _schema_ready:
        return
    target = _server_engine()
    with target.begin() as conn:
        conn.execute(text(_CREATE_SQL))
        conn.execute(text(_INDEX_SQL))
        if target.dialect.name == "sqlite":
            existing = _sqlite_columns(conn)
            for column, ddl in _EXTRA_COLUMNS:
                if column not in existing:
                    conn.execute(text(f"ALTER TABLE {TABLE_NAME} ADD COLUMN {column} {ddl}"))
        else:
            for column, ddl in _EXTRA_COLUMNS:
                conn.execute(
                    text(f"ALTER TABLE {TABLE_NAME} ADD COLUMN IF NOT EXISTS {column} {ddl}")
                )
    _schema_ready = True


def _hash_key(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


def _mask_key(plain: str) -> str:
    """掩码格式与 QuotaAccount.masked_key 一致（前 4 + * + 后 4；≤8 位全掩码）。"""
    if len(plain) <= 8:
        return "*" * len(plain)
    return f"{plain[:4]}{'*' * 8}{plain[-4:]}"


def _provider_display_name(provider_id: str, fallback: str) -> str:
    """优先取 registry 显示名，取不到用扫描器给的名称/id。"""
    try:
        from app.services.subscription_quota.registry import PROVIDER_SPECS

        for spec in PROVIDER_SPECS:
            if spec.id == provider_id:
                return spec.name
    except Exception:  # registry 不可用时退回 fallback，不阻断同步
        pass
    return fallback or provider_id


def _base_label(provider_name: str, channel: str) -> str:
    return f"{provider_name}-{channel}"


# ---------------------------------------------------------------- 归一化与批内去重（设计 §5.1）


def _normalize(report: ScanReport) -> list[ScannedSubscription]:
    """空 Key 剔除 → provider 归一化 → 批内按 (provider_id, key hash) 去重合并来源。"""
    merged: dict[tuple[str, str], ScannedSubscription] = {}
    for item in report.items:
        key = (item.api_key or "").strip()
        if not key:
            continue  # 空 Key 不入库（报告层面已由扫描器计入 report_only）
        item.api_key = key
        if item.provider_id == "custom" or not item.provider_id:
            # 未识别供应商：显示名取 base_url host（如 api.example.com），仍可入库
            item.provider_name = host_of(item.base_url) or item.provider_name or "custom"

        dedup_key = (item.provider_id, _hash_key(key))
        if dedup_key not in merged:
            merged[dedup_key] = item
            continue
        # 多源重叠：保留优先级更高的元数据，合并来源列表
        kept = merged[dedup_key]
        if _SOURCE_PRIORITY.index(item.source_agents[0]) < _SOURCE_PRIORITY.index(
            kept.source_agents[0]
        ):
            merged[dedup_key] = item
            item.source_agents = list(dict.fromkeys(item.source_agents + kept.source_agents))
        else:
            kept.source_agents = list(dict.fromkeys(kept.source_agents + item.source_agents))
    return list(merged.values())


# ---------------------------------------------------------------- 同步主流程


def sync_local_subscriptions(user_id: str, *, dry_run: bool = False) -> dict[str, Any]:
    """扫描本机 → 归一化 → 按规则 1/2 写远程主库。返回安全统计（无明文 Key）。"""
    from app.core.security import decrypt_api_key, encrypt_api_key

    report = scan_local_subscriptions()
    items = _normalize(report)

    _ensure_schema()
    engine = _server_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT id, provider_id, api_key_enc, api_key_hash, label "
                f"FROM {TABLE_NAME} WHERE user_id = :uid"
            ),
            {"uid": user_id},
        ).fetchall()

    # key_index: provider_id -> {hash: row_id}（规则 1 的供应商内判重）
    # global_key_index: hash -> provider_id（同 Key 全局唯一入库：同一凭据不因
    #   provider 归类差异（如救援通道的 custom 次优归类）被重复罗列）
    # hash_pending: row_id -> 需回填的 hash（存量行 api_key_hash 为空、经解密比对命中的）
    key_index: dict[str, dict[str, str]] = {}
    global_key_index: dict[str, str] = {}
    label_index: dict[tuple[str, str], str] = {}
    hash_pending: dict[str, str] = {}
    for row in rows:
        mapping = row._mapping if hasattr(row, "_mapping") else row
        pid = mapping["provider_id"]
        row_id = mapping["id"]
        stored_hash = mapping["api_key_hash"] or ""
        if not stored_hash and mapping["api_key_enc"]:
            try:
                stored_hash = _hash_key(decrypt_api_key(mapping["api_key_enc"]))
                hash_pending[row_id] = stored_hash  # 记录：该行命中时可回填
            except Exception:
                stored_hash = ""  # 解不开的存量行不参与判重（无法比对即视为不存在）
        if stored_hash:
            key_index.setdefault(pid, {})[stored_hash] = row_id
            global_key_index.setdefault(stored_hash, pid)
        # label 占位值用 "unknown" 哨兵而非空串：解不开 hash 的存量行同样占用 label，
        # 否则规则 2 的消歧判断会把已占用的 label 误判为空闲（假阴性）
        label_index[(pid, mapping["label"] or "")] = stored_hash or "unknown"

    result_items: list[dict[str, Any]] = []
    created = skipped = backfilled = 0
    backfilled_ids: set[str] = set()

    for item in items:
        h = _hash_key(item.api_key)
        provider_name = _provider_display_name(item.provider_id, item.provider_name)
        existing_row_id = key_index.get(item.provider_id, {}).get(h)
        # 同 Key 全局唯一：凭据已在该用户名下（任意供应商）→ 不重复入库，
        # 明细注明既有归属（供应商内命中 = 规则 1；跨供应商命中 = 防重复罗列）
        global_owner = global_key_index.get(h)

        if existing_row_id or global_owner:
            # 规则 1：同供应商同 Key → 不覆盖不更新，保留原本配置
            skipped += 1
            result_items.append(
                {
                    "providerId": item.provider_id,
                    "providerName": provider_name,
                    "channel": item.channel,
                    "label": None,
                    "maskedKey": _mask_key(item.api_key),
                    "action": "skip",
                    "sourceAgents": item.source_agents,
                    # 既有归属供应商（跨供应商命中时与 providerId 不同，供前端/排查区分）
                    "existingProviderId": global_owner or item.provider_id,
                }
            )
            # 命中的存量行原本没有 hash（老数据）→ 顺手回填（仅 api_key_hash 一列；dry_run 不动库）
            if not dry_run and existing_row_id and existing_row_id in hash_pending and existing_row_id not in backfilled_ids:
                backfilled_ids.add(existing_row_id)
            continue

        # 规则 2：同 (provider, 渠道) 不同 Key → 新增渠道行，label 消歧保证命名不同
        label = _base_label(provider_name, item.channel)
        if label_index.get((item.provider_id, label)):
            label = f"{label}·{item.api_key[-4:]}"
            suffix = 2
            base = label
            while label_index.get((item.provider_id, label)):
                label = f"{base}-{suffix}"
                suffix += 1
        action, final_label = "create", label

        result_items.append(
            {
                "providerId": item.provider_id,
                "providerName": provider_name,
                "channel": item.channel,
                "label": final_label,
                "maskedKey": _mask_key(item.api_key),
                "action": action,
                "sourceAgents": item.source_agents,
            }
        )

        if dry_run:
            continue

        extra = {
            "base_url": item.base_url,
            "region": item.region,
            "channel": item.channel,
            "source_agents": item.source_agents,
        }
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        new_id = _new_uuid()
        with engine.begin() as conn:
            next_order = conn.execute(
                text(
                    f"SELECT COALESCE(MAX(sort_order), -1) + 1 AS n "
                    f"FROM {TABLE_NAME} WHERE user_id = :uid"
                ),
                {"uid": user_id},
            ).scalar()
            conn.execute(
                text(
                    f"INSERT INTO {TABLE_NAME} "
                    "(id, user_id, provider_id, label, api_key_enc, extra_json, enabled, "
                    " sort_order, created_at, updated_at, category, app, api_key_hash, is_channel) "
                    "VALUES (:id, :uid, :pid, :label, :key, :extra, TRUE, :order, :now, :now, "
                    " :category, :app, :hash, TRUE)"
                ),
                {
                    "id": new_id,
                    "uid": user_id,
                    "pid": item.provider_id,
                    "label": final_label,
                    "key": encrypt_api_key(item.api_key),
                    "extra": json.dumps(extra, ensure_ascii=False),
                    "order": int(next_order or 0),
                    "now": now,
                    "category": classify_channel(item.provider_id, item.base_url)[1],
                    "app": item.source_agents[0] if item.source_agents else "",
                    "hash": h,
                },
            )
        # 批内即时更新索引（设计 §5.3）：同批后续条目立刻可见，避免重名/重复
        key_index.setdefault(item.provider_id, {})[h] = new_id
        global_key_index[h] = item.provider_id
        label_index[(item.provider_id, final_label)] = h
        created += 1

    # 回填存量行 hash（仅 api_key_hash 一列，WHERE 兜底幂等）
    if not dry_run:
        for row_id in backfilled_ids:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        f"UPDATE {TABLE_NAME} SET api_key_hash = :hash "
                        f"WHERE user_id = :uid AND id = :aid AND api_key_hash = ''"
                    ),
                    {"hash": hash_pending[row_id], "uid": user_id, "aid": row_id},
                )
            backfilled += 1

    logger.info(
        "用户 %s 同步本机订阅到远程库：扫描 %d 条，新建 %d，跳过 %d（规则1），回填 hash %d%s",
        user_id,
        len(items),
        created,
        skipped,
        backfilled,
        "（dry run）" if dry_run else "",
    )

    return {
        "agents": [asdict(a) for a in report.agents],
        "items": result_items,
        "created": 0 if dry_run else created,
        "skipped": skipped,
        "backfilled": 0 if dry_run else backfilled,
        "dryRun": dry_run,
    }


def _new_uuid() -> str:
    import uuid

    return str(uuid.uuid4())


# ---------------------------------------------------------------- 云端渠道查询


def list_cloud_accounts(user_id: str) -> dict[str, Any]:
    """读取远程主库中该用户的订阅渠道（掩码展示，无明文 Key）。"""
    _ensure_schema()
    engine = _server_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(f"SELECT * FROM {TABLE_NAME} WHERE user_id = :uid ORDER BY created_at ASC"),
            {"uid": user_id},
        ).fetchall()

    accounts: list[dict[str, Any]] = []
    for row in rows:
        mapping = row._mapping if hasattr(row, "_mapping") else row
        try:
            extra = json.loads(mapping.get("extra_json") or "{}")
        except (json.JSONDecodeError, TypeError):
            extra = {}
        masked: Optional[str] = None
        if mapping.get("api_key_enc"):
            from app.core.security import decrypt_api_key

            try:
                masked = _mask_key(decrypt_api_key(mapping["api_key_enc"]))
            except Exception:
                masked = "***"
        created = mapping.get("created_at")
        updated = mapping.get("updated_at")
        accounts.append(
            {
                "id": mapping["id"],
                "providerId": mapping["provider_id"],
                "label": mapping.get("label") or "",
                "maskedKey": masked,
                "category": mapping.get("category") or "official",
                "app": mapping.get("app") or "",
                "baseUrl": extra.get("base_url") or "",
                "channel": extra.get("channel") or "",
                "sourceAgents": extra.get("source_agents") or [],
                "enabled": bool(mapping.get("enabled")),
                "createdAt": created.isoformat() if isinstance(created, datetime) else created,
                "updatedAt": updated.isoformat() if isinstance(updated, datetime) else updated,
            }
        )
    return {"accounts": accounts, "total": len(accounts)}

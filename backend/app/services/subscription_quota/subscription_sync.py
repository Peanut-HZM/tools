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

import json
import logging
import threading
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.services.subscription_quota.accounts import (
    _CREATE_SQL,
    _EXTRA_COLUMNS,
    _INDEX_SQL,
    _acquire_pg_advisory_lock,
    _sqlite_columns,
    ensure_dedupe_index,
)
from app.services.subscription_quota.dedupe import (
    ExistingIndex,
    dedupe_mode,
    find_duplicate_groups,
    mask_key,
    sha256_hex,
)
from app.services.subscription_quota.url_norm import normalize_base_url
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


_schema_ddl_lock = threading.Lock()


def _ensure_schema() -> None:
    """在远程主库幂等建表/补列（DDL 复用 accounts，防两处漂移）。

    并发防护同 accounts.ensure_schema：进程内锁 + PG 咨询锁——
    多台机器的后端共用同一远程 PG 时串行化 DDL，避免 AccessExclusiveLock 死锁。
    """
    global _schema_ready
    if _schema_ready:
        return
    with _schema_ddl_lock:
        if _schema_ready:  # 双重检查：等锁期间可能已完成
            return
        target = _server_engine()
        with target.begin() as conn:
            _acquire_pg_advisory_lock(conn)
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
    # 建去重唯一索引（有冲突/失败则降级为无索引运行，绝不阻断服务）
    report = ensure_dedupe_index(target)
    if report.get("conflicts"):
        logger.warning("去重索引未创建：存在 %d 组重复订阅，见 /subscriptions/duplicates", len(report["conflicts"]))


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


# ---------------------------------------------------------------- 归一化与批内去重（设计 §5.1）

#: 兼容既有测试/外部引用；实现已迁移到 ``dedupe.sha256_hex``
_hash_key = sha256_hex


def _normalize(report: ScanReport) -> list[ScannedSubscription]:
    """空 Key 剔除 → provider 归一化 → 批内按统一去重键（URL+Key）去重合并来源。"""
    merged: dict[tuple, ScannedSubscription] = {}
    mode = dedupe_mode()
    for item in report.items:
        key = (item.api_key or "").strip()
        if not key:
            continue  # 空 Key 不入库（报告层面已由扫描器计入 report_only）
        item.api_key = key
        if item.provider_id == "custom" or not item.provider_id:
            # 未识别供应商：显示名取 base_url host（如 api.example.com），仍可入库
            item.provider_name = host_of(item.base_url) or item.provider_name or "custom"

        if mode == "legacy":
            dedup_key: tuple = ("legacy", item.provider_id, sha256_hex(key))
        else:
            dedup_key = ("url_key", normalize_base_url(item.base_url), sha256_hex(key))
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
    """扫描本机 → 归一化 → 按统一去重规则（URL+Key）写远程主库。

    返回安全统计（无明文 Key）。设计见
    ``specs/agent-subscription-bridge-design.md`` §5。
    """
    report = scan_local_subscriptions()
    items = _normalize(report)
    result = ingest_items(user_id, items, dry_run=dry_run)
    result["agents"] = [asdict(a) for a in report.agents]
    return result


def ingest_items(
    user_id: str, items: list[ScannedSubscription], *, dry_run: bool = False
) -> dict[str, Any]:
    """把一批订阅条目写入远程主库（扫描同步与客户端上传共用同一条路径）。

    ``items`` 来自 :func:`_normalize`（本机扫描）或 ``/subscriptions/push-items``
    （客户端上传）。判重、label 消歧、hash 回填全部由 :mod:`dedupe` 完成。
    """
    from app.core.security import decrypt_api_key, encrypt_api_key

    _ensure_schema()
    engine = _server_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT id, provider_id, base_url, base_url_norm, api_key_enc, api_key_hash, label "
                f"FROM {TABLE_NAME} WHERE user_id = :uid"
            ),
            {"uid": user_id},
        ).fetchall()

    # 判重索引统一由 dedupe.ExistingIndex 构建（url_key / legacy 由开关决定）
    index = ExistingIndex.from_rows(rows, decrypt_fn=decrypt_api_key)

    result_items: list[dict[str, Any]] = []
    created = skipped = backfilled = 0
    backfilled_ids: set[str] = set()

    for item in items:
        provider_name = _provider_display_name(item.provider_id, item.provider_name)
        decision = index.decide(
            provider_id=item.provider_id,
            provider_name=provider_name,
            channel=item.channel,
            base_url=item.base_url,
            api_key=item.api_key,
        )

        if decision.action == "skip":
            skipped += 1
            existing_row_id = index.key_index.get(decision.key)
            result_items.append(
                {
                    "providerId": item.provider_id,
                    "providerName": provider_name,
                    "channel": item.channel,
                    "label": None,
                    "maskedKey": mask_key(item.api_key),
                    "action": "skip",
                    "sourceAgents": item.source_agents,
                    "reason": decision.reason,
                    # 既有归属供应商（跨供应商命中时与 providerId 不同）
                    "existingProviderId": index.row_provider.get(existing_row_id or "")
                    or index.global_index.get(decision.key[2])
                    or item.provider_id,
                }
            )
            # 命中的存量行原本没有 hash（老数据）→ 顺手回填（仅 api_key_hash 一列；dry_run 不动库）
            if (
                not dry_run
                and existing_row_id
                and existing_row_id in index.hash_pending
                and existing_row_id not in backfilled_ids
            ):
                backfilled_ids.add(existing_row_id)
            continue

        final_label = decision.label or provider_name

        if dry_run:
            result_items.append(
                {
                    "providerId": item.provider_id,
                    "providerName": provider_name,
                    "channel": item.channel,
                    "label": final_label,
                    "maskedKey": mask_key(item.api_key),
                    "action": "create",
                    "sourceAgents": item.source_agents,
                    "reason": None,
                }
            )
            continue

        extra = {
            "base_url": item.base_url,
            "region": item.region,
            "channel": item.channel,
            "source_agents": item.source_agents,
        }
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        new_id = _new_uuid()
        try:
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
                        " sort_order, created_at, updated_at, category, app, api_key_hash, is_channel, "
                        " base_url, base_url_norm) "
                        "VALUES (:id, :uid, :pid, :label, :key, :extra, TRUE, :order, :now, :now, "
                        " :category, :app, :hash, TRUE, :base_url, :base_url_norm)"
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
                        "hash": sha256_hex(item.api_key),
                        "base_url": (item.base_url or "").strip(),
                        "base_url_norm": decision.key[1],
                    },
                )
        except IntegrityError:
            # 并发写同一 (url,key)：唯一索引兜底 → 按 skip 处理，绝不 500（设计 §5）
            skipped += 1
            result_items.append(
                {
                    "providerId": item.provider_id,
                    "providerName": provider_name,
                    "channel": item.channel,
                    "label": None,
                    "maskedKey": mask_key(item.api_key),
                    "action": "skip",
                    "sourceAgents": item.source_agents,
                    "reason": "duplicate",
                    "existingProviderId": item.provider_id,
                }
            )
            continue

        result_items.append(
            {
                "providerId": item.provider_id,
                "providerName": provider_name,
                "channel": item.channel,
                "label": final_label,
                "maskedKey": mask_key(item.api_key),
                "action": "create",
                "sourceAgents": item.source_agents,
                "reason": None,
            }
        )
        # 批内即时更新索引：同批后续条目立刻可见，避免重名/重复
        index.register(
            provider_id=item.provider_id,
            key=decision.key,
            row_id=new_id,
            label=final_label,
            api_key=item.api_key,
        )
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
                    {"hash": index.hash_pending[row_id], "uid": user_id, "aid": row_id},
                )
            backfilled += 1

    logger.info(
        "用户 %s 写入订阅条目：待处理 %d 条，新建 %d，跳过 %d（同 URL+Key），回填 hash %d%s",
        user_id,
        len(items),
        created,
        skipped,
        backfilled,
        "（dry run）" if dry_run else "",
    )

    return {
        "items": result_items,
        "created": 0 if dry_run else created,
        "skipped": skipped,
        "backfilled": 0 if dry_run else backfilled,
        "dryRun": dry_run,
    }


def list_duplicates(user_id: str) -> dict[str, Any]:
    """按统一去重键列出重复订阅分组（只读，不删除任何数据）

    设计 §5：存量重复不自动处理，由用户在 UI 单条/批量确认。
    """
    _ensure_schema()
    engine = _server_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT id, user_id, provider_id, label, base_url, base_url_norm, "
                f"api_key_hash FROM {TABLE_NAME} WHERE user_id = :uid"
            ),
            {"uid": user_id},
        ).fetchall()
    groups = find_duplicate_groups(rows)
    return {"count": len(groups), "groups": groups, "mode": dedupe_mode()}


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
                masked = mask_key(decrypt_api_key(mapping["api_key_enc"]))
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

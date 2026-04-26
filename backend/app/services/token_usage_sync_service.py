"""Token Usage 增量同步服务 — 从 CLI 工具获取数据并写入数据库"""

import logging
from datetime import datetime, timedelta, date
from typing import Optional

from app.models.base import SessionLocal
from app.models.token_usage_models import TokenUsageRecord, TokenUsageSyncLog, DeviceRegistry
from app.utils.usage_fetcher import UsageFetcher
from app.utils.device_id import get_device_id

logger = logging.getLogger(__name__)


def _safe_int(d: dict, *keys: str) -> int:
    for k in keys:
        v = d.get(k)
        if v is not None:
            try:
                return int(v)
            except (ValueError, TypeError):
                pass
    return 0


def _safe_float(d: dict, *keys: str) -> float:
    for k in keys:
        v = d.get(k)
        if v is not None:
            try:
                return float(v)
            except (ValueError, TypeError):
                pass
    return 0.0


def _parse_date(date_val: str) -> Optional[date]:
    """解析日期字符串为 date 对象"""
    if not date_val:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(date_val, fmt).date()
        except ValueError:
            continue
    return None


def _fetch_claude_daily(days: int) -> list[dict]:
    """获取 Claude 数据（daily 粒度，带 breakdown）"""
    since = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")
    raw = UsageFetcher.fetch_claude(report_type="daily", since=since, breakdown=True)
    if "error" in raw:
        logger.warning(f"Claude 数据获取失败: {raw['error']}")
        return []
    entries = raw.get("daily", raw.get("data", raw.get("rows", [])))
    if isinstance(entries, dict):
        entries = [entries]
    if not isinstance(entries, list):
        return []
    return entries


def _fetch_opencode_daily(days: int) -> list[dict]:
    """获取 OpenCode 数据（daily 粒度）"""
    raw = UsageFetcher.fetch_opencode(days=days)
    if "error" in raw:
        logger.warning(f"OpenCode 数据获取失败: {raw['error']}")
        return []
    # opencode-usage 返回 {period, total, rows: [...]}，rows 是 daily
    entries = raw.get("rows", raw.get("daily", raw.get("data", [])))
    if isinstance(entries, dict):
        entries = [entries]
    if not isinstance(entries, list):
        return []
    return entries


def _parse_claude_entries(entries: list[dict]) -> list[dict]:
    """
    解析 Claude CLI 输出为结构化数据。
    返回 [{date, model, input_tokens, output_tokens, ...}] 列表，每个模型一条。
    """
    results = []
    for entry in entries:
        date_val = entry.get("date") or entry.get("label") or ""
        record_date = _parse_date(date_val)
        if not record_date:
            continue

        # ccusage daily breakdown 的模型明细在 modelBreakdowns 或 models 中
        breakdowns = entry.get("modelBreakdowns", entry.get("models_used", []))
        if not breakdowns:
            # 没有 breakdown，使用总体数据，模型名用汇总标识
            tokens = entry.get("tokens", {})
            results.append({
                "record_date": record_date,
                "model": entry.get("model") or "_total",
                "input_tokens": _safe_int(tokens, "input") or _safe_int(entry, "inputTokens", "input_tokens"),
                "output_tokens": _safe_int(tokens, "output") or _safe_int(entry, "outputTokens", "output_tokens"),
                "cache_creation_tokens": _safe_int(tokens, "cache_write") or _safe_int(entry, "cacheCreationTokens", "cache_creation_tokens"),
                "cache_read_tokens": _safe_int(tokens, "cache_read") or _safe_int(entry, "cacheReadTokens", "cache_read_tokens"),
                "total_tokens": _safe_int(tokens, "total") or _safe_int(entry, "totalTokens", "total_tokens"),
                "total_cost": _safe_float(entry, "cost") or _safe_float(entry, "totalCost", "costUSD"),
            })
        else:
            for bk in breakdowns:
                model_name = bk.get("model") or bk.get("name") or "unknown"
                tokens = bk.get("tokens", bk)
                results.append({
                    "record_date": record_date,
                    "model": model_name,
                    "input_tokens": _safe_int(tokens, "input") or _safe_int(bk, "inputTokens", "input_tokens"),
                    "output_tokens": _safe_int(tokens, "output") or _safe_int(bk, "outputTokens", "output_tokens"),
                    "cache_creation_tokens": _safe_int(tokens, "cache_write") or _safe_int(bk, "cacheCreationTokens", "cache_creation_tokens"),
                    "cache_read_tokens": _safe_int(tokens, "cache_read") or _safe_int(bk, "cacheReadTokens", "cache_read_tokens"),
                    "total_tokens": _safe_int(tokens, "total") or _safe_int(bk, "totalTokens", "total_tokens"),
                    "total_cost": _safe_float(bk, "cost") or _safe_float(bk, "totalCost", "costUSD"),
                })
    return results


def _parse_opencode_entries(entries: list[dict]) -> list[dict]:
    """解析 OpenCode CLI 输出为结构化数据"""
    results = []
    for entry in entries:
        date_val = entry.get("date") or entry.get("label") or ""
        record_date = _parse_date(date_val)
        if not record_date:
            continue

        # opencode-usage 按模型分组，每条 entry 包含 models 子列表
        models = entry.get("models", [])
        if not models:
            # 没有模型明细，使用总体数据
            results.append({
                "record_date": record_date,
                "model": entry.get("model") or "_total",
                "input_tokens": _safe_int(entry, "inputTokens", "input_tokens"),
                "output_tokens": _safe_int(entry, "outputTokens", "output_tokens"),
                "cache_creation_tokens": _safe_int(entry, "cacheCreationTokens", "cache_creation_tokens"),
                "cache_read_tokens": _safe_int(entry, "cacheReadTokens", "cache_read_tokens"),
                "total_tokens": _safe_int(entry, "totalTokens", "total_tokens"),
                "total_cost": _safe_float(entry, "totalCost", "costUSD", "cost"),
            })
        else:
            for mod in models:
                model_name = mod.get("model") or mod.get("name") or "unknown"
                results.append({
                    "record_date": record_date,
                    "model": model_name,
                    "input_tokens": _safe_int(mod, "inputTokens", "input_tokens"),
                    "output_tokens": _safe_int(mod, "outputTokens", "output_tokens"),
                    "cache_creation_tokens": _safe_int(mod, "cacheCreationTokens", "cache_creation_tokens"),
                    "cache_read_tokens": _safe_int(mod, "cacheReadTokens", "cache_read_tokens"),
                    "total_tokens": _safe_int(mod, "totalTokens", "total_tokens"),
                    "total_cost": _safe_float(mod, "totalCost", "costUSD", "cost"),
                })
    return results


def sync_token_usage(user_id: str, days: int = 90) -> dict:
    """
    增量同步 Token Usage 数据到数据库。

    Args:
        user_id: 当前用户 ID
        days: 同步最近 N 天数据

    Returns:
        {sources_synced: [...], total_records: int, errors: [...]}
    """
    device_id = get_device_id()
    db = SessionLocal()
    result = {"sources_synced": [], "total_records": 0, "errors": []}

    # 确保设备已注册到 device_registry
    try:
        existing = db.query(DeviceRegistry).filter_by(
            user_id=user_id, device_id=device_id
        ).first()
        if not existing:
            db.add(DeviceRegistry(
                user_id=user_id,
                device_id=device_id,
                display_name=None,
            ))
            db.commit()
    except Exception as e:
        logger.warning(f"设备注册失败: {e}")

    try:
        sources = [
            ("claude", _fetch_claude_daily, _parse_claude_entries),
            ("opencode", _fetch_opencode_daily, _parse_opencode_entries),
        ]

        for source_name, fetch_fn, parse_fn in sources:
            try:
                raw_entries = fetch_fn(days)
                if not raw_entries:
                    result["errors"].append(f"{source_name}: 无数据")
                    continue

                parsed = parse_fn(raw_entries)
                # 去重：同一天同一模型只保留最后一条（取聚合后的记录）
                deduped: dict[tuple, dict] = {}
                for rec in parsed:
                    key = (rec["record_date"], rec["model"])
                    deduped[key] = rec  # 后面的覆盖前面的
                parsed = list(deduped.values())
                count = _upsert_records(db, user_id, device_id, source_name, parsed)
                result["sources_synced"].append(source_name)
                result["total_records"] += count

                # 记录同步日志
                _log_sync(db, user_id, device_id, source_name, "success", count)
                logger.info(f"[{source_name}] 同步 {count} 条记录到数据库")

            except Exception as e:
                error_msg = f"{source_name}: {str(e)}"
                result["errors"].append(error_msg)
                logger.error(f"同步失败 {error_msg}")
                try:
                    _log_sync(db, user_id, device_id, source_name, "failed", 0, str(e))
                except Exception:
                    pass

        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"数据库事务失败: {e}")
        result["errors"].append(f"数据库: {str(e)}")
    finally:
        db.close()

    return result


def _upsert_records(db, user_id: str, device_id: str, source: str, records: list[dict]) -> int:
    """批量 INSERT 或 UPDATE，返回实际写入的记录数"""
    count = 0
    for rec in records:
        existing = db.query(TokenUsageRecord).filter_by(
            user_id=user_id,
            device_id=device_id,
            record_date=rec["record_date"],
            source=source,
            model=rec["model"],
        ).first()

        if not existing:
            db.add(TokenUsageRecord(
                user_id=user_id,
                device_id=device_id,
                record_date=rec["record_date"],
                source=source,
                model=rec["model"],
                input_tokens=rec["input_tokens"],
                output_tokens=rec["output_tokens"],
                cache_creation_tokens=rec["cache_creation_tokens"],
                cache_read_tokens=rec["cache_read_tokens"],
                total_tokens=rec["total_tokens"],
                total_cost=rec["total_cost"],
            ))
            count += 1
        else:
            if (existing.input_tokens != rec["input_tokens"] or
                    existing.output_tokens != rec["output_tokens"] or
                    existing.cache_creation_tokens != rec["cache_creation_tokens"] or
                    existing.cache_read_tokens != rec["cache_read_tokens"] or
                    existing.total_tokens != rec["total_tokens"] or
                    float(existing.total_cost or 0) != rec["total_cost"]):
                existing.input_tokens = rec["input_tokens"]
                existing.output_tokens = rec["output_tokens"]
                existing.cache_creation_tokens = rec["cache_creation_tokens"]
                existing.cache_read_tokens = rec["cache_read_tokens"]
                existing.total_tokens = rec["total_tokens"]
                existing.total_cost = rec["total_cost"]
                count += 1

    return count


def _log_sync(db, user_id: str, device_id: str, source: str,
              status: str, records_count: int, error_message: str = None):
    """记录同步日志"""
    existing = db.query(TokenUsageSyncLog).filter_by(
        user_id=user_id,
        device_id=device_id,
        source=source,
        sync_date=date.today(),
    ).first()

    if existing:
        existing.status = status
        existing.records_count = records_count
        existing.error_message = error_message
    else:
        db.add(TokenUsageSyncLog(
            user_id=user_id,
            device_id=device_id,
            source=source,
            sync_date=date.today(),
            status=status,
            records_count=records_count,
            error_message=error_message,
        ))

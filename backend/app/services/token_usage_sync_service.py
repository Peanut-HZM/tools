"""Token Usage 增量同步服务 — 从 CLI 工具获取数据并写入数据库"""

import logging
from datetime import datetime, timedelta, date
from typing import Optional

from app.models.base import SessionLocal
from app.models.token_usage_models import (
    TokenUsageRecord,
    TokenUsageSyncLog,
    DeviceRegistry,
    DeviceIdAlias,
)
from app.utils.usage_fetcher import UsageFetcher
from app.utils.device_id import get_device_id, get_device_display_name, get_device_fingerprint
from app.utils.ccusage_invoker import CcusageError

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


def _get_date_key(day: dict) -> Optional[str]:
    """统一读取 ccusage daily 条目的日期字段。

    ccusage CLI 不同子命令返回的日期字段可能为 date 或 period，
    这里优先取 date，不存在时 fallback 到 period，避免数据被跳过。
    """
    if not isinstance(day, dict):
        return None
    return day.get("date") or day.get("period") or None


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


def _calc_total_tokens(
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int,
    cache_read_tokens: int,
) -> int:
    """当 total_tokens 为 0 时，回退计算各组件之和"""
    return input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens


def _map_source_to_tool(source: str) -> dict:
    source_value = source or "unknown"
    mapping = {
        "claude": {"tool_id": "claude-code", "tool_name": "Claude Code"},
        "opencode": {"tool_id": "opencode", "tool_name": "OpenCode"},
        "codex": {"tool_id": "codex", "tool_name": "Codex"},
        "openclaw": {"tool_id": "openclaw", "tool_name": "OpenClaw"},
        "amp": {"tool_id": "amp", "tool_name": "Amp"},
        "droid": {"tool_id": "droid", "tool_name": "Droid"},
        "codebuff": {"tool_id": "codebuff", "tool_name": "Codebuff"},
        "hermes": {"tool_id": "hermes", "tool_name": "Hermes"},
        "pi": {"tool_id": "pi", "tool_name": "pi"},
        "goose": {"tool_id": "goose", "tool_name": "Goose"},
        "kilo": {"tool_id": "kilo", "tool_name": "Kilo"},
        "copilot": {"tool_id": "copilot", "tool_name": "GitHub Copilot"},
        "gemini": {"tool_id": "gemini", "tool_name": "Gemini"},
        "kimi": {"tool_id": "kimi", "tool_name": "Kimi"},
        "qwen": {"tool_id": "qwen", "tool_name": "Qwen"},
    }
    return mapping.get(
        source_value,
        {"tool_id": source_value, "tool_name": source_value},
    )


def _display_model_name(model: str, tool_name: str = "Unknown Tool") -> str:
    if model == "_total":
        return f"{tool_name} total"
    if not model:
        return "未知模型"
    return model


def _build_dimension_fields(source: str, device_name: str, model: str) -> dict:
    tool = _map_source_to_tool(source)
    return {
        "source_raw": source,
        "tool_id": tool["tool_id"],
        "tool_name": tool["tool_name"],
        "device_name": device_name,
        "model_display_name": _display_model_name(model, tool["tool_name"]),
    }


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
            input_tokens = _safe_int(tokens, "input") or _safe_int(entry, "inputTokens", "input_tokens")
            output_tokens = _safe_int(tokens, "output") or _safe_int(entry, "outputTokens", "output_tokens")
            cache_creation_tokens = _safe_int(tokens, "cache_write") or _safe_int(entry, "cacheCreationTokens", "cache_creation_tokens")
            cache_read_tokens = _safe_int(tokens, "cache_read") or _safe_int(entry, "cacheReadTokens", "cache_read_tokens")
            total_tokens = _safe_int(tokens, "total") or _safe_int(entry, "totalTokens", "total_tokens")
            if total_tokens == 0:
                total_tokens = _calc_total_tokens(input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens)
            results.append({
                "record_date": record_date,
                "model": entry.get("model") or "_total",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_tokens": cache_creation_tokens,
                "cache_read_tokens": cache_read_tokens,
                "total_tokens": total_tokens,
                "total_cost": _safe_float(entry, "cost") or _safe_float(entry, "totalCost", "costUSD"),
            })
        else:
            for bk in breakdowns:
                model_name = bk.get("modelName") or bk.get("model") or bk.get("name") or "unknown"
                tokens = bk.get("tokens", bk)
                input_tokens = _safe_int(tokens, "input") or _safe_int(bk, "inputTokens", "input_tokens")
                output_tokens = _safe_int(tokens, "output") or _safe_int(bk, "outputTokens", "output_tokens")
                cache_creation_tokens = _safe_int(tokens, "cache_write") or _safe_int(bk, "cacheCreationTokens", "cache_creation_tokens")
                cache_read_tokens = _safe_int(tokens, "cache_read") or _safe_int(bk, "cacheReadTokens", "cache_read_tokens")
                total_tokens = _safe_int(tokens, "total") or _safe_int(bk, "totalTokens", "total_tokens")
                if total_tokens == 0:
                    total_tokens = _calc_total_tokens(input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens)
                results.append({
                    "record_date": record_date,
                    "model": model_name,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_creation_tokens": cache_creation_tokens,
                    "cache_read_tokens": cache_read_tokens,
                    "total_tokens": total_tokens,
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
            input_tokens = _safe_int(entry, "inputTokens", "input_tokens")
            output_tokens = _safe_int(entry, "outputTokens", "output_tokens")
            cache_creation_tokens = _safe_int(entry, "cacheCreationTokens", "cache_creation_tokens")
            cache_read_tokens = _safe_int(entry, "cacheReadTokens", "cache_read_tokens")
            total_tokens = _safe_int(entry, "totalTokens", "total_tokens")
            if total_tokens == 0:
                total_tokens = _calc_total_tokens(input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens)
            results.append({
                "record_date": record_date,
                "model": entry.get("model") or "_total",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_tokens": cache_creation_tokens,
                "cache_read_tokens": cache_read_tokens,
                "total_tokens": total_tokens,
                "total_cost": _safe_float(entry, "totalCost", "costUSD", "cost"),
            })
        else:
            for mod in models:
                model_name = mod.get("modelName") or mod.get("model") or mod.get("name") or "unknown"
                input_tokens = _safe_int(mod, "inputTokens", "input_tokens")
                output_tokens = _safe_int(mod, "outputTokens", "output_tokens")
                cache_creation_tokens = _safe_int(mod, "cacheCreationTokens", "cache_creation_tokens")
                cache_read_tokens = _safe_int(mod, "cacheReadTokens", "cache_read_tokens")
                total_tokens = _safe_int(mod, "totalTokens", "total_tokens")
                if total_tokens == 0:
                    total_tokens = _calc_total_tokens(input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens)
                results.append({
                    "record_date": record_date,
                    "model": model_name,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_creation_tokens": cache_creation_tokens,
                    "cache_read_tokens": cache_read_tokens,
                    "total_tokens": total_tokens,
                    "total_cost": _safe_float(mod, "totalCost", "costUSD", "cost"),
                })
    return results


def sync_token_usage(
    user_id: str,
    days: int = 90,
    *,
    since_date: Optional[date] = None,
    until_date: Optional[date] = None,
) -> dict:
    """
    增量同步 Token Usage 数据到数据库。

    Args:
        user_id: 当前用户 ID
        days: 同步最近 N 天数据
        since_date: 起始日期（覆盖 days）
        until_date: 结束日期（覆盖 days）

    Returns:
        {sources_synced: [...], total_records: int, errors: [...]}
    """
    if until_date is None:
        until_date = date.today()
    if since_date is None:
        since_date = until_date - timedelta(days=days - 1)

    device_id = get_device_id()
    device_name = get_device_display_name()
    device_fingerprint, id_type = get_device_fingerprint()
    fingerprint_match = None

    result = {"sources_synced": [], "total_records": 0, "errors": []}

    # ===== 阶段一：抓取数据（慢操作：ccusage / claude CLI 子进程，全程不持有数据库连接）=====
    # 将耗时的子进程抓取与数据库写入解耦，避免后台同步在抓取期间长时间占用连接池连接，
    # 进而导致前端接口因 "connection pool exhausted" 长时间 Pending。

    # claude 源（v2 流程已覆盖 opencode，此处仅保留 claude 以防降级）
    claude_parsed: list[dict] = []
    claude_fetch_error: Optional[Exception] = None
    try:
        raw_entries = _fetch_claude_daily(days)
        if not raw_entries:
            result["errors"].append({
                "source": "claude",
                "error": "claude: 无数据",
                "error_code": "NO_DATA",
                "remediation": "请检查是否有使用该工具的记录",
                "details": {},
            })
        else:
            parsed = _parse_claude_entries(raw_entries)
            # 去重：同一天同一模型只保留最后一条（取聚合后的记录）
            deduped: dict[tuple, dict] = {}
            for rec in parsed:
                key = (rec["record_date"], rec["model"])
                deduped[key] = rec  # 后面的覆盖前面的
            claude_parsed = list(deduped.values())
    except Exception as e:
        claude_fetch_error = e
        if isinstance(e, CcusageError):
            result["errors"].append({
                "source": "claude",
                "error": e.message,
                "error_code": e.code,
                "remediation": e.remediation,
                "details": e.details,
            })
        else:
            result["errors"].append({
                "source": "claude",
                "error": f"claude: {str(e)}",
                "error_code": "FETCH_ERROR",
                "remediation": "请检查网络连接或工具安装状态",
                "details": {"exception": str(e)},
            })
        logger.error(f"同步失败 claude: {e}")

    # ccusage v2 统一数据源抓取
    ccusage_records: list[dict] = []
    try:
        fetched = _fetch_ccusage_v2_records(since_date, until_date)
        ccusage_records = fetched["records"]
        result["errors"].extend(fetched["errors"])
    except Exception as e:
        logger.error(f"[ccusage-v2] 抓取失败: {e}", exc_info=True)
        if isinstance(e, CcusageError):
            result["errors"].append({
                "source": "ccusage-v2",
                "error": e.message,
                "error_code": e.code,
                "remediation": e.remediation,
                "details": e.details,
            })
        else:
            result["errors"].append({
                "source": "ccusage-v2",
                "error": f"ccusage-v2: {str(e)}",
                "error_code": "V2_SYNC_ERROR",
                "remediation": "请检查 ccusage 安装和网络连接",
                "details": {"exception": str(e)},
            })

    # ===== 阶段二：写入数据库（快操作，仅短暂持有连接池连接）=====
    db = SessionLocal()

    # 确保设备已注册到 device_registry，并更新指纹
    try:
        existing = db.query(DeviceRegistry).filter_by(
            user_id=user_id, device_id=device_id
        ).first()
        if not existing:
            # 检查是否有相同指纹的设备
            matched = None
            if device_fingerprint:
                matched = db.query(DeviceRegistry).filter_by(
                    user_id=user_id, device_fingerprint=device_fingerprint
                ).first()

            db.add(DeviceRegistry(
                user_id=user_id,
                device_id=device_id,
                display_name=None,
                default_display_name=device_name,
                device_fingerprint=device_fingerprint,
                fingerprint_version=1,
                id_type=id_type,
            ))
            db.commit()

            # 自动合并相同指纹的设备
            if matched and matched.device_id != device_id:
                existing_alias = db.query(DeviceIdAlias).filter_by(
                    user_id=user_id, alias_device_id=device_id
                ).first()
                if not existing_alias:
                    db.add(DeviceIdAlias(
                        alias_device_id=device_id,
                        canonical_device_id=matched.device_id,
                        user_id=user_id,
                    ))
                    db.commit()
                    logger.info(f"自动合并设备 {device_id} -> {matched.device_id} (指纹匹配)")
                fingerprint_match = {
                    "matched_device_id": matched.device_id,
                    "matched_device_name": matched.display_name
                    or matched.default_display_name
                    or matched.device_id,
                }
        else:
            existing.device_fingerprint = device_fingerprint
            existing.fingerprint_version = 1
            existing.id_type = id_type
            if not existing.default_display_name:
                existing.default_display_name = device_name
            db.commit()
    except Exception as e:
        logger.warning(f"设备注册失败: {e}")

    try:
        # 写入 claude 记录（数据已在阶段一抓取完成）
        if claude_fetch_error is not None:
            # 抓取阶段已失败，补记一条失败的同步日志
            try:
                _log_sync(db, user_id, device_id, "claude", "failed", 0, str(claude_fetch_error))
            except Exception:
                pass
        elif claude_parsed:
            try:
                count = _upsert_records(
                    db,
                    user_id,
                    device_id,
                    "claude",
                    claude_parsed,
                    device_name,
                )
                result["sources_synced"].append("claude")
                result["total_records"] += count
                _log_sync(db, user_id, device_id, "claude", "success", count)
                logger.info(f"[claude] 同步 {count} 条记录到数据库")
            except Exception as e:
                result["errors"].append({
                    "source": "claude",
                    "error": f"claude: {str(e)}",
                    "error_code": "DB_WRITE_ERROR",
                    "remediation": "请检查数据库连接",
                    "details": {"exception": str(e)},
                })
                logger.error(f"写入失败 claude: {e}")
                try:
                    _log_sync(db, user_id, device_id, "claude", "failed", 0, str(e))
                except Exception:
                    pass

        # 写入 ccusage v2 记录（数据已在阶段一抓取完成）
        try:
            v2_count = _write_ccusage_v2_records(
                db, user_id, device_id, device_name, ccusage_records
            )
            if v2_count > 0:
                result["ccusage_records"] = v2_count
                result["total_records"] += v2_count
        except Exception as e:
            logger.error(f"[ccusage-v2] 写入失败: {e}", exc_info=True)
            result["errors"].append({
                "source": "ccusage-v2",
                "error": f"ccusage-v2: {str(e)}",
                "error_code": "DB_WRITE_ERROR",
                "remediation": "请检查数据库连接",
                "details": {"exception": str(e)},
            })

        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"数据库事务失败: {e}")
        # 检查是否是 CcusageError 类型
        if isinstance(e, CcusageError):
            result["errors"].append({
                "source": "database",
                "error": e.message,
                "error_code": e.code,
                "remediation": e.remediation,
                "details": e.details,
            })
        else:
            result["errors"].append({
                "source": "database",
                "error": f"数据库: {str(e)}",
                "error_code": "DB_TRANSACTION_ERROR",
                "remediation": "请检查数据库连接",
                "details": {"exception": str(e)},
            })
    finally:
        if fingerprint_match:
            result["fingerprint_match"] = fingerprint_match
        db.close()

    return result


def _upsert_records(
    db,
    user_id: str,
    device_id: str,
    source: str,
    records: list[dict],
    device_name: str,
) -> int:
    """批量 INSERT 或 UPDATE，返回实际写入的记录数"""
    count = 0
    for rec in records:
        dimension_fields = _build_dimension_fields(
            source=source,
            device_name=device_name,
            model=rec["model"],
        )
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
                source_raw=dimension_fields["source_raw"],
                tool_id=dimension_fields["tool_id"],
                tool_name=dimension_fields["tool_name"],
                model=rec["model"],
                model_display_name=dimension_fields["model_display_name"],
                device_name=dimension_fields["device_name"],
                input_tokens=rec["input_tokens"],
                output_tokens=rec["output_tokens"],
                cache_creation_tokens=rec["cache_creation_tokens"],
                cache_read_tokens=rec["cache_read_tokens"],
                total_tokens=rec["total_tokens"],
                total_cost=rec["total_cost"],
            ))
            count += 1
        else:
            changed = (
                existing.input_tokens != rec["input_tokens"] or
                existing.output_tokens != rec["output_tokens"] or
                existing.cache_creation_tokens != rec["cache_creation_tokens"] or
                existing.cache_read_tokens != rec["cache_read_tokens"] or
                existing.total_tokens != rec["total_tokens"] or
                float(existing.total_cost or 0) != rec["total_cost"] or
                existing.source_raw != dimension_fields["source_raw"] or
                existing.tool_id != dimension_fields["tool_id"] or
                existing.tool_name != dimension_fields["tool_name"] or
                existing.device_name != dimension_fields["device_name"] or
                existing.model_display_name != dimension_fields["model_display_name"]
            )
            if changed:
                existing.input_tokens = rec["input_tokens"]
                existing.output_tokens = rec["output_tokens"]
                existing.cache_creation_tokens = rec["cache_creation_tokens"]
                existing.cache_read_tokens = rec["cache_read_tokens"]
                existing.total_tokens = rec["total_tokens"]
                existing.total_cost = rec["total_cost"]
                existing.source_raw = dimension_fields["source_raw"]
                existing.tool_id = dimension_fields["tool_id"]
                existing.tool_name = dimension_fields["tool_name"]
                existing.device_name = dimension_fields["device_name"]
                existing.model_display_name = dimension_fields["model_display_name"]
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


# ========================================================================
# ccusage 统一数据源（v2）— 替代 _parse_opencode_entries
# ========================================================================

# agent_id → 显示名映射
AGENT_DISPLAY_NAMES = {
    "claude": "Claude Code",
    "opencode": "OpenCode",
    "openclaw": "OpenClaw",
    "codex": "Codex",
    "amp": "Amp",
    "droid": "Droid",
    "codebuff": "Codebuff",
    "hermes": "Hermes",
    "pi": "pi",
    "goose": "Goose",
    "kilo": "Kilo",
    "copilot": "GitHub Copilot",
    "gemini": "Gemini",
    "kimi": "Kimi",
    "qwen": "Qwen",
}


def _build_agent_record(
    agent: str,
    record_date: date,
    model_name: str,
    bd: dict,
) -> dict:
    """根据单个模型明细 dict 构造一条记录（归属固定为该 agent）。

    兼容两种明细格式：
    - modelBreakdowns 元素（claude/opencode）：{modelName, inputTokens, ...}
    - models 字典值（codex）：{input, output, cache_read, cache_write, cost}
    """
    input_tokens = _safe_int(bd, "inputTokens", "input_tokens", "input")
    output_tokens = _safe_int(bd, "outputTokens", "output_tokens", "output")
    cache_creation_tokens = _safe_int(bd, "cacheCreationTokens", "cache_creation_tokens", "cache_write")
    cache_read_tokens = _safe_int(bd, "cacheReadTokens", "cache_read_tokens", "cache_read")
    total_tokens = _safe_int(bd, "totalTokens", "total_tokens")
    if total_tokens == 0:
        total_tokens = _calc_total_tokens(
            input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
        )
    total_cost = _safe_float(bd, "cost", "totalCost", "costUSD")

    return {
        "record_date": record_date,
        "source": agent,
        "tool_id": agent,
        "tool_name": AGENT_DISPLAY_NAMES.get(agent, agent),
        "model": model_name,
        "model_display_name": model_name,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_tokens": cache_creation_tokens,
        "cache_read_tokens": cache_read_tokens,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "source_raw": "ccusage-agent-daily",
    }


def _parse_agent_daily(agent: str, daily: list[dict]) -> list[dict]:
    """解析单个 agent 的 daily 明细为 (date, model) 记录。

    直接使用 ccusage <agent> daily 返回的模型级明细（modelBreakdowns
    或 models 字典），每条记录天然归属该 agent，从根本上避免多 agent
    同日共用同一模型时"推断归属"造成的用量丢失（曾导致 opencode 与
    claude 共用 deepseek-v4-pro 时 opencode 数据全部被计入 claude）。

    Returns:
        list of dict, 每条含 record_date, source, model, 4 个 token 字段, total_cost 等
    """
    results = []
    for day in daily:
        period = _get_date_key(day)
        if not period:
            continue
        try:
            record_date = date.fromisoformat(period)
        except (ValueError, TypeError):
            continue

        breakdowns = day.get("modelBreakdowns") or []
        if breakdowns:
            for bd in breakdowns:
                model_name = bd.get("modelName") or bd.get("model") or "_unknown"
                results.append(_build_agent_record(agent, record_date, model_name, bd))
        else:
            # codex 等 agent 使用 models 字典 {model: {input, output, ...}}
            models = day.get("models") or {}
            for model_name, md in models.items():
                if not isinstance(md, dict):
                    continue
                results.append(_build_agent_record(agent, record_date, model_name, md))

    return results


def _fetch_ccusage_v2_records(since_date, until_date) -> dict:
    """v2: 仅执行 ccusage 子进程抓取与解析（慢操作，不持有数据库连接）。

    将耗时的 ccusage CLI 子进程调用与数据库写入解耦，避免后台同步在抓取期间
    长时间占用连接池连接。

    Returns:
        {"records": list[dict], "errors": list[dict]}
        records 为待写入的记录列表；errors 为抓取阶段的结构化错误。
    """
    from app.utils.usage_fetcher_v2 import UsageFetcherV2

    since_str = since_date.isoformat() if hasattr(since_date, "isoformat") else str(since_date)
    until_str = until_date.isoformat() if hasattr(until_date, "isoformat") else str(until_date)

    errors: list[dict] = []

    daily_result = UsageFetcherV2.fetch_ccusage_daily(since=since_str, until=until_str)
    if "error" in daily_result:
        logger.warning(f"[ccusage-v2] daily 拉取失败: {daily_result['error']}")
        return {
            "records": [],
            "errors": [
                {
                    "source": "ccusage-v2:daily",
                    "error": daily_result["error"],
                    "error_code": daily_result.get("error_code"),
                    "remediation": daily_result.get("remediation"),
                    "details": daily_result.get("details") or {},
                }
            ],
        }

    daily_list = daily_result.get("daily", [])
    if not daily_list:
        logger.info(f"[ccusage-v2] {since_str} ~ {until_str} 无数据")
        return {"records": [], "errors": []}

    # 合并 daily 仅用于发现当日有哪些 agent 有数据
    all_agents: set[str] = set()
    for day in daily_list:
        meta = day.get("metadata", {}) or {}
        for a in meta.get("agents", []) or []:
            all_agents.add(a)

    if not all_agents:
        logger.info("[ccusage-v2] 合并 daily 未发现任何 agent")
        return {"records": [], "errors": []}

    # 每个 agent 直接使用自己的 daily 模型明细生成记录，不做归属推断
    records: list[dict] = []
    errors: list[dict] = []
    for agent in sorted(all_agents):
        agent_result = UsageFetcherV2.fetch_ccusage_agent_daily(
            agent=agent, since=since_str, until=until_str
        )
        if "error" in agent_result:
            logger.warning(f"[ccusage-v2] {agent} daily 拉取失败: {agent_result['error']}")
            errors.append(
                {
                    "source": f"ccusage-v2:{agent}",
                    "error": agent_result["error"],
                    "error_code": agent_result.get("error_code"),
                    "remediation": agent_result.get("remediation"),
                    "details": agent_result.get("details") or {},
                }
            )
            continue
        agent_daily = agent_result.get("daily") or []
        records.extend(_parse_agent_daily(agent, agent_daily))

    return {"records": records, "errors": errors}


def _write_ccusage_v2_records(
    db,
    user_id: str,
    device_id: str,
    device_name: str,
    records: list[dict],
) -> int:
    """v2: 将已抓取解析的记录写入数据库（快操作）。"""
    if not records:
        return 0

    # 先刷出 claude 遗留路径已 add 的 pending 记录，避免 v2 的"先查再插"
    # 查不到同键记录而重复插入，触发唯一约束冲突
    db.flush()

    # 按 agent 分组，分别 upsert，确保每个 Agent 有正确的 source/tool_id/tool_name
    from itertools import groupby

    records_sorted = sorted(records, key=lambda r: r["source"])
    total_count = 0
    for agent, group in groupby(records_sorted, key=lambda r: r["source"]):
        agent_records = list(group)
        count = _upsert_records(db, user_id, device_id, agent, agent_records, device_name)
        total_count += count
        logger.info(f"[ccusage-v2] {agent}: 同步 {count} 条")

    logger.info(f"[ccusage-v2] 总计同步 {total_count} 条")
    return total_count


def _run_ccusage_v2_sync(
    db,
    user_id: str,
    device_id: str,
    device_name: str,
    since_date,
    until_date,
) -> dict:
    """v2: ccusage 统一数据源同步（抓取 + 写入）。

    保留给 scheduler / 手动端点等直接传入 db 的调用方使用。后台同步走
    sync_token_usage 中拆分后的「先抓取后写入」流程，不再经由此函数。

    Returns:
        {"count": int, "errors": list[dict]}
        errors 中每个元素为 {"source": "...", "error": "...", "error_code": "...",
                              "remediation": "...", "details": {...}}
    """
    fetched = _fetch_ccusage_v2_records(since_date, until_date)
    records = fetched["records"]
    errors = fetched["errors"]

    total_count = _write_ccusage_v2_records(
        db, user_id, device_id, device_name, records
    )
    return {"count": total_count, "errors": errors}


def sync_token_usage_v2(
    db,
    user_id: str,
    device_id: str,
    device_name: str,
    since: str,
    until: str,
) -> dict:
    """公开 API：v2 ccusage 同步入口，供 scheduler 和手动端点使用。

    Returns:
        {"count": int, "errors": list[dict]}
    """
    since_date = date.fromisoformat(since)
    until_date = date.fromisoformat(until)
    return _run_ccusage_v2_sync(
        db=db,
        user_id=user_id,
        device_id=device_id,
        device_name=device_name,
        since_date=since_date,
        until_date=until_date,
    )

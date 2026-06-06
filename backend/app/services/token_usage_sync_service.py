"""Token Usage 增量同步服务 — 从 CLI 工具获取数据并写入数据库"""

import logging
from datetime import datetime, timedelta, date
from typing import Optional

from app.models.base import SessionLocal
from app.models.token_usage_models import TokenUsageRecord, TokenUsageSyncLog, DeviceRegistry
from app.utils.usage_fetcher import UsageFetcher
from app.utils.device_id import get_device_id, get_device_display_name

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
                default_display_name=device_name,
            ))
            db.commit()
        elif not existing.default_display_name:
            # 旧设备没有 default_display_name，补填
            existing.default_display_name = device_name
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
                count = _upsert_records(
                    db,
                    user_id,
                    device_id,
                    source_name,
                    parsed,
                    device_name,
                )
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

    # V2: ccusage 统一数据源
    try:
        v2_count = _run_ccusage_v2_sync(
            db, user_id, device_id, device_name, since_date, until_date
        )
        if v2_count > 0:
            result["ccusage_records"] = v2_count
            result["total_records"] += v2_count
    except Exception as e:
        logger.error(f"[ccusage-v2] 同步失败: {e}", exc_info=True)
        result["errors"].append(f"ccusage-v2: {e}")

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

# Agent 优先级（用于模型归属歧义时的 tie-breaker）
AGENT_PRIORITY = [
    "claude", "opencode", "openclaw", "codex", "amp",
    "droid", "codebuff", "hermes", "pi", "goose",
    "kilo", "copilot", "gemini", "kimi", "qwen",
]

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
    "other": "Other",
}


def _infer_agent(
    model_name: str,
    date_str: str,
    agent_models_dict: dict,
) -> str:
    """根据模型名 + 当日各 agent 的 modelsUsed 字典推断归属。

    agent_models_dict 形如:
    {
        "2026-06-05": {
            "claude": {"claude-opus-4-8", "gpt-5.5", ...},
            "opencode": {"minimax-m3-free", "qwen3.6-plus", ...},
        },
    }

    规则:
    1. 模型在当日某 agent 的 modelsUsed 中 → 归属该 agent
    2. 多个 agent 都含该模型（歧义）→ 按 AGENT_PRIORITY 选最高优先级
    3. 都不含 → "other"（兜底，WARNING 日志）
    """
    day_agents = agent_models_dict.get(date_str, {})
    candidates = [agent for agent, models in day_agents.items() if model_name in models]
    if not candidates:
        return "other"
    for priority_agent in AGENT_PRIORITY:
        if priority_agent in candidates:
            return priority_agent
    return candidates[0]


def _parse_ccusage_records(
    daily: list[dict],
    agent_models_dict: dict,
) -> list[dict]:
    """解析 ccusage daily JSON 为 (date, agent, model) 三元组记录。

    Args:
        daily: ccusage daily --json 的 daily 数组
        agent_models_dict: 来自 ccusage <agent> daily --json 的 {date: {agent: modelsUsed set}}

    Returns:
        list of dict, 每条含 record_date, source, model, 4 个 token 字段, total_cost 等
    """
    results = []
    for day in daily:
        period = day.get("period") or day.get("date")
        if not period:
            continue
        try:
            record_date = date.fromisoformat(period)
        except (ValueError, TypeError):
            continue

        breakdowns = day.get("modelBreakdowns") or []
        for bd in breakdowns:
            model_name = bd.get("modelName") or bd.get("model") or "_unknown"
            agent = _infer_agent(model_name, period, agent_models_dict)
            if agent == "other":
                logger.warning(
                    f"[ccusage] 模型 {model_name}（{period}）不在任何 per-agent modelsUsed 中，归 'other'"
                )

            input_tokens = _safe_int(bd, "inputTokens", "input_tokens")
            output_tokens = _safe_int(bd, "outputTokens", "output_tokens")
            cache_creation_tokens = _safe_int(bd, "cacheCreationTokens", "cache_creation_tokens")
            cache_read_tokens = _safe_int(bd, "cacheReadTokens", "cache_read_tokens")
            total_tokens = _calc_total_tokens(
                input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
            )
            total_cost = _safe_float(bd, "cost")

            results.append({
                "record_date": record_date,
                "source": agent,
                "tool_id": agent,
                "tool_name": AGENT_DISPLAY_NAMES.get(agent, "Other"),
                "model": model_name,
                "model_display_name": model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_tokens": cache_creation_tokens,
                "cache_read_tokens": cache_read_tokens,
                "total_tokens": total_tokens,
                "total_cost": total_cost,
                "source_raw": "ccusage-daily",
            })
    return results


def _run_ccusage_v2_sync(
    db,
    user_id: str,
    device_id: str,
    device_name: str,
    since_date,
    until_date,
) -> int:
    """v2: ccusage 统一数据源同步"""
    from app.utils.usage_fetcher_v2 import UsageFetcherV2

    since_str = since_date.isoformat() if hasattr(since_date, "isoformat") else str(since_date)
    until_str = until_date.isoformat() if hasattr(until_date, "isoformat") else str(until_date)

    daily_result = UsageFetcherV2.fetch_ccusage_daily(since=since_str, until=until_str)
    if "error" in daily_result:
        logger.warning(f"[ccusage-v2] daily 拉取失败: {daily_result['error']}")
        return 0

    daily_list = daily_result.get("daily", [])
    if not daily_list:
        logger.info(f"[ccusage-v2] {since_str} ~ {until_str} 无数据")
        return 0

    all_agents: set[str] = set()
    for day in daily_list:
        meta = day.get("metadata", {}) or {}
        for a in meta.get("agents", []) or []:
            all_agents.add(a)

    agent_models_dict: dict[str, dict[str, set[str]]] = {}
    for agent in sorted(all_agents):
        agent_result = UsageFetcherV2.fetch_ccusage_agent_daily(
            agent=agent, since=since_str, until=until_str
        )
        if "error" in agent_result:
            logger.warning(f"[ccusage-v2] {agent} daily 拉取失败: {agent_result['error']}")
            continue
        for day in (agent_result.get("daily") or []):
            date_key = day.get("date")
            if not date_key:
                continue
            agent_models_dict.setdefault(date_key, {}).setdefault(agent, set()).update(
                day.get("modelsUsed") or []
            )

    records = _parse_ccusage_records(daily_list, agent_models_dict)
    if not records:
        logger.info(f"[ccusage-v2] 解析后 0 条记录（{since_str} ~ {until_str}）")
        return 0

    # 按 agent 分组，分别 upsert，确保每个 Agent 有正确的 source/tool_id/tool_name
    from itertools import groupby

    records_sorted = sorted(records, key=lambda r: r["source"])
    total_count = 0
    for agent, group in groupby(records_sorted, key=lambda r: r["source"]):
        agent_records = list(group)
        count = _upsert_records(db, user_id, device_id, agent, agent_records, device_name)
        total_count += count
        logger.info(f"[ccusage-v2] {agent}: 同步 {count} 条")

    logger.info(f"[ccusage-v2] {since_str} ~ {until_str} 总计同步 {total_count} 条")
    return total_count


def sync_token_usage_v2(
    db,
    user_id: str,
    device_id: str,
    device_name: str,
    since: str,
    until: str,
) -> int:
    """公开 API：v2 ccusage 同步入口，供 scheduler 和手动端点使用。"""
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

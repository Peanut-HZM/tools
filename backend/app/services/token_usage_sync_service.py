"""Token Usage 增量同步服务 — 从 CLI 工具获取数据并写入数据库"""

import logging
from contextlib import contextmanager
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


# source → tool 映射表（模块级常量，供多处引用，避免硬编码 source 列表）
SOURCE_TOOL_MAPPING: dict[str, dict] = {
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
    "zcode": {"tool_id": "zcode", "tool_name": "ZCode"},
    "minimax": {"tool_id": "minimax", "tool_name": "MiniMax Code"},
}

# 已迁移到原生读取器的 source（与 ccusage 的 agent id 完全一致，
# 因此切换期间写入同一唯一键，不会产生重复统计）
NATIVE_READER_SOURCES: tuple[str, ...] = (
    "claude",
    "codex",
    "copilot",
    "kimi",
    "zcode",
    "openclaw",
    "opencode",
)

# 无 ccusage 对应实现、始终由原生读取器提供的 source
NATIVE_ONLY_SOURCES: tuple[str, ...] = ("minimax",)

# ccusage 能够提供数据的 source 全集（= SOURCE_TOOL_MAPPING 的 key 去掉独占来源）。
# 用于在全原生模式下检查覆盖度：没有原生读取器的 source 会被明确列出，
# 而不是静默丢数据。
CCUSAGE_CAPABLE_SOURCES: tuple[str, ...] = tuple(
    source for source in SOURCE_TOOL_MAPPING if source not in NATIVE_ONLY_SOURCES
)


def _map_source_to_tool(source: str) -> dict:
    source_value = source or "unknown"
    return SOURCE_TOOL_MAPPING.get(
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


def _native_readers_mode() -> str:
    """读取原生读取器模式配置。

    Returns:
        ``off`` / ``shadow`` / ``on`` / ``native``；配置非法时回退为 ``off``（最保守）。

        - ``off``    ：ccusage 采集写库；原生读取器只负责无 ccusage 对应实现的来源
        - ``shadow`` ：同 off，额外做逐日对账观测
        - ``on``     ：已迁移 source 由原生写库，其余仍走 ccusage
        - ``native`` ：全原生，不调用任何 ccusage 子进程
    """
    from app.config.config import settings

    mode = str(getattr(settings, "TOKEN_USAGE_NATIVE_READERS_MODE", "off") or "off").lower().strip()
    if mode not in ("off", "shadow", "on", "native"):
        logger.warning(
            "[native-readers] 未知的 TOKEN_USAGE_NATIVE_READERS_MODE=%r，回退为 off",
            mode,
        )
        return "off"
    return mode


def _log_uncovered_sources(result: dict) -> None:
    """全原生模式下检查 source 覆盖度，明确列出没有原生读取器的 source。

    全原生（native）模式不调用 ccusage，因此 ccusage 能采集但没有原生读取器
    实现的 source 会采集不到。这里把缺口显式记进 errors 与日志，
    避免出现"看起来同步成功、实际少了某类数据"的静默丢失。
    """
    try:
        from app.utils.agent_readers import READERS
    except Exception:  # pragma: no cover - 读取器注册表不可用时不影响主流程
        return

    uncovered = [s for s in CCUSAGE_CAPABLE_SOURCES if s not in READERS]
    if not uncovered:
        return

    logger.warning(
        "[native-readers] 全原生模式：以下 source 尚无原生读取器，本轮不会采集: %s",
        ", ".join(uncovered),
    )
    result["errors"].append({
        "source": "native-readers",
        "error": f"全原生模式下以下 source 无原生读取器，未采集: {', '.join(uncovered)}",
        "error_code": "SOURCE_NOT_COVERED",
        "remediation": (
            "为这些 source 实现原生读取器；"
            "或改用 TOKEN_USAGE_NATIVE_READERS_MODE=on 保留 ccusage 兜底"
        ),
        "details": {"uncovered_sources": uncovered},
    })


@contextmanager
def native_readers_mode_override(mode: str):
    """临时覆盖原生读取器模式（供脚本按固定口径回填使用）。

    ``_native_readers_mode()`` 每次调用都从 settings 读取，因此覆盖 settings
    即可让单次同步按指定口径执行，退出时恢复原值。
    """
    from app.config.config import settings

    previous = settings.TOKEN_USAGE_NATIVE_READERS_MODE
    settings.TOKEN_USAGE_NATIVE_READERS_MODE = mode
    try:
        yield mode
    finally:
        settings.TOKEN_USAGE_NATIVE_READERS_MODE = previous


def _fetch_native_records(since_date, until_date, only=None) -> dict:
    """抓取原生读取器数据。

    Args:
        since_date: 起始日期（含）。
        until_date: 结束日期（含）。
        only: 仅抓取这些 source；为空表示全部已登记读取器。

    Returns:
        ``{"records": [...], "errors": [...], "sources": [...]}``
    """
    from app.utils.agent_readers import read_all_agents

    return read_all_agents(since_date, until_date, only=only)


def _write_native_records(
    db,
    user_id: str,
    device_id: str,
    device_name: str,
    records: list[dict],
) -> int:
    """写入原生读取器记录，按 source 分组 upsert。

    source id 与 ccusage 完全一致，因此与 ccusage 写入的是同一唯一键，
    切换期间不会出现重复行（只会互相覆盖）。
    """
    from itertools import groupby

    if not records:
        return 0

    db.flush()

    records_sorted = sorted(records, key=lambda r: r["source"])
    total_count = 0
    for source, group in groupby(records_sorted, key=lambda r: r["source"]):
        source_records = list(group)
        count = _upsert_records(
            db, user_id, device_id, source, source_records, device_name
        )
        total_count += count
        logger.info(f"[native-readers] {source}: 同步 {count} 条")

    logger.info(f"[native-readers] 总计同步 {total_count} 条")
    return total_count


def _compare_native_with_ccusage(
    native_records: list[dict],
    ccusage_records: list[dict],
) -> list[dict]:
    """对比原生读取器与 ccusage 的 (日期, 模型) token 明细，返回差异列表。

    仅用于 shadow 模式的对账观测，不影响写库。
    """
    def _index(rows: list[dict]) -> dict:
        result: dict[tuple[str, str], list[int]] = {}
        for row in rows:
            key = (str(row["record_date"]), row["model"])
            bucket = result.setdefault(key, [0, 0, 0, 0, 0])
            bucket[0] += row.get("input_tokens", 0)
            bucket[1] += row.get("output_tokens", 0)
            bucket[2] += row.get("cache_creation_tokens", 0)
            bucket[3] += row.get("cache_read_tokens", 0)
            bucket[4] += row.get("total_tokens", 0)
        return result

    native_index = _index(native_records)
    ccusage_index = _index(ccusage_records)

    differences: list[dict] = []
    for key in sorted(set(native_index) | set(ccusage_index)):
        left = native_index.get(key)
        right = ccusage_index.get(key)
        if left != right:
            differences.append(
                {
                    "record_date": key[0],
                    "model": key[1],
                    "native": left,
                    "ccusage": right,
                }
            )
    return differences


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

    # 模式必须在抓取阶段之前确定：native 模式下不调用任何 ccusage 子进程
    native_mode = _native_readers_mode()
    use_ccusage = native_mode != "native"

    # ===== 阶段一：抓取数据（慢操作：ccusage / claude CLI 子进程，全程不持有数据库连接）=====
    # 将耗时的子进程抓取与数据库写入解耦，避免后台同步在抓取期间长时间占用连接池连接，
    # 进而导致前端接口因 "connection pool exhausted" 长时间 Pending。

    # claude 源（v2 流程已覆盖 opencode，此处仅保留 claude 以防降级）
    claude_parsed: list[dict] = []
    claude_fetch_error: Optional[Exception] = None
    if not use_ccusage:
        logger.info("[native-readers] 模式=native，跳过 ccusage 抓取（全部由原生读取器供数）")
        _log_uncovered_sources(result)
    else:
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
    if use_ccusage:
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

    # zcode 数据源抓取（从本地 SQLite 读取）
    zcode_records: list[dict] = []
    try:
        from app.utils.zcode_usage_reader import fetch_zcode_records
        zcode_result = fetch_zcode_records(since_date, until_date)
        zcode_records = zcode_result["records"]
        # 透传结构化错误（含 candidates_checked 等 details）
        for err in zcode_result["errors"]:
            # 给 zcode 错误的 details 补 source_raw / db_path 便于排查
            if err.get("error_code") == "DB_NOT_FOUND":
                details = err.setdefault("details", {})
                details.setdefault("source", "zcode:path_discovery")
            result["errors"].append(err)
    except Exception as e:
        logger.error(f"[zcode] 抓取失败: {e}", exc_info=True)
        result["errors"].append({
            "source": "zcode",
            "error": f"zcode: {str(e)}",
            "error_code": "ZCODE_FETCH_ERROR",
            "remediation": "请检查 ZCode 安装是否完整",
            "details": {"exception": str(e)},
        })

    # ===== 阶段二：写入数据库（快操作，仅短暂持有连接池连接）=====

    # 原生读取器抓取（替代 / 对账 ccusage）
    native_records: list[dict] = []
    if native_mode != "off":
        # on / shadow / native 都跑全部已登记的原生读取器
        native_targets = None
    else:
        # off 模式只抓取"无 ccusage 对应实现"的来源（当前为 MiniMax Code），
        # 其余 Agent 仍由 ccusage 负责，行为与改造前保持一致
        native_targets = list(NATIVE_ONLY_SOURCES)

    try:
        native_result = _fetch_native_records(since_date, until_date, only=native_targets)
        native_records = native_result["records"]
        result["errors"].extend(native_result["errors"])
        logger.info(
            "[native-readers] 模式=%s，读取 %s 条记录，来源: %s",
            native_mode,
            len(native_records),
            ", ".join(native_result["sources"]) or "无",
        )
    except Exception as e:
        logger.error(f"[native-readers] 抓取失败: {e}", exc_info=True)
        result["errors"].append({
            "source": "native-readers",
            "error": f"native-readers: {str(e)}",
            "error_code": "NATIVE_FETCH_ERROR",
            "remediation": "请检查本地 Agent 数据目录权限",
            "details": {"exception": str(e)},
        })

    db = SessionLocal()

    def _safe_rollback(reason: str) -> None:
        """在任何 except 块中调用，确保 session 干净后才放回连接池。

        关键：不 rollback 会让 PostgreSQL 连接保持 transaction aborted 状态，
        下次同连接被 request handler 复用时，所有 ORM 属性访问都会返回列键
        字符串（如 'token_usage_records_id'）而非真实值，导致 500。
        """
        try:
            db.rollback()
        except Exception as rb_exc:
            logger.warning("[sync_token_usage] rollback 失败 (%s): %s", reason, rb_exc)

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
        _safe_rollback("设备注册失败")

    try:
        # 写入 claude 记录（数据已在阶段一抓取完成）
        if claude_fetch_error is not None:
            # 抓取阶段已失败，补记一条失败的同步日志
            try:
                _log_sync(db, user_id, device_id, "claude", "failed", 0, str(claude_fetch_error))
            except Exception:
                pass
        elif claude_parsed and native_mode not in ("on", "native"):
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
                _safe_rollback("claude 写入失败")
                try:
                    _log_sync(db, user_id, device_id, "claude", "failed", 0, str(e))
                except Exception:
                    pass

        # 写入 ccusage v2 记录（数据已在阶段一抓取完成）
        # 模式为 on 时，已迁移到原生读取器的 source 不再由 ccusage 写入，
        # 避免同一 (source, date, model) 被写两遍
        # 模式为 native 时完全不写 ccusage 数据（连抓取都不会执行）
        if use_ccusage:
            ccusage_excluded = set(NATIVE_READER_SOURCES) if native_mode == "on" else set()
            try:
                v2_count = _write_ccusage_v2_records(
                    db,
                    user_id,
                    device_id,
                    device_name,
                    ccusage_records,
                    exclude_sources=ccusage_excluded,
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
                _safe_rollback("ccusage-v2 写入失败")

        # 写入原生读取器记录
        # - on    ：写入已迁移的 source（claude/codex/kimi/zcode）+ 独占 source（minimax）
        # - native：写入全部原生读取器产出的 source
        # - off/shadow：仅写入独占 source（minimax），迁移过的 source 仍由 ccusage 负责
        native_to_write: list[dict] = []
        if native_records:
            if native_mode in ("on", "native"):
                native_to_write = native_records
            else:
                native_to_write = [
                    r for r in native_records if r.get("source") in NATIVE_ONLY_SOURCES
                ]
        if native_to_write:
            try:
                native_count = _write_native_records(
                    db, user_id, device_id, device_name, native_to_write
                )
                if native_count > 0:
                    result["native_records"] = native_count
                    result["total_records"] += native_count
                    for source in sorted({r["source"] for r in native_to_write}):
                        if source not in result["sources_synced"]:
                            result["sources_synced"].append(source)
                        _log_sync(
                            db, user_id, device_id, source, "success", native_count
                        )
            except Exception as e:
                logger.error(f"[native-readers] 写入失败: {e}", exc_info=True)
                result["errors"].append({
                    "source": "native-readers",
                    "error": f"native-readers: {str(e)}",
                    "error_code": "DB_WRITE_ERROR",
                    "remediation": "请检查数据库连接",
                    "details": {"exception": str(e)},
                })
                _safe_rollback("native-readers 写入失败")

        # 安全兜底：某个已迁移的 source 若原生读取器完全没有产出数据
        # （例如本地数据目录被清理、读取器异常），退回 ccusage / 既有实现，
        # 避免该 source 在本次同步后"消失"。原生数据已存在时不写入，
        # 以保证原生口径（与 ccusage 20.0.44 对账零差异）不被覆盖。
        if native_mode == "on":
            native_sources = {r["source"] for r in native_to_write}
            missing_native = [s for s in NATIVE_READER_SOURCES if s not in native_sources]
            if missing_native:
                fallback_rows = [
                    r for r in ccusage_records if r.get("source") in missing_native
                ]
                if not fallback_rows and "zcode" in missing_native:
                    fallback_rows = list(zcode_records)
                if not fallback_rows and "claude" in missing_native:
                    fallback_rows = list(claude_parsed)
                if fallback_rows:
                    try:
                        fb_count = _write_native_records(
                            db, user_id, device_id, device_name, fallback_rows
                        )
                        logger.warning(
                            "[native-readers] 以下 source 原生读取无数据，已回退 ccusage/既有实现: %s（写入 %s 条）",
                            missing_native,
                            fb_count,
                        )
                        result["total_records"] += fb_count
                    except Exception as e:
                        logger.error(f"[native-readers] 回退写入失败: {e}", exc_info=True)
                        _safe_rollback("native-readers 回退写入失败")

        # shadow 模式：对比原生读取器与 ccusage 的差异（仅观测，不影响写库）
        # 注意：ccusage 抓取失败时 ccusage_records 为空，此时对比结果全是
        # "仅原生有"，属于假阳性，必须跳过并给出明确告警。
        if native_mode == "shadow" and native_records:
            if not ccusage_records:
                logger.warning(
                    "[native-readers] shadow 对账跳过：ccusage 未取到任何数据，"
                    "对比结果不可信"
                )
                result["native_vs_ccusage_differences"] = None
            else:
                try:
                    migrated = set(NATIVE_READER_SOURCES)
                    differences = _compare_native_with_ccusage(
                        [r for r in native_records if r.get("source") in migrated],
                        [r for r in ccusage_records if r.get("source") in migrated],
                    )
                    if differences:
                        logger.warning(
                            "[native-readers] 与 ccusage 存在 %s 处差异（前 5 条）: %s",
                            len(differences),
                            differences[:5],
                        )
                        result["native_vs_ccusage_differences"] = len(differences)
                    else:
                        logger.info("[native-readers] 与 ccusage 逐日对账：零差异")
                except Exception as e:
                    logger.error(f"[native-readers] 对账失败: {e}", exc_info=True)

        # 写入 zcode 记录（从本地 SQLite 读取，数据已在阶段一抓取完成）
        # 模式为 on/native 时 zcode 由原生读取器写入，此处跳过，避免重复写入
        if zcode_records and native_mode not in ("on", "native"):
            try:
                zcode_count = _upsert_records(
                    db, user_id, device_id, "zcode", zcode_records, device_name
                )
                if zcode_count > 0:
                    result["sources_synced"].append("zcode")
                    result["total_records"] += zcode_count
                    _log_sync(db, user_id, device_id, "zcode", "success", zcode_count)
                    logger.info(f"[zcode] 同步 {zcode_count} 条记录到数据库")
            except Exception as e:
                logger.error(f"[zcode] 写入失败: {e}", exc_info=True)
                result["errors"].append({
                    "source": "zcode",
                    "error": f"zcode: {str(e)}",
                    "error_code": "DB_WRITE_ERROR",
                    "remediation": "请检查数据库连接",
                    "details": {"exception": str(e)},
                })
                _safe_rollback("zcode 写入失败")
                try:
                    _log_sync(db, user_id, device_id, "zcode", "failed", 0, str(e))
                except Exception:
                    pass

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
            # SessionLocal 配置了 autoflush=False，同一批同步里后续相同
            # (record_date, model) 的记录查询不到刚 add 的行（v2 zcode 与
            # 本地 zcode 读取器就可能各产出一条同 key 记录），最终 commit 时
            # 两条一起 INSERT 触发唯一约束冲突。这里立即 flush，保证后续
            # 查询能看到已插入的行并走 UPDATE 分支。
            db.flush()
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
    "zcode": "ZCode",
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
    exclude_sources: Optional[set[str]] = None,
) -> int:
    """v2: 将已抓取解析的记录写入数据库（快操作）。

    Args:
        exclude_sources: 需要跳过的 source 集合（已由原生读取器接管的来源），
            避免同一次同步里同一个 (source, date, model) 被写两遍。
    """
    if exclude_sources:
        records = [r for r in records if r.get("source") not in exclude_sources]
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

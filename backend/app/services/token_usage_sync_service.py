"""Token Usage 增量同步服务 — 从本机 Agent 数据目录采集并写入数据库"""

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
from app.utils.device_id import get_device_id, get_device_display_name, get_device_fingerprint

logger = logging.getLogger(__name__)


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

# 已由原生读取器覆盖的 source（source id 与历史 ccusage agent id 保持一致，
# 因此历史数据与原生数据写入同一唯一键，不会产生重复统计）
NATIVE_READER_SOURCES: tuple[str, ...] = (
    "claude",
    "codex",
    "copilot",
    "kimi",
    "zcode",
    "openclaw",
    "opencode",
)

# 已知 source 全集（= SOURCE_TOOL_MAPPING 的 key）。
# 用于检查原生读取器的覆盖度：没有原生读取器的 source 会被明确列出，
# 而不是静默丢数据。
KNOWN_SOURCES: tuple[str, ...] = tuple(SOURCE_TOOL_MAPPING.keys())


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


def _log_uncovered_sources(result: dict) -> None:
    """检查 source 覆盖度，明确列出没有原生读取器的 source。

    采集只走原生读取器，因此没有原生读取器实现的 source 采集不到。
    这里把缺口显式记进 errors 与日志，避免出现"看起来同步成功、实际少了
    某类数据"的静默丢失。
    """
    try:
        from app.utils.agent_readers import READERS
    except Exception:  # pragma: no cover - 读取器注册表不可用时不影响主流程
        return

    uncovered = [s for s in KNOWN_SOURCES if s not in READERS]
    if not uncovered:
        return

    logger.warning(
        "[native-readers] 以下 source 尚无原生读取器，本轮不会采集: %s",
        ", ".join(uncovered),
    )
    result["errors"].append({
        "source": "native-readers",
        "error": f"以下 source 无原生读取器，未采集: {', '.join(uncovered)}",
        "error_code": "SOURCE_NOT_COVERED",
        "remediation": "为这些 source 实现原生读取器后登记到 READERS",
        "details": {"uncovered_sources": uncovered},
    })


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

    # ===== 阶段一：抓取数据（慢操作：本地文件 / SQLite 读取，全程不持有数据库连接）=====
    # 将耗时的抓取与数据库写入解耦，避免后台同步在抓取期间长时间占用连接池连接，
    # 进而导致前端接口因 "connection pool exhausted" 长时间 Pending。
    #
    # 数据全部来自本机 Agent 数据目录（原生读取器），不调用任何外部 CLI。

    # 没有原生读取器的来源必须显式暴露，不能静默丢数据
    _log_uncovered_sources(result)

    native_records: list[dict] = []
    try:
        native_result = _fetch_native_records(since_date, until_date)
        native_records = native_result["records"]
        result["errors"].extend(native_result["errors"])
        logger.info(
            "[native-readers] 读取 %s 条记录，来源: %s",
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
        # 写入原生读取器记录（唯一的数据来源）
        if native_records:
            try:
                native_count = _write_native_records(
                    db, user_id, device_id, device_name, native_records
                )
                if native_count > 0:
                    result["native_records"] = native_count
                    result["total_records"] += native_count
                    for source in sorted({r["source"] for r in native_records}):
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

        db.commit()

    except Exception as e:
        db.rollback()
        logger.error(f"数据库事务失败: {e}")
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

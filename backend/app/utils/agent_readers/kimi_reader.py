"""Kimi / Kimi Code 原生 Token 用量读取器

数据源：

- ``~/.kimi/sessions/**/*.jsonl``（Kimi CLI）
- ``~/.kimi-code/sessions/**/*.jsonl``（Kimi Code）
- ``KIMI_DATA_DIR`` 环境变量可覆盖（逗号分隔）

与 ccusage ``rust/adapters/kimi`` 对齐的关键点：

1. **文件布局**：只认名为 ``wire.jsonl`` 的文件，且相对 ``sessions/`` 的路径
   必须恰好 3 段（旧布局 ``<group>/<session>/wire.jsonl``）或 5 段
   （新布局 ``<ws>/<session>/agents/<agent>/wire.jsonl``）。
2. **新格式**（Kimi Code）：``type == "usage.record"`` 且 ``usageScope == "turn"``。
   ``usageScope`` 为 ``session`` 的是**累计值**，必须排除，否则会重复统计。
3. **旧格式**（Kimi CLI）：``message.type == "StatusUpdate"`` 且
   ``message.payload.token_usage`` 存在。
4. **字段**：``inputOther`` → input，``output`` → output，
   ``inputCacheRead`` → cache read，``inputCacheCreation`` → cache creation。
5. **时间戳**：新格式取顶层 ``time``（epoch 毫秒），旧格式取顶层 ``timestamp``
   （epoch 秒）。两者都没有时退回文件 mtime。
6. **模型**：取 ``model`` 字段并剥掉 ``kimi-code/`` 前缀，缺省为 ``kimi-for-coding``。
7. **去重**：key = session_id : message_id : timestamp : model : 四项 token。
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from app.utils.agent_readers.base import (
    AgentReadResult,
    aggregate_records,
    collect_files,
    env_path_list,
    epoch_ms_to_local_date,
    epoch_seconds_to_ms,
    iter_jsonl,
    lenient_obj,
    lenient_str,
    lenient_u64,
    real_home,
)

logger = logging.getLogger(__name__)

SOURCE = "kimi"

_DEFAULT_MODEL = "kimi-for-coding"
_WIRE_FILE_NAME = "wire.jsonl"


def _kimi_roots() -> list[Path]:
    """返回 Kimi 数据根目录（``~/.kimi`` 与 ``~/.kimi-code``）。"""
    configured = env_path_list("KIMI_DATA_DIR")
    if configured:
        return configured

    home = real_home()
    roots: list[Path] = []
    for name in (".kimi", ".kimi-code"):
        candidate = home / name
        if candidate.is_dir():
            roots.append(candidate)
    return roots


def _is_wire_file(sessions_dir: Path, file_path: Path) -> bool:
    """校验文件是否为受支持的 wire.jsonl 布局（3 段或 5 段）。"""
    if file_path.name != _WIRE_FILE_NAME:
        return False
    try:
        relative = file_path.relative_to(sessions_dir)
    except ValueError:
        return False
    depth = len(relative.parts)
    return depth in (3, 5)


def _file_mtime_ms(path: Path) -> int:
    try:
        return int(path.stat().st_mtime * 1000)
    except OSError:
        return 0


def _extract_model(record: dict) -> Optional[str]:
    """提取模型名并剥掉 ``kimi-code/`` 前缀。"""
    raw = lenient_str(record.get("model"))
    if not raw:
        return None
    if raw.startswith("kimi-code/"):
        raw = raw[len("kimi-code/") :]
    return raw or None


def read_kimi_records(since_date: date, until_date: date) -> AgentReadResult:
    """读取 Kimi / Kimi Code 的 Token 用量。

    Args:
        since_date: 起始日期（含）。
        until_date: 结束日期（含）。

    Returns:
        AgentReadResult：records 为按 (日期, 模型) 聚合后的记录。
    """
    result = AgentReadResult()
    roots = _kimi_roots()
    if not roots:
        return result

    since_str = since_date.isoformat()
    until_str = until_date.isoformat()
    rows: list[dict] = []
    seen: set[tuple] = set()
    file_count = 0

    for root in roots:
        sessions_dir = root / "sessions"
        if not sessions_dir.is_dir():
            continue
        for path in collect_files(sessions_dir, (".jsonl",)):
            if not _is_wire_file(sessions_dir, path):
                continue
            file_count += 1
            fallback_ts = _file_mtime_ms(path)
            session_id = path.parent.name if path.parent.name != "agents" else path.parent.parent.name

            for record in iter_jsonl(path):
                usage = None
                timestamp_ms: Optional[int] = None
                message_id: Optional[str] = None
                model: Optional[str] = None

                record_type = record.get("type")
                if record_type == "usage.record":
                    # session 作用域是累计值，必须排除
                    if record.get("usageScope") != "turn":
                        continue
                    usage = lenient_obj(record.get("usage"))
                    if usage is None:
                        continue
                    raw_time = record.get("time")
                    if isinstance(raw_time, (int, float)) and raw_time > 0:
                        timestamp_ms = int(raw_time)
                    model = _extract_model(record)
                else:
                    message = lenient_obj(record.get("message"))
                    if message is None or message.get("type") != "StatusUpdate":
                        continue
                    payload = lenient_obj(message.get("payload"))
                    if payload is None:
                        continue
                    usage = lenient_obj(payload.get("token_usage"))
                    if usage is None:
                        continue
                    raw_ts = record.get("timestamp")
                    if isinstance(raw_ts, (int, float)) and raw_ts > 0:
                        timestamp_ms = epoch_seconds_to_ms(float(raw_ts))
                    message_id = lenient_str(payload.get("message_id"))
                    model = _extract_model(record)

                if usage is None:
                    continue
                if timestamp_ms is None:
                    timestamp_ms = fallback_ts
                if timestamp_ms <= 0:
                    continue
                if not model:
                    model = _DEFAULT_MODEL

                record_day = epoch_ms_to_local_date(timestamp_ms)
                if not (since_str <= record_day <= until_str):
                    continue

                input_tokens = lenient_u64(usage.get("inputOther"))
                output_tokens = lenient_u64(usage.get("output"))
                cache_read = lenient_u64(usage.get("inputCacheRead"))
                cache_creation = lenient_u64(usage.get("inputCacheCreation"))
                total_tokens = lenient_u64(usage.get("total"))

                key = (
                    session_id,
                    message_id or "",
                    timestamp_ms,
                    model,
                    input_tokens,
                    output_tokens,
                    cache_creation,
                    cache_read,
                )
                if key in seen:
                    continue
                seen.add(key)

                rows.append(
                    {
                        "record_date": record_day,
                        "model": model,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cache_creation_tokens": cache_creation,
                        "cache_read_tokens": cache_read,
                        "extra_total_tokens": 0,
                        "total_cost": 0.0,
                        "_total": total_tokens,
                    }
                )

    # 来源自报 total 若大于四项之和，按 ccusage 口径补进 output / extra
    for row in rows:
        declared = row.pop("_total", 0)
        known = (
            row["input_tokens"]
            + row["output_tokens"]
            + row["cache_creation_tokens"]
            + row["cache_read_tokens"]
        )
        if declared > known:
            missing = declared - known
            if row["output_tokens"] == 0:
                row["output_tokens"] = missing
            else:
                row["extra_total_tokens"] = missing

    result.records = aggregate_records(rows, source=SOURCE, source_raw="kimi-wire")
    logger.info("[kimi] 原生读取 %s 个 wire.jsonl，聚合 %s 条记录", file_count, len(result.records))
    return result

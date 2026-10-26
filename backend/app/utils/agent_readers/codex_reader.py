"""Codex 原生 Token 用量读取器

数据源：``~/.codex/sessions/**/*.jsonl`` 与 ``~/.codex/archived_sessions/**/*.jsonl``
（``CODEX_HOME`` 可覆盖根目录）。

文件格式：Codex 较新版本会把会话记录写成 **zstd 压缩**的 ``*.jsonl.zst``，
较早版本是纯文本 ``*.jsonl``。两种都要读，否则在开启压缩的机器上会读到 0 条。
压缩文件由 ``base.iter_jsonl`` 自动识别并流式解压。

与 ccusage ``rust/adapters/codex`` 对齐的关键点：

1. **记录类型**：``type == "event_msg"`` 且 ``payload.type == "token_count"``。
2. **累计 vs 增量**（最关键）：Codex 同时提供
   ``info.last_token_usage``（本次调用）与 ``info.total_token_usage``（会话累计）。
   ccusage 的判定规则是：

   - 累计值发生变化 → 采用 ``last_token_usage``
   - 累计值未变化 → 用 ``total_token_usage − 上一次累计`` 求差

   直接采用 ``last_token_usage`` 会在累计未推进时重复计数，
   直接采用累计值则会把整个会话重复累加。
3. **input 含 cache**：``input_tokens`` **包含** ``cached_input_tokens``，
   需扣减后才能作为净输入；``cache_write_input_tokens`` 同理。
4. **reasoning ⊂ output**：`reasoning_output_tokens` 已包含在
   ``output_tokens`` 内，单独再加会重复统计。
5. **模型**：``payload.model`` → ``payload.model_name`` → ``payload.metadata.model``
   → ``info.model`` → ``info.model_name`` → ``info.metadata.model``
   → 最近一次 ``turn_context`` 的模型 → 兜底 ``gpt-5``。
6. **时间戳**：顶层 ``timestamp``，支持 ISO-8601 字符串或 epoch 数字
   （小于 1e10 视为秒，否则视为毫秒）。
7. **去重**：优先用 ``response_id``；没有时用
   (时间戳, 模型, 各 token 桶) 组合键。
"""

from __future__ import annotations

import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from app.utils.agent_readers.base import (
    AgentReadResult,
    aggregate_records,
    collect_files,
    epoch_ms_to_local_date,
    expand_user_path,
    iter_jsonl,
    lenient_obj,
    lenient_str,
    lenient_u64,
    parse_iso_timestamp_ms,
    real_home,
    split_inclusive_input,
)

logger = logging.getLogger(__name__)

SOURCE = "codex"

_FALLBACK_MODEL = "gpt-5"


def _codex_roots() -> list[Path]:
    """返回 Codex 根目录（``CODEX_HOME`` 优先）。"""
    configured = os.environ.get("CODEX_HOME", "")
    roots: list[Path] = []
    seen: set[str] = set()
    if configured.strip():
        for item in configured.split(","):
            item = item.strip()
            if not item:
                continue
            path = expand_user_path(item)
            key = os.path.normcase(str(path))
            if path.is_dir() and key not in seen:
                seen.add(key)
                roots.append(path)
        if roots:
            return roots
    home = real_home()
    candidate = home / ".codex"
    if candidate.is_dir():
        roots.append(candidate)
    return roots


def _source_dirs(root: Path) -> list[Path]:
    """返回 Codex 会话目录；两个子目录都不存在时回退到根目录本身。"""
    dirs = [root / "sessions", root / "archived_sessions"]
    existing = [d for d in dirs if d.is_dir()]
    if existing:
        return existing
    return [root] if root.is_dir() else []


def _parse_timestamp_ms(value) -> Optional[int]:
    """解析 Codex 时间戳：ISO 字符串或 epoch 数字（秒/毫秒自动判定）。"""
    if isinstance(value, str):
        parsed = parse_iso_timestamp_ms(value)
        if parsed is not None:
            return parsed
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if number <= 0:
            return None
        return int(number if number >= 10_000_000_000 else number * 1000)
    return None


def _model_candidates(payload: dict, info: dict) -> list[str]:
    """按 ccusage 的优先级收集候选模型名。"""
    candidates: list[str] = []
    for container, keys in (
        (payload, ("model", "model_name")),
        (info, ("model", "model_name")),
    ):
        for key in keys:
            value = lenient_str(container.get(key))
            if value:
                candidates.append(value)
                break
        if candidates:
            break
    metadata = lenient_obj(payload.get("metadata"))
    if metadata:
        value = lenient_str(metadata.get("model"))
        if value:
            candidates.append(value)
    info_metadata = lenient_obj(info.get("metadata"))
    if info_metadata:
        value = lenient_str(info_metadata.get("model"))
        if value:
            candidates.append(value)
    return candidates


def _subtract_cumulative(current: dict, previous: Optional[dict]) -> dict:
    """用累计值求差（饱和减法）。"""
    if not previous:
        return dict(current)
    result = {}
    for key, value in current.items():
        prev = previous.get(key, 0)
        result[key] = max(0, value - prev)
    return result


def read_codex_records(since_date: date, until_date: date) -> AgentReadResult:
    """读取 Codex 的 Token 用量。

    Args:
        since_date: 起始日期（含）。
        until_date: 结束日期（含）。

    Returns:
        AgentReadResult：records 为按 (日期, 模型) 聚合后的记录。
    """
    result = AgentReadResult()
    since_str = since_date.isoformat()
    until_str = until_date.isoformat()

    rows: list[dict] = []
    seen: set[tuple] = set()
    file_count = 0

    for root in _codex_roots():
        for source_dir in _source_dirs(root):
            for path in collect_files(source_dir, (".jsonl", ".jsonl.zst")):
                file_count += 1
                session_id = str(path.relative_to(source_dir)).replace("\\", "/")
                previous_total: Optional[dict] = None
                last_model: Optional[str] = None

                for record in iter_jsonl(path):
                    record_type = record.get("type")
                    payload = lenient_obj(record.get("payload"))
                    if payload is None:
                        continue

                    if record_type == "turn_context":
                        candidate = lenient_str(payload.get("model"))
                        if candidate:
                            last_model = candidate
                        continue

                    if record_type != "event_msg":
                        continue
                    if payload.get("type") != "token_count":
                        continue

                    info = lenient_obj(payload.get("info"))
                    if info is None:
                        continue

                    cumulative = lenient_obj(info.get("total_token_usage"))
                    last_usage = lenient_obj(info.get("last_token_usage"))

                    if cumulative is not None:
                        cumulative_norm = {
                            "input": lenient_u64(cumulative.get("input_tokens")),
                            "cached": lenient_u64(cumulative.get("cached_input_tokens")),
                            "cache_write": lenient_u64(
                                cumulative.get("cache_write_input_tokens")
                            ),
                            "output": lenient_u64(cumulative.get("output_tokens")),
                            "total": lenient_u64(cumulative.get("total_tokens")),
                        }
                        advanced = previous_total != cumulative_norm
                        if last_usage is not None and advanced:
                            raw = {
                                "input": lenient_u64(last_usage.get("input_tokens")),
                                "cached": lenient_u64(
                                    last_usage.get("cached_input_tokens")
                                ),
                                "cache_write": lenient_u64(
                                    last_usage.get("cache_write_input_tokens")
                                ),
                                "output": lenient_u64(last_usage.get("output_tokens")),
                                "total": lenient_u64(last_usage.get("total_tokens")),
                            }
                        else:
                            raw = _subtract_cumulative(cumulative_norm, previous_total)
                        previous_total = cumulative_norm
                    elif last_usage is not None:
                        raw = {
                            "input": lenient_u64(last_usage.get("input_tokens")),
                            "cached": lenient_u64(last_usage.get("cached_input_tokens")),
                            "cache_write": lenient_u64(
                                last_usage.get("cache_write_input_tokens")
                            ),
                            "output": lenient_u64(last_usage.get("output_tokens")),
                            "total": lenient_u64(last_usage.get("total_tokens")),
                        }
                    else:
                        continue

                    timestamp_ms = _parse_timestamp_ms(record.get("timestamp"))
                    if timestamp_ms is None:
                        continue

                    models = _model_candidates(payload, info)
                    model = models[0] if models else (last_model or _FALLBACK_MODEL)

                    net_input, cache_read, cache_creation = split_inclusive_input(
                        raw["input"], raw["cached"], raw["cache_write"]
                    )
                    output_tokens = raw["output"]

                    if net_input == 0 and output_tokens == 0 and cache_read == 0 and cache_creation == 0:
                        continue

                    response_id = lenient_str(payload.get("response_id"))
                    if response_id:
                        dedupe_key = ("response", response_id, model)
                    else:
                        dedupe_key = (
                            "usage",
                            timestamp_ms,
                            model,
                            net_input,
                            output_tokens,
                            cache_creation,
                            cache_read,
                        )
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)

                    record_day = epoch_ms_to_local_date(timestamp_ms)
                    if not (since_str <= record_day <= until_str):
                        continue

                    rows.append(
                        {
                            "record_date": record_day,
                            "model": model,
                            "input_tokens": net_input,
                            "output_tokens": output_tokens,
                            "cache_creation_tokens": cache_creation,
                            "cache_read_tokens": cache_read,
                            "extra_total_tokens": 0,
                            "total_cost": 0.0,
                            "_session": session_id,
                        }
                    )

    for row in rows:
        row.pop("_session", None)

    result.records = aggregate_records(rows, source=SOURCE, source_raw="codex-rollout")
    logger.info("[codex] 原生读取 %s 个文件，聚合 %s 条记录", file_count, len(result.records))
    return result

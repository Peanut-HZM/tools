"""Claude Code 原生 Token 用量读取器

数据源：``~/.claude/projects/**/*.jsonl``（可用 ``CLAUDE_CONFIG_DIR`` 覆盖）。

与 ccusage ``rust/adapters/claude`` 对齐的关键点：

1. **路径**：``~/.claude`` 与 ``$XDG_CONFIG_HOME/claude`` 两个根，只有存在
   ``projects/`` 子目录才算有效；``CLAUDE_CONFIG_DIR`` 逗号分隔并优先，
   指向 ``projects`` 本身时自动回退到其父目录。
2. **字段**（全部取自 ``message.usage``，snake_case）：
   - input ← ``input_tokens``
   - output ← ``output_tokens``
   - cache creation ← ``cache_creation_input_tokens``，但当存在
     ``cache_creation`` 结构化对象时改用
     ``ephemeral_5m_input_tokens + ephemeral_1h_input_tokens``
   - cache read ← ``cache_read_input_tokens``
   - total 不由来源提供，按四项求和
3. **模型** ``<synthetic>`` 丢弃；``message.model`` 为空丢弃。
4. **去重**（ccusage ``usage_dedupe_hash``）：
   - 有 ``requestId``：key = (message.id, requestId)
   - 无 ``requestId`` 且 message id 以 ``msg_``/``resp_`` 开头：
     key = (message.id, sessionId)
   - 无 ``requestId`` 且 message id 为其它形态：
     key = (message.id, sessionId, timestamp)
   - 冲突时**保留 token 总量最大的一条**（``should_replace_deduped_entry``：
     先比较四项之和，再比较是否非 sidechain，最后比较是否带 speed）
5. **sidechain 重放抑制**：sidechain 记录额外按 (message.id, sessionId)
   去重 —— Claude Code 会把 subagent 的消息按内容块拆成多行写入，
   这些行 message id 相同但时间戳不同，必须按 (message.id, sessionId)
   折叠，否则同一笔请求会被重复统计。
"""

from __future__ import annotations

import logging
import os
from datetime import date
from pathlib import Path
from typing import Any, Optional

from app.utils.agent_readers.base import (
    AgentReadResult,
    aggregate_records,
    collect_files,
    epoch_ms_to_local_date,
    iter_jsonl,
    lenient_obj,
    lenient_str,
    lenient_u64,
    parse_iso_timestamp_ms,
    real_home,
)

logger = logging.getLogger(__name__)

SOURCE = "claude"

# 这些字段若显式为 null 则整行作废（对齐 ccusage has_unsupported_null_field）
_NULL_FORBIDDEN_TOP = (
    "id",
    "cwd",
    "model",
    "speed",
    "costUSD",
    "version",
    "sessionId",
    "requestId",
    "isApiErrorMessage",
)
_NULL_FORBIDDEN_USAGE = (
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)


def _claude_roots() -> list[Path]:
    """返回 Claude 配置根目录列表（已去重、排序）。"""
    configured = os.environ.get("CLAUDE_CONFIG_DIR", "")
    roots: list[Path] = []
    seen: set[str] = set()

    def _add(path: Path) -> None:
        key = os.path.normcase(str(path))
        if path.is_dir() and key not in seen:
            seen.add(key)
            roots.append(path)

    if configured.strip():
        for item in configured.split(","):
            item = item.strip()
            if not item:
                continue
            path = Path(item).expanduser()
            # 允许直接指向 projects 目录，此时取其父目录作为配置根
            if path.name == "projects" and path.is_dir():
                path = path.parent
            _add(path)
        return roots

    home = real_home()
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    candidates = [home / ".claude"]
    if xdg:
        candidates.insert(0, Path(xdg).expanduser() / "claude")
    for candidate in candidates:
        _add(candidate)
    return roots


def _is_anthropic_message_id(message_id: Optional[str]) -> bool:
    """判断是否为 Anthropic 形态的 message id（msg_ / resp_ 前缀）。"""
    if not message_id:
        return False
    return message_id.startswith("msg_") or message_id.startswith("resp_")


def _cache_creation_tokens(usage: dict) -> int:
    """cache creation 计数：结构化对象优先，否则用扁平字段。"""
    breakdown = lenient_obj(usage.get("cache_creation"))
    if breakdown is not None:
        return lenient_u64(breakdown.get("ephemeral_5m_input_tokens")) + lenient_u64(
            breakdown.get("ephemeral_1h_input_tokens")
        )
    return lenient_u64(usage.get("cache_creation_input_tokens"))


def _has_forbidden_null(record: dict, usage: dict) -> bool:
    """命中 ccusage 的 null 字段拒绝规则则返回 True。"""
    for key in _NULL_FORBIDDEN_TOP:
        if key in record and record[key] is None:
            return True
    for key in _NULL_FORBIDDEN_USAGE:
        if key in usage and usage[key] is None:
            return True
    return False


def read_claude_records(since_date: date, until_date: date) -> AgentReadResult:
    """读取 Claude Code 的 Token 用量。

    Args:
        since_date: 起始日期（含）。
        until_date: 结束日期（含）。

    Returns:
        AgentReadResult：records 为按 (日期, 模型) 聚合后的记录。
    """
    result = AgentReadResult()
    files: list[Path] = []
    for root in _claude_roots():
        files.extend(collect_files(root / "projects", (".jsonl",)))

    if not files:
        return result

    # 主去重桶 + sidechain 重放桶，两者独立，冲突时保留 token 总量最大者
    main_best: dict[tuple, tuple] = {}
    sidechain_best: dict[tuple, tuple] = {}
    rows: list[dict] = []

    for path in files:
        for record in iter_jsonl(path):
            message = lenient_obj(record.get("message"))
            if message is None:
                continue
            usage = lenient_obj(message.get("usage"))
            if usage is None:
                continue
            if _has_forbidden_null(record, usage):
                continue

            model = lenient_str(message.get("model"))
            if not model or model == "<synthetic>":
                continue

            timestamp_ms = parse_iso_timestamp_ms(record.get("timestamp"))
            if timestamp_ms is None:
                continue
            record_day = epoch_ms_to_local_date(timestamp_ms)
            if not (since_date.isoformat() <= record_day <= until_date.isoformat()):
                continue

            message_id = message.get("id")
            request_id = record.get("requestId")
            session_id = record.get("sessionId")
            is_sidechain = bool(record.get("isSidechain"))

            input_tokens = lenient_u64(usage.get("input_tokens"))
            output_tokens = lenient_u64(usage.get("output_tokens"))
            cache_read = lenient_u64(usage.get("cache_read_input_tokens"))
            cache_creation = _cache_creation_tokens(usage)
            completeness = input_tokens + output_tokens + cache_creation + cache_read
            if completeness == 0:
                continue

            # 候选排序键：token 总量 → 非 sidechain → 带 speed
            candidate = (
                completeness,
                not is_sidechain,
                bool(usage.get("speed")),
            )
            payload = {
                "record_date": record_day,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_creation_tokens": cache_creation,
                "cache_read_tokens": cache_read,
                "extra_total_tokens": 0,
                "total_cost": 0.0,
            }

            if is_sidechain:
                key = ("sidechain", message_id, session_id)
                previous = sidechain_best.get(key)
                if previous is None or candidate > previous[0]:
                    sidechain_best[key] = (candidate, payload)
            else:
                if request_id:
                    key = ("request", message_id, request_id)
                elif _is_anthropic_message_id(
                    message_id if isinstance(message_id, str) else None
                ):
                    key = ("session", message_id, session_id)
                else:
                    key = (
                        "timestamp",
                        message_id,
                        session_id,
                        record.get("timestamp"),
                    )
                previous = main_best.get(key)
                if previous is None or candidate > previous[0]:
                    main_best[key] = (candidate, payload)

    for _candidate, payload in list(main_best.values()) + list(sidechain_best.values()):
        rows.append(payload)

    result.records = aggregate_records(rows, source=SOURCE, source_raw="claude-jsonl")
    logger.info(
        "[claude] 原生读取 %s 个文件，聚合 %s 条记录", len(files), len(result.records)
    )
    return result

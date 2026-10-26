"""GitHub Copilot CLI 原生 Token 用量读取器

数据源
------

1. **session-state**（主来源）：``~/.copilot/session-state/<session-id>/events.jsonl``
   只取 ``session-state`` 的**直接子目录**下的 ``events.jsonl``，不递归更深层
   （对齐 ccusage ``rust/adapters/copilot/paths.rs`` 只遍历一层 ``read_dir``）。
2. **OTEL**：``~/.copilot/otel/**/*.jsonl``（递归）。
3. **OTEL 单文件**：``COPILOT_OTEL_FILE_EXPORTER_PATH`` 环境变量指向的文件。

根目录由 ``COPILOT_HOME`` 决定（非空才生效），否则回退 ``~/.copilot``。
家目录用 ``base.real_home()`` 展开（**不能**用 ``Path.home()``：``config.py``
会把 ``HOME`` 覆盖成 ``backend/data/cache``）；环境变量里的 ``~`` 用
``base.expand_user_path()`` 展开（同样不能用 ``Path.expanduser()``）。

口径（对齐 ccusage **20.0.42** ``rust/adapters/copilot``）
---------------------------------------------------------

1. **只处理 ``type == "session.shutdown"`` 事件**。
   ``session.usage_checkpoint`` 只影响 credit 快照，不影响 token 总量，直接忽略。
2. **逐 model 产出一条 entry**：``data.modelMetrics`` 结构为
   ``{model: {requests: {count}, usage: {...}}}``。
3. **模型名归一** ``normalize_copilot_model``：先 trim，再去掉后缀
   ``-1m-internal``，否则去掉 ``-1m``。
4. **input 扣减**：Copilot 的 ``inputTokens`` **含 cache**，
   ``input = max(0, inputTokens - (cacheReadTokens + cacheWriteTokens))``。
5. ``output = outputTokens``、``cache_creation = cacheWriteTokens``、
   ``cache_read = cacheReadTokens``。
6. **reasoningTokens 单独记录，不计入 total**。ccusage 的 total 口径是
   ``input + output + cache_creation + cache_read + extra``，reasoning 既不进
   output 也不进 extra —— 本机 2026-05-04 的 total 就是
   ``31982 + 505 = 32487``（不含 reasoning 448）。
7. **去重键** ``session_state_dedup_key``：
   - 有 ``id`` → ``shutdown:{session_id}:{event_id}:{model}``
   - 无 ``id`` → ``shutdown:{session_id}:{timestamp}:{model}:{in}:{out}:{cr}:{cw}:{reasoning}:{count}``
     （此处用**原始** usage 值，而非扣减后的 input）
   同键只保留最后一条（旧条目 timestamp <= 新条目 timestamp 时用新条目替换）。
8. **差值（最关键）**：同一 ``(session_id, model)`` 的多条 shutdown 是**累计快照**，
   必须按 ``(timestamp, 原始顺序)`` 逐条减去前一条的用量（饱和减法），
   首条基线为 0。对齐 ccusage ``reconcile_session_state_entries`` +
   ``subtract_usage``。差值基线覆盖**全部** shutdown（含日期区间之外的），
   与 ccusage 一致：先做完整差值链，再按日期区间裁剪。
9. **全 0 且 ``requests.count == 0`` 的 model 直接跳过**（对齐 Rust 判断）。
10. **时间戳**用事件 ``timestamp``（严格 ISO-8601），归桶到**本机时区**自然日。

与 Rust 实现的已知差异
----------------------

- **credit gap 对账未实现**：ccusage 会把 session 级 ``totalNanoAiu`` 超出
  ``modelMetrics`` 的部分记为 ``unknown`` 模型的 cost-only 条目。该逻辑只影响
  **cost**，token 四桶全为 0；本读取器按任务约定 ``total_cost`` 恒为 0.0，
  故未实现。本机 4 条 shutdown 事件均无 ``totalNanoAiu``，该分支在此机器上
  不会产生任何差异。
- **OTEL 分支未做数值对账**：本机不存在 ``~/.copilot/otel/`` 目录，
  ``COPILOT_OTEL_FILE_EXPORTER_PATH`` 也未设置，**没有 OTEL 数据可用于对账**。
  OTEL 解析按 Rust ``parse_otel_file`` 逐条移植（来源识别、trace 上下文回填、
  重复 chat span 去重、跨来源抑制、dedup 键），但**其数值行为未与 ccusage
  做过实测比对**。OTEL 与 session-state 的相互对账
  （``otel_replacement_start`` / ``otel_after``）同理未实测。
- **畸形 modelMetrics 更宽容**：Rust 中 ``modelMetrics`` 里某个 model 的值不是
  对象时会导致整行反序列化失败（整行丢弃）；本实现只跳过该 model，保留同一
  事件里的其它 model。正常数据下无差异。
"""

from __future__ import annotations

import bisect
import logging
import os
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.utils.agent_readers.base import (
    AgentReadResult,
    aggregate_records,
    collect_files,
    date_range_to_ms_bounds,
    epoch_ms_to_local_date,
    expand_user_path,
    iter_jsonl,
    lenient_obj,
    lenient_str,
    lenient_u64,
    parse_iso_timestamp_ms,
    real_home,
)

logger = logging.getLogger(__name__)

# source id 必须与 ccusage 的 agent id 一致，否则会与历史数据产生重复行
SOURCE = "copilot"
SOURCE_RAW = "copilot-session-state"

COPILOT_HOME_ENV = "COPILOT_HOME"
COPILOT_OTEL_FILE_EXPORTER_PATH_ENV = "COPILOT_OTEL_FILE_EXPORTER_PATH"

_SHUTDOWN_EVENT = "session.shutdown"

_KIND_SESSION_STATE = "session-state"
_KIND_OTEL = "otel"

# OTEL 来源分类（对齐 Rust ``CopilotUsageSource``）
_OTEL_CHAT_SPAN = "chat-span"
_OTEL_INFERENCE_LOG = "inference-log"
_OTEL_AGENT_TURN_LOG = "agent-turn-log"
_OTEL_AGENT_SUMMARY_SPAN = "agent-summary-span"

# 模型名属性（按优先级）
_OTEL_MODEL_ATTRS = ("gen_ai.response.model", "gen_ai.request.model")

# 会话 id 属性（按优先级，取最高者；同优先级取靠后者，对齐 Rust ``max_by_key``）
_OTEL_SESSION_ATTRS: tuple[tuple[str, int], ...] = (
    ("gen_ai.conversation.id", 3),
    ("copilot_chat.session_id", 3),
    ("copilot_chat.chat_session_id", 3),
    ("session.id", 3),
    ("github.copilot.interaction_id", 2),
    ("gen_ai.response.id", 1),
)

# cache write 属性（取第一个大于 0 的）
_OTEL_CACHE_CREATION_ATTRS = (
    "gen_ai.usage.cache_write.input_tokens",
    "gen_ai.usage.cache_creation.input_tokens",
)

# reasoning 属性（取第一个大于 0 的）
_OTEL_REASONING_ATTRS = (
    "gen_ai.usage.reasoning.output_tokens",
    "gen_ai.usage.reasoning_tokens",
)

# 来源自报 total 属性（取第一个大于 0 的）
_OTEL_TOTAL_ATTRS = (
    "gen_ai.usage.total_tokens",
    "gen_ai.usage.total.token_count",
)


@dataclass
class _Entry:
    """一条 Copilot 用量条目（session-state 与 OTEL 共用）。"""

    timestamp: int
    timestamp_text: str
    session_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    reasoning_tokens: int
    extra_total_tokens: int
    request_count: int
    dedup_key: str


@dataclass
class _TraceContext:
    """OTEL trace 级上下文（模型名 / 会话 id 的回填来源）。"""

    model: Optional[str] = None
    session_id: Optional[str] = None
    session_id_priority: int = 0


@dataclass
class _OtelCandidate:
    """OTEL 候选条目（尚未做跨来源抑制）。"""

    source: str
    trace_id: Optional[str]
    response_id: Optional[str]
    model: str
    session_id: str
    timestamp: int
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    reasoning_tokens: int
    extra_total_tokens: int
    dedup_key: str


# ---------------------------------------------------------------------------
# 路径发现
# ---------------------------------------------------------------------------


def _copilot_root() -> Path:
    """返回 Copilot 根目录。

    ``COPILOT_HOME`` 非空时优先（并展开 ``~``），否则回退 ``~/.copilot``。
    """
    configured = os.environ.get(COPILOT_HOME_ENV, "").strip()
    if configured:
        return expand_user_path(configured)
    return real_home() / ".copilot"


def _session_state_files(root: Path) -> list[Path]:
    """返回 ``<root>/session-state/*/events.jsonl``（只取直接子目录）。"""
    session_dir = root / "session-state"
    if not session_dir.is_dir():
        return []
    try:
        children = sorted(session_dir.iterdir(), key=lambda p: str(p))
    except OSError as exc:
        logger.debug("[copilot] 遍历 session-state 失败 %s: %s", session_dir, exc)
        return []

    files: list[Path] = []
    for child in children:
        try:
            if not child.is_dir():
                continue
        except OSError:
            continue
        path = child / "events.jsonl"
        try:
            if path.is_file():
                files.append(path)
        except OSError:
            continue
    return files


def _otel_files(root: Path) -> list[Path]:
    """返回 ``<root>/otel/**/*.jsonl``（递归）。"""
    return collect_files(root / "otel", (".jsonl",))


def _explicit_otel_file() -> Optional[Path]:
    """返回 ``COPILOT_OTEL_FILE_EXPORTER_PATH`` 指向的文件（存在时）。"""
    configured = os.environ.get(COPILOT_OTEL_FILE_EXPORTER_PATH_ENV, "").strip()
    if not configured:
        return None
    path = expand_user_path(configured)
    try:
        return path if path.is_file() else None
    except OSError:
        return None


def _discover_sources() -> list[tuple[str, Path]]:
    """返回全部数据源 ``(kind, path)``，按路径排序并按路径去重。

    对齐 Rust ``paths()``：OTEL 目录优先登记，因此同一路径同时出现在两处时
    归类为 OTEL；最终按路径整体排序。
    """
    sources: dict[str, tuple[str, Path]] = {}

    def _add(kind: str, path: Path) -> None:
        key = str(path)
        if key not in sources:
            sources[key] = (kind, path)

    root = _copilot_root()
    for path in _otel_files(root):
        _add(_KIND_OTEL, path)
    for path in _session_state_files(root):
        _add(_KIND_SESSION_STATE, path)

    explicit = _explicit_otel_file()
    if explicit is not None:
        _add(_KIND_OTEL, explicit)

    return [sources[key] for key in sorted(sources)]


# ---------------------------------------------------------------------------
# 通用小工具
# ---------------------------------------------------------------------------


def _format_rfc3339_millis(timestamp_ms: int) -> str:
    """把 epoch 毫秒格式化为 ``YYYY-MM-DDTHH:MM:SS.mmmZ``（UTC）。"""
    moment = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    return f"{moment.strftime('%Y-%m-%dT%H:%M:%S')}.{moment.microsecond // 1000:03d}Z"


def _normalize_model(model: str) -> str:
    """归一化 Copilot 模型名（对齐 Rust ``normalize_copilot_model``）。"""
    text = model.strip()
    if text.endswith("-1m-internal"):
        return text[: -len("-1m-internal")]
    if text.endswith("-1m"):
        return text[: -len("-1m")]
    return text


def _uncached_input_tokens(raw_input: int, cache_read: int, cache_write: int) -> int:
    """扣掉 cache 后的净 input（Copilot 的 inputTokens 含 cache）。"""
    return max(0, raw_input - (cache_read + cache_write))


def _has_usage(entry: _Entry) -> bool:
    """条目是否携带任何用量（对齐 Rust ``has_usage``）。"""
    return (
        entry.input_tokens > 0
        or entry.output_tokens > 0
        or entry.cache_creation_tokens > 0
        or entry.cache_read_tokens > 0
        or entry.reasoning_tokens > 0
        or entry.extra_total_tokens > 0
        or entry.request_count > 0
    )


def _subtract_usage(current: _Entry, baseline: _Entry) -> _Entry:
    """累计快照差值（对齐 Rust ``subtract_usage``，饱和减法）。"""
    return replace(
        current,
        input_tokens=max(0, current.input_tokens - baseline.input_tokens),
        output_tokens=max(0, current.output_tokens - baseline.output_tokens),
        cache_creation_tokens=max(
            0, current.cache_creation_tokens - baseline.cache_creation_tokens
        ),
        cache_read_tokens=max(0, current.cache_read_tokens - baseline.cache_read_tokens),
        reasoning_tokens=max(0, current.reasoning_tokens - baseline.reasoning_tokens),
        extra_total_tokens=max(
            0, current.extra_total_tokens - baseline.extra_total_tokens
        ),
        request_count=max(0, current.request_count - baseline.request_count),
    )


# ---------------------------------------------------------------------------
# session-state 解析
# ---------------------------------------------------------------------------


def _session_state_dedup_key(
    session_id: str,
    event_id: Optional[str],
    timestamp_text: str,
    model: str,
    raw_input: int,
    raw_output: int,
    cache_read: int,
    cache_write: int,
    reasoning: int,
    request_count: int,
) -> str:
    """构造 session-state 去重键（对齐 Rust ``session_state_dedup_key``）。"""
    if event_id:
        return f"shutdown:{session_id}:{event_id}:{model}"
    return (
        f"shutdown:{session_id}:{timestamp_text}:{model}:"
        f"{raw_input}:{raw_output}:{cache_read}:{cache_write}:{reasoning}:{request_count}"
    )


def _parse_session_state_file(path: Path) -> list[_Entry]:
    """解析一个 ``events.jsonl``，返回其中的 session-state 条目。"""
    session_id = path.parent.name.strip()
    if not session_id:
        return []

    entries: list[_Entry] = []
    for record in iter_jsonl(path):
        # 只处理 session.shutdown；session.usage_checkpoint 只影响 credit 快照
        if lenient_str(record.get("type")) != _SHUTDOWN_EVENT:
            continue

        timestamp_text = lenient_str(record.get("timestamp"))
        if not timestamp_text:
            continue
        timestamp_ms = parse_iso_timestamp_ms(timestamp_text)
        if timestamp_ms is None:
            continue

        data = lenient_obj(record.get("data")) or {}
        model_metrics = lenient_obj(data.get("modelMetrics")) or {}
        event_id = lenient_str(record.get("id"))
        entry_timestamp_text = _format_rfc3339_millis(timestamp_ms)

        # Rust 用 BTreeMap，模型按字典序遍历
        for raw_model in sorted(model_metrics):
            metrics = lenient_obj(model_metrics[raw_model]) or {}

            request_count = 0
            requests = lenient_obj(metrics.get("requests"))
            if requests is not None:
                request_count = lenient_u64(requests.get("count"))

            usage = lenient_obj(metrics.get("usage"))
            if usage is None:
                continue

            model = _normalize_model(raw_model)
            raw_input = lenient_u64(usage.get("inputTokens"))
            raw_output = lenient_u64(usage.get("outputTokens"))
            cache_read = lenient_u64(usage.get("cacheReadTokens"))
            cache_write = lenient_u64(usage.get("cacheWriteTokens"))
            reasoning = lenient_u64(usage.get("reasoningTokens"))

            if not model or (
                raw_input == 0
                and raw_output == 0
                and cache_read == 0
                and cache_write == 0
                and reasoning == 0
                and request_count == 0
            ):
                continue

            dedup_key = _session_state_dedup_key(
                session_id,
                event_id,
                entry_timestamp_text,
                model,
                raw_input,
                raw_output,
                cache_read,
                cache_write,
                reasoning,
                request_count,
            )
            entries.append(
                _Entry(
                    timestamp=timestamp_ms,
                    timestamp_text=entry_timestamp_text,
                    session_id=session_id,
                    model=model,
                    input_tokens=_uncached_input_tokens(raw_input, cache_read, cache_write),
                    output_tokens=raw_output,
                    cache_creation_tokens=cache_write,
                    cache_read_tokens=cache_read,
                    reasoning_tokens=reasoning,
                    extra_total_tokens=0,
                    request_count=request_count,
                    dedup_key=dedup_key,
                )
            )
    return entries


# ---------------------------------------------------------------------------
# OTEL 解析（对齐 Rust ``parse_otel_file``）
# ---------------------------------------------------------------------------


def _string_value(value: Any) -> Optional[str]:
    """字符串值（trim 后非空才算存在）。"""
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def _number_value(value: Any) -> Optional[int]:
    """数值解析（对齐 Rust ``number_value``：仅非负整数与数字字符串有效）。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        # serde_json 的浮点数既不是 u64 也不是 i64
        return None
    if isinstance(value, str):
        text = value.strip()
        try:
            parsed = int(text)
        except ValueError:
            return None
        return parsed if parsed >= 0 else None
    return None


def _attr_string(attributes: dict, key: str) -> Optional[str]:
    return _string_value(attributes.get(key))


def _attr_number(attributes: dict, key: str) -> int:
    return _number_value(attributes.get(key)) or 0


def _attr_number_first(attributes: dict, keys: tuple[str, ...]) -> int:
    for key in keys:
        value = _attr_number(attributes, key)
        if value > 0:
            return value
    return 0


def _first_non_empty_attr(attributes: dict, keys: tuple[str, ...]) -> Optional[str]:
    for key in keys:
        value = _attr_string(attributes, key)
        if value is not None:
            return value
    return None


def _best_session_attr(attributes: dict) -> Optional[tuple[str, int]]:
    """取优先级最高的会话 id 属性（同优先级取靠后者，对齐 Rust ``max_by_key``）。"""
    best: Optional[tuple[str, int]] = None
    for key, priority in _OTEL_SESSION_ATTRS:
        value = _attr_string(attributes, key)
        if value is None:
            continue
        if best is None or priority >= best[1]:
            best = (value, priority)
    return best


def _first_non_empty_model_attr(attributes: dict) -> Optional[str]:
    raw = _first_non_empty_attr(attributes, _OTEL_MODEL_ATTRS)
    return _normalize_model(raw) if raw is not None else None


def _nested_string(value: Any, key: str) -> Optional[str]:
    if isinstance(value, dict):
        return _string_value(value.get(key))
    return None


def _trace_id_from_record(record: dict) -> Optional[str]:
    trace_id = _string_value(record.get("traceId"))
    if trace_id is not None:
        return trace_id
    return _nested_string(record.get("spanContext"), "traceId")


def _span_id_from_record(record: dict) -> Optional[str]:
    span_id = _string_value(record.get("spanId"))
    if span_id is not None:
        return span_id
    return _nested_string(record.get("spanContext"), "spanId")


def _record_body(record: dict) -> Optional[str]:
    body = _string_value(record.get("body"))
    if body is not None:
        return body
    return _string_value(record.get("_body"))


def _is_span_record(record: dict) -> bool:
    """是否是 span 记录（对齐 Rust ``is_span_record``）。"""
    record_type = record.get("type")
    if isinstance(record_type, str):
        return record_type == "span"
    name = _string_value(record.get("name"))
    if not name:
        return False
    return (
        _string_value(record.get("spanId")) is not None
        or _string_value(record.get("traceId")) is not None
        or "startTime" in record
        or "endTime" in record
        or "duration" in record
        or "kind" in record
    )


def _is_chat_span_record(record: dict, attributes: dict) -> bool:
    if not _is_span_record(record):
        return False
    if _attr_string(attributes, "gen_ai.operation.name") == "chat":
        return True
    name = _string_value(record.get("name"))
    return name is not None and name.startswith("chat ")


def _is_agent_summary_span_record(record: dict, attributes: dict) -> bool:
    if not _is_span_record(record):
        return False
    if _attr_string(attributes, "gen_ai.operation.name") == "invoke_agent":
        return True
    name = _string_value(record.get("name"))
    return name is not None and name.startswith("invoke_agent ")


def _is_inference_log_record(record: dict, attributes: dict) -> bool:
    if _is_span_record(record):
        return False
    if _attr_string(attributes, "event.name") == "gen_ai.client.inference.operation.details":
        return True
    body = _record_body(record)
    return body is not None and body.startswith("GenAI inference:")


def _is_agent_turn_log_record(record: dict, attributes: dict) -> bool:
    if _is_span_record(record):
        return False
    if _attr_string(attributes, "event.name") == "copilot_chat.agent.turn":
        return True
    body = _record_body(record)
    return body is not None and body.startswith("copilot_chat.agent.turn")


def _timestamp_from_parts(value: Any) -> Optional[int]:
    """``[seconds, nanos]`` 形式的时间戳。"""
    if not isinstance(value, list) or len(value) < 2:
        return None
    seconds = _number_value(value[0])
    nanos = _number_value(value[1])
    if seconds is None or nanos is None:
        return None
    return seconds * 1000 + nanos // 1_000_000


def _timestamp_from_scalar(value: Any) -> Optional[int]:
    """标量时间戳（按数量级自动判定秒 / 毫秒 / 微秒 / 纳秒）。"""
    raw = _number_value(value)
    if raw is None:
        return None
    if raw >= 100_000_000_000_000_000:
        return raw // 1_000_000
    if raw >= 100_000_000_000_000:
        return raw // 1_000
    if raw >= 100_000_000_000:
        return raw
    return raw * 1000


def _timestamp_from_unix_nanos(value: Any) -> Optional[int]:
    raw = _number_value(value)
    if raw is None or raw <= 0:
        return None
    return raw // 1_000_000


def _timestamp_from_record(record: dict) -> Optional[int]:
    """从 OTEL 记录里取时间戳（对齐 Rust ``timestamp_from_record``）。"""
    for key in ("endTime", "startTime", "hrTime", "_hrTime", "time"):
        timestamp = _timestamp_from_parts(record.get(key))
        if timestamp is not None:
            return timestamp
    timestamp = _timestamp_from_scalar(record.get("timestamp"))
    if timestamp is not None:
        return timestamp
    timestamp = _timestamp_from_scalar(record.get("observedTimestamp"))
    if timestamp is not None:
        return timestamp
    return _timestamp_from_unix_nanos(record.get("timeUnixNano"))


def _file_modified_timestamp(path: Path) -> int:
    """文件 mtime（epoch 毫秒），OTEL 记录缺时间戳时的兜底。"""
    try:
        return int(path.stat().st_mtime * 1000)
    except OSError:
        return 0


def _collect_trace_contexts(records: list[dict]) -> dict[str, _TraceContext]:
    """收集 trace 级上下文（模型名 / 会话 id 的回填来源）。"""
    contexts: dict[str, _TraceContext] = {}
    for record in records:
        trace_id = _trace_id_from_record(record)
        if trace_id is None:
            continue
        attributes = record.get("attributes")
        if not isinstance(attributes, dict):
            continue
        context = contexts.setdefault(trace_id, _TraceContext())
        if context.model is None:
            context.model = _first_non_empty_model_attr(attributes)
        best = _best_session_attr(attributes)
        if best is not None and best[1] > context.session_id_priority:
            context.session_id = best[0]
            context.session_id_priority = best[1]
    return contexts


def _dedup_key_for_record(
    source: str,
    record: dict,
    attributes: dict,
    trace_id: Optional[str],
    session_id: str,
    timestamp: int,
    index: int,
) -> str:
    """OTEL 去重键（对齐 Rust ``dedup_key_for_record``）。"""
    span_id = _span_id_from_record(record)
    if source in (_OTEL_CHAT_SPAN, _OTEL_AGENT_SUMMARY_SPAN):
        if trace_id is not None and span_id is not None:
            return f"{trace_id}:{span_id}"
        return f"span:{session_id}:{timestamp}:{index}"
    if source == _OTEL_INFERENCE_LOG:
        if trace_id is not None and span_id is not None:
            return f"log:{trace_id}:{span_id}"
        return f"log:{session_id}:{timestamp}:{index}"

    turn_index = _number_value(attributes.get("turn.index"))
    if turn_index is None:
        turn_index = _number_value(attributes.get("copilot_chat.turn.index"))
    turn_text = f"idx-{index}" if turn_index is None else str(turn_index)
    if trace_id is not None:
        return f"agent-turn:{trace_id}:{turn_text}"
    return f"agent-turn:{session_id}:{turn_text}:{index}"


def _to_otel_candidate(
    record: dict,
    index: int,
    fallback_timestamp: int,
    trace_contexts: dict[str, _TraceContext],
) -> Optional[_OtelCandidate]:
    """把一条 OTEL 记录转成候选条目。"""
    # 每条可用记录都带 attributes 对象，缺它的行直接跳过
    attributes = record.get("attributes")
    if not isinstance(attributes, dict):
        return None

    if _is_chat_span_record(record, attributes):
        source = _OTEL_CHAT_SPAN
    elif _is_inference_log_record(record, attributes):
        source = _OTEL_INFERENCE_LOG
    elif _is_agent_turn_log_record(record, attributes):
        source = _OTEL_AGENT_TURN_LOG
    elif _is_agent_summary_span_record(record, attributes):
        source = _OTEL_AGENT_SUMMARY_SPAN
    else:
        return None

    input_tokens = _attr_number(attributes, "gen_ai.usage.input_tokens")
    output_tokens = _attr_number(attributes, "gen_ai.usage.output_tokens")
    cache_read = _attr_number(attributes, "gen_ai.usage.cache_read.input_tokens")
    cache_creation = _attr_number_first(attributes, _OTEL_CACHE_CREATION_ATTRS)
    reasoning = _attr_number_first(attributes, _OTEL_REASONING_ATTRS)
    total = _attr_number_first(attributes, _OTEL_TOTAL_ATTRS)

    # Copilot 把 cache read / write 计入 input tokens，与 session-state 一致
    net_input = max(0, input_tokens - (cache_read + cache_creation))
    extra_total_tokens = 0
    known = net_input + output_tokens + cache_creation + cache_read + extra_total_tokens
    missing = max(0, total - known)
    if missing:
        if output_tokens == 0:
            output_tokens = missing
        else:
            extra_total_tokens += missing
    if known + missing == 0:
        return None

    trace_id = _trace_id_from_record(record)
    trace_context = trace_contexts.get(trace_id) if trace_id is not None else None
    response_id = _attr_string(attributes, "gen_ai.response.id")
    model = _first_non_empty_model_attr(attributes)
    if model is None:
        model = trace_context.model if trace_context is not None else None
    if model is None:
        model = "unknown"

    session_id = None
    best = _best_session_attr(attributes)
    if best is not None:
        session_id = best[0]
    elif trace_context is not None:
        session_id = trace_context.session_id
    if session_id is None:
        session_id = trace_id
    if session_id is None:
        session_id = "unknown-session"

    timestamp = _timestamp_from_record(record)
    if timestamp is None:
        timestamp = fallback_timestamp

    dedup_key = _dedup_key_for_record(
        source, record, attributes, trace_id, session_id, timestamp, index
    )
    return _OtelCandidate(
        source=source,
        trace_id=trace_id,
        response_id=response_id,
        model=model,
        session_id=session_id,
        timestamp=timestamp,
        input_tokens=net_input,
        output_tokens=output_tokens,
        cache_creation_tokens=cache_creation,
        cache_read_tokens=cache_read,
        reasoning_tokens=reasoning,
        extra_total_tokens=extra_total_tokens,
        dedup_key=dedup_key,
    )


def _repeated_chat_spans(candidates: list[_OtelCandidate]) -> set[int]:
    """找出重复导出的 chat span（对齐 Rust ``repeated_chat_spans``）。"""
    earliest: dict[tuple, int] = {}
    repeated: set[int] = set()
    for index, candidate in enumerate(candidates):
        if candidate.source != _OTEL_CHAT_SPAN or candidate.response_id is None:
            continue
        call = (
            candidate.response_id,
            candidate.model,
            candidate.input_tokens,
            candidate.output_tokens,
            candidate.cache_creation_tokens,
            candidate.cache_read_tokens,
            candidate.reasoning_tokens,
            candidate.extra_total_tokens,
        )
        kept = earliest.setdefault(call, index)
        if kept == index:
            continue
        if candidate.timestamp < candidates[kept].timestamp:
            repeated.add(kept)
            earliest[call] = index
        else:
            repeated.add(index)
    return repeated


def _should_emit_otel_candidate(
    index: int,
    candidate: _OtelCandidate,
    chat_traces: set[str],
    inference_traces: set[str],
    agent_turn_traces: set[str],
    chat_response_ids: set[str],
    inference_response_ids: set[str],
    agent_turn_response_ids: set[str],
    repeated_chat_spans: set[int],
) -> bool:
    """跨来源抑制（对齐 Rust ``should_emit_candidate``）。"""

    def trace_match(values: set[str]) -> bool:
        return candidate.trace_id is not None and candidate.trace_id in values

    def response_match(values: set[str]) -> bool:
        return candidate.response_id is not None and candidate.response_id in values

    if candidate.source == _OTEL_CHAT_SPAN:
        return index not in repeated_chat_spans
    if candidate.source == _OTEL_INFERENCE_LOG:
        return not trace_match(chat_traces) and not response_match(chat_response_ids)
    if candidate.source == _OTEL_AGENT_TURN_LOG:
        return (
            not trace_match(chat_traces)
            and not trace_match(inference_traces)
            and not response_match(chat_response_ids)
            and not response_match(inference_response_ids)
        )
    return (
        not trace_match(chat_traces)
        and not trace_match(inference_traces)
        and not trace_match(agent_turn_traces)
        and not response_match(chat_response_ids)
        and not response_match(inference_response_ids)
        and not response_match(agent_turn_response_ids)
    )


def _parse_otel_file(path: Path) -> list[_Entry]:
    """解析一个 OTEL jsonl 文件，返回其中的用量条目。"""
    records: list[dict] = list(iter_jsonl(path))

    trace_contexts = _collect_trace_contexts(records)
    fallback_timestamp = _file_modified_timestamp(path)

    candidates: list[_OtelCandidate] = []
    for index, record in enumerate(records):
        candidate = _to_otel_candidate(
            record, index, fallback_timestamp, trace_contexts
        )
        if candidate is not None:
            candidates.append(candidate)

    chat_traces = {
        c.trace_id for c in candidates if c.source == _OTEL_CHAT_SPAN and c.trace_id
    }
    inference_traces = {
        c.trace_id for c in candidates if c.source == _OTEL_INFERENCE_LOG and c.trace_id
    }
    agent_turn_traces = {
        c.trace_id for c in candidates if c.source == _OTEL_AGENT_TURN_LOG and c.trace_id
    }
    chat_response_ids = {
        c.response_id
        for c in candidates
        if c.source == _OTEL_CHAT_SPAN and c.response_id
    }
    inference_response_ids = {
        c.response_id
        for c in candidates
        if c.source == _OTEL_INFERENCE_LOG and c.response_id
    }
    agent_turn_response_ids = {
        c.response_id
        for c in candidates
        if c.source == _OTEL_AGENT_TURN_LOG and c.response_id
    }
    repeated = _repeated_chat_spans(candidates)

    entries: list[_Entry] = []
    for index, candidate in enumerate(candidates):
        if not _should_emit_otel_candidate(
            index,
            candidate,
            chat_traces,
            inference_traces,
            agent_turn_traces,
            chat_response_ids,
            inference_response_ids,
            agent_turn_response_ids,
            repeated,
        ):
            continue
        entries.append(
            _Entry(
                timestamp=candidate.timestamp,
                timestamp_text=_format_rfc3339_millis(candidate.timestamp),
                session_id=candidate.session_id,
                model=candidate.model,
                input_tokens=candidate.input_tokens,
                output_tokens=candidate.output_tokens,
                cache_creation_tokens=candidate.cache_creation_tokens,
                cache_read_tokens=candidate.cache_read_tokens,
                reasoning_tokens=candidate.reasoning_tokens,
                extra_total_tokens=candidate.extra_total_tokens,
                request_count=1,
                dedup_key=candidate.dedup_key,
            )
        )
    return entries


# ---------------------------------------------------------------------------
# 去重 / 差值对账
# ---------------------------------------------------------------------------


def _deduplicate_entries(entries: list[_Entry]) -> list[_Entry]:
    """同键只保留最后一条（对齐 Rust ``deduplicate_session_entries``）。"""
    indexes: dict[str, int] = {}
    for index, entry in enumerate(entries):
        previous = indexes.get(entry.dedup_key)
        if previous is None or entries[previous].timestamp <= entry.timestamp:
            indexes[entry.dedup_key] = index
    return [entries[index] for index in sorted(indexes.values())]


def _otel_call_timestamps(
    otel_entries: list[_Entry],
) -> dict[tuple[str, str], list[int]]:
    """按 ``(session, model)`` 汇总 OTEL 调用时间戳（已排序）。"""
    calls: dict[tuple[str, str], list[int]] = {}
    for entry in otel_entries:
        calls.setdefault((entry.session_id, entry.model), []).append(entry.timestamp)
    for timestamps in calls.values():
        timestamps.sort()
    return calls


def _otel_replacement_start(
    entries: list[_Entry],
    sorted_indices: list[int],
    calls: list[int],
) -> Optional[int]:
    """OTEL 取代 session-state 区间的起点（对齐 Rust ``otel_replacement_start``）。

    Copilot 进程会恢复上次 shutdown 的用量明细，被杀 / 崩溃 / 被重启时缺少
    shutdown，后续 shutdown 的累计值因此偏低；OTEL 有每次调用的明细，
    当它记录的调用数多于 shutdown 报告的请求数时，用 OTEL 取代对应区间。
    """
    if any(entries[index].request_count == 0 for index in sorted_indices):
        return None

    start: Optional[int] = None
    counted_calls = 0
    otel_calls = 0
    reported_calls = 0
    previous_requests = 0
    for position, index in enumerate(sorted_indices):
        entry = entries[index]
        calls_through = bisect.bisect_right(calls, entry.timestamp)
        interval_calls = calls_through - counted_calls
        counted_calls = calls_through
        if start is None and interval_calls > 0:
            start = position
        if start is not None:
            otel_calls += interval_calls
            reported_calls += max(0, entry.request_count - previous_requests)
        previous_requests = entry.request_count

    if start is None:
        return None
    return start if otel_calls > reported_calls else None


def _reconcile_session_entries(
    entries: list[_Entry],
    otel_calls: dict[tuple[str, str], list[int]],
    since_ms: Optional[int],
    until_ms: Optional[int],
) -> tuple[list[_Entry], dict[tuple[str, str], int]]:
    """把累计快照转成区间用量（对齐 Rust ``reconcile_session_state_entries``）。

    Returns:
        ``(区间条目列表, 每个 (session, model) 的 OTEL 起始时间)``
    """
    entries = _deduplicate_entries(entries)

    grouped: dict[tuple[str, str], list[int]] = {}
    for index, entry in enumerate(entries):
        grouped.setdefault((entry.session_id, entry.model), []).append(index)

    interval_entries: list[_Entry] = []
    otel_after: dict[tuple[str, str], int] = {}

    for key in sorted(grouped):
        sorted_indices = sorted(
            grouped[key], key=lambda index: (entries[index].timestamp, index)
        )

        # until 区间内最后一条可见条目的位置
        latest_visible: Optional[int] = None
        if until_ms is None:
            latest_visible = len(sorted_indices) - 1
        else:
            for position, index in enumerate(sorted_indices):
                if entries[index].timestamp < until_ms:
                    latest_visible = position

        calls = otel_calls.get(key)
        otel_start = (
            _otel_replacement_start(entries, sorted_indices, calls)
            if calls is not None
            else None
        )
        if otel_start is None:
            otel_after_position = latest_visible
        elif otel_start == 0:
            otel_after_position = None
        else:
            otel_after_position = otel_start - 1
        if otel_after_position is not None:
            otel_after[key] = entries[sorted_indices[otel_after_position]].timestamp

        previous: Optional[_Entry] = None
        for position, index in enumerate(sorted_indices):
            current = entries[index]
            # 差值基线覆盖全部 shutdown（含日期区间之外的），与 ccusage 一致
            reconciled = current if previous is None else _subtract_usage(current, previous)
            previous = current

            if latest_visible is None or position > latest_visible:
                continue
            if otel_start is not None and position >= otel_start:
                continue
            if since_ms is not None and current.timestamp < since_ms:
                continue
            if not _has_usage(reconciled):
                continue
            interval_entries.append(reconciled)

    interval_entries.sort(key=lambda entry: (entry.timestamp, entry.dedup_key))
    return interval_entries, otel_after


# ---------------------------------------------------------------------------
# 对外入口
# ---------------------------------------------------------------------------


def read_copilot_records(since_date: date, until_date: date) -> AgentReadResult:
    """读取 GitHub Copilot CLI 的 Token 用量。

    Args:
        since_date: 起始日期（含）。
        until_date: 结束日期（含）。

    Returns:
        AgentReadResult：records 为按 (日期, 模型) 聚合后的记录。
    """
    result = AgentReadResult()

    sources = _discover_sources()
    session_entries: list[_Entry] = []
    otel_entries: list[_Entry] = []
    for kind, path in sources:
        try:
            if kind == _KIND_OTEL:
                otel_entries.extend(_parse_otel_file(path))
            else:
                session_entries.extend(_parse_session_state_file(path))
        except Exception as exc:  # 单个文件失败只丢该文件
            logger.warning("[copilot] 解析文件失败 %s: %s", path, exc, exc_info=True)

    since_ms, until_ms = date_range_to_ms_bounds(since_date, until_date)
    interval_entries, otel_after = _reconcile_session_entries(
        session_entries, _otel_call_timestamps(otel_entries), since_ms, until_ms
    )

    # OTEL 行只在 session-state 对应区间之后计入
    kept_otel: list[_Entry] = []
    for entry in otel_entries:
        after = otel_after.get((entry.session_id, entry.model))
        if after is not None and entry.timestamp <= after:
            continue
        kept_otel.append(entry)

    since_str = since_date.isoformat()
    until_str = until_date.isoformat()
    rows: list[dict] = []
    for entry in interval_entries + kept_otel:
        record_date = epoch_ms_to_local_date(entry.timestamp)
        if not (since_str <= record_date <= until_str):
            continue
        rows.append(
            {
                "record_date": record_date,
                "model": entry.model,
                "input_tokens": entry.input_tokens,
                "output_tokens": entry.output_tokens,
                "cache_creation_tokens": entry.cache_creation_tokens,
                "cache_read_tokens": entry.cache_read_tokens,
                # reasoning_tokens 单独记录，不计入 total（对齐 ccusage 口径）
                "extra_total_tokens": entry.extra_total_tokens,
                "total_cost": 0.0,
            }
        )

    result.records = aggregate_records(rows, source=SOURCE, source_raw=SOURCE_RAW)
    logger.info(
        "[copilot] 原生读取 %s 个文件，聚合 %s 条记录",
        len(sources),
        len(result.records),
    )
    return result

"""OpenCode 原生 Token 用量读取器

完全替代 ccusage CLI 的 ``opencode`` 适配器，统计结果与其**逐日逐模型一致**
（对齐 ccusage **20.0.42**，参考实现：
``rust/adapters/opencode/{paths,parser,loader}.rs`` 与 ``ccusage-core`` 的
``apply_total_token_fallback``）。

数据源（三个，按 ccusage 的顺序读取）：

1. **SQLite v1 表 ``message``** —— 旧版 opencode 的消息表，``data`` 里用扁平字段
   ``modelID`` / ``providerID`` 记录模型。
2. **SQLite v2 表 ``session_message``** —— 新版 opencode 的消息表，``data`` 里用
   对象字段 ``model.id`` / ``model.providerID`` 记录模型，并且只统计
   ``type == "assistant"`` 的消息。
3. **旧 JSON 文件 ``storage/message/<session_id>/<msg_id>.json``** —— 早期版本
   的消息落盘文件。

另外读取 ``session_v2`` 表的 fork 信息（``fork_session_id`` / ``fork_boundary``），
用于剔除 fork 会话里"从父会话复制过来"的助手消息（见下文 fork 段落）。

与 ccusage 对齐的关键口径：

1. **Token 四桶**：
   ``input = tokens.input``、``output = tokens.output``、
   ``cache_creation = tokens.cache.write``、``cache_read = tokens.cache.read``。
   opencode 的 ``tokens.input`` **不含** cache，**不做** cache 扣减。
2. **reasoning 进 extra 桶**（不可见桶，只计入 total）：
   ``extra_total_tokens = tokens.reasoning``。
3. **total 兜底**（``apply_total_token_fallback``）：
   ``known = input + output + cache_creation + cache_read + extra``；
   ``missing = max(0, tokens.total - known)``；
   ``missing > 0`` 时 ``output == 0`` → 补进 output，否则补进 extra。
   最终 ``total = input + output + cache_creation + cache_read + extra``。
4. **四个桶全 0 且 extra 也 0** → 丢弃该条。
5. **模型名取原值**：``modelID``（v1）或 ``model.id``（v2）。ccusage 内部的
   ``resolve_open_code_model_name`` / ``normalize_open_code_model_name``
   （``gemini-3-pro-high`` → ``gemini-3-pro-preview``、``k2p6`` → ``kimi-k2.6``、
   ``claude-opus-4.5`` → ``claude-opus-4-5``）**只用于定价查找**，不改写展示名。
6. **缺 model 或缺 providerID 的行直接丢弃**（ccusage 的
   ``value.model_id.clone()?`` / ``value.provider_id.clone()?``）。
7. **按 message id 去重**：v1 / v2 / JSON 三个来源之间有大量同 id 重复，
   ccusage 的顺序是"先到先得"（v1 → v2 → JSON），本实现保持一致。
8. **时间戳**：``data.time.created``（epoch 毫秒）；v2 在 payload 缺失时回退到
   ``session_message.time_created`` 列。日期按**本机时区**自然日归桶。
9. **fork 复制剔除**：fork 会话开头复制自父会话的那段消息不应重复统计，
   ccusage 通过 ``session_v2.fork_boundary`` 定位边界并按 ``seq`` 截断。
10. **单条解析失败只丢该条**，绝不中断整体。
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Optional

from app.utils.agent_readers.base import (
    AgentReadResult,
    aggregate_records,
    apply_total_fallback,
    collect_files,
    date_range_to_ms_bounds,
    epoch_ms_to_local_date,
    expand_user_path,
    lenient_obj,
    lenient_str,
    lenient_u64,
    open_sqlite_readonly,
    real_home,
    table_columns,
)

logger = logging.getLogger(__name__)

SOURCE = "opencode"
SOURCE_RAW = "opencode-sqlite"

#: 一天的毫秒数，用于 SQL 下推窗口的左右各放宽一天
_MILLIS_PER_DAY = 86_400_000

#: 判定 ``time_created`` 是否为毫秒级的下界（1973 年之后的 Unix 毫秒至少 12 位）
_MIN_MILLIS_SCALE = 100_000_000_000

#: ``OPENCODE_DATA_DIR``：逗号分隔的数据根目录
_OPENCODE_DATA_DIR_ENV = "OPENCODE_DATA_DIR"

#: ``XDG_DATA_HOME``：XDG 数据根目录
_XDG_DATA_HOME_ENV = "XDG_DATA_HOME"


# ---------------------------------------------------------------------------
# 中间结构
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Usage:
    """一条已归一化的消息用量。"""

    message_id: Optional[str]
    session_id: Optional[str]
    model: str
    provider: str
    timestamp_ms: int
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    extra_total_tokens: int
    cost: float


@dataclass(frozen=True)
class _Window:
    """左闭右开的 epoch 毫秒窗口。"""

    start: Optional[int]
    end: Optional[int]

    @property
    def is_unbounded(self) -> bool:
        return self.start is None and self.end is None

    def contains(self, millis: int) -> bool:
        if self.start is not None and millis < self.start:
            return False
        if self.end is not None and millis >= self.end:
            return False
        return True

    def widened(self) -> "_Window":
        """左右各放宽一天，用于 SQL 下推（列值只是 payload 的代理值）。"""
        return _Window(
            start=self.start - _MILLIS_PER_DAY if self.start is not None else None,
            end=self.end + _MILLIS_PER_DAY if self.end is not None else None,
        )


_UNBOUNDED = _Window(start=None, end=None)


# ---------------------------------------------------------------------------
# 路径发现（对齐 opencode_paths.rs）
# ---------------------------------------------------------------------------


def _opencode_data_dirs() -> list[Path]:
    """发现 opencode 数据根目录。

    顺序与 ccusage ``opencode_paths::paths`` 一致：

    1. 设置了 ``OPENCODE_DATA_DIR``（逗号分隔）→ **只用它，不回落**，
       非目录项跳过；变量存在但为空时结果为空列表。
    2. ``XDG_DATA_HOME`` 为绝对路径 → ``<XDG_DATA_HOME>/opencode``。
    3. 否则 → ``~/.local/share/opencode``。
    """
    raw = os.environ.get(_OPENCODE_DATA_DIR_ENV)
    if raw is not None:
        dirs: list[Path] = []
        seen: set[str] = set()
        for item in raw.split(","):
            item = item.strip()
            if not item:
                continue
            path = expand_user_path(item)
            key = os.path.normcase(str(path))
            if path.is_dir() and key not in seen:
                seen.add(key)
                dirs.append(path)
        return dirs

    data_home: Optional[Path] = None
    xdg = os.environ.get(_XDG_DATA_HOME_ENV)
    if xdg is not None:
        candidate = expand_user_path(xdg.strip())
        if candidate.is_absolute():
            data_home = candidate
    if data_home is None:
        data_home = real_home() / ".local" / "share"

    candidate = data_home / "opencode"
    return [candidate] if candidate.is_dir() else []


def _is_channel_db_name(name: str) -> bool:
    """判断是否为 channel 专属数据库文件名（``opencode-*.db``）。"""
    if not name.startswith("opencode-") or not name.endswith(".db"):
        return False
    middle = name[len("opencode-") : len(name) - len(".db")]
    return all(ch.isalnum() and ch.isascii() or ch in ("_", "-") for ch in middle)


def _db_path(opencode_dir: Path) -> Optional[Path]:
    """定位 opencode 数据库文件。

    优先 ``<dir>/opencode.db``；否则取目录内按名称排序的第一个
    ``opencode-*.db``。
    """
    default_path = opencode_dir / "opencode.db"
    if default_path.is_file():
        return default_path
    try:
        candidates = sorted(
            path
            for path in opencode_dir.iterdir()
            if path.is_file() and _is_channel_db_name(path.name)
        )
    except OSError:
        return None
    return candidates[0] if candidates else None


# ---------------------------------------------------------------------------
# 解析辅助
# ---------------------------------------------------------------------------


def _extract_message_timestamp_ms(raw: str) -> Optional[int]:
    """从原始 JSON 文本粗提取 ``time.created``（epoch 毫秒）。

    对齐 ccusage ``opencode_loader::extract_message_timestamp``：只认
    ``"time": { ... "created": <数字> ... }`` 这一种形状，且查找 ``created``
    时不会跳出该对象。**失败即返回 None**（调用方按"完整解析"处理），
    宁可多解析几条，也不要因为猜错而丢掉区间内的记录。
    """
    time_key = '"time":'
    created_key = '"created":'

    time_index = raw.find(time_key)
    if time_index < 0:
        return None
    rest = raw[time_index + len(time_key) :].lstrip()
    if not rest.startswith("{"):
        return None
    object_end = rest.find("}")
    if object_end < 0:
        return None
    time_object = rest[:object_end]

    created_index = time_object.find(created_key)
    if created_index < 0:
        return None
    after_key = time_object[created_index + len(created_key) :].lstrip()

    end = 0
    while end < len(after_key) and after_key[end].isascii() and after_key[end].isdigit():
        end += 1
    if end == 0:
        return None
    try:
        return int(after_key[:end])
    except ValueError:
        return None


def _created_ms(payload: dict) -> Optional[int]:
    """读取 payload 里的 ``time.created``（毫秒）。"""
    time_obj = lenient_obj(payload.get("time"))
    if time_obj is None:
        return None
    value = time_obj.get("created")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    millis = int(value)
    return millis if millis > 0 else None


def _parse_token_buckets(tokens: Any) -> Optional[tuple[int, int, int, int, int, int]]:
    """解析 ``tokens`` 块，返回 (input, output, reasoning, cache_read, cache_write, total)。

    ``tokens`` 不是对象时返回 None（对应 Rust 的 ``value.tokens.as_ref()?``）。
    """
    obj = lenient_obj(tokens)
    if obj is None:
        return None
    cache = lenient_obj(obj.get("cache")) or {}
    return (
        lenient_u64(obj.get("input")),
        lenient_u64(obj.get("output")),
        lenient_u64(obj.get("reasoning")),
        lenient_u64(cache.get("read")),
        lenient_u64(cache.get("write")),
        lenient_u64(obj.get("total")),
    )


def _stored_cost(payload: dict) -> float:
    """读取 opencode 自报的成本（缺失或非正数按 0 处理）。"""
    value = payload.get("cost")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0.0
    cost = float(value)
    return cost if cost > 0.0 else 0.0


def _legacy_model_and_provider(payload: dict) -> tuple[Optional[str], Optional[str]]:
    """v1（``message`` 表 / JSON 文件）的模型与 provider。"""
    return lenient_str(payload.get("modelID")), lenient_str(payload.get("providerID"))


def _v2_model_and_provider(payload: dict) -> tuple[Optional[str], Optional[str]]:
    """v2（``session_message`` 表）的模型与 provider。

    模型取 ``model.id`` → ``model.modelID`` → 顶层 ``modelID``；
    provider 取 ``model.providerID`` → 顶层 ``providerID``。
    """
    model_ref = lenient_obj(payload.get("model")) or {}
    model_id = (
        lenient_str(model_ref.get("id"))
        or lenient_str(model_ref.get("modelID"))
        or lenient_str(payload.get("modelID"))
    )
    provider_id = lenient_str(model_ref.get("providerID")) or lenient_str(
        payload.get("providerID")
    )
    return model_id, provider_id


def _build_usage(
    payload: dict,
    *,
    model_id: Optional[str],
    provider_id: Optional[str],
    timestamp_ms: int,
    message_id: Optional[str],
    session_id: Optional[str],
) -> Optional[_Usage]:
    """把一条消息 payload 转成用量记录；不符合 ccusage 口径时返回 None。"""
    buckets = _parse_token_buckets(payload.get("tokens"))
    if buckets is None:
        return None
    input_tokens, output_tokens, reasoning, cache_read, cache_write, total = buckets

    input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens, extra = (
        apply_total_fallback(
            input_tokens,
            output_tokens,
            cache_write,
            cache_read,
            reasoning,
            total,
        )
    )

    if (
        input_tokens == 0
        and output_tokens == 0
        and cache_creation_tokens == 0
        and cache_read_tokens == 0
        and extra == 0
    ):
        return None

    if not model_id or not provider_id:
        return None

    return _Usage(
        message_id=message_id,
        session_id=session_id,
        model=model_id,
        provider=provider_id,
        timestamp_ms=timestamp_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_tokens=cache_creation_tokens,
        cache_read_tokens=cache_read_tokens,
        extra_total_tokens=extra,
        cost=_stored_cost(payload),
    )


# ---------------------------------------------------------------------------
# fork 复制截断（对齐 opencode_loader.rs）
# ---------------------------------------------------------------------------


def _last_parent_seq_before(
    conn: sqlite3.Connection, parent_id: str, boundary_seq: int
) -> Optional[int]:
    """父会话中严格小于 ``boundary_seq`` 的最大 ``seq``。"""
    try:
        row = conn.execute(
            "SELECT MAX(seq) FROM session_message WHERE session_id = ?1 AND seq < ?2",
            (parent_id, boundary_seq),
        ).fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    return row[0]


def _fork_copy_cutoff(
    conn: sqlite3.Connection, parent_id: str, boundary: str
) -> Optional[int]:
    """计算一个 fork 会话里"仍属于复制历史"的最大 ``seq``。

    - ``through`` 边界 → 父会话边界消息自身的 ``seq``；
    - ``before`` 边界 → 父会话中边界之前最后一条消息的 ``seq``。

    边界无法解析（父行缺失 / 边界行缺失 / 边界 payload 非法）时返回 None，
    即该 fork 保留全部消息，而不是靠猜测丢弃。
    """
    try:
        boundary_obj = json.loads(boundary)
    except (ValueError, TypeError):
        return None
    if not isinstance(boundary_obj, dict):
        return None
    boundary_type = boundary_obj.get("type")
    if not isinstance(boundary_type, str):
        return None
    parent_message_id = boundary_obj.get("messageID")
    if not isinstance(parent_message_id, str):
        return None

    try:
        row = conn.execute(
            "SELECT seq FROM session_message WHERE session_id = ?1 AND id = ?2 LIMIT 1",
            (parent_id, parent_message_id),
        ).fetchone()
    except sqlite3.Error:
        return None
    if row is None:
        return None
    boundary_seq = row[0]
    if not isinstance(boundary_seq, int) or isinstance(boundary_seq, bool):
        return None

    if boundary_type == "through":
        return boundary_seq
    if boundary_type == "before":
        return _last_parent_seq_before(conn, parent_id, boundary_seq)
    return None


def _fork_copy_cutoffs(conn: sqlite3.Connection) -> dict[str, int]:
    """返回 ``{fork 会话 id: 复制历史的最大 seq}``。

    ``session_v2`` 提供 fork 关联（``fork_session_id`` + ``fork_boundary``），
    ``session_message`` 提供 fork 保留下来的 ``seq``。
    """
    cutoffs: dict[str, int] = {}
    if not table_columns(conn, "session_v2") or not table_columns(conn, "session_message"):
        return cutoffs
    if not {"id", "fork_session_id", "fork_boundary"} <= table_columns(conn, "session_v2"):
        return cutoffs
    if not {"id", "session_id", "seq"} <= table_columns(conn, "session_message"):
        return cutoffs

    try:
        rows = conn.execute(
            "SELECT id, fork_session_id, fork_boundary FROM session_v2 "
            "WHERE fork_session_id IS NOT NULL AND fork_boundary IS NOT NULL"
        ).fetchall()
    except sqlite3.Error:
        return cutoffs

    for fork_id, parent_id, boundary in rows:
        if not isinstance(fork_id, str) or not isinstance(parent_id, str):
            continue
        if not isinstance(boundary, str):
            continue
        if not fork_id or not parent_id:
            continue
        cutoff = _fork_copy_cutoff(conn, parent_id, boundary)
        if cutoff is not None:
            cutoffs[fork_id] = cutoff
    return cutoffs


def _is_fork_copy(cutoffs: dict[str, int], session_id: str, seq: Any) -> bool:
    """判断一条 v2 消息是否属于 fork 的复制历史。

    ``seq`` 读不出来时保留该行（无法分类就不丢）。
    """
    cutoff = cutoffs.get(session_id)
    if cutoff is None:
        return False
    if not isinstance(seq, int) or isinstance(seq, bool):
        return False
    return seq <= cutoff


# ---------------------------------------------------------------------------
# 数据库读取
# ---------------------------------------------------------------------------


def _time_created_looks_like_millis(conn: sqlite3.Connection, table: str) -> bool:
    """抽样判断 ``time_created`` 是否为毫秒级。

    与 ccusage 一致：抽前 8 行取最大值，低于 1e11 视为非毫秒级（此时禁用
    毫秒下推，交由 payload 里的真实时间戳过滤）。
    """
    if "time_created" not in table_columns(conn, table):
        return False
    try:
        row = conn.execute(
            f"SELECT max(time_created) FROM (SELECT time_created FROM {table} LIMIT 8)"
        ).fetchone()
    except sqlite3.Error:
        return False
    if row is None or row[0] is None:
        return False
    return isinstance(row[0], int) and row[0] >= _MIN_MILLIS_SCALE


def _pushdown_window(
    conn: sqlite3.Connection, table: str, window: _Window
) -> _Window:
    """计算 SQL 下推窗口。

    ``time_created`` 只是 payload 时间戳的代理值，因此左右各放宽一天；
    若列值明显不是毫秒级，则放弃下推、扫描全表。
    """
    if window.is_unbounded:
        return window.widened()
    if _time_created_looks_like_millis(conn, table):
        return window.widened()
    return _UNBOUNDED


def _load_v1_entries(
    conn: sqlite3.Connection, window: _Window, seen: set[str]
) -> list[_Usage]:
    """读取 v1 ``message`` 表。"""
    columns = table_columns(conn, "message")
    if not {"id", "session_id", "data"} <= columns:
        return []

    pushdown = _pushdown_window(conn, "message", window)
    has_time_created = "time_created" in columns

    if has_time_created and pushdown.start is not None and pushdown.end is not None:
        sql = (
            "SELECT id, session_id, data FROM message WHERE id IN "
            "(SELECT id FROM message WHERE time_created >= ?1 AND time_created < ?2)"
        )
        params: tuple = (pushdown.start, pushdown.end)
    elif has_time_created and pushdown.start is not None:
        sql = (
            "SELECT id, session_id, data FROM message WHERE id IN "
            "(SELECT id FROM message WHERE time_created >= ?1)"
        )
        params = (pushdown.start,)
    elif has_time_created and pushdown.end is not None:
        sql = (
            "SELECT id, session_id, data FROM message WHERE id IN "
            "(SELECT id FROM message WHERE time_created < ?1)"
        )
        params = (pushdown.end,)
    else:
        sql = "SELECT id, session_id, data FROM message"
        params = ()

    try:
        cursor = conn.execute(sql, params)
    except sqlite3.Error as exc:
        logger.warning("[opencode] 读取 message 表失败: %s", exc)
        return []

    entries: list[_Usage] = []
    for row in cursor:
        message_id, session_id, data = row[0], row[1], row[2]
        if not isinstance(message_id, str) or not isinstance(session_id, str):
            continue
        if not isinstance(data, str):
            continue
        if not window.is_unbounded:
            millis = _extract_message_timestamp_ms(data)
            if millis is not None and not window.contains(millis):
                continue
        try:
            payload = json.loads(data)
        except (ValueError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        model_id, provider_id = _legacy_model_and_provider(payload)
        timestamp_ms = _created_ms(payload)
        if timestamp_ms is None:
            # v1 没有列级时间兜底：时间缺失的记录会被归到 1970-01-01，
            # 最终在日期过滤阶段被丢弃。
            timestamp_ms = 0
        usage = _build_usage(
            payload,
            model_id=model_id,
            provider_id=provider_id,
            timestamp_ms=timestamp_ms,
            message_id=message_id,
            session_id=session_id,
        )
        if usage is None:
            continue
        if message_id in seen:
            continue
        seen.add(message_id)
        entries.append(usage)
    return entries


def _load_v2_entries(
    conn: sqlite3.Connection, window: _Window, seen: set[str]
) -> list[_Usage]:
    """读取 v2 ``session_message`` 表（只取 ``type == "assistant"``）。"""
    columns = table_columns(conn, "session_message")
    if not {"id", "session_id", "type", "data"} <= columns:
        return []

    has_time_created = "time_created" in columns
    has_seq = "seq" in columns
    pushdown = _pushdown_window(conn, "session_message", window)

    select_columns = ["id", "session_id", "type", "data"]
    select_columns.append("time_created" if has_time_created else "NULL")
    if has_seq:
        select_columns.append("seq")
    sql = f"SELECT {', '.join(select_columns)} FROM session_message"

    if has_time_created and pushdown.start is not None and pushdown.end is not None:
        sql += " WHERE time_created >= ?1 AND time_created < ?2"
        params: tuple = (pushdown.start, pushdown.end)
    elif has_time_created and pushdown.start is not None:
        sql += " WHERE time_created >= ?1"
        params = (pushdown.start,)
    elif has_time_created and pushdown.end is not None:
        sql += " WHERE time_created < ?1"
        params = (pushdown.end,)
    else:
        params = ()

    try:
        cursor = conn.execute(sql, params)
    except sqlite3.Error as exc:
        logger.warning("[opencode] 读取 session_message 表失败: %s", exc)
        return []

    fork_copies = _fork_copy_cutoffs(conn)

    entries: list[_Usage] = []
    for row in cursor:
        message_id, session_id, message_type, data = row[0], row[1], row[2], row[3]
        time_created = row[4]
        seq = row[5] if has_seq else None

        if not isinstance(message_id, str) or not isinstance(session_id, str):
            continue
        if message_type != "assistant":
            continue
        if not isinstance(data, str):
            continue
        if _is_fork_copy(fork_copies, session_id, seq):
            continue
        if not window.is_unbounded:
            millis = _extract_message_timestamp_ms(data)
            if millis is not None and not window.contains(millis):
                continue
        try:
            payload = json.loads(data)
        except (ValueError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue

        model_id, provider_id = _v2_model_and_provider(payload)
        timestamp_ms = _created_ms(payload)
        if timestamp_ms is None:
            # v2 允许回退到 time_created 列（v1 不允许）。
            if isinstance(time_created, int) and not isinstance(time_created, bool):
                timestamp_ms = time_created if time_created > 0 else 0
            else:
                timestamp_ms = 0
        usage = _build_usage(
            payload,
            model_id=model_id,
            provider_id=provider_id,
            timestamp_ms=timestamp_ms,
            message_id=message_id,
            session_id=session_id,
        )
        if usage is None:
            continue
        if message_id in seen:
            continue
        seen.add(message_id)
        entries.append(usage)
    return entries


def _load_database_entries(db_path: Path, window: _Window) -> list[_Usage]:
    """从 SQLite 读取 v1 + v2 的消息用量。"""
    conn = open_sqlite_readonly(db_path)
    if conn is None:
        logger.warning("[opencode] 无法以只读方式打开数据库: %s", db_path)
        return []
    try:
        seen: set[str] = set()
        entries: list[_Usage] = []
        # 顺序与 ccusage 一致：v1 先读，v2 后读，同 id 时 v1 保留。
        entries.extend(_load_v1_entries(conn, window, seen))
        entries.extend(_load_v2_entries(conn, window, seen))
        return entries
    except sqlite3.Error as exc:
        logger.warning("[opencode] 读取数据库失败 %s: %s", db_path, exc)
        return []
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 旧 JSON 文件读取
# ---------------------------------------------------------------------------


def _load_message_file_entries(
    opencode_dir: Path, window: _Window, seen: set[str]
) -> tuple[list[_Usage], int]:
    """读取 ``storage/message/**/*.json`` 旧消息文件。

    Returns:
        ``(用量列表, 扫描到的消息文件数)``
    """
    messages_dir = opencode_dir / "storage" / "message"
    files = collect_files(messages_dir, (".json",))
    if not files:
        return [], 0

    # 数据库已经覆盖过的 message id 不必再读文件（文件名 stem 即 message id）。
    files = [path for path in files if path.stem not in seen]

    entries: list[_Usage] = []
    for path in files:
        try:
            raw = path.read_bytes()
        except OSError as exc:
            logger.debug("[opencode] 读取消息文件失败 %s: %s", path, exc)
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            # 与 serde_json 一致：非 UTF-8 内容直接判为解析失败。
            continue
        if not window.is_unbounded:
            millis = _extract_message_timestamp_ms(text)
            if millis is not None and not window.contains(millis):
                continue
        try:
            payload = json.loads(text)
        except (ValueError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue

        model_id, provider_id = _legacy_model_and_provider(payload)
        timestamp_ms = _created_ms(payload) or 0
        message_id = lenient_str(payload.get("id"))
        session_id = lenient_str(payload.get("sessionID"))
        usage = _build_usage(
            payload,
            model_id=model_id,
            provider_id=provider_id,
            timestamp_ms=timestamp_ms,
            message_id=message_id,
            session_id=session_id,
        )
        if usage is None:
            continue
        if message_id is not None:
            if message_id in seen:
                continue
            seen.add(message_id)
        entries.append(usage)
    return entries, len(files)


# ---------------------------------------------------------------------------
# 对外入口
# ---------------------------------------------------------------------------


def read_opencode_records(since_date: date, until_date: date) -> AgentReadResult:
    """读取 OpenCode 的 Token 用量。

    Args:
        since_date: 起始日期（含）。
        until_date: 结束日期（含）。

    Returns:
        AgentReadResult：records 为按 (日期, 模型) 聚合后的记录。
    """
    result = AgentReadResult()
    start_ms, end_ms = date_range_to_ms_bounds(since_date, until_date)
    window = _Window(start=start_ms, end=end_ms)
    since_str = since_date.isoformat()
    until_str = until_date.isoformat()

    rows: list[dict] = []
    global_seen: set[str] = set()
    scanned_dirs = 0
    db_count = 0
    file_count = 0

    for opencode_dir in _opencode_data_dirs():
        scanned_dirs += 1
        dir_seen: set[str] = set()

        db_path = _db_path(opencode_dir)
        db_entries: list[_Usage] = []
        if db_path is not None:
            db_count += 1
            db_entries = _load_database_entries(db_path, window)
            dir_seen.update(entry.message_id for entry in db_entries if entry.message_id)

        file_entries, scanned_files = _load_message_file_entries(
            opencode_dir, window, dir_seen
        )
        file_count += scanned_files

        for usage in db_entries + file_entries:
            if usage.message_id is not None:
                if usage.message_id in global_seen:
                    continue
                global_seen.add(usage.message_id)

            record_day = epoch_ms_to_local_date(usage.timestamp_ms)
            if not (since_str <= record_day <= until_str):
                continue

            rows.append(
                {
                    "record_date": record_day,
                    "model": usage.model,
                    "input_tokens": usage.input_tokens,
                    "output_tokens": usage.output_tokens,
                    "cache_creation_tokens": usage.cache_creation_tokens,
                    "cache_read_tokens": usage.cache_read_tokens,
                    "extra_total_tokens": usage.extra_total_tokens,
                    "total_cost": usage.cost,
                }
            )

    result.records = aggregate_records(rows, source=SOURCE, source_raw=SOURCE_RAW)
    logger.info(
        "[opencode] 原生读取 %s 个数据目录（%s 个数据库，读取 %s 个消息文件），聚合 %s 条记录",
        scanned_dirs,
        db_count,
        file_count,
        len(result.records),
    )
    return result

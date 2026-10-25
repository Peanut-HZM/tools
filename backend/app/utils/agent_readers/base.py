"""Agent 原生 Token 用量读取器 — 公共基础能力

本模块提供各 Agent 读取器共享的底层能力，目标是在**不依赖 ccusage CLI** 的
前提下，复现 ccusage 的取数语义（路径发现 / 字段映射 / 去重 / 总数口径），
使 Token 消耗统计可以完全原生化。

与 ccusage 对齐的关键语义（见 ccusage rust/adapters + rust/crates/ccusage-core）：

1. **总 token 口径**统一为 ``input + output + cache_creation + cache_read + extra``
   （extra 为"已知存在但无法归入四类"的桶，仅计入 total，不单独展示）。
2. **input 是否含 cache** 各 Agent 不同，读取器必须按 Agent 语义扣减，
   否则会重复统计（zcode / copilot / grok / gemini 的 input 均**含** cache）。
3. **时间戳**只接受 ccusage 支持的 4 种 ISO-8601 形状，长度必须为 20/24/25/29。
4. **日期归桶**使用本机时区的自然日（ccusage ``format_date_tz`` 默认系统时区）。
5. **单行解析失败只丢该行**，不得中断整个文件/目录的读取。
6. **文件遍历**按扩展名精确匹配、递归、只取文件、排序后去重。
"""

from __future__ import annotations

import json
import logging
import os
import platform
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 时间戳 / 日期
# ---------------------------------------------------------------------------

# ccusage parse_ts_timestamp 只接受这 4 种长度：秒级 / 毫秒级，带 Z 或 ±HH:MM
_ISO_TS_LENGTHS = (20, 24, 25, 29)


def parse_iso_timestamp_ms(value: Any) -> Optional[int]:
    """解析严格 ISO-8601 时间戳为 epoch 毫秒。

    与 ccusage ``parse_ts_timestamp`` 对齐：只接受长度为 20 / 24 / 25 / 29 的
    ``YYYY-MM-DDTHH:MM:SS[.mmm](Z|±HH:MM)``；不接受裸 epoch 数字、不接受
    无时区后缀、不接受小写 z/t、不接受超过 3 位小数、不接受用空格代替
    ``T`` 的形式。

    Args:
        value: 待解析值，非字符串或长度不符直接返回 None。

    Returns:
        epoch 毫秒；无法解析时返回 None。
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    length = len(text)
    if length not in _ISO_TS_LENGTHS:
        return None

    # 固定位置的分隔符必须是 - - T : :
    if (
        text[4] != "-"
        or text[7] != "-"
        or text[10] != "T"
        or text[13] != ":"
        or text[16] != ":"
    ):
        return None

    # 毫秒部分（长度 24 / 29）必须恰好 3 位
    if length in (24, 29):
        if text[19] != "." or not text[20:23].isdigit():
            return None

    # 时区后缀
    if length in (20, 24):
        tz_char = text[19] if length == 20 else text[23]
        if tz_char not in ("Z", "+", "-"):
            return None
    else:
        # ±HH:MM 形式：长度 25 从第 19 位开始，长度 29 从第 23 位开始
        tz_start = 19 if length == 25 else 23
        sign = text[tz_start]
        if sign not in ("+", "-"):
            return None
        hours = text[tz_start + 1 : tz_start + 3]
        minutes = text[tz_start + 4 : tz_start + 6]
        if not (hours.isdigit() and minutes.isdigit()):
            return None
        if int(hours) > 23 or int(minutes) > 59:
            return None

    try:
        normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        # ccusage 要求显式时区；缺时区视为非法
        return None
    return int(parsed.timestamp() * 1000)


def epoch_ms_to_local_date(timestamp_ms: int) -> str:
    """将 epoch 毫秒转换为本机时区的自然日（``YYYY-MM-DD``）。

    对齐 ccusage ``format_date_tz`` 的默认行为（系统时区）。
    """
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d")


def epoch_seconds_to_ms(value: float) -> int:
    """epoch 秒/毫秒自动判定为毫秒。

    ccusage 对 goose / hermes / kilo 等来源使用 ``> 1e12`` 判定毫秒的启发式。
    """
    if value > 1_000_000_000_000:
        return int(value)
    return int(value * 1000)


def date_range_to_ms_bounds(since_date: date, until_date: date) -> tuple[int, int]:
    """把日期区间转换为左闭右开的 epoch 毫秒区间。"""
    start = datetime.combine(since_date, datetime.min.time())
    end = datetime.combine(until_date + timedelta(days=1), datetime.min.time())
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


# ---------------------------------------------------------------------------
# 真实用户主目录
# ---------------------------------------------------------------------------

def real_home() -> Path:
    """获取真实用户主目录，绕过 ``config.py`` 对 HOME 的覆盖。

    ``app/config/config.py`` 在非桌面模式下会把 ``HOME`` 改写为
    ``backend/data/cache``，导致需要读取用户目录的模块拿不到正确路径。
    与 ``zcode_usage_reader._get_real_home`` 保持一致的跨平台策略：

    - Windows：通过 ``%USERPROFILE%`` 获取（无 pwd 模块）
    - macOS/Linux：通过 pwd 数据库查询真实家目录（不依赖 $HOME）
    """
    if platform.system() == "Windows":
        userprofile = os.environ.get("USERPROFILE", "")
        if userprofile:
            return Path(userprofile)
        return Path.home()

    try:
        import pwd  # Unix 独有
    except ImportError:  # pragma: no cover - Windows 平台
        pwd = None  # type: ignore[assignment]

    if pwd is not None:
        try:
            return Path(pwd.getpwuid(os.getuid()).pw_dir)
        except (KeyError, OSError):
            pass
    return Path.home()


def env_path_list(env_name: str) -> list[Path]:
    """解析逗号分隔的环境变量路径列表，返回已存在的目录（去重、保持顺序）。"""
    raw = os.environ.get(env_name, "")
    result: list[Path] = []
    seen: set[str] = set()
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        path = Path(item).expanduser()
        key = os.path.normcase(str(path))
        if path.is_dir() and key not in seen:
            seen.add(key)
            result.append(path)
    return result


# ---------------------------------------------------------------------------
# 文件遍历与 JSONL 解析
# ---------------------------------------------------------------------------

def collect_files(root: Path, extensions: Iterable[str]) -> list[Path]:
    """递归收集指定扩展名的文件，按路径排序。

    对齐 ccusage ``collect_files_with_extension``：递归、扩展名精确匹配
    （大小写敏感）、只取文件、缺失目录静默返回空列表。
    """
    wanted = {ext.lower() for ext in extensions}
    found: list[Path] = []
    if not root.is_dir():
        return found
    try:
        entries = sorted(root.iterdir(), key=lambda p: str(p))
    except OSError:
        return found
    for entry in entries:
        try:
            if entry.is_dir():
                found.extend(collect_files(entry, wanted))
            elif entry.is_file() and entry.suffix.lower() in wanted:
                found.append(entry)
        except OSError:
            continue
    return sorted(set(found), key=lambda p: str(p))


def iter_jsonl(path: Path) -> Iterator[dict]:
    """逐行解析 JSONL，跳过无法解析的行。

    对齐 ccusage ``jsonl::records``：单行解析失败只丢该行，绝不中断整个文件。
    """
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except (ValueError, TypeError):
                    continue
                if isinstance(obj, dict):
                    yield obj
    except OSError as exc:
        logger.debug("[agent-readers] 读取文件失败 %s: %s", path, exc)


# ---------------------------------------------------------------------------
# 宽松字段读取（对齐 ccusage 的 lenient deserializer）
# ---------------------------------------------------------------------------

def lenient_u64(value: Any) -> int:
    """宽松读取无符号整数：非整数/负数/字符串/None 一律视为 0。"""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value if value > 0 else 0
    if isinstance(value, float):
        return int(value) if value > 0 else 0
    return 0


def lenient_f64(value: Any) -> float:
    """宽松读取浮点数：非数字返回 0.0。"""
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def lenient_str(value: Any) -> Optional[str]:
    """宽松读取非空字符串：去除首尾空白，空串视为缺失。"""
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return None


def lenient_obj(value: Any) -> Optional[dict]:
    """宽松读取对象：非 dict 返回 None。"""
    return value if isinstance(value, dict) else None


def first_present(mapping: dict, keys: Iterable[str]) -> Any:
    """按顺序返回第一个存在且非 None 的字段值。"""
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


# ---------------------------------------------------------------------------
# 总 token 口径
# ---------------------------------------------------------------------------

def total_usage_tokens(
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int,
    cache_read_tokens: int,
) -> int:
    """四个可见桶之和（饱和加法，等价 ccusage ``total_usage_tokens``）。"""
    return (
        max(0, input_tokens)
        + max(0, output_tokens)
        + max(0, cache_creation_tokens)
        + max(0, cache_read_tokens)
    )


def apply_total_fallback(
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int,
    cache_read_tokens: int,
    extra_total_tokens: int,
    total_tokens: int,
) -> tuple[int, int, int, int, int]:
    """对齐 ccusage ``apply_total_token_fallback``。

    当来源自报的总 token 大于各分桶之和时，差值先补进 ``output_tokens``
    （当 output 为 0），否则累加到不可见的 ``extra`` 桶 —— 两种情况下对外
    呈现的总 token 都不变。

    Returns:
        ``(input, output, cache_creation, cache_read, extra)``
    """
    known = total_usage_tokens(
        input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens
    ) + max(0, extra_total_tokens)
    missing = max(0, total_tokens - known)
    if missing == 0:
        return (
            input_tokens,
            output_tokens,
            cache_creation_tokens,
            cache_read_tokens,
            extra_total_tokens,
        )
    if output_tokens == 0:
        return (
            input_tokens,
            missing,
            cache_creation_tokens,
            cache_read_tokens,
            extra_total_tokens,
        )
    return (
        input_tokens,
        output_tokens,
        cache_creation_tokens,
        cache_read_tokens,
        extra_total_tokens + missing,
    )


def split_inclusive_input(
    raw_input: int, cache_read: int, cache_creation: int
) -> tuple[int, int, int]:
    """把"含 cache"的 input 拆分为 (净 input, cache_read, cache_creation)。

    zcode / copilot / grok / gemini 的 input 字段**包含** cache 部分，
    直接使用会导致 cache 被重复统计，必须先扣减。

    扣减顺序与 ccusage zcode 适配器一致：cache_read 先封顶到 input，
    cache_creation 再封顶到 input - cache_read。
    """
    bounded_read = max(0, min(cache_read, raw_input))
    bounded_creation = max(0, min(cache_creation, raw_input - bounded_read))
    net_input = max(0, raw_input - bounded_read - bounded_creation)
    return net_input, bounded_read, bounded_creation


# ---------------------------------------------------------------------------
# SQLite 只读打开
# ---------------------------------------------------------------------------

def open_sqlite_readonly(db_path: Path) -> Optional[sqlite3.Connection]:
    """以只读模式打开 SQLite，失败返回 None。

    - ``mode=ro`` + URI：不会创建 ``-wal`` / ``-shm`` 文件，也不会写 journal
    - ``busy_timeout=5000``：数据库被工具占用时等待而不是立刻报错
    - ``query_only``：连接级只读保护

    对齐 ccusage 各 SQLite 适配器的连接策略。
    """
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
    except sqlite3.Error as exc:
        logger.debug("[agent-readers] 打开数据库失败 %s: %s", db_path, exc)
        return None
    try:
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA query_only = ON")
    except sqlite3.Error as exc:
        logger.debug("[agent-readers] 设置数据库 PRAGMA 失败 %s: %s", db_path, exc)
        conn.close()
        return None
    return conn


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    """返回表的列名集合；表不存在时返回空集合。"""
    try:
        cursor = conn.execute(f'SELECT * FROM "{table}" LIMIT 0')
        return {desc[0] for desc in cursor.description or []}
    except sqlite3.Error:
        return set()


# ---------------------------------------------------------------------------
# 读取结果
# ---------------------------------------------------------------------------

@dataclass
class AgentReadResult:
    """单个 Agent 读取器的结果。

    Attributes:
        records: 归一化后的记录列表（已按 record_date + model 聚合）。
        errors: 结构化错误列表，格式与 ccusage 路径保持一致。
    """

    records: list[dict] = field(default_factory=list)
    errors: list[dict] = field(default_factory=list)

    def add_error(
        self,
        source: str,
        error: str,
        error_code: str,
        remediation: str = "",
        details: Optional[dict] = None,
    ) -> None:
        """追加一条结构化错误。"""
        self.errors.append(
            {
                "source": source,
                "error": error,
                "error_code": error_code,
                "remediation": remediation,
                "details": details or {},
            }
        )


def make_record(
    record_date: date,
    source: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int,
    cache_read_tokens: int,
    total_tokens: int,
    total_cost: float = 0.0,
    source_raw: str = "",
) -> dict:
    """构造一条归一化记录，字段与 ``token_usage_records`` 表结构对齐。

    ``record_date`` 允许传入 ``date`` 或 ``YYYY-MM-DD`` 字符串，统一归一化为
    ``date``，避免下游出现两种类型。
    """
    if isinstance(record_date, str):
        record_date = date.fromisoformat(record_date)
    return {
        "record_date": record_date,
        "source": source,
        "source_raw": source_raw or source,
        "model": model,
        "model_display_name": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_tokens": cache_creation_tokens,
        "cache_read_tokens": cache_read_tokens,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
    }


def aggregate_records(
    rows: Iterable[dict],
    source: str,
    source_raw: str = "",
) -> list[dict]:
    """把逐条用量行按 (日期, 模型) 聚合为最终记录。

    这是各读取器共用的收尾步骤，保证：
    - 同一 (record_date, model) 只产生一条记录（与 DB 唯一键一致）
    - total 口径统一为四项之和 + extra
    """
    buckets: dict[tuple[str, str], list[int]] = {}
    models: dict[tuple[str, str], str] = {}
    costs: dict[tuple[str, str], float] = {}

    for row in rows:
        key = (row["record_date"], row["model"])
        bucket = buckets.setdefault(key, [0, 0, 0, 0, 0])
        bucket[0] += row.get("input_tokens", 0)
        bucket[1] += row.get("output_tokens", 0)
        bucket[2] += row.get("cache_creation_tokens", 0)
        bucket[3] += row.get("cache_read_tokens", 0)
        bucket[4] += row.get("extra_total_tokens", 0)
        models[key] = row["model"]
        costs[key] = costs.get(key, 0.0) + float(row.get("total_cost", 0.0) or 0.0)

    records: list[dict] = []
    for (record_date, model), (inp, out, cc, cr, extra) in buckets.items():
        records.append(
            make_record(
                record_date=record_date,
                source=source,
                model=model,
                input_tokens=inp,
                output_tokens=out,
                cache_creation_tokens=cc,
                cache_read_tokens=cr,
                total_tokens=total_usage_tokens(inp, out, cc, cr) + extra,
                total_cost=round(costs.get((record_date, model), 0.0), 6),
                source_raw=source_raw or source,
            )
        )
    records.sort(key=lambda r: (r["record_date"], r["model"]))
    return records

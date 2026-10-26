"""OpenClaw 原生 Token 用量读取器

数据源：

- ``~/.openclaw/**`` 下所有 OpenClaw 会话文件（``*.jsonl``）
- ``OPENCLAW_DIR`` 环境变量可覆盖数据根（逗号分隔，优先级最高）

对齐 ccusage ``rust/adapters/openclaw``（本机实测基准：ccusage 20.0.42），
关键语义如下：

1. **路径发现**：``OPENCLAW_DIR`` 环境变量优先；否则依次取
   ``~/.openclaw`` / ``~/.clawdbot`` / ``~/.moltbot`` / ``~/.moldbot``
   中**实际存在**的目录（``.moltbot`` 常是 ``.openclaw`` 的软链，两者都会被
   扫描，靠去重消除重复）。
2. **文件命名**：文件名中 ``.jsonl`` 之后的后缀必须是 ``.jsonl`` /
   ``.jsonl.deleted.*`` / ``.jsonl.reset.*``（归档会话）。``.jsonl.bak`` 等
   其它后缀不算会话文件。
3. **软链跳过**：遍历目录时软链（文件与目录）一律跳过，避免同一份会话
   被重复扫描。
4. **状态化模型追踪**：按文件顺序扫描，``type == "model_change"`` 与
   ``type == "custom" && customType == "model-snapshot"`` 两条记录都会更新
   「当前模型 / 当前供应商」。
5. **模型名**：``message.modelId`` → ``message.model`` → 追踪到的当前模型 →
   ``unknown``；最终统一加上前缀 ``[openclaw] ``（与 DB 既有数据一致）。
6. **token 口径**：``usage.input`` **不含** cache，因此**不做** cache 扣减；
   ``cacheWrite`` → cache creation，``cacheRead`` → cache read。
7. **总数兜底**：来源自报的 ``totalTokens`` 大于四桶之和时，差值先补进
   ``output``（``output == 0`` 时），否则计入不可见的 ``extra`` 桶。
8. **时间戳**：**消息级** ``message.timestamp`` 优先，其次是记录级
   ``timestamp``，最后回退到文件 mtime（对齐 ccusage
   ``message.timestamp.as_ref().or(record.timestamp.as_ref())``）。
   日期按**本机时区**自然日归桶。
9. **去重**：按 ccusage ``migration_id``（会话 id + 时间戳 + 模型 + 四桶
   token + extra）去重。注意 ccusage 的 JSONL 路径**不使用**记录 id 去重
   （记录 id 只用于 SQLite 迁移副本的识别）。
10. **只统计 assistant 角色**的 usage 记录；单行解析失败只丢该行。

不内置价格表，因此 ``total_cost`` 取会话文件内自带的 ``usage.cost.total``。
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
    apply_total_fallback,
    epoch_ms_to_local_date,
    expand_user_path,
    iter_jsonl,
    lenient_f64,
    lenient_obj,
    lenient_str,
    lenient_u64,
    parse_iso_timestamp_ms,
    real_home,
)
logger = logging.getLogger(__name__)

SOURCE = "openclaw"
SOURCE_RAW = "openclaw-jsonl"

#: ccusage 对 OpenClaw 模型统一加的 store 前缀
MODEL_PREFIX = "[openclaw] "

#: 模型完全无法判定时的占位名（对齐 ccusage 的 ``unknown``）
DEFAULT_MODEL = "unknown"

#: 数据根环境变量（逗号分隔）
OPENCLAW_DIR_ENV = "OPENCLAW_DIR"

#: 默认数据根候选目录（按顺序尝试）
DEFAULT_ROOT_NAMES = (".openclaw", ".clawdbot", ".moltbot", ".moldbot")


# ---------------------------------------------------------------------------
# 路径发现
# ---------------------------------------------------------------------------


def _expand_home(raw: str) -> Path:
    """把 ``~`` 前缀展开为真实用户主目录。

    刻意**不**用 ``os.path.expanduser`` / ``Path.home()``：``config.py`` 会把
    ``HOME`` 覆盖成 ``backend/data/cache``，两者会展开到缓存目录。

    也不复用 ``base.expand_user_path``：它依赖 ``app.config.config`` 的
    ``REAL_HOME``，而该模块是**惰性导入**的 —— 若在 ``HOME`` 已被改写之后才
    首次导入，``REAL_HOME`` 会取到被改写的值。``real_home()`` 直接查 pwd
    数据库，不受 ``HOME`` 影响，结果最稳定。
    """
    if raw == "~":
        return real_home()
    if raw.startswith("~/"):
        return real_home() / raw[2:]
    return Path(raw)


def _openclaw_roots() -> list[Path]:
    """返回需要扫描的 OpenClaw 数据根目录。"""
    configured = os.environ.get(OPENCLAW_DIR_ENV, "")
    if configured.strip():
        roots: list[Path] = []
        seen: set[str] = set()
        for item in configured.split(","):
            item = item.strip()
            if not item:
                continue
            path = _expand_home(item)
            key = os.path.normcase(str(path))
            # 与 ccusage 一致：只保留真实存在的目录
            if path.is_dir() and key not in seen:
                seen.add(key)
                roots.append(path)
        return roots

    home = real_home()
    return [home / name for name in DEFAULT_ROOT_NAMES if (home / name).is_dir()]


def _is_openclaw_session_file(name: str) -> bool:
    """判断文件名是否为 OpenClaw 会话文件。

    对齐 ccusage ``is_openclaw_session_file``：以 ``.jsonl`` 首次出现位置
    为界，后缀必须是 ``.jsonl`` / ``.jsonl.deleted.*`` / ``.jsonl.reset.*``。
    """
    index = name.find(".jsonl")
    if index < 0:
        return False
    suffix = name[index:]
    return (
        suffix == ".jsonl"
        or suffix.startswith(".jsonl.deleted.")
        or suffix.startswith(".jsonl.reset.")
    )


def _collect_session_files(root: Path) -> list[Path]:
    """递归收集会话文件，跳过软链（对齐 ccusage ``collect_session_files``）。"""
    if not root.is_dir():
        return []
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # 软链目录不递归（ccusage 的 file_type.is_symlink() 直接跳过）
        dirnames[:] = [
            name for name in dirnames if not os.path.islink(os.path.join(dirpath, name))
        ]
        for filename in filenames:
            path = Path(dirpath) / filename
            try:
                if path.is_symlink():
                    continue
            except OSError:
                continue
            if _is_openclaw_session_file(filename):
                found.append(path)
    return sorted(found)


def _extract_session_id(path: Path) -> str:
    """从文件名提取会话 id（``.jsonl`` 之前的部分）。

    对齐 ccusage ``extract_session_id``：``a.jsonl.reset.X`` 与 ``a.jsonl``
    共享会话 id ``a``。
    """
    name = path.name
    index = name.find(".jsonl")
    if index < 0:
        return name
    stem = name[:index]
    return stem if stem else name


# ---------------------------------------------------------------------------
# 记录解析
# ---------------------------------------------------------------------------


def _model_change_source(record: dict) -> tuple[Optional[str], Optional[str]]:
    """提取模型变更记录里的 (模型, 供应商)。

    对齐 ccusage ``model_change_source``：``data`` 块存在时**只**看
    ``data``，否则看记录根部的 ``modelId`` / ``model`` / ``provider``。
    """
    source = lenient_obj(record.get("data"))
    if source is not None:
        model_id = lenient_str(source.get("modelId"))
        model = lenient_str(source.get("model"))
        provider = lenient_str(source.get("provider"))
    else:
        model_id = lenient_str(record.get("modelId"))
        model = lenient_str(record.get("model"))
        provider = lenient_str(record.get("provider"))
    return model_id or model, provider


def _timestamp_ms(value: Any) -> Optional[int]:
    """把时间戳值解析为 epoch 毫秒。

    对齐 ccusage ``timestamp_from_value``：整数按 **毫秒** 解释（负数视为
    非法），浮点先截断再按毫秒解释，字符串走严格 ISO-8601 解析。
    """
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        truncated = int(value)
        return truncated if truncated >= 0 else None
    if isinstance(value, str):
        return parse_iso_timestamp_ms(value)
    return None


def _file_mtime_ms(path: Path) -> int:
    """文件 mtime（epoch 毫秒），取不到时返回 0。"""
    try:
        return int(path.stat().st_mtime * 1000)
    except OSError:
        return 0


def _is_model_change(record: dict) -> bool:
    """判断记录是否为模型变更事件（对齐 ccusage ``is_model_change``）。"""
    record_type = record.get("type")
    if record_type == "model_change":
        return True
    return record_type == "custom" and record.get("customType") == "model-snapshot"


def _usage_cost(usage: dict) -> Optional[float]:
    """提取会话自带的成本（``usage.cost.total``），不存在时返回 None。"""
    cost = lenient_obj(usage.get("cost"))
    if cost is None or "total" not in cost:
        return None
    return lenient_f64(cost.get("total"))


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def read_openclaw_records(since_date: date, until_date: date) -> AgentReadResult:
    """读取 OpenClaw 的 Token 用量。

    Args:
        since_date: 起始日期（含）。
        until_date: 结束日期（含）。

    Returns:
        AgentReadResult：records 为按 (日期, 模型) 聚合后的记录。
    """
    result = AgentReadResult()
    roots = _openclaw_roots()
    if not roots:
        return result

    since_str = since_date.isoformat()
    until_str = until_date.isoformat()

    rows: list[dict] = []
    # ccusage 用 migration_id 去重：会话 id + 时间戳 + 模型 + 四桶 + extra
    seen: set[tuple] = set()
    file_count = 0
    record_count = 0

    for root in roots:
        for path in _collect_session_files(root):
            file_count += 1
            session_id = _extract_session_id(path)
            fallback_ts = _file_mtime_ms(path)
            current_model: Optional[str] = None
            current_provider: Optional[str] = None

            for record in iter_jsonl(path):
                # 1) 模型 / 供应商状态追踪
                if _is_model_change(record):
                    model, provider = _model_change_source(record)
                    if model is not None:
                        current_model = model
                    if provider is not None:
                        current_provider = provider
                    continue

                # 2) 只处理 message 记录
                if record.get("type") != "message":
                    continue
                message = lenient_obj(record.get("message"))
                if message is None:
                    continue
                if message.get("role") != "assistant":
                    continue
                usage = lenient_obj(message.get("usage"))
                if usage is None:
                    continue

                input_tokens = lenient_u64(usage.get("input"))
                output_tokens = lenient_u64(usage.get("output"))
                cache_creation = lenient_u64(usage.get("cacheWrite"))
                cache_read = lenient_u64(usage.get("cacheRead"))
                declared_total = lenient_u64(usage.get("totalTokens"))

                # 3) 总数兜底（ccusage apply_total_token_fallback）
                (
                    input_tokens,
                    output_tokens,
                    cache_creation,
                    cache_read,
                    extra_total_tokens,
                ) = apply_total_fallback(
                    input_tokens,
                    output_tokens,
                    cache_creation,
                    cache_read,
                    0,
                    declared_total,
                )
                if (
                    input_tokens
                    + output_tokens
                    + cache_creation
                    + cache_read
                    + extra_total_tokens
                ) == 0:
                    continue

                # 4) 时间戳：消息级优先，其次记录级，最后文件 mtime
                timestamp_ms = _timestamp_ms(message.get("timestamp"))
                if timestamp_ms is None:
                    timestamp_ms = _timestamp_ms(record.get("timestamp"))
                if timestamp_ms is None:
                    timestamp_ms = fallback_ts

                # 5) 模型名（ccusage 优先级 + store 前缀）
                model = (
                    lenient_str(message.get("modelId"))
                    or lenient_str(message.get("model"))
                    or current_model
                    or DEFAULT_MODEL
                )
                provider = lenient_str(message.get("provider")) or current_provider

                record_day = epoch_ms_to_local_date(timestamp_ms)
                if not (since_str <= record_day <= until_str):
                    continue

                # 6) 去重（对齐 ccusage migration_id）
                cost = _usage_cost(usage)
                cost_value = float(cost) if cost is not None else 0.0
                dedup_key = (
                    session_id,
                    timestamp_ms,
                    f"{MODEL_PREFIX}{model}",
                    input_tokens,
                    output_tokens,
                    cache_creation,
                    cache_read,
                    extra_total_tokens,
                    cost_value,
                )
                if dedup_key in seen:
                    continue
                seen.add(dedup_key)

                record_count += 1
                rows.append(
                    {
                        "record_date": record_day,
                        "model": f"{MODEL_PREFIX}{model}",
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cache_creation_tokens": cache_creation,
                        "cache_read_tokens": cache_read,
                        "extra_total_tokens": extra_total_tokens,
                        "total_cost": cost_value,
                        # 供应商对齐 ccusage 的 data.version；base.aggregate_records
                        # 只读取上面的 token 字段，provider 不进入 DB 记录
                        "provider": provider or "",
                    }
                )

    result.records = aggregate_records(rows, source=SOURCE, source_raw=SOURCE_RAW)
    logger.info(
        "[openclaw] 原生读取 %s 个会话文件 / %s 条用量记录，聚合 %s 条结果",
        file_count,
        record_count,
        len(result.records),
    )
    return result

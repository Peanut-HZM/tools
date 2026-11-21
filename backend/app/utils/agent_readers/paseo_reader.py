"""Paseo 原生 Token 用量读取器

数据源：``~/.paseo/usage/acp-usage.jsonl``（由 Paseo 的 ACP 中间层写入）。

背景
----
Paseo 托管的 ACP Agent（GLM / Kimi / Cursor / Kiro / MiniMax Code 等）
通过 ACP 协议的 ``session/prompt`` 响应上报 token 用量：

.. code-block:: text

    { "stopReason": "end_turn",
      "usage": { "inputTokens": N, "outputTokens": N, "totalTokens": N,
                 "cachedReadTokens": N, "cachedWriteTokens": N,
                 "thoughtTokens": N } }

但这条数据**只存在于内存**：

1. Paseo 服务端把 usage 存进 ``agent.lastUsage``（内存对象），
   ``agent-storage.ts`` 的落盘 schema 里没有任何 usage 列，重建 agent 时
   直接丢弃；
2. ACP Agent 自己也不落盘 usage —— glm-acp-agent 的会话文件
   （``~/.local/state/glm-acp-agent/sessions/*.json``）里每条 message 只有
   ``role`` / ``content`` / ``reasoning_content`` / ``tool_calls``，
   **没有 token 字段**。

唯一能拿到 token 的位置是 ACP 通信的中间层。因此由
``~/.paseo/providers/glm-acp-agent-pmhub.mjs`` 之类的 shim 在转发
``session/prompt`` 响应时把 usage 追加写入本文件，Toolbox 再从本文件采集。

口径说明
--------
1. **``inputTokens`` 是净输入**（不含 cache），与 opencode / minimax 一致，
   因此**不需要**做 cache 扣减。
2. **``cachedReadTokens`` → cache_read**，**``cachedWriteTokens`` →
   cache_creation**。
3. **``thoughtTokens``（推理 token）属于 output 的一部分**，按全站口径计入
   output（与 Anthropic 的 ``output_tokens_details.thinking_tokens`` 同义）。
   ACP 规范里 ``outputTokens`` 不含 thoughtTokens，所以这里要加上。
4. **``totalTokens`` 兜底**：ACP 自报的 total 可能与四桶之和不等（不同
   实现的补齐口径不一致），统一用 ``apply_total_fallback`` 对齐 ccusage
   行为——差值补进 output（output 为 0 时）或 extra 桶。
5. **单行解析失败只丢该行**，绝不中断整体。
6. **日期归桶**用行上的 ``ts``（ISO-8601 UTC）转换到**本机时区**自然日。
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from app.utils.agent_readers.base import (
    AgentReadResult,
    aggregate_records,
    apply_total_fallback,
    expand_user_path,
    real_home,
)

logger = logging.getLogger(__name__)

SOURCE = "paseo"
SOURCE_RAW = "paseo-acp-usage"

#: 默认的用量文件路径（相对真实家目录，绕过 config.py 对 HOME 的覆盖）
_USAGE_RELATIVE = Path(".paseo") / "usage" / "acp-usage.jsonl"

#: 环境变量可覆盖（便于测试用冻结快照做确定性对账）
_USAGE_FILE_ENV = "PASEO_USAGE_FILE"

#: 读取的最大文件大小上限，避免异常膨胀的日志文件拖垮同步
_MAX_FILE_BYTES = 64 * 1024 * 1024

#: 已有**原生读取器**的 provider id。
#:
#: 这些 Agent（Paseo 也托管了其中几个）自己会把用量落盘到本地数据库/日志，
#: 原生读取器已经在采集。若它们同时被 ACP recorder 记录，会**重复统计**，
#: 导致汇总翻倍——所以 paseo 读取器必须跳过这些 provider。
#:
#: 判断依据是本机实测：kimi / minimax 的原生读取器都能读到数据（见
#: tests/test_paseo_reader.py 的登记一致性测试）。
_NATIVELY_COVERED_PROVIDERS: frozenset[str] = frozenset(
    {"claude", "codex", "copilot", "kimi", "zcode", "minimax", "openclaw", "opencode"}
)


def _usage_file_candidates() -> list[Path]:
    """返回用量文件候选路径（按优先级）。

    ``PASEO_USAGE_FILE`` 优先，可指向冻结快照做确定性对账；
    未设置时回退到 ``~/.paseo/usage/acp-usage.jsonl``。
    """
    configured = os.environ.get(_USAGE_FILE_ENV, "").strip()
    if configured:
        return [expand_user_path(item) for item in configured.split(",") if item.strip()]

    home = real_home()
    return [home / _USAGE_RELATIVE]


def _parse_ts(value: Any) -> Optional[datetime]:
    """解析行上的 ``ts`` 字段（ISO-8601 字符串）。

    解析不了返回 None——该行会被跳过（宁可少一条，也不猜时间戳）。
    """
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _non_negative_int(value: Any) -> int:
    """把 JSON 值转成非负整数；非法值按 0 处理。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    if value != value or value in (float("inf"), float("-inf")):  # NaN / inf
        return 0
    return max(0, int(value))


def _row_to_usage(row: dict) -> Optional[dict]:
    """把一行 JSONL 转成归一化的用量桶。

    返回 None 表示该行不可用（缺时间戳等），调用方负责跳过。
    """
    ts = _parse_ts(row.get("ts"))
    if ts is None:
        return None

    model = row.get("model")
    if not isinstance(model, str) or not model.strip():
        model = "unknown"

    provider = row.get("provider")
    if not isinstance(provider, str) or not provider.strip():
        provider = "unknown"

    input_tokens = _non_negative_int(row.get("inputTokens"))
    output_tokens = _non_negative_int(row.get("outputTokens"))
    cache_read = _non_negative_int(row.get("cachedReadTokens"))
    cache_creation = _non_negative_int(row.get("cachedWriteTokens"))
    thought = _non_negative_int(row.get("thoughtTokens"))
    reported_total = _non_negative_int(row.get("totalTokens"))

    # thoughtTokens 属于 output 的一部分（ACP 的 outputTokens 不含推理 token）
    output_tokens += thought

    # 自报 total 与四桶之和不一致时，用统一兜底补齐（extra 桶只计入 total）
    (
        input_tokens,
        output_tokens,
        cache_creation,
        cache_read,
        extra,
    ) = apply_total_fallback(
        input_tokens,
        output_tokens,
        cache_creation,
        cache_read,
        0,
        reported_total,
    )

    return {
        # ts 是 UTC ISO-8601，必须转成本机时区再取自然日
        # （否则 UTC 00:00~08:00 的记录会被归到前一天）。
        "record_date": datetime.fromtimestamp(ts.timestamp()).date(),
        "model": model,
        "provider": provider,
        "channel": provider,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_creation_tokens": cache_creation,
        "cache_read_tokens": cache_read,
        "extra_total_tokens": extra,
        "total_cost": 0.0,
    }


def read_paseo_records(since_date: date, until_date: date) -> AgentReadResult:
    """读取 Paseo ACP Agent 的 Token 用量。

    Args:
        since_date: 起始日期（含）。
        until_date: 结束日期（含）。

    Returns:
        AgentReadResult：records 为按 (日期, 模型) 聚合后的记录。
    """
    result = AgentReadResult()

    usage_path: Optional[Path] = None
    for candidate in _usage_file_candidates():
        if candidate.is_file():
            usage_path = candidate
            break

    if usage_path is None:
        # 未启用 Paseo 用量记录不是异常：与 claude / codex 读取器一致，
        # 数据文件缺失时静默跳过，不计入同步告警
        logger.info(
            "[paseo] 未找到用量文件，跳过（候选: %s）",
            ", ".join(str(p) for p in _usage_file_candidates()),
        )
        return result

    try:
        if usage_path.stat().st_size > _MAX_FILE_BYTES:
            result.add_error(
                source=SOURCE,
                error=f"用量文件过大：{usage_path}",
                error_code="FILE_TOO_LARGE",
                remediation="请清理或轮转 Paseo 用量日志",
                details={"path": str(usage_path), "size": usage_path.stat().st_size},
            )
            return result

        text = usage_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        result.add_error(
            source=SOURCE,
            error=f"读取用量文件失败：{exc}",
            error_code="FILE_READ_ERROR",
            remediation="请检查文件权限",
            details={"path": str(usage_path)},
        )
        return result

    rows: list[dict] = []
    skipped = 0
    duplicates = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except ValueError:
            # 单行损坏只丢该行，绝不中断整体
            skipped += 1
            continue
        if not isinstance(payload, dict):
            skipped += 1
            continue
        usage = _row_to_usage(payload)
        if usage is None:
            skipped += 1
            continue
        # 已有原生读取器覆盖的 provider 跳过，避免与原生数据**重复统计**
        if usage["provider"] in _NATIVELY_COVERED_PROVIDERS:
            duplicates += 1
            continue
        # 日期区间过滤（与其它读取器一致：区间外的记录不进统计）
        if not (since_date <= usage["record_date"] <= until_date):
            continue
        rows.append(usage)

    result.records = aggregate_records(rows, source=SOURCE, source_raw=SOURCE_RAW)
    logger.info(
        "[paseo] 原生读取 %s，聚合 %s 条记录（跳过 %s 条无效行，%s 条与原生读取器重复）",
        usage_path,
        len(result.records),
        skipped,
        duplicates,
    )
    return result

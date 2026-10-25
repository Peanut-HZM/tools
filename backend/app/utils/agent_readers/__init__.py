"""Agent 原生 Token 用量读取器注册表

统一入口：``read_all_agents(since_date, until_date)``。

设计要点（与「不重复统计」直接相关）：

1. **每个 Agent 只有一个读取器**，source id 与 ccusage 的 agent id 完全一致
   （``claude`` / ``codex`` / ``kimi`` / ``zcode`` / ``minimax``）。
   因为 ``token_usage_records`` 的唯一键是
   ``(user_id, device_id, record_date, source, model)``，source id 一致就意味着
   **原生读取器与 ccusage 写的是同一批行**，切换实现不会产生重复，
   只会互相覆盖（覆盖期间也不会出现两份）。
2. **读取器只产出 source，不产出 tool 维度**：tool_id / tool_name 统一由
   ``token_usage_sync_service.SOURCE_TOOL_MAPPING`` 推导，避免两处维护。
3. **单个读取器失败不影响其它读取器**：异常被捕获并转成结构化 error。
4. **未迁移的 Agent 继续走 ccusage**：本注册表只包含已完成"原生 vs ccusage
   逐日对账零差异"的 Agent；其余 Agent 暂由 ccusage 兜底，
   迁移时只需新增一个读取器并登记，无需改动同步主流程。
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Callable, Optional

from app.utils.agent_readers.base import AgentReadResult
from app.utils.agent_readers.claude_reader import read_claude_records
from app.utils.agent_readers.codex_reader import read_codex_records
from app.utils.agent_readers.kimi_reader import read_kimi_records
from app.utils.agent_readers.minimax_reader import read_minimax_records

logger = logging.getLogger(__name__)

# 读取器签名：接收日期区间，返回 AgentReadResult
ReaderFn = Callable[[date, date], AgentReadResult]


def _read_zcode_records(since_date: date, until_date: date) -> AgentReadResult:
    """ZCode 读取器适配层。

    ZCode 的实现沿用既有模块 ``app.utils.zcode_usage_reader``（含完整单测），
    这里只做结果结构适配，避免同一份取数逻辑出现两份实现。
    """
    from app.utils.zcode_usage_reader import fetch_zcode_records

    result = AgentReadResult()
    payload = fetch_zcode_records(since_date, until_date)
    result.records = payload.get("records", [])
    result.errors = payload.get("errors", [])
    return result


# source id → 读取器
# 说明：source id 必须与 ccusage 的 agent id 一致，否则会与历史数据产生重复行。
READERS: dict[str, ReaderFn] = {
    "claude": read_claude_records,
    "codex": read_codex_records,
    "kimi": read_kimi_records,
    "zcode": _read_zcode_records,
    "minimax": read_minimax_records,
}

# 已完成"原生 vs ccusage 逐日对账零差异"的 Agent
VERIFIED_AGENTS: tuple[str, ...] = ("claude", "codex", "kimi", "zcode")


def supported_agents() -> list[str]:
    """返回已登记的原生读取器 source 列表。"""
    return list(READERS.keys())


def read_all_agents(
    since_date: date,
    until_date: date,
    only: Optional[list[str]] = None,
) -> dict:
    """读取所有（或指定的）Agent 本地用量。

    Args:
        since_date: 起始日期（含）。
        until_date: 结束日期（含）。
        only: 仅读取这些 source；为空表示全部。

    Returns:
        ``{"records": [...], "errors": [...], "sources": [...]}``
        - records: 全部读取器归一化后的记录
        - errors: 结构化错误列表
        - sources: 本次实际产出了数据的 source 列表
    """
    targets = {s: READERS[s] for s in (only or list(READERS.keys())) if s in READERS}

    records: list[dict] = []
    errors: list[dict] = []
    sources: list[str] = []

    for source, reader in targets.items():
        try:
            result = reader(since_date, until_date)
        except Exception as exc:  # pragma: no cover - 兜底，单个 Agent 失败不阻塞其它
            logger.error("[agent-readers] %s 读取异常: %s", source, exc, exc_info=True)
            errors.append(
                {
                    "source": source,
                    "error": f"{source}: {exc}",
                    "error_code": "READER_ERROR",
                    "remediation": "请检查该 Agent 的本地数据目录权限与格式",
                    "details": {"exception": str(exc)},
                }
            )
            continue

        records.extend(result.records)
        errors.extend(result.errors)
        if result.records:
            sources.append(source)

    return {"records": records, "errors": errors, "sources": sources}

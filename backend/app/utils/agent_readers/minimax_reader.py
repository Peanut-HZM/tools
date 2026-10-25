"""MiniMax Code (MCode) 原生 Token 用量读取器

数据源：``~/.minimax/v2/sqlite/runtime-state.sqlite`` 的 ``local_runtime_token_usage`` 表。

MiniMax Code（MCode 桌面端）的运行时把每一次模型调用的用量写入 SQLite：

.. code-block:: text

    local_runtime_token_usage(
        id, session_id, agent_name, framework_type, turn_id, model,
        ts,                    -- epoch 毫秒
        input_tokens, output_tokens, reasoning_tokens,
        cache_read_tokens, cache_write_tokens,
        cost_usd, raw
    )

口径说明：

1. **input_tokens 是净输入**（不含 cache），与 ZCode / Copilot 等"含 cache"的
   来源不同，因此**不需要**做 cache 扣减。
2. **reasoning_tokens** 是推理 token，MiniMax Code 单独记录；它属于输出的一部分，
   计入 output（与 Anthropic 的 ``output_tokens_details.thinking_tokens`` 同义）。
3. **cache_write_tokens → cache_creation**，**cache_read_tokens → cache read**。
4. **cost_usd 恒为 0**（MiniMax Code 不暴露费用数据），与 ZCode 情况一致。
5. **total** = input + output + cache_creation + cache_read（与全站口径一致），
   实测 ``raw.totalTokens`` 恰等于该四项之和。

平台差异：Windows / macOS 路径一致，均为 ``~/.minimax/v2/sqlite/runtime-state.sqlite``。
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from app.utils.agent_readers.base import (
    AgentReadResult,
    aggregate_records,
    date_range_to_ms_bounds,
    epoch_ms_to_local_date,
    open_sqlite_readonly,
    real_home,
    table_columns,
)

logger = logging.getLogger(__name__)

SOURCE = "minimax"

_DB_RELATIVE = Path(".minimax") / "v2" / "sqlite" / "runtime-state.sqlite"
_TABLE = "local_runtime_token_usage"

_REQUIRED_COLUMNS = {
    "ts",
    "model",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
}


def _db_candidates() -> list[Path]:
    """返回 MiniMax Code 数据库候选路径（按优先级）。"""
    home = real_home()
    return [home / _DB_RELATIVE]


def read_minimax_records(since_date: date, until_date: date) -> AgentReadResult:
    """读取 MiniMax Code 的 Token 用量。

    Args:
        since_date: 起始日期（含）。
        until_date: 结束日期（含）。

    Returns:
        AgentReadResult：records 为按 (日期, 模型) 聚合后的记录。
    """
    result = AgentReadResult()

    db_path: Optional[Path] = None
    for candidate in _db_candidates():
        if candidate.is_file():
            db_path = candidate
            break

    if db_path is None:
        # 未安装 MiniMax Code 不是异常：与 claude / codex / kimi 读取器一致，
        # 数据目录缺失时静默跳过，不计入同步告警
        logger.info(
            "[minimax] 未找到 MiniMax Code 数据库，跳过（候选: %s）",
            ", ".join(str(p) for p in _db_candidates()),
        )
        return result

    conn = open_sqlite_readonly(db_path)
    if conn is None:
        result.add_error(
            source=SOURCE,
            error=f"MiniMax Code 数据库无法打开：{db_path}",
            error_code="DB_READ_ERROR",
            remediation="请检查数据库是否被占用或损坏",
            details={"db_path": str(db_path)},
        )
        return result

    try:
        columns = table_columns(conn, _TABLE)
        if not columns:
            result.add_error(
                source=SOURCE,
                error=f"MiniMax Code 数据库缺 {_TABLE} 表：{db_path}",
                error_code="TABLE_MISSING",
                remediation="请升级 MiniMax Code 到包含该表的版本",
                details={"db_path": str(db_path)},
            )
            return result

        missing = _REQUIRED_COLUMNS - columns
        if missing:
            result.add_error(
                source=SOURCE,
                error=f"MiniMax Code {_TABLE} 表缺少必要列：{sorted(missing)}",
                error_code="SCHEMA_MISMATCH",
                remediation="请升级 MiniMax Code 到包含该表的版本",
                details={"db_path": str(db_path), "missing_columns": sorted(missing)},
            )
            return result

        has_reasoning = "reasoning_tokens" in columns
        has_cost = "cost_usd" in columns
        reasoning_expr = "reasoning_tokens" if has_reasoning else "0"
        cost_expr = "cost_usd" if has_cost else "0"

        cursor = conn.execute(
            f"""
            SELECT
                DATE(ts / 1000, 'unixepoch', 'localtime') AS record_date,
                COALESCE(NULLIF(TRIM(model), ''), 'unknown') AS model,
                SUM(MAX(COALESCE(input_tokens, 0), 0)) AS input_tokens,
                SUM(MAX(COALESCE(output_tokens, 0), 0)
                    + MAX(COALESCE({reasoning_expr}, 0), 0)) AS output_tokens,
                SUM(MAX(COALESCE(cache_write_tokens, 0), 0)) AS cache_creation_tokens,
                SUM(MAX(COALESCE(cache_read_tokens, 0), 0)) AS cache_read_tokens,
                SUM(MAX(COALESCE({cost_expr}, 0), 0)) AS total_cost,
                COUNT(*) AS request_count
            FROM {_TABLE}
            WHERE ts IS NOT NULL
              AND ts >= ?
              AND ts <= ?
            GROUP BY record_date, model
            ORDER BY record_date DESC, input_tokens DESC
            """,
            (
                date_range_to_ms_bounds(since_date, until_date)[0],
                date_range_to_ms_bounds(since_date, until_date)[1] - 1,
            ),
        )

        rows = []
        for row in cursor.fetchall():
            record_date_str = row[0]
            if not record_date_str:
                continue
            try:
                record_date = date.fromisoformat(record_date_str)
            except (ValueError, TypeError):
                continue
            input_tokens = int(row[2] or 0)
            output_tokens = int(row[3] or 0)
            cache_creation = int(row[4] or 0)
            cache_read = int(row[5] or 0)
            rows.append(
                {
                    "record_date": record_date.isoformat(),
                    "model": row[1] or "unknown",
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_creation_tokens": cache_creation,
                    "cache_read_tokens": cache_read,
                    "extra_total_tokens": 0,
                    "total_cost": float(row[6] or 0.0),
                }
            )

        result.records = aggregate_records(rows, source=SOURCE, source_raw="minimax-sqlite")
        logger.info(
            "[minimax] 原生读取 %s，聚合 %s 条记录",
            db_path,
            len(result.records),
        )
    except Exception as exc:  # pragma: no cover - 兜底，避免影响其它数据源
        logger.error("[minimax] 读取失败: %s", exc, exc_info=True)
        result.add_error(
            source=SOURCE,
            error=f"minimax: {exc}",
            error_code="READ_ERROR",
            remediation="请检查 MiniMax Code 数据库是否完整",
            details={"exception": str(exc), "db_path": str(db_path)},
        )
    finally:
        conn.close()

    return result

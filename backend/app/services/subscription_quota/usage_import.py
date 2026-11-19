"""从 cc-switch 读取用量与成本（magpie 的 usage/cost 视图）

cc-switch 的 `usage_daily_rollups` 已经按「日期 × 供应商 × 模型」聚合好请求数、
token 与成本；`proxy_request_logs` 有逐条明细。本模块**只读**这两张表，
把数据整理成前端可直接展示的结构。

这样本工具同时具备：
* 额度（还剩多少）
* 用量（花了多少、跑多少 token）

两者互补，才是完整的「订阅额度中心」。
"""

from __future__ import annotations

import logging
import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def ccswitch_db_path() -> Path:
    """cc-switch 数据库位置（可用 CCSWITCH_DB 覆盖）。

    必须基于 ``REAL_HOME``：``app.config.config`` 在非桌面模式会把 ``HOME``
    覆盖成 ``backend/data/cache``，此时 ``Path.home()`` 返回缓存目录，会把
    ``~/.cc-switch/cc-switch.db`` 解析到不存在的位置，页面便会误报
    「未找到 cc-switch 数据库」。（见 CLAUDE.md「用户目录访问必须使用真实家目录」）
    """
    override = os.environ.get("CCSWITCH_DB")
    if override:
        return Path(override)
    from app.services.subscription_quota.credentials import real_home

    return real_home() / ".cc-switch" / "cc-switch.db"


@dataclass
class UsageBucket:
    """一个聚合维度（按天 / 按供应商 / 按模型）"""

    key: str
    requests: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cost_usd: float = 0.0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_read_tokens
            + self.cache_creation_tokens
        )

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "requests": self.requests,
            "inputTokens": self.input_tokens,
            "outputTokens": self.output_tokens,
            "cacheReadTokens": self.cache_read_tokens,
            "cacheCreationTokens": self.cache_creation_tokens,
            "totalTokens": self.total_tokens,
            "costUsd": round(self.cost_usd, 6),
        }


@dataclass
class UsageSummary:
    available: bool = False
    message: Optional[str] = None
    days: int = 0
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    totals: UsageBucket = field(default_factory=lambda: UsageBucket(key="total"))
    by_day: list[UsageBucket] = field(default_factory=list)
    by_provider: list[UsageBucket] = field(default_factory=list)
    by_model: list[UsageBucket] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "available": self.available,
            "message": self.message,
            "days": self.days,
            "dateFrom": self.date_from,
            "dateTo": self.date_to,
            "totals": self.totals.to_dict(),
            "byDay": [b.to_dict() for b in self.by_day],
            "byProvider": [b.to_dict() for b in self.by_provider],
            "byModel": [b.to_dict() for b in self.by_model],
        }


def _connect_ro(path: Path) -> Optional[sqlite3.Connection]:
    if not path.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as exc:
        logger.warning("打开 cc-switch 数据库失败: %s", exc)
        return None


def read_usage(days: int = 30) -> UsageSummary:
    """读取最近 N 天的用量与成本（来自 cc-switch）"""
    path = ccswitch_db_path()
    conn = _connect_ro(path)
    if conn is None:
        return UsageSummary(
            message=f"未找到 cc-switch 数据库（{path}）；装过 cc-switch 并跑过请求后即可显示用量"
        )

    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "usage_daily_rollups" not in tables:
            return UsageSummary(message="cc-switch 数据库里没有 usage_daily_rollups 表")

        bounds = conn.execute(
            "SELECT MIN(date) AS d0, MAX(date) AS d1 FROM usage_daily_rollups"
        ).fetchone()
        if not bounds or not bounds["d1"]:
            return UsageSummary(message="cc-switch 还没有任何用量记录")

        date_to = str(bounds["d1"])
        # 「最近 N 天」= 从最新数据日期往前推 N-1 个日历天（不是「最近 N 个有数据的日期」，
        # 否则中间有断档时会把很久以前的数据算进窗口）
        from datetime import date as _date, timedelta as _timedelta

        try:
            end = _date.fromisoformat(date_to[:10])
            date_from_cutoff = (end - _timedelta(days=max(1, days) - 1)).isoformat()
        except ValueError:
            date_from_cutoff = None

        rows = conn.execute(
            """
            SELECT date, provider_id, model, request_count,
                   input_tokens, output_tokens, cache_read_tokens,
                   cache_creation_tokens, total_cost_usd
            FROM usage_daily_rollups
            ORDER BY date DESC
            """,
        ).fetchall()

        keep = {
            str(r["date"])
            for r in rows
            if date_from_cutoff is None or str(r["date"])[:10] >= date_from_cutoff
        }

        provider_names = {}
        if "providers" in tables:
            for prow in conn.execute("SELECT id, name FROM providers").fetchall():
                provider_names[str(prow["id"])] = prow["name"] or "(unknown)"

        summary = UsageSummary(
            available=True,
            days=len({str(r["date"]) for r in rows if str(r["date"]) in keep}),
            date_from=min(keep) if keep else None,
            date_to=date_to,
        )

        by_day: dict[str, UsageBucket] = {}
        by_provider: dict[str, UsageBucket] = {}
        by_model: dict[str, UsageBucket] = {}

        def _accumulate(bucket: UsageBucket, row) -> None:
            bucket.requests += int(row["request_count"] or 0)
            bucket.input_tokens += int(row["input_tokens"] or 0)
            bucket.output_tokens += int(row["output_tokens"] or 0)
            bucket.cache_read_tokens += int(row["cache_read_tokens"] or 0)
            bucket.cache_creation_tokens += int(row["cache_creation_tokens"] or 0)
            bucket.cost_usd += float(row["total_cost_usd"] or 0.0)

        for row in rows:
            date = str(row["date"])
            if date not in keep:
                continue
            provider = provider_names.get(str(row["provider_id"] or ""), "(unknown)")
            model = str(row["model"] or "(unknown)")

            _accumulate(summary.totals, row)
            _accumulate(by_day.setdefault(date, UsageBucket(key=date)), row)
            _accumulate(
                by_provider.setdefault(provider, UsageBucket(key=provider)), row
            )
            _accumulate(by_model.setdefault(model, UsageBucket(key=model)), row)

        summary.by_day = sorted(by_day.values(), key=lambda b: b.key)
        summary.by_provider = sorted(
            by_provider.values(), key=lambda b: b.cost_usd, reverse=True
        )
        summary.by_model = sorted(
            by_model.values(), key=lambda b: b.cost_usd, reverse=True
        )[:20]  # 模型太多，只留成本前 20
        return summary
    finally:
        conn.close()

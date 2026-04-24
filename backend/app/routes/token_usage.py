"""Token 消耗统计 API 路由"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.utils.usage_fetcher import UsageFetcher
from app.services.token_usage_cache import (
    get_cached_data,
    set_cached_data,
    invalidate_cache,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/token-usage", tags=["token-usage"])


class UsageRequest(BaseModel):
    source: str = Field(default="claude", description="claude, opencode")
    type: str = Field(default="daily", description="daily, weekly, monthly")
    days: int = Field(default=30, ge=1, le=365, description="最近 N 天")
    since: Optional[str] = Field(default=None, description="YYYYMMDD")
    until: Optional[str] = Field(default=None, description="YYYYMMDD")
    by: Optional[str] = Field(default=None, description="model, agent, provider")
    breakdown: bool = Field(default=False, description="是否显示模型明细")


class UsageItem(BaseModel):
    date: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    total_cost: float
    models_used: list[str] = Field(default_factory=list)
    model_breakdowns: list[dict] = Field(default_factory=list)


class UsageSummary(BaseModel):
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_cost: float
    days_count: int
    avg_daily_cost: float


class UsageResponse(BaseModel):
    items: list[UsageItem]
    summary: UsageSummary
    cached: bool = False
    cache_time: Optional[str] = None


def _safe_int(d: dict, *keys: str) -> int:
    for k in keys:
        v = d.get(k)
        if v is not None:
            try:
                return int(v)
            except (ValueError, TypeError):
                pass
    return 0


def _safe_float(d: dict, *keys: str) -> float:
    for k in keys:
        v = d.get(k)
        if v is not None:
            try:
                return float(v)
            except (ValueError, TypeError):
                pass
    return 0.0


def normalize_entries(raw: dict, report_type: str) -> list[UsageItem]:
    """统一规范化三种数据源的输出"""
    entries = raw.get(
        report_type, raw.get("data", raw.get("daily", raw.get("rows", [])))
    )
    if isinstance(entries, dict):
        entries = [entries]
    elif not isinstance(entries, list):
        entries = []

    items = []
    for entry in entries:
        date_val = (
            entry.get("date")
            or entry.get("label")
            or entry.get("week")
            or entry.get("month")
            or entry.get("timestamp", "")
        )
        if not date_val and entry.get("week"):
            date_val = str(entry["week"])

        tokens = entry.get("tokens", {})
        items.append(
            UsageItem(
                date=date_val,
                input_tokens=_safe_int(tokens, "input")
                or _safe_int(entry, "inputTokens", "input_tokens"),
                output_tokens=_safe_int(tokens, "output")
                or _safe_int(entry, "outputTokens", "output_tokens"),
                cache_creation_tokens=_safe_int(tokens, "cache_write")
                or _safe_int(entry, "cacheCreationTokens", "cache_creation_tokens"),
                cache_read_tokens=_safe_int(tokens, "cache_read")
                or _safe_int(entry, "cacheReadTokens", "cache_read_tokens"),
                total_tokens=_safe_int(tokens, "total")
                or _safe_int(entry, "totalTokens", "total_tokens"),
                total_cost=_safe_float(entry, "cost")
                or _safe_float(entry, "totalCost", "costUSD"),
                models_used=entry.get("modelsUsed", entry.get("models_used", [])),
                model_breakdowns=entry.get(
                    "modelBreakdowns", entry.get("model_breakdowns", [])
                ),
            )
        )
    return items


def aggregate_by_week(items: list[UsageItem]) -> list[UsageItem]:
    """按周聚合"""
    weekly: dict[str, dict] = defaultdict(
        lambda: {
            "inputTokens": 0,
            "outputTokens": 0,
            "totalTokens": 0,
            "totalCost": 0,
            "cacheCreationTokens": 0,
            "cacheReadTokens": 0,
            "modelsUsed": set(),
        }
    )
    for item in items:
        if not item.date:
            continue
        try:
            dt = datetime.strptime(item.date[:10], "%Y-%m-%d")
            iso_week = dt.strftime("%Y-W%W")
        except (ValueError, TypeError):
            iso_week = item.date[:7] if item.date else "unknown"

        w = weekly[iso_week]
        w["inputTokens"] += item.input_tokens
        w["outputTokens"] += item.output_tokens
        w["totalTokens"] += item.total_tokens
        w["totalCost"] += item.total_cost
        w["cacheCreationTokens"] += item.cache_creation_tokens
        w["cacheReadTokens"] += item.cache_read_tokens
        for m in item.models_used:
            w["modelsUsed"].add(m)

    return [
        UsageItem(
            date=k,
            input_tokens=v["inputTokens"],
            output_tokens=v["outputTokens"],
            cache_creation_tokens=v["cacheCreationTokens"],
            cache_read_tokens=v["cacheReadTokens"],
            total_tokens=v["totalTokens"],
            total_cost=round(v["totalCost"], 4),
            models_used=list(v["modelsUsed"]),
        )
        for k, v in sorted(weekly.items())
    ]


def aggregate_by_month(items: list[UsageItem]) -> list[UsageItem]:
    """按月聚合"""
    monthly: dict[str, dict] = defaultdict(
        lambda: {
            "inputTokens": 0,
            "outputTokens": 0,
            "totalTokens": 0,
            "totalCost": 0,
            "cacheCreationTokens": 0,
            "cacheReadTokens": 0,
            "modelsUsed": set(),
        }
    )
    for item in items:
        if not item.date:
            continue
        month_str = item.date[:7]
        m = monthly[month_str]
        m["inputTokens"] += item.input_tokens
        m["outputTokens"] += item.output_tokens
        m["totalTokens"] += item.total_tokens
        m["totalCost"] += item.total_cost
        m["cacheCreationTokens"] += item.cache_creation_tokens
        m["cacheReadTokens"] += item.cache_read_tokens
        for mod in item.models_used:
            m["modelsUsed"].add(mod)

    return [
        UsageItem(
            date=k,
            input_tokens=v["inputTokens"],
            output_tokens=v["outputTokens"],
            cache_creation_tokens=v["cacheCreationTokens"],
            cache_read_tokens=v["cacheReadTokens"],
            total_tokens=v["totalTokens"],
            total_cost=round(v["totalCost"], 4),
            models_used=list(v["modelsUsed"]),
        )
        for k, v in sorted(monthly.items())
    ]


def compute_summary(items: list[UsageItem]) -> UsageSummary:
    """计算汇总统计"""
    count = max(len(items), 1)
    return UsageSummary(
        total_input_tokens=sum(i.input_tokens for i in items),
        total_output_tokens=sum(i.output_tokens for i in items),
        total_tokens=sum(i.total_tokens for i in items),
        total_cost=round(sum(i.total_cost for i in items), 4),
        days_count=len(items),
        avg_daily_cost=round(sum(i.total_cost for i in items) / count, 4),
    )


def apply_aggregation(items: list[UsageItem], report_type: str) -> list[UsageItem]:
    """根据 report_type 应用聚合"""
    if report_type == "weekly":
        return aggregate_by_week(items)
    elif report_type == "monthly":
        return aggregate_by_month(items)
    return items


@router.post("", response_model=UsageResponse)
async def get_token_usage(req: UsageRequest):
    """获取 Token 消耗统计数据（优先从缓存读取）"""
    if req.source not in ("claude", "opencode"):
        raise HTTPException(
            400,
            detail="source 必须是 'claude' 或 'opencode'",
        )
    if req.type not in ("daily", "weekly", "monthly"):
        raise HTTPException(
            400,
            detail="type 必须是 'daily', 'weekly' 或 'monthly'",
        )

    # 1. 尝试从缓存读取
    cached = get_cached_data(
        source=req.source,
        report_type=req.type,
        days=req.days,
        since=req.since,
        until=req.until,
        breakdown=req.breakdown,
        by=req.by,
    )

    if cached:
        logger.info("返回缓存数据")
        return UsageResponse(
            items=[UsageItem(**item) for item in cached["items"]],
            summary=UsageSummary(**cached["summary"]),
            cached=True,
            cache_time=cached.get("cache_time"),
        )

    # 2. 缓存未命中，执行 CLI 调用
    if req.source == "claude":
        since = req.since
        until = req.until
        if not since and req.days:
            since_date = datetime.now() - timedelta(days=req.days)
            since = since_date.strftime("%Y%m%d")
        # ccusage monthly/weekly 不支持 --since，统一取 daily 后由后端聚合
        raw = UsageFetcher.fetch_claude(
            report_type="daily",
            since=since,
            until=until,
            breakdown=req.breakdown,
        )
    else:
        raw = UsageFetcher.fetch_opencode(
            days=req.days,
            by=req.by,
        )

    if "error" in raw:
        tool_name = "ccusage" if req.source == "claude" else "opencode-usage"
        raise HTTPException(
            500,
            detail=f"{tool_name} 数据获取失败: {raw['error']}",
        )

    items = normalize_entries(raw, req.type)
    items = apply_aggregation(items, req.type)
    summary = compute_summary(items)

    # 3. 写入缓存
    cache_time = datetime.now().isoformat()
    cache_data = {
        "items": [item.model_dump() for item in items],
        "summary": summary.model_dump(),
        "cache_time": cache_time,
    }
    set_cached_data(
        source=req.source,
        report_type=req.type,
        days=req.days,
        data=cache_data,
        since=req.since,
        until=req.until,
        breakdown=req.breakdown,
        by=req.by,
    )

    return UsageResponse(
        items=items,
        summary=summary,
        cached=False,
        cache_time=cache_time,
    )


@router.get("/health")
async def health_check():
    """检查所有 CLI 工具是否可用"""
    return UsageFetcher.health_check()


@router.post("/refresh")
async def refresh_cache():
    """手动刷新所有 Token Usage 缓存"""
    invalidate_cache()
    return {"message": "缓存已清除，下次访问将重新获取数据"}

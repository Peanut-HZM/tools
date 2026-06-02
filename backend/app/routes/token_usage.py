"""Token 消耗统计 API 路由"""

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, date
from types import SimpleNamespace
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Body
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import func, or_

from app.config.config import settings
from app.utils.usage_fetcher import UsageFetcher
from app.services.token_usage_cache import (
    get_cached_data,
    set_cached_data,
    invalidate_cache,
    invalidate_user_query_cache,
    get_query_cached_data,
    get_query_cached_payload,
    set_query_cached_data,
    acquire_refresh_lock,
    release_refresh_lock,
)
from app.models.base import SessionLocal
from app.models.token_usage_models import (
    TokenUsageRecord,
    TokenUsageSyncLog,
    DeviceRegistry,
)
from app.services.token_usage_sync_service import sync_token_usage
from app.services.token_usage_background_sync import register_pending_sync_user
from app.routes.auth import get_current_user_id
from app.utils.device_id import get_device_id

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


class AggregateUsageRequest(BaseModel):
    type: str = Field(default="daily", description="daily, weekly, monthly")
    days: int = Field(default=30, ge=1, le=365, description="最近 N 天")
    by: Optional[str] = Field(default=None, description="model, agent, provider")
    breakdown: bool = Field(default=False, description="是否显示模型明细")


class UsageItem(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
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
    # opencode-usage 返回 {period, total, rows: [...]}
    entries = raw.get(
        report_type, raw.get("data", raw.get("daily", raw.get("rows", [])))
    )
    # 兼容 opencode-usage: 没有 daily/data 时用 rows
    if not entries and raw.get("rows"):
        entries = raw.get("rows")
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
        input_tokens = _safe_int(tokens, "input") or _safe_int(
            entry, "inputTokens", "input_tokens"
        )
        output_tokens = _safe_int(tokens, "output") or _safe_int(
            entry, "outputTokens", "output_tokens"
        )
        cache_creation = _safe_int(tokens, "cache_write") or _safe_int(
            entry, "cacheCreationTokens", "cache_creation_tokens"
        )
        cache_read = _safe_int(tokens, "cache_read") or _safe_int(
            entry, "cacheReadTokens", "cache_read_tokens"
        )

        # 提取 breakdowns，支持多种字段名：modelBreakdowns, model_breakdowns, models
        breakdowns = (
            entry.get("modelBreakdowns")
            or entry.get("model_breakdowns")
            or entry.get("models")
            or []
        )

        # 提取 models_used，支持多种字段名并自动解析
        models_used = entry.get("modelsUsed") or entry.get("models_used") or []
        if not models_used and breakdowns:
            models_used = [
                m.get("model") or m.get("name") or m.get("modelName") or "unknown"
                for m in breakdowns
            ]

        items.append(
            UsageItem(
                date=date_val,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation_tokens=cache_creation,
                cache_read_tokens=cache_read,
                total_tokens=input_tokens + output_tokens + cache_creation + cache_read,
                total_cost=_safe_float(entry, "cost")
                or _safe_float(entry, "totalCost", "costUSD"),
                models_used=models_used,
                model_breakdowns=breakdowns,
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
    # 强制从四项组件之和计算 total_tokens，防止 CLI 返回的 total=0 污染统计
    total_input = sum(i.input_tokens for i in items)
    total_output = sum(i.output_tokens for i in items)
    total_cache_creation = sum(i.cache_creation_tokens for i in items)
    total_cache_read = sum(i.cache_read_tokens for i in items)
    total_tokens = total_input + total_output + total_cache_creation + total_cache_read

    return UsageSummary(
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_tokens=total_tokens,
        total_cost=round(sum(i.total_cost for i in items), 4),
        days_count=len(items),
        avg_daily_cost=round(sum(i.total_cost for i in items) / max(len(items), 1), 4),
    )


def apply_aggregation(items: list[UsageItem], report_type: str) -> list[UsageItem]:
    """根据 report_type 应用聚合"""
    if report_type == "weekly":
        return aggregate_by_week(items)
    elif report_type == "monthly":
        return aggregate_by_month(items)
    return items


def merge_items(items_a: list[UsageItem], items_b: list[UsageItem]) -> list[UsageItem]:
    """合并两个数据源的 UsageItem 列表，按日期分组求和"""
    merged: dict[str, dict] = defaultdict(
        lambda: {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "models_used": set(),
            "model_breakdowns": [],
        }
    )
    for items in (items_a, items_b):
        for item in items:
            if not item.date:
                continue
            m = merged[item.date]
            m["input_tokens"] += item.input_tokens
            m["output_tokens"] += item.output_tokens
            m["cache_creation_tokens"] += item.cache_creation_tokens
            m["cache_read_tokens"] += item.cache_read_tokens
            m["total_tokens"] += item.total_tokens
            m["total_cost"] += item.total_cost
            for mod in item.models_used:
                m["models_used"].add(mod)
            m["model_breakdowns"].extend(item.model_breakdowns)

    return [
        UsageItem(
            date=k,
            input_tokens=v["input_tokens"],
            output_tokens=v["output_tokens"],
            cache_creation_tokens=v["cache_creation_tokens"],
            cache_read_tokens=v["cache_read_tokens"],
            total_tokens=v["total_tokens"],
            total_cost=round(v["total_cost"], 4),
            models_used=list(v["models_used"]),
            model_breakdowns=v["model_breakdowns"],
        )
        for k, v in sorted(merged.items())
    ]


@router.get("/health")
async def health_check():
    """检查所有 CLI 工具是否可用"""
    return UsageFetcher.health_check()


class RefreshUsageRequest(BaseModel):
    days: int = Field(default=90, ge=1, le=365, description="同步最近 N 天数据")
    background: bool = Field(default=False, description="是否为前端自动触发的静默刷新")
    reason: str = Field(default="manual", description="manual | stale")


@router.post("/refresh")
async def refresh_cache(
    req: RefreshUsageRequest = Body(default_factory=RefreshUsageRequest),
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """手动同步当前用户数据，并刷新该用户的 Token Usage 缓存。"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    owner = str(uuid.uuid4())
    lock = acquire_refresh_lock(user_id, owner)
    if not lock["acquired"]:
        logger.info(f"用户 {user_id} Token Usage 刷新被锁拦截: {lock}")
        return {
            "message": "已有刷新任务进行中",
            "sources_synced": [],
            "total_records": 0,
            "errors": [],
            "locked": True,
            "lock_ttl_seconds": lock["ttl_seconds"],
        }

    try:
        logger.info(
            f"用户 {user_id} 刷新 Token Usage 数据: days={req.days}, background={req.background}, reason={req.reason}"
        )
        invalidate_user_query_cache(user_id)
        result = sync_token_usage(user_id=user_id, days=req.days)
        invalidate_user_query_cache(user_id)
        result["message"] = "同步完成，缓存已刷新"
        result["locked"] = False
        return result
    finally:
        release_refresh_lock(user_id, owner)


@router.post("/clear-data")
async def clear_usage_data(
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """一键清理当前用户的 Token 使用数据（数据库记录 + Redis 缓存）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    db = SessionLocal()
    try:
        # 1. 统计将删除的记录数
        records_count = (
            db.query(TokenUsageRecord)
            .filter(TokenUsageRecord.user_id == user_id)
            .count()
        )
        sync_logs_count = (
            db.query(TokenUsageSyncLog)
            .filter(TokenUsageSyncLog.user_id == user_id)
            .count()
        )

        # 2. 删除数据库记录
        db.query(TokenUsageRecord).filter(TokenUsageRecord.user_id == user_id).delete()
        db.query(TokenUsageSyncLog).filter(
            TokenUsageSyncLog.user_id == user_id
        ).delete()
        db.commit()

        # 3. 清除 Redis 缓存
        invalidate_cache()

        logger.info(
            f"用户 {user_id} 已清理数据: {records_count} 条使用记录, {sync_logs_count} 条同步日志"
        )

        return {
            "message": f"数据已清理完成，共删除 {records_count} 条使用记录和 {sync_logs_count} 条同步日志",
            "records_deleted": records_count,
            "sync_logs_deleted": sync_logs_count,
        }
    except Exception as e:
        db.rollback()
        logger.error(f"清理数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"清理数据失败: {str(e)}")
    finally:
        db.close()


@router.get("/devices")
async def get_user_devices(
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """获取当前用户的设备列表"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    db = SessionLocal()
    try:
        regs = db.query(DeviceRegistry).filter(DeviceRegistry.user_id == user_id).all()

        if regs:
            devices = [
                {
                    "id": reg.device_id,
                    "name": reg.display_name
                    or reg.default_display_name
                    or reg.device_id,
                }
                for reg in regs
            ]
        else:
            device_ids = (
                db.query(TokenUsageRecord.device_id)
                .filter(TokenUsageRecord.user_id == user_id)
                .distinct()
                .all()
            )
            devices = [{"id": row[0], "name": row[0]} for row in device_ids]

        return {"devices": devices}
    finally:
        db.close()


# ========== 数据库查询与同步端点 ==========


class DbQueryRequest(BaseModel):
    type: str = Field(default="daily", description="daily | weekly | monthly")
    days: int = Field(default=30, ge=1, le=365, description="最近 N 天")
    group_by: str = Field(default="none", description="none | device | tool | model")
    source: str = Field(default="all", description="claude | opencode | all")
    device_id: Optional[str] = Field(
        default=None, description="筛选特定设备，不传则查全部"
    )
    tool_id: Optional[str] = Field(default=None, description="tool id")
    model: Optional[str] = Field(default=None, description="model")
    sort_by: str = Field(default="date", description="date | total_tokens | total_cost")
    sort_order: str = Field(default="desc", description="asc | desc")


class DbUsageItem(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    date: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    total_cost: float
    models_used: list[str] = Field(default_factory=list)
    model_breakdowns: list[dict] = Field(default_factory=list)
    group_key: Optional[str] = Field(
        default=None, description="设备名或模型名（分组时）"
    )


class DeviceInfo(BaseModel):
    id: str
    name: str


class RefreshLockMeta(BaseModel):
    locked: bool = False
    owner: Optional[str] = None
    ttl_seconds: int = 0


class ModelSummaryItem(BaseModel):
    source: str
    model: str
    display_model: str
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    total_cost: float


class DimensionSummaryItem(BaseModel):
    dimension: str
    key: str
    label: str
    device_id: Optional[str] = None
    tool_id: Optional[str] = None
    source: Optional[str] = None
    model: Optional[str] = None
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    total_tokens: int
    total_cost: float
    token_share: float
    cost_share: float
    records_count: int
    last_used_at: Optional[str] = None


class DimensionSummaries(BaseModel):
    devices: list[DimensionSummaryItem] = Field(default_factory=list)
    tools: list[DimensionSummaryItem] = Field(default_factory=list)
    models: list[DimensionSummaryItem] = Field(default_factory=list)


class ToolFilterOption(BaseModel):
    tool_id: str
    tool_name: str
    records_count: int


class DeviceFilterOption(BaseModel):
    device_id: str
    device_name: str
    records_count: int


class ModelFilterOption(BaseModel):
    tool_id: str
    source: str
    model: str
    model_display_name: str
    records_count: int


class FilterOptions(BaseModel):
    tools: list[ToolFilterOption] = Field(default_factory=list)
    devices: list[DeviceFilterOption] = Field(default_factory=list)
    models: list[ModelFilterOption] = Field(default_factory=list)


class SyncMeta(BaseModel):
    last_synced_at: Optional[str] = None
    last_success_at: Optional[str] = None
    cache_written_at: Optional[str] = None
    cache_ttl_seconds: int = 0
    cache_expires_at: Optional[str] = None
    data_age_seconds: Optional[int] = None
    is_stale: bool = False
    stale_reason: Optional[str] = None
    refresh_lock: RefreshLockMeta = Field(default_factory=RefreshLockMeta)
    sources_status: list[dict] = Field(default_factory=list)


class DbUsageResponse(BaseModel):
    items: list[DbUsageItem]
    summary: UsageSummary
    devices: list[dict] = Field(default_factory=list)
    cached: bool = False
    actual_days: Optional[int] = Field(default=None)
    auto_expanded: bool = False
    model_summary: list[ModelSummaryItem] = Field(default_factory=list)
    dimension_summaries: DimensionSummaries = Field(default_factory=DimensionSummaries)
    filter_options: FilterOptions = Field(default_factory=FilterOptions)
    sync_meta: SyncMeta = Field(default_factory=SyncMeta)


class ChartSeriesItem(BaseModel):
    date: str
    group_key: Optional[str] = None
    total_tokens: int
    total_cost: float


class SummaryUsageSummary(BaseModel):
    """summary 端点专用的汇总结构（比 UsageSummary 多了 cache 拆分）"""
    total_input_tokens: int
    total_output_tokens: int
    total_cache_creation_tokens: int
    total_cache_read_tokens: int
    total_tokens: int
    total_cost: float
    days_count: int
    avg_daily_cost: float


class SummaryResponse(BaseModel):
    summary: SummaryUsageSummary
    dimension_summaries: DimensionSummaries = Field(default_factory=DimensionSummaries)
    model_summary: list[ModelSummaryItem] = Field(default_factory=list)
    filter_options: FilterOptions = Field(default_factory=FilterOptions)
    sync_meta: SyncMeta = Field(default_factory=SyncMeta)
    chart_series: list[ChartSeriesItem] = Field(default_factory=list)
    cached: bool = False
    auto_expanded: bool = False
    actual_days: Optional[int] = None
    devices: list[dict] = Field(default_factory=list)


class DetailsRequest(BaseModel):
    source: str = Field(default="all", description="claude | opencode | all")
    type: str = Field(default="daily", description="daily | weekly | monthly")
    days: int = Field(default=30, ge=1, le=365)
    group_by: str = Field(default="none", description="none | device | tool | model")
    device_id: Optional[str] = None
    tool_id: Optional[str] = None
    model: Optional[str] = None
    sort_by: str = Field(default="date")
    sort_order: str = Field(default="desc")
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class DetailsResponse(BaseModel):
    items: list[DbUsageItem]
    total: int
    limit: int
    offset: int
    has_more: bool
    cached: bool = False


@router.get("/summary", response_model=SummaryResponse)
async def get_token_usage_summary(
    source: str = "all",
    type: str = "daily",
    days: int = 30,
    group_by: str = "none",
    device_id: Optional[str] = None,
    tool_id: Optional[str] = None,
    model: Optional[str] = None,
    authorization: Optional[str] = Header(None),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    # sort_by="__summary__" 命名空间避免与 /db-query 共用缓存键造成互相覆盖
    cached_payload = get_query_cached_payload(
        source=source,
        report_type=type,
        days=days,
        group_by=group_by,
        user_id=user_id,
        device_id=device_id or "",
        tool_id=tool_id or "",
        model=model or "",
        sort_by="__summary__",
        sort_order="desc",
    )

    if cached_payload and "summary_data" in cached_payload:
        logger.info(f"summary 缓存命中 user={user_id}")
        payload = cached_payload["summary_data"]
        return SummaryResponse(**payload)

    db = SessionLocal()
    try:
        req = SimpleNamespace(
            source=source,
            type=type,
            days=days,
            group_by=group_by,
            device_id=device_id,
            tool_id=tool_id,
            model=model,
            sort_by="date",
            sort_order="desc",
        )

        has_data = (
            db.query(TokenUsageRecord)
            .filter(TokenUsageRecord.user_id == user_id)
            .first()
            is not None
        )
        if not has_data:
            return SummaryResponse(
                summary=SummaryUsageSummary(
                    total_input_tokens=0,
                    total_output_tokens=0,
                    total_cache_creation_tokens=0,
                    total_cache_read_tokens=0,
                    total_tokens=0,
                    total_cost=0.0,
                    days_count=0,
                    avg_daily_cost=0.0,
                )
            )

        since_date = datetime.now() - timedelta(days=days)
        records = (
            db.query(TokenUsageRecord)
            .filter(*_build_record_filters(user_id, req, since_date))
            .all()
        )

        total_input = sum(int(getattr(r, "input_tokens", 0) or 0) for r in records)
        total_output = sum(int(getattr(r, "output_tokens", 0) or 0) for r in records)
        total_cc = sum(int(getattr(r, "cache_creation_tokens", 0) or 0) for r in records)
        total_cr = sum(int(getattr(r, "cache_read_tokens", 0) or 0) for r in records)
        total_tokens = total_input + total_output + total_cc + total_cr
        total_cost = sum(float(getattr(r, "total_cost", 0) or 0) for r in records)
        days_count = len({r.record_date for r in records}) if records else 0

        summary = SummaryUsageSummary(
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_cache_creation_tokens=total_cc,
            total_cache_read_tokens=total_cr,
            total_tokens=total_tokens,
            total_cost=round(total_cost, 4),
            days_count=days_count,
            avg_daily_cost=round(total_cost / max(days_count, 1), 4),
        )

        dimension_rows, filter_options = _query_dimension_data(
            db, user_id, req, since_date
        )

        model_rows = _execute_model_summary_query(db, user_id, req, since_date)
        model_summary = _rows_to_model_summary(model_rows)

        device_names = _load_device_names(db, user_id)
        devices = [{"id": did, "name": name} for did, name in device_names.items()]

        chart_series = build_chart_series(records, group_by)

        sync_meta = _get_sync_meta(db, user_id, req, None)

        payload = SummaryResponse(
            summary=summary,
            dimension_summaries=_to_dimension_summaries(dimension_rows),
            model_summary=model_summary,
            filter_options=_to_filter_options(filter_options),
            sync_meta=_to_sync_meta(sync_meta),
            chart_series=[ChartSeriesItem(**s) for s in chart_series],
            devices=devices,
        ).model_dump(exclude={"cached"})

        set_query_cached_data(
            source=source,
            report_type=type,
            days=days,
            group_by=group_by,
            user_id=user_id,
            device_id=device_id or "",
            tool_id=tool_id or "",
            model=model or "",
            sort_by="__summary__",
            sort_order="desc",
            data={"summary_data": payload},
        )

        return SummaryResponse(**payload, cached=False)
    finally:
        db.close()


@router.post("/details", response_model=DetailsResponse)
async def get_token_usage_details(
    req: DetailsRequest,
    authorization: Optional[str] = Header(None),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    # sort_by 用 "details:<sort>:<order>:<limit>:<offset>" 命名空间避免与 /db-query / /summary 共享缓存键
    cache_key_extra = f"details:{req.sort_by}:{req.sort_order}:{req.limit}:{req.offset}"
    cached_payload = get_query_cached_data(
        source=req.source,
        report_type=req.type,
        days=req.days,
        group_by=req.group_by,
        user_id=user_id,
        device_id=req.device_id or "",
        tool_id=req.tool_id or "",
        model=req.model or "",
        sort_by=cache_key_extra,
        sort_order="desc",
    )
    if cached_payload and "details_data" in cached_payload:
        logger.info(f"details 缓存命中 user={user_id}")
        return DetailsResponse(**cached_payload["details_data"], cached=True)

    db = SessionLocal()
    try:
        req_ns = SimpleNamespace(
            source=req.source,
            type=req.type,
            days=req.days,
            group_by=req.group_by,
            device_id=req.device_id,
            tool_id=req.tool_id,
            model=req.model,
            sort_by=req.sort_by,
            sort_order=req.sort_order,
        )

        has_data = (
            db.query(TokenUsageRecord)
            .filter(TokenUsageRecord.user_id == user_id)
            .first()
            is not None
        )
        if not has_data:
            return DetailsResponse(
                items=[], total=0, limit=req.limit, offset=req.offset, has_more=False
            )

        since_date = datetime.now() - timedelta(days=req.days)
        records = (
            db.query(TokenUsageRecord)
            .filter(*_build_record_filters(user_id, req_ns, since_date))
            .all()
        )

        sorted_records = _sort_usage_items(records, req.sort_by, req.sort_order)
        total = len(sorted_records)
        paged = sorted_records[req.offset : req.offset + req.limit]

        items = []
        for r in paged:
            date_val = r.record_date
            date_key = date_val.isoformat() if hasattr(date_val, "isoformat") else str(date_val)
            group_key = None
            if req.group_by == "device":
                group_key = r.device_id
            elif req.group_by == "tool":
                group_key = r.tool_id
            elif req.group_by == "model":
                group_key = r.model

            items.append(
                DbUsageItem(
                    date=date_key,
                    input_tokens=int(r.input_tokens or 0),
                    output_tokens=int(r.output_tokens or 0),
                    cache_creation_tokens=int(r.cache_creation_tokens or 0),
                    cache_read_tokens=int(r.cache_read_tokens or 0),
                    total_tokens=int(r.total_tokens or 0),
                    total_cost=float(r.total_cost or 0),
                    models_used=[r.model] if r.model else [],
                    model_breakdowns=[],
                    group_key=group_key,
                )
            )

        has_more = (req.offset + len(items)) < total

        response = DetailsResponse(
            items=items,
            total=total,
            limit=req.limit,
            offset=req.offset,
            has_more=has_more,
        )
        cached_dict = response.model_dump(exclude={"cached"})

        set_query_cached_data(
            source=req.source,
            report_type=req.type,
            days=req.days,
            group_by=req.group_by,
            user_id=user_id,
            device_id=req.device_id or "",
            tool_id=req.tool_id or "",
            model=req.model or "",
            sort_by=cache_key_extra,
            sort_order="desc",
            data={"details_data": cached_dict},
        )

        return DetailsResponse(**cached_dict, cached=False)
    finally:
        db.close()


@router.post("/db-query", response_model=DbUsageResponse)
async def db_query_token_usage(
    req: DbQueryRequest,
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """从数据库查询 Token 消耗统计（支持按设备、模型分组）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    # 1. 优先查 Redis 缓存
    cached = get_query_cached_data(
        source=req.source,
        report_type=req.type,
        days=req.days,
        group_by=req.group_by,
        user_id=user_id,
        device_id=req.device_id or "",
        tool_id=req.tool_id or "",
        model=req.model or "",
        sort_by=req.sort_by,
        sort_order=req.sort_order,
    )
    if cached:
        logger.info(f"查询: Redis 缓存命中 /{req.source}/{req.type}/{req.days}天")
        return DbUsageResponse(
            items=[DbUsageItem(**item) for item in cached["items"]],
            summary=UsageSummary(**cached["summary"]),
            devices=cached.get("devices", []),
            cached=True,
            dimension_summaries=_to_dimension_summaries(
                cached.get("dimension_summaries")
            ),
            filter_options=_to_filter_options(cached.get("filter_options")),
        )

    # 2. Redis 未命中，查数据库
    db = SessionLocal()
    try:
        has_data = (
            db.query(TokenUsageRecord)
            .filter(TokenUsageRecord.user_id == user_id)
            .first()
            is not None
        )

        if not has_data:
            # 降级到 CLI 直查模式
            return await _fallback_to_cli(req)

        # 获取设备列表（从 device_registry）
        regs = db.query(DeviceRegistry).filter(DeviceRegistry.user_id == user_id).all()

        if regs:
            devices = []
            for reg in regs:
                name = reg.display_name or reg.default_display_name or reg.device_id
                devices.append({"id": reg.device_id, "name": name})
        else:
            # 兼容：旧数据没有 device_registry 记录，回退到 token_usage_records
            device_ids = (
                db.query(TokenUsageRecord.device_id)
                .filter(TokenUsageRecord.user_id == user_id)
                .distinct()
                .all()
            )
            devices = [{"id": row[0], "name": row[0]} for row in device_ids]

        # 如果有 source 过滤，只显示该 source 下有数据的设备
        if req.source != "all":
            active_ids = set(
                row[0]
                for row in db.query(TokenUsageRecord.device_id)
                .filter(
                    TokenUsageRecord.user_id == user_id,
                    TokenUsageRecord.source == req.source,
                )
                .distinct()
                .all()
            )
            devices = [d for d in devices if d["id"] in active_ids]

        # 执行查询
        since_date = datetime.now() - timedelta(days=req.days)
        items = _execute_db_query(db, user_id, req, since_date)

        # 计算汇总
        dimension_rows, filter_options = _query_dimension_data(
            db, user_id, req, since_date
        )
        summary = compute_summary(items)

        return DbUsageResponse(
            items=items,
            summary=summary,
            devices=devices,
            dimension_summaries=DimensionSummaries(**dimension_rows),
            filter_options=FilterOptions(**filter_options),
        )
    finally:
        db.close()


@router.post("/sync")
async def sync_token_usage_endpoint(
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """手动触发 Token Usage 同步到数据库"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    invalidate_user_query_cache(user_id)
    result = sync_token_usage(user_id=user_id, days=90)
    invalidate_user_query_cache(user_id)
    return result


@router.put("/devices/{device_id}/rename")
async def rename_device(
    device_id: str,
    name: str = Body(
        ..., embed=True, description="设备显示名称，空字符串表示重置为默认"
    ),
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """重命名设备（display_name 为空时回退到 username@hostname）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    db = SessionLocal()
    try:
        reg = (
            db.query(DeviceRegistry)
            .filter_by(user_id=user_id, device_id=device_id)
            .first()
        )
        if not reg:
            raise HTTPException(status_code=404, detail="设备不存在")

        reg.display_name = name.strip()[:128] if name.strip() else None
        db.commit()

        return {"device_id": device_id, "display_name": reg.display_name}
    finally:
        db.close()


async def _fallback_to_cli(req: DbQueryRequest) -> DbUsageResponse:
    """降级到 CLI 直查模式"""
    if req.source == "all":
        # 聚合查询
        loop = asyncio.get_event_loop()
        since_date = datetime.now() - timedelta(days=req.days)
        since = since_date.strftime("%Y%m%d")
        claude_raw, opencode_raw = await asyncio.gather(
            loop.run_in_executor(
                None,
                lambda: UsageFetcher.fetch_claude(
                    report_type="daily", since=since, breakdown=True
                ),
            ),
            loop.run_in_executor(
                None, lambda: UsageFetcher.fetch_opencode(days=req.days)
            ),
            return_exceptions=True,
        )
        if isinstance(claude_raw, Exception):
            claude_raw = {"error": str(claude_raw)}
        if isinstance(opencode_raw, Exception):
            opencode_raw = {"error": str(opencode_raw)}

        items_a = (
            normalize_entries(claude_raw, req.type) if "error" not in claude_raw else []
        )
        items_b = (
            normalize_entries(opencode_raw, req.type)
            if "error" not in opencode_raw
            else []
        )
        items_a = apply_aggregation(items_a, req.type)
        items_b = apply_aggregation(items_b, req.type)
        merged = merge_items(items_a, items_b)
        summary = compute_summary(merged)
        db_items = [DbUsageItem(**item.model_dump()) for item in merged]
    else:
        since = (datetime.now() - timedelta(days=req.days)).strftime("%Y%m%d")
        raw = (
            UsageFetcher.fetch_claude(report_type="daily", since=since, breakdown=True)
            if req.source == "claude"
            else UsageFetcher.fetch_opencode(days=req.days)
        )
        if "error" in raw:
            raise HTTPException(500, detail=f"CLI 数据获取失败: {raw['error']}")
        items = normalize_entries(raw, req.type)
        items = apply_aggregation(items, req.type)
        summary = compute_summary(items)
        db_items = [DbUsageItem(**item.model_dump()) for item in items]

    return DbUsageResponse(items=db_items, summary=summary, devices=[])


def compute_db_summary(items: list[DbUsageItem]) -> UsageSummary:
    """从 DB 查询结果计算汇总统计"""
    total_input = sum(i.input_tokens for i in items)
    total_output = sum(i.output_tokens for i in items)
    total_cache_creation = sum(i.cache_creation_tokens for i in items)
    total_cache_read = sum(i.cache_read_tokens for i in items)
    total_tokens = total_input + total_output + total_cache_creation + total_cache_read
    total_cost = sum(i.total_cost for i in items)
    days_count = len(items) if items else 1
    return UsageSummary(
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_tokens=total_tokens,
        total_cost=round(total_cost, 4),
        days_count=days_count,
        avg_daily_cost=round(total_cost / days_count, 4) if days_count else 0,
    )


# ========== Freshness / Meta 辅助函数 ==========


def _to_iso(value) -> Optional[str]:
    """将数据库时间安全转换为 ISO 字符串。"""
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _parse_cache_time(value: Optional[str]):
    """解析缓存写入时间，解析失败时返回 None。"""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _align_datetime_to_reference(value, reference: datetime):
    if not value or not hasattr(value, "tzinfo"):
        return value
    value_has_tz = value.tzinfo is not None and value.utcoffset() is not None
    reference_has_tz = (
        reference.tzinfo is not None and reference.utcoffset() is not None
    )
    if value_has_tz == reference_has_tz:
        return value
    if value_has_tz:
        return value.replace(tzinfo=None)
    return value.replace(tzinfo=reference.tzinfo)


def _map_source_to_tool(source: str) -> dict:
    source_value = source or "unknown"
    mapping = {
        "claude": {"tool_id": "claude-code", "tool_name": "Claude Code"},
        "opencode": {"tool_id": "opencode", "tool_name": "OpenCode"},
        "codex": {"tool_id": "codex", "tool_name": "Codex"},
    }
    return mapping.get(
        source_value,
        {"tool_id": source_value, "tool_name": source_value},
    )


def _display_model_name(model: str, tool_name: str = "Unknown Tool") -> str:
    """生成模型展示名，同时保留原始模型名用于排查。"""
    if model == "_total":
        return f"{tool_name} total"
    if not model:
        return "未知模型"
    return model


def _normalize_record_dimensions(row, device_names: dict[str, str]) -> dict:
    tool = _map_source_to_tool(getattr(row, "source", None))
    tool_id = getattr(row, "tool_id", None) or tool["tool_id"]
    tool_name = getattr(row, "tool_name", None) or tool["tool_name"]
    device_id = getattr(row, "device_id", None) or "unknown"
    device_name = (
        getattr(row, "device_name", None)
        or device_names.get(device_id)
        or device_id
    )
    model = getattr(row, "model", None) or "unknown"
    model_display_name = getattr(
        row, "model_display_name", None
    ) or _display_model_name(model, tool_name)
    return {
        "source": getattr(row, "source", None) or "unknown",
        "tool_id": tool_id,
        "tool_name": tool_name,
        "device_id": device_id,
        "device_name": device_name,
        "model": model,
        "model_display_name": model_display_name,
    }


def _load_device_names(db, user_id: str) -> dict[str, str]:
    rows = db.query(DeviceRegistry).filter(DeviceRegistry.user_id == user_id).all()
    return {
        row.device_id: row.display_name or row.default_display_name or row.device_id
        for row in rows
    }


def _build_dimension_summary(
    rows,
    dimension: str,
    total_tokens: int,
    total_cost: float,
) -> list[dict]:
    result = []
    for row in rows:
        row_tokens = int(getattr(row, "total_tokens", 0) or 0)
        row_cost = float(getattr(row, "total_cost", 0) or 0)
        result.append(
            {
                "dimension": dimension,
                "key": getattr(row, "key", "") or "",
                "label": getattr(row, "label", "") or "",
                "device_id": getattr(row, "device_id", None),
                "tool_id": getattr(row, "tool_id", None),
                "source": getattr(row, "source", None),
                "model": getattr(row, "model", None),
                "input_tokens": int(getattr(row, "input_tokens", 0) or 0),
                "output_tokens": int(getattr(row, "output_tokens", 0) or 0),
                "cache_creation_tokens": int(
                    getattr(row, "cache_creation_tokens", 0) or 0
                ),
                "cache_read_tokens": int(getattr(row, "cache_read_tokens", 0) or 0),
                "total_tokens": row_tokens,
                "total_cost": round(row_cost, 4),
                "token_share": round(
                    (row_tokens / total_tokens * 100) if total_tokens else 0,
                    4,
                ),
                "cost_share": round(
                    (row_cost / total_cost * 100) if total_cost else 0,
                    4,
                ),
                "records_count": int(getattr(row, "records_count", 0) or 0),
                "last_used_at": _to_iso(getattr(row, "last_used_at", None)),
            }
        )
    return result


def _empty_dimension_rows() -> DimensionSummaries:
    return DimensionSummaries()


def _empty_filter_options() -> FilterOptions:
    return FilterOptions()


def _empty_sync_meta() -> SyncMeta:
    return SyncMeta()


def _to_dimension_summaries(value) -> DimensionSummaries:
    if isinstance(value, DimensionSummaries):
        return value
    if not value:
        return _empty_dimension_rows()
    return DimensionSummaries(**value)


def _to_filter_options(value) -> FilterOptions:
    if isinstance(value, FilterOptions):
        return value
    if not value:
        return _empty_filter_options()
    return FilterOptions(**value)


def _to_sync_meta(value) -> SyncMeta:
    if isinstance(value, SyncMeta):
        return value
    if not value:
        return _empty_sync_meta()
    return SyncMeta(**value)


def _rollup_dimension(bucket: dict, row, dims: dict) -> None:
    bucket["input_tokens"] += int(getattr(row, "input_tokens", 0) or 0)
    bucket["output_tokens"] += int(getattr(row, "output_tokens", 0) or 0)
    bucket["cache_creation_tokens"] += int(
        getattr(row, "cache_creation_tokens", 0) or 0
    )
    bucket["cache_read_tokens"] += int(getattr(row, "cache_read_tokens", 0) or 0)
    bucket["total_tokens"] += int(getattr(row, "total_tokens", 0) or 0)
    bucket["total_cost"] += float(getattr(row, "total_cost", 0) or 0)
    bucket["records_count"] += 1
    updated_at = getattr(row, "updated_at", None) or getattr(row, "created_at", None)
    if updated_at and (
        bucket.get("last_used_at") is None or updated_at > bucket["last_used_at"]
    ):
        bucket["last_used_at"] = updated_at
    bucket.update(dims)


def _bucket_to_row(bucket: dict):
    return SimpleNamespace(**bucket)


def _build_dimension_data(records, device_names: dict[str, str]) -> tuple[dict, dict]:
    device_buckets: dict[str, dict] = {}
    tool_buckets: dict[str, dict] = {}
    model_buckets: dict[str, dict] = {}

    for row in records:
        dims = _normalize_record_dimensions(row, device_names)
        device_key = dims["device_id"]
        tool_key = dims["tool_id"]
        model_key = f"{dims['tool_id']}:{dims['model']}"

        device_bucket = device_buckets.setdefault(
            device_key,
            {
                "dimension": "device",
                "key": device_key,
                "label": dims["device_name"],
                "device_id": device_key,
                "tool_id": None,
                "source": None,
                "model": None,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0,
                "records_count": 0,
                "last_used_at": None,
            },
        )
        _rollup_dimension(device_bucket, row, {"label": dims["device_name"]})

        tool_bucket = tool_buckets.setdefault(
            tool_key,
            {
                "dimension": "tool",
                "key": tool_key,
                "label": dims["tool_name"],
                "device_id": None,
                "tool_id": tool_key,
                "source": dims["source"],
                "model": None,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0,
                "records_count": 0,
                "last_used_at": None,
            },
        )
        _rollup_dimension(
            tool_bucket,
            row,
            {"label": dims["tool_name"], "source": dims["source"]},
        )

        model_bucket = model_buckets.setdefault(
            model_key,
            {
                "dimension": "model",
                "key": model_key,
                "label": dims["model_display_name"],
                "device_id": None,
                "tool_id": tool_key,
                "source": dims["source"],
                "model": dims["model"],
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "total_tokens": 0,
                "total_cost": 0,
                "records_count": 0,
                "last_used_at": None,
            },
        )
        _rollup_dimension(
            model_bucket,
            row,
            {
                "label": dims["model_display_name"],
                "tool_id": tool_key,
                "source": dims["source"],
                "model": dims["model"],
            },
        )

    total_tokens = sum(bucket["total_tokens"] for bucket in device_buckets.values())
    total_cost = sum(bucket["total_cost"] for bucket in device_buckets.values())

    dimension_rows = {
        "devices": _build_dimension_summary(
            [_bucket_to_row(bucket) for bucket in device_buckets.values()],
            "device",
            total_tokens,
            total_cost,
        ),
        "tools": _build_dimension_summary(
            [_bucket_to_row(bucket) for bucket in tool_buckets.values()],
            "tool",
            total_tokens,
            total_cost,
        ),
        "models": _build_dimension_summary(
            [_bucket_to_row(bucket) for bucket in model_buckets.values()],
            "model",
            total_tokens,
            total_cost,
        ),
    }
    for values in dimension_rows.values():
        values.sort(key=lambda item: (item["total_cost"], item["total_tokens"]), reverse=True)

    filter_options = {
        "tools": [
            {
                "tool_id": item["tool_id"] or item["key"],
                "tool_name": item["label"],
                "records_count": item["records_count"],
            }
            for item in dimension_rows["tools"]
        ],
        "devices": [
            {
                "device_id": item["device_id"] or item["key"],
                "device_name": item["label"],
                "records_count": item["records_count"],
            }
            for item in dimension_rows["devices"]
        ],
        "models": [
            {
                "tool_id": item["tool_id"] or "",
                "source": item["source"] or "",
                "model": item["model"] or "",
                "model_display_name": item["label"],
                "records_count": item["records_count"],
            }
            for item in dimension_rows["models"]
        ],
    }
    return dimension_rows, filter_options


def build_chart_series(
    records: list, group_by: str
) -> list[dict]:
    """将 TokenUsageRecord 列表转换为图表所需的 (date, group_key) 序列。

    按 date + (可选) group_key 聚合 total_tokens 和 total_cost。
    行数上限：days × 最多 5 个 group_key（取 top 5 cost 维度）。
    """
    if not records:
        return []

    if group_by != "none":
        key_totals: dict[str, float] = {}
        for row in records:
            if group_by == "device":
                key = getattr(row, "device_id", None) or "unknown"
            elif group_by == "tool":
                key = getattr(row, "tool_id", None) or _map_source_to_tool(
                    getattr(row, "source", None)
                )["tool_id"]
            elif group_by == "model":
                key = getattr(row, "model", None) or "unknown"
            else:
                key = "_total"
            key_totals[key] = key_totals.get(key, 0.0) + float(
                getattr(row, "total_cost", 0) or 0
            )
        top_keys = sorted(key_totals.items(), key=lambda x: x[1], reverse=True)[:5]
        allowed_keys = {k for k, _ in top_keys}
    else:
        allowed_keys = None

    series_map: dict[tuple, dict] = {}
    for row in records:
        date_val = getattr(row, "record_date", None)
        if date_val is None:
            continue
        date_key = date_val.isoformat() if hasattr(date_val, "isoformat") else str(date_val)

        if group_by == "none":
            gk = None
        elif group_by == "device":
            gk = getattr(row, "device_id", None) or "unknown"
        elif group_by == "tool":
            gk = getattr(row, "tool_id", None) or _map_source_to_tool(
                getattr(row, "source", None)
            )["tool_id"]
        elif group_by == "model":
            gk = getattr(row, "model", None) or "unknown"
        else:
            gk = None

        if allowed_keys is not None and gk is not None and gk not in allowed_keys:
            continue

        key = (date_key, gk)
        bucket = series_map.setdefault(
            key, {"date": date_key, "group_key": gk, "total_tokens": 0, "total_cost": 0.0}
        )
        bucket["total_tokens"] += int(getattr(row, "total_tokens", 0) or 0)
        bucket["total_cost"] += float(getattr(row, "total_cost", 0) or 0)

    result = [
        {
            "date": v["date"],
            "group_key": v["group_key"],
            "total_tokens": v["total_tokens"],
            "total_cost": round(v["total_cost"], 4),
        }
        for v in series_map.values()
    ]
    result.sort(key=lambda x: (x["date"], x["group_key"] or ""))
    return result


def _query_dimension_data(db, user_id: str, req, since_date: datetime) -> tuple[dict, dict]:
    filters = _build_record_filters(user_id, req, since_date)
    records = db.query(TokenUsageRecord).filter(*filters).all()
    device_names = _load_device_names(db, user_id)
    if not records:
        return (
            _empty_dimension_rows().model_dump(),
            _empty_filter_options().model_dump(),
        )
    return _build_dimension_data(records, device_names)


def _sort_usage_items(items, sort_by: str, sort_order: str):
    allowed = {
        "date",
        "total_tokens",
        "total_cost",
        "input_tokens",
        "output_tokens",
        "cache_tokens",
    }
    selected = sort_by if sort_by in allowed else "date"
    reverse = sort_order != "asc"

    def sort_value(item):
        if selected == "cache_tokens":
            return (getattr(item, "cache_creation_tokens", 0) or 0) + (
                getattr(item, "cache_read_tokens", 0) or 0
            )
        return getattr(item, selected, None) or 0

    return sorted(items, key=sort_value, reverse=reverse)


def _build_sync_meta_from_values(
    now: datetime,
    last_success_at,
    cache_written_at,
    cache_ttl_seconds: int,
    configured_ttl_seconds: int,
    sources_status: list[dict],
    refresh_lock: dict,
) -> dict:
    """根据同步日志和缓存 TTL 计算数据新鲜度。"""
    last_dt = _align_datetime_to_reference(last_success_at, now)
    data_age_seconds = int((now - last_dt).total_seconds()) if last_dt else None
    stale_limit_minutes = max(int(configured_ttl_seconds / 60), 1)
    is_stale = last_dt is None or (
        data_age_seconds is not None and data_age_seconds > configured_ttl_seconds
    )

    stale_reason = None
    if last_dt is None:
        stale_reason = "尚未成功同步"
    elif is_stale:
        stale_reason = f"数据超过 {stale_limit_minutes} 分钟未同步"

    cache_expires_at = None
    if cache_written_at and cache_ttl_seconds > 0:
        written = _align_datetime_to_reference(cache_written_at, now)
        cache_expires_at = _to_iso(written + timedelta(seconds=cache_ttl_seconds))

    return {
        "last_synced_at": _to_iso(last_success_at),
        "last_success_at": _to_iso(last_success_at),
        "cache_written_at": _to_iso(cache_written_at),
        "cache_ttl_seconds": max(int(cache_ttl_seconds or 0), 0),
        "cache_expires_at": cache_expires_at,
        "data_age_seconds": data_age_seconds,
        "is_stale": is_stale,
        "stale_reason": stale_reason,
        "refresh_lock": refresh_lock,
        "sources_status": sources_status,
    }


def _rows_to_model_summary(rows) -> list[dict]:
    """将按 source/model 聚合的行转换为前端模型汇总。"""
    result = []
    for row in rows:
        source = row.source or "unknown"
        model = row.model or "unknown"
        tool_name = _map_source_to_tool(source)["tool_name"]
        result.append(
            {
                "source": source,
                "model": model,
                "display_model": _display_model_name(model, tool_name),
                "input_tokens": int(row.input_tokens or 0),
                "output_tokens": int(row.output_tokens or 0),
                "cache_creation_tokens": int(row.cache_creation_tokens or 0),
                "cache_read_tokens": int(row.cache_read_tokens or 0),
                "total_tokens": int(row.total_tokens or 0),
                "total_cost": round(float(row.total_cost or 0), 4),
            }
        )
    return sorted(
        result,
        key=lambda item: (item["total_cost"], item["total_tokens"]),
        reverse=True,
    )


def _build_record_filters(user_id: str, req, since_date: Optional[datetime] = None) -> list:
    """构建 Token Usage 记录查询条件，保证元信息和明细口径一致。"""
    filters = [TokenUsageRecord.user_id == user_id]
    if since_date is not None:
        filters.append(TokenUsageRecord.record_date >= since_date.date())
    if getattr(req, "source", "all") != "all":
        filters.append(TokenUsageRecord.source == req.source)
    if getattr(req, "device_id", None):
        filters.append(TokenUsageRecord.device_id == req.device_id)
    tool_id = getattr(req, "tool_id", None)
    if tool_id:
        source_matches = [
            source
            for source in ("claude", "opencode", "codex")
            if _map_source_to_tool(source)["tool_id"] == tool_id
        ]
        if tool_id not in source_matches:
            source_matches.append(tool_id)
        fallback_filters = [TokenUsageRecord.tool_id == tool_id]
        if source_matches:
            fallback_filters.append(
                (TokenUsageRecord.tool_id.is_(None))
                & (TokenUsageRecord.source.in_(source_matches))
            )
        filters.append(or_(*fallback_filters))
    if getattr(req, "model", None):
        filters.append(TokenUsageRecord.model == req.model)
    return filters


def _latest_record_updated_at(db, user_id: str, req):
    """当同步日志缺失时，用实际记录更新时间兜底显示数据更新时间。"""
    filters = _build_record_filters(user_id, req)
    row = (
        db.query(
            func.max(TokenUsageRecord.updated_at).label("updated_at"),
            func.max(TokenUsageRecord.created_at).label("created_at"),
        )
        .filter(*filters)
        .first()
    )
    if not row:
        return None
    return row.updated_at or row.created_at


def _query_item_model_map(db, user_id: str, req, since_date: datetime) -> dict[tuple, list[str]]:
    """查询每个明细行对应的模型集合，用于补全表格模型列。"""
    filters = _build_record_filters(user_id, req, since_date)

    if req.group_by == "device":
        rows = (
            db.query(
                TokenUsageRecord.record_date.label("date"),
                TokenUsageRecord.device_id.label("group_key"),
                TokenUsageRecord.model.label("model"),
            )
            .filter(*filters)
            .group_by(
                TokenUsageRecord.record_date,
                TokenUsageRecord.device_id,
                TokenUsageRecord.model,
            )
            .all()
        )
        model_map: dict[tuple, set[str]] = defaultdict(set)
        for row in rows:
            date_key = row.date.isoformat() if isinstance(row.date, date) else str(row.date)
            if row.model:
                model_map[(date_key, row.group_key)].add(row.model)
        return {key: sorted(values) for key, values in model_map.items()}

    if req.group_by == "model":
        rows = (
            db.query(
                TokenUsageRecord.record_date.label("date"),
                TokenUsageRecord.model.label("model"),
            )
            .filter(*filters)
            .group_by(TokenUsageRecord.record_date, TokenUsageRecord.model)
            .all()
        )
        result = {}
        for row in rows:
            date_key = row.date.isoformat() if isinstance(row.date, date) else str(row.date)
            result[(date_key, row.model)] = [row.model] if row.model else []
        return result

    if req.group_by == "tool":
        rows = db.query(TokenUsageRecord).filter(*filters).all()
        model_map: dict[tuple, set[str]] = defaultdict(set)
        for row in rows:
            dims = _normalize_record_dimensions(row, {})
            date_key = (
                row.record_date.isoformat()
                if isinstance(row.record_date, date)
                else str(row.record_date)
            )
            if row.model:
                model_map[(date_key, dims["tool_id"])].add(row.model)
        return {key: sorted(values) for key, values in model_map.items()}

    rows = (
        db.query(
            TokenUsageRecord.record_date.label("date"),
            TokenUsageRecord.model.label("model"),
        )
        .filter(*filters)
        .group_by(TokenUsageRecord.record_date, TokenUsageRecord.model)
        .all()
    )
    model_map = defaultdict(set)
    for row in rows:
        date_key = row.date.isoformat() if isinstance(row.date, date) else str(row.date)
        if row.model:
            model_map[(date_key, None)].add(row.model)
    return {key: sorted(values) for key, values in model_map.items()}


def _attach_models_to_items(db, user_id: str, req, since_date: datetime, items: list[DbUsageItem]) -> None:
    """为 DB 聚合结果补充 models_used，避免前端明细表模型列为空。"""
    model_map = _query_item_model_map(db, user_id, req, since_date)
    for item in items:
        key = (item.date, item.group_key if req.group_by != "none" else None)
        item.models_used = model_map.get(key, [])


def _get_sync_meta(db, user_id: str, req, cached_payload: Optional[dict]) -> dict:
    """读取同步日志并合成前端可展示的数据新鲜度。"""
    filters = [TokenUsageSyncLog.user_id == user_id]
    if req.source != "all":
        filters.append(TokenUsageSyncLog.source == req.source)

    latest_success = (
        db.query(TokenUsageSyncLog)
        .filter(
            *filters,
            TokenUsageSyncLog.status == "success",
        )
        .order_by(TokenUsageSyncLog.synced_at.desc())
        .first()
    )

    latest_logs = (
        db.query(TokenUsageSyncLog)
        .filter(*filters)
        .order_by(TokenUsageSyncLog.synced_at.desc())
        .limit(20)
        .all()
    )

    seen_sources = set()
    sources_status = []
    for row in latest_logs:
        if row.source in seen_sources:
            continue
        seen_sources.add(row.source)
        sources_status.append(
            {
                "source": row.source,
                "status": row.status,
                "records_count": row.records_count,
                "synced_at": _to_iso(row.synced_at),
                "error_message": row.error_message,
            }
        )

    last_success_at = latest_success.synced_at if latest_success else None
    if last_success_at is None:
        last_success_at = _latest_record_updated_at(db, user_id, req)

    return _build_sync_meta_from_values(
        now=datetime.now(),
        last_success_at=last_success_at,
        cache_written_at=_parse_cache_time(
            (cached_payload or {}).get("cache_written_at")
        ),
        cache_ttl_seconds=int((cached_payload or {}).get("_cache_ttl_seconds") or 0),
        configured_ttl_seconds=settings.CACHE_REDIS_TOKEN_USAGE_TTL,
        sources_status=sources_status,
        refresh_lock={"locked": False, "owner": None, "ttl_seconds": 0},
    )


def _execute_model_summary_query(db, user_id: str, req, since_date: datetime):
    """按 source/model 聚合模型统计，避免前端从日期行猜测。"""
    filters = _build_record_filters(user_id, req, since_date)

    return (
        db.query(
            TokenUsageRecord.source.label("source"),
            TokenUsageRecord.model.label("model"),
            func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
            func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
            func.sum(TokenUsageRecord.cache_creation_tokens).label(
                "cache_creation_tokens"
            ),
            func.sum(TokenUsageRecord.cache_read_tokens).label("cache_read_tokens"),
            func.sum(TokenUsageRecord.total_tokens).label("total_tokens"),
            func.sum(TokenUsageRecord.total_cost).label("total_cost"),
        )
        .filter(*filters)
        .group_by(
            TokenUsageRecord.source,
            TokenUsageRecord.model,
        )
        .all()
    )


def _finish_query_response(
    *,
    request_id: str,
    started_at: float,
    user_id: str,
    req: DbQueryRequest,
    items: list[DbUsageItem],
    summary: UsageSummary,
    devices: list[dict],
    cached: bool,
    response_source: str,
    actual_days: Optional[int] = None,
    auto_expanded: bool = False,
    model_summary: Optional[list] = None,
    dimension_summaries=None,
    filter_options=None,
    sync_meta=None,
) -> DbUsageResponse:
    """统一收口 Token Usage 查询响应和耗时日志。"""
    elapsed_ms = (time.perf_counter() - started_at) * 1000
    item_count = len(items)
    logger.info(
        "[%s] Token Usage 查询出口: 用户=%s, 来源=%s, source=%s, type=%s, "
        "days=%s, items=%s, cached=%s, 耗时=%.2fms",
        request_id,
        user_id,
        response_source,
        req.source,
        req.type,
        req.days,
        item_count,
        cached,
        elapsed_ms,
    )
    if elapsed_ms > 1000:
        logger.warning(
            "[%s] Token Usage 查询耗时超过 1 秒: 用户=%s, 耗时=%.2fms",
            request_id,
            user_id,
            elapsed_ms,
        )

    return DbUsageResponse(
        items=items,
        summary=summary,
        devices=devices,
        cached=cached,
        actual_days=actual_days,
        auto_expanded=auto_expanded,
        model_summary=[
            item if isinstance(item, ModelSummaryItem) else ModelSummaryItem(**item)
            for item in (model_summary or [])
        ],
        dimension_summaries=_to_dimension_summaries(dimension_summaries),
        filter_options=_to_filter_options(filter_options),
        sync_meta=_to_sync_meta(sync_meta),
    )


@router.post("/query", response_model=DbUsageResponse)
async def query_token_usage(
    req: DbQueryRequest,
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """统一查询端点：优先 Redis 缓存 → 降级 DB"""
    request_id = str(uuid.uuid4())
    started_at = time.perf_counter()
    user_id = "unknown"
    logger.info(
        "[%s] Token Usage 查询入口: source=%s, type=%s, days=%s, group_by=%s",
        request_id,
        req.source,
        req.type,
        req.days,
        req.group_by,
    )

    try:
        if not authorization:
            raise HTTPException(status_code=401, detail="Authorization header missing")
        try:
            user_id = get_current_user_id(authorization=authorization)
        except HTTPException:
            raise HTTPException(status_code=401, detail="认证失败")

        register_pending_sync_user(user_id)

        # 优先读取 Redis 缓存，命中时不访问数据库和 CLI。
        cached = get_query_cached_payload(
            source=req.source,
            report_type=req.type,
            days=req.days,
            group_by=req.group_by,
            user_id=user_id,
            device_id=req.device_id or "",
            tool_id=req.tool_id or "",
            model=req.model or "",
            sort_by=req.sort_by,
            sort_order=req.sort_order,
        )
        if cached:
            cached_items = [DbUsageItem(**item) for item in cached["items"]]
            return _finish_query_response(
                request_id=request_id,
                started_at=started_at,
                user_id=user_id,
                req=req,
                items=cached_items,
                summary=UsageSummary(**cached["summary"]),
                devices=cached.get("devices", []),
                cached=True,
                response_source="redis",
                model_summary=cached.get("model_summary", []),
                dimension_summaries=cached.get("dimension_summaries"),
                filter_options=cached.get("filter_options"),
                sync_meta=cached.get("sync_meta"),
            )

        # Redis 未命中时只读 DB，不在请求链路执行同步。
        db = SessionLocal()
        try:
            regs = (
                db.query(DeviceRegistry)
                .filter(DeviceRegistry.user_id == user_id)
                .all()
            )
            if regs:
                devices = [
                    {
                        "id": reg.device_id,
                        "name": reg.display_name
                        or reg.default_display_name
                        or reg.device_id,
                    }
                    for reg in regs
                ]
            else:
                device_ids = (
                    db.query(TokenUsageRecord.device_id)
                    .filter(TokenUsageRecord.user_id == user_id)
                    .distinct()
                    .all()
                )
                devices = [{"id": row[0], "name": row[0]} for row in device_ids]

            if req.source != "all":
                active_ids = set(
                    row[0]
                    for row in db.query(TokenUsageRecord.device_id)
                    .filter(
                        TokenUsageRecord.user_id == user_id,
                        TokenUsageRecord.source == req.source,
                    )
                    .distinct()
                    .all()
                )
                devices = [d for d in devices if d["id"] in active_ids]

            since_date = datetime.now() - timedelta(days=req.days)
            items = _execute_db_query(db, user_id, req, since_date)
            dimension_rows, filter_options = _query_dimension_data(
                db, user_id, req, since_date
            )
            _attach_models_to_items(db, user_id, req, since_date, items)

            auto_expanded = False
            actual_days = req.days
            if not items and req.days < 365:
                source_filter = _build_record_filters(user_id, req)
                has_any_data = (
                    db.query(TokenUsageRecord).filter(*source_filter).first()
                    is not None
                )
                if has_any_data:
                    since_date = datetime.now() - timedelta(days=365)
                    items = _execute_db_query(db, user_id, req, since_date)
                    _attach_models_to_items(db, user_id, req, since_date, items)
                    auto_expanded = True
                    actual_days = 365

            summary = compute_db_summary(items)
            model_summary = _rows_to_model_summary(
                _execute_model_summary_query(db, user_id, req, since_date)
            )
            dimension_rows, filter_options = _query_dimension_data(
                db, user_id, req, since_date
            )
            sync_meta_dict = _get_sync_meta(db, user_id, req, None)

            if not items:
                return _finish_query_response(
                    request_id=request_id,
                    started_at=started_at,
                    user_id=user_id,
                    req=req,
                    items=[],
                    summary=summary,
                    devices=devices,
                    cached=False,
                    response_source="db_empty",
                    actual_days=actual_days if auto_expanded else None,
                    auto_expanded=auto_expanded,
                    model_summary=model_summary,
                    dimension_summaries=dimension_rows,
                    filter_options=filter_options,
                    sync_meta=sync_meta_dict,
                )

            cache_payload = {
                "items": [item.model_dump() for item in items],
                "summary": summary.model_dump(),
                "devices": devices,
                "model_summary": model_summary,
                "dimension_summaries": dimension_rows,
                "filter_options": filter_options,
                "sync_meta": sync_meta_dict,
            }
            set_query_cached_data(
                source=req.source,
                report_type=req.type,
                days=req.days,
                group_by=req.group_by,
                user_id=user_id,
                device_id=req.device_id or "",
                tool_id=req.tool_id or "",
                model=req.model or "",
                sort_by=req.sort_by,
                sort_order=req.sort_order,
                data=cache_payload,
            )

            return _finish_query_response(
                request_id=request_id,
                started_at=started_at,
                user_id=user_id,
                req=req,
                items=items,
                summary=summary,
                devices=devices,
                cached=False,
                response_source="db",
                actual_days=actual_days if auto_expanded else None,
                auto_expanded=auto_expanded,
                model_summary=model_summary,
                dimension_summaries=dimension_rows,
                filter_options=filter_options,
                sync_meta=sync_meta_dict,
            )
        finally:
            db.close()
    except HTTPException:
        raise
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        logger.error(
            "[%s] Token Usage 查询异常: 错误=%s, 耗时=%.2fms",
            request_id,
            exc,
            elapsed_ms,
            exc_info=True,
        )
        return _finish_query_response(
            request_id=request_id,
            started_at=started_at,
            user_id=user_id,
            req=req,
            items=[],
            summary=compute_db_summary([]),
            devices=[],
            cached=False,
            response_source="fallback_empty",
            model_summary=[],
            dimension_summaries=_empty_dimension_rows(),
            filter_options=_empty_filter_options(),
            sync_meta=_empty_sync_meta(),
        )


def _execute_db_query(
    db, user_id: str, req: DbQueryRequest, since_date: datetime
) -> list[DbUsageItem]:
    """执行数据库聚合查询"""
    base_filter = _build_record_filters(user_id, req, since_date)

    if req.group_by == "device":
        # 按设备分组，返回每个设备的每日聚合
        results = (
            db.query(
                TokenUsageRecord.record_date.label("date"),
                TokenUsageRecord.device_id.label("group_key"),
                func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
                func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
                func.sum(TokenUsageRecord.cache_creation_tokens).label(
                    "cache_creation_tokens"
                ),
                func.sum(TokenUsageRecord.cache_read_tokens).label("cache_read_tokens"),
                func.sum(TokenUsageRecord.total_tokens).label("total_tokens"),
                func.sum(TokenUsageRecord.total_cost).label("total_cost"),
            )
            .filter(*base_filter)
            .group_by(TokenUsageRecord.record_date, TokenUsageRecord.device_id)
            .order_by(TokenUsageRecord.record_date)
            .all()
        )
    elif req.group_by == "tool":
        records = db.query(TokenUsageRecord).filter(*base_filter).all()
        buckets: dict[tuple[str, str], dict] = {}
        for record in records:
            dims = _normalize_record_dimensions(record, {})
            date_str = (
                record.record_date.isoformat()
                if isinstance(record.record_date, date)
                else str(record.record_date)
            )
            key = (date_str, dims["tool_id"])
            bucket = buckets.setdefault(
                key,
                {
                    "date": date_str,
                    "group_key": dims["tool_id"],
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_creation_tokens": 0,
                    "cache_read_tokens": 0,
                    "total_tokens": 0,
                    "total_cost": 0,
                },
            )
            bucket["input_tokens"] += int(record.input_tokens or 0)
            bucket["output_tokens"] += int(record.output_tokens or 0)
            bucket["cache_creation_tokens"] += int(record.cache_creation_tokens or 0)
            bucket["cache_read_tokens"] += int(record.cache_read_tokens or 0)
            bucket["total_tokens"] += int(record.total_tokens or 0)
            bucket["total_cost"] += float(record.total_cost or 0)
        results = [_bucket_to_row(bucket) for bucket in buckets.values()]
    elif req.group_by == "model":
        # 按模型分组
        results = (
            db.query(
                TokenUsageRecord.record_date.label("date"),
                TokenUsageRecord.model.label("group_key"),
                func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
                func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
                func.sum(TokenUsageRecord.cache_creation_tokens).label(
                    "cache_creation_tokens"
                ),
                func.sum(TokenUsageRecord.cache_read_tokens).label("cache_read_tokens"),
                func.sum(TokenUsageRecord.total_tokens).label("total_tokens"),
                func.sum(TokenUsageRecord.total_cost).label("total_cost"),
            )
            .filter(*base_filter)
            .group_by(TokenUsageRecord.record_date, TokenUsageRecord.model)
            .order_by(TokenUsageRecord.record_date)
            .all()
        )
    else:
        # 不分组，按日期聚合
        results = (
            db.query(
                TokenUsageRecord.record_date.label("date"),
                func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
                func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
                func.sum(TokenUsageRecord.cache_creation_tokens).label(
                    "cache_creation_tokens"
                ),
                func.sum(TokenUsageRecord.cache_read_tokens).label("cache_read_tokens"),
                func.sum(TokenUsageRecord.total_tokens).label("total_tokens"),
                func.sum(TokenUsageRecord.total_cost).label("total_cost"),
            )
            .filter(*base_filter)
            .group_by(TokenUsageRecord.record_date)
            .order_by(TokenUsageRecord.record_date)
            .all()
        )

    items = []
    for row in results:
        date_str = row.date.isoformat() if isinstance(row.date, date) else str(row.date)
        item = DbUsageItem(
            date=date_str,
            input_tokens=row.input_tokens or 0,
            output_tokens=row.output_tokens or 0,
            cache_creation_tokens=row.cache_creation_tokens or 0,
            cache_read_tokens=row.cache_read_tokens or 0,
            total_tokens=row.total_tokens or 0,
            total_cost=float(row.total_cost or 0),
        )
        if req.group_by in ("device", "tool", "model"):
            item.group_key = row.group_key
        items.append(item)

    return _sort_usage_items(items, req.sort_by, req.sort_order)

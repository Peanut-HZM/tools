"""Token 消耗统计 API 路由"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, date
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Body
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import func

from app.utils.usage_fetcher import UsageFetcher
from app.services.token_usage_cache import (
    get_cached_data,
    set_cached_data,
    invalidate_cache,
    get_query_cached_data,
    set_query_cached_data,
)
from app.models.base import SessionLocal
from app.models.token_usage_models import TokenUsageRecord, TokenUsageSyncLog, DeviceRegistry
from app.services.token_usage_sync_service import sync_token_usage
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
        input_tokens = _safe_int(tokens, "input") or _safe_int(entry, "inputTokens", "input_tokens")
        output_tokens = _safe_int(tokens, "output") or _safe_int(entry, "outputTokens", "output_tokens")
        cache_creation = _safe_int(tokens, "cache_write") or _safe_int(entry, "cacheCreationTokens", "cache_creation_tokens")
        cache_read = _safe_int(tokens, "cache_read") or _safe_int(entry, "cacheReadTokens", "cache_read_tokens")
        
        # 提取 breakdowns，支持多种字段名：modelBreakdowns, model_breakdowns, models
        breakdowns = entry.get("modelBreakdowns") or entry.get("model_breakdowns") or entry.get("models") or []
        
        # 提取 models_used，支持多种字段名并自动解析
        models_used = entry.get("modelsUsed") or entry.get("models_used") or []
        if not models_used and breakdowns:
            models_used = [m.get("model") or m.get("name") or m.get("modelName") or "unknown" for m in breakdowns]

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


@router.post("/refresh")
async def refresh_cache():
    """手动刷新所有 Token Usage 缓存"""
    invalidate_cache()
    return {"message": "缓存已清除，下次访问将重新获取数据"}


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
        regs = db.query(DeviceRegistry).filter(
            DeviceRegistry.user_id == user_id
        ).all()

        if regs:
            devices = [
                {"id": reg.device_id, "name": reg.display_name or reg.default_display_name or reg.device_id}
                for reg in regs
            ]
        else:
            device_ids = db.query(TokenUsageRecord.device_id).filter(
                TokenUsageRecord.user_id == user_id
            ).distinct().all()
            devices = [{"id": row[0], "name": row[0]} for row in device_ids]

        return {"devices": devices}
    finally:
        db.close()


# ========== 数据库查询与同步端点 ==========


class DbQueryRequest(BaseModel):
    type: str = Field(default="daily", description="daily | weekly | monthly")
    days: int = Field(default=30, ge=1, le=365, description="最近 N 天")
    group_by: str = Field(default="none", description="none | device | model")
    source: str = Field(default="all", description="claude | opencode | all")
    device_id: Optional[str] = Field(default=None, description="筛选特定设备，不传则查全部")


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
    group_key: Optional[str] = Field(default=None, description="设备名或模型名（分组时）")


class DeviceInfo(BaseModel):
    id: str
    name: str


class DbUsageResponse(BaseModel):
    items: list[DbUsageItem]
    summary: UsageSummary
    devices: list[dict] = Field(default_factory=list)
    cached: bool = False
    actual_days: Optional[int] = Field(default=None)
    auto_expanded: bool = False


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

    # 检查数据库中是否有该用户的数据
    db = SessionLocal()
    try:
        has_data = db.query(TokenUsageRecord).filter(
            TokenUsageRecord.user_id == user_id
        ).first() is not None

        if not has_data:
            # 降级到 CLI 直查模式
            return await _fallback_to_cli(req)

        # 获取设备列表（从 device_registry）
        regs = db.query(DeviceRegistry).filter(
            DeviceRegistry.user_id == user_id
        ).all()

        if regs:
            devices = []
            for reg in regs:
                name = reg.display_name or reg.default_display_name or reg.device_id
                devices.append({"id": reg.device_id, "name": name})
        else:
            # 兼容：旧数据没有 device_registry 记录，回退到 token_usage_records
            device_ids = db.query(TokenUsageRecord.device_id).filter(
                TokenUsageRecord.user_id == user_id
            ).distinct().all()
            devices = [{"id": row[0], "name": row[0]} for row in device_ids]

        # 如果有 source 过滤，只显示该 source 下有数据的设备
        if req.source != "all":
            active_ids = set(
                row[0] for row in db.query(TokenUsageRecord.device_id).filter(
                    TokenUsageRecord.user_id == user_id,
                    TokenUsageRecord.source == req.source,
                ).distinct().all()
            )
            devices = [d for d in devices if d["id"] in active_ids]

        # 执行查询
        since_date = datetime.now() - timedelta(days=req.days)
        items = _execute_db_query(db, user_id, req, since_date)

        # 计算汇总
        summary = compute_summary(items)

        return DbUsageResponse(
            items=items,
            summary=summary,
            devices=devices,
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

    result = sync_token_usage(user_id=user_id, days=90)
    return result


@router.put("/devices/{device_id}/rename")
async def rename_device(
    device_id: str,
    name: str = Body(..., embed=True, description="设备显示名称，空字符串表示重置为默认"),
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
        reg = db.query(DeviceRegistry).filter_by(
            user_id=user_id, device_id=device_id
        ).first()
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
            loop.run_in_executor(None, lambda: UsageFetcher.fetch_claude(
                report_type="daily", since=since, breakdown=True
            )),
            loop.run_in_executor(None, lambda: UsageFetcher.fetch_opencode(days=req.days)),
            return_exceptions=True,
        )
        if isinstance(claude_raw, Exception):
            claude_raw = {"error": str(claude_raw)}
        if isinstance(opencode_raw, Exception):
            opencode_raw = {"error": str(opencode_raw)}

        items_a = normalize_entries(claude_raw, req.type) if "error" not in claude_raw else []
        items_b = normalize_entries(opencode_raw, req.type) if "error" not in opencode_raw else []
        items_a = apply_aggregation(items_a, req.type)
        items_b = apply_aggregation(items_b, req.type)
        merged = merge_items(items_a, items_b)
        summary = compute_summary(merged)
        db_items = [DbUsageItem(**item.model_dump()) for item in merged]
    else:
        since = (datetime.now() - timedelta(days=req.days)).strftime("%Y%m%d")
        raw = UsageFetcher.fetch_claude(report_type="daily", since=since, breakdown=True) \
            if req.source == "claude" else UsageFetcher.fetch_opencode(days=req.days)
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


async def _fallback_to_cli_for_query(req: DbQueryRequest) -> DbUsageResponse:
    """DB 无数据时的最后降级（仅 claude source）"""
    loop = asyncio.get_event_loop()
    since = (datetime.now() - timedelta(days=req.days)).strftime("%Y%m%d")

    raw = await loop.run_in_executor(None, lambda: UsageFetcher.fetch_claude(
        report_type="daily", since=since, breakdown=False
    ))

    if "error" in raw:
        return DbUsageResponse(items=[], summary=UsageSummary(
            total_input_tokens=0, total_output_tokens=0, total_tokens=0,
            total_cost=0, days_count=0, avg_daily_cost=0
        ), devices=[])

    items = normalize_entries(raw, req.type)
    items = apply_aggregation(items, req.type)
    summary = compute_summary(items)

    return DbUsageResponse(
        items=[DbUsageItem(**i.model_dump()) for i in items],
        summary=summary,
        devices=[],
        cached=False,
    )


@router.post("/query", response_model=DbUsageResponse)
async def query_token_usage(
    req: DbQueryRequest,
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """统一查询端点：优先 Redis 缓存 → 降级 DB"""
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
    )
    if cached:
        logger.info(f"查询: Redis 缓存命中 /{req.source}/{req.type}/{req.days}天")
        return DbUsageResponse(
            items=[DbUsageItem(**item) for item in cached["items"]],
            summary=UsageSummary(**cached["summary"]),
            devices=cached.get("devices", []),
            cached=True,
        )

    # 2. Redis 未命中，查 DB
    db = SessionLocal()
    try:
        regs = db.query(DeviceRegistry).filter(
            DeviceRegistry.user_id == user_id
        ).all()
        if regs:
            devices = [
                {"id": reg.device_id, "name": reg.display_name or reg.default_display_name or reg.device_id}
                for reg in regs
            ]
        else:
            device_ids = db.query(TokenUsageRecord.device_id).filter(
                TokenUsageRecord.user_id == user_id
            ).distinct().all()
            devices = [{"id": row[0], "name": row[0]} for row in device_ids]

        if req.source != "all":
            active_ids = set(
                row[0] for row in db.query(TokenUsageRecord.device_id).filter(
                    TokenUsageRecord.user_id == user_id,
                    TokenUsageRecord.source == req.source,
                ).distinct().all()
            )
            devices = [d for d in devices if d["id"] in active_ids]

        since_date = datetime.now() - timedelta(days=req.days)
        items = _execute_db_query(db, user_id, req, since_date)

        auto_expanded = False
        actual_days = req.days
        if not items and req.days < 365:
            source_filter = [TokenUsageRecord.user_id == user_id]
            if req.source != "all":
                source_filter.append(TokenUsageRecord.source == req.source)
            if req.device_id:
                source_filter.append(TokenUsageRecord.device_id == req.device_id)
            has_any_data = db.query(TokenUsageRecord).filter(*source_filter).first() is not None
            if has_any_data:
                since_date = datetime.now() - timedelta(days=365)
                items = _execute_db_query(db, user_id, req, since_date)
                auto_expanded = True
                actual_days = 365

        summary = compute_db_summary(items)

        if not items:
            return await _fallback_to_cli(req)

        # 3. 写入 Redis 缓存
        cache_payload = {
            "items": [item.model_dump() for item in items],
            "summary": summary.model_dump(),
            "devices": devices,
        }
        set_query_cached_data(
            source=req.source,
            report_type=req.type,
            days=req.days,
            group_by=req.group_by,
            user_id=user_id,
            device_id=req.device_id or "",
            data=cache_payload,
        )

        return DbUsageResponse(
            items=items,
            summary=summary,
            devices=devices,
            cached=False,
            actual_days=actual_days if auto_expanded else None,
            auto_expanded=auto_expanded,
        )
    finally:
        db.close()


def _execute_db_query(db, user_id: str, req: DbQueryRequest, since_date: datetime) -> list[DbUsageItem]:
    """执行数据库聚合查询"""
    base_filter = [
        TokenUsageRecord.user_id == user_id,
        TokenUsageRecord.record_date >= since_date.date(),
    ]
    if req.source != "all":
        base_filter.append(TokenUsageRecord.source == req.source)
    if req.device_id:
        base_filter.append(TokenUsageRecord.device_id == req.device_id)

    if req.group_by == "device":
        # 按设备分组，返回每个设备的每日聚合
        results = db.query(
            TokenUsageRecord.record_date.label("date"),
            TokenUsageRecord.device_id.label("group_key"),
            func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
            func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
            func.sum(TokenUsageRecord.cache_creation_tokens).label("cache_creation_tokens"),
            func.sum(TokenUsageRecord.cache_read_tokens).label("cache_read_tokens"),
            func.sum(TokenUsageRecord.total_tokens).label("total_tokens"),
            func.sum(TokenUsageRecord.total_cost).label("total_cost"),
        ).filter(*base_filter).group_by(
            TokenUsageRecord.record_date, TokenUsageRecord.device_id
        ).order_by(TokenUsageRecord.record_date).all()
    elif req.group_by == "model":
        # 按模型分组
        results = db.query(
            TokenUsageRecord.record_date.label("date"),
            TokenUsageRecord.model.label("group_key"),
            func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
            func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
            func.sum(TokenUsageRecord.cache_creation_tokens).label("cache_creation_tokens"),
            func.sum(TokenUsageRecord.cache_read_tokens).label("cache_read_tokens"),
            func.sum(TokenUsageRecord.total_tokens).label("total_tokens"),
            func.sum(TokenUsageRecord.total_cost).label("total_cost"),
        ).filter(*base_filter).group_by(
            TokenUsageRecord.record_date, TokenUsageRecord.model
        ).order_by(TokenUsageRecord.record_date).all()
    else:
        # 不分组，按日期聚合
        results = db.query(
            TokenUsageRecord.record_date.label("date"),
            func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
            func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
            func.sum(TokenUsageRecord.cache_creation_tokens).label("cache_creation_tokens"),
            func.sum(TokenUsageRecord.cache_read_tokens).label("cache_read_tokens"),
            func.sum(TokenUsageRecord.total_tokens).label("total_tokens"),
            func.sum(TokenUsageRecord.total_cost).label("total_cost"),
        ).filter(*base_filter).group_by(
            TokenUsageRecord.record_date
        ).order_by(TokenUsageRecord.record_date).all()

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
        if req.group_by != "none":
            item.group_key = row.group_key
        items.append(item)

    return items

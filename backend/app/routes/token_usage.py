"""Token 消耗统计 API 路由"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, date
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Body
from pydantic import BaseModel, Field
from sqlalchemy import func, delete

from app.utils.usage_fetcher import UsageFetcher
from app.services.token_usage_cache import (
    get_cached_data,
    set_cached_data,
    invalidate_cache,
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
        input_tok = _safe_int(tokens, "input") or _safe_int(entry, "inputTokens", "input_tokens")
        output_tok = _safe_int(tokens, "output") or _safe_int(entry, "outputTokens", "output_tokens")
        cache_create_tok = _safe_int(tokens, "cache_write") or _safe_int(entry, "cacheCreationTokens", "cache_creation_tokens")
        cache_read_tok = _safe_int(tokens, "cache_read") or _safe_int(entry, "cacheReadTokens", "cache_read_tokens")
        # total_tokens 始终从四项之和计算，确保数值一致性
        total_tok = input_tok + output_tok + cache_create_tok + cache_read_tok
        items.append(
            UsageItem(
                date=date_val,
                input_tokens=input_tok,
                output_tokens=output_tok,
                cache_creation_tokens=cache_create_tok,
                cache_read_tokens=cache_read_tok,
                total_tokens=total_tok,
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
            total_tokens=v["inputTokens"] + v["outputTokens"] + v["cacheCreationTokens"] + v["cacheReadTokens"],
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
            total_tokens=v["inputTokens"] + v["outputTokens"] + v["cacheCreationTokens"] + v["cacheReadTokens"],
            total_cost=round(v["totalCost"], 4),
            models_used=list(v["modelsUsed"]),
        )
        for k, v in sorted(monthly.items())
    ]


def compute_summary(items: list[UsageItem]) -> UsageSummary:
    """计算汇总统计

    total_tokens 始终从四项组件之和计算，确保数值一致性：
    total_tokens = total_input_tokens + total_output_tokens
                 + total_cache_creation_tokens + total_cache_read_tokens
    不直接信任存储的 total_tokens 字段，因为历史数据可能存在 total_tokens=0 的错误记录。
    """
    count = max(len(items), 1)
    total_input = sum(i.input_tokens for i in items)
    total_output = sum(i.output_tokens for i in items)
    total_cache_creation = sum(i.cache_creation_tokens for i in items)
    total_cache_read = sum(i.cache_read_tokens for i in items)
    # 强制从四项组件计算，保证 total >= input
    total_tokens = total_input + total_output + total_cache_creation + total_cache_read
    return UsageSummary(
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_tokens=total_tokens,
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


def merge_items(items_a: list[UsageItem], items_b: list[UsageItem]) -> list[UsageItem]:
    """合并两个数据源的 UsageItem 列表，按日期分组求和"""
    merged: dict[str, dict] = defaultdict(
        lambda: {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
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
            total_tokens=v["input_tokens"] + v["output_tokens"] + v["cache_creation_tokens"] + v["cache_read_tokens"],
            total_cost=round(v["total_cost"], 4),
            models_used=list(v["models_used"]),
            model_breakdowns=v["model_breakdowns"],
        )
        for k, v in sorted(merged.items())
    ]


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


@router.post("/aggregate", response_model=UsageResponse)
async def get_aggregated_token_usage(req: AggregateUsageRequest):
    """获取所有工具的聚合 Token 消耗统计（优先从缓存读取）"""
    if req.type not in ("daily", "weekly", "monthly"):
        raise HTTPException(
            400,
            detail="type 必须是 'daily', 'weekly' 或 'monthly'",
        )

    # 1. 尝试从缓存读取
    cached = get_cached_data(
        source="aggregate",
        report_type=req.type,
        days=req.days,
        since=None,
        until=None,
        breakdown=req.breakdown,
        by=req.by,
    )
    if cached:
        logger.info("聚合数据: 返回缓存")
        return UsageResponse(
            items=[UsageItem(**item) for item in cached["items"]],
            summary=UsageSummary(**cached["summary"]),
            cached=True,
            cache_time=cached.get("cache_time"),
        )

    # 2. 缓存未命中，并发获取两个数据源
    loop = asyncio.get_event_loop()
    since_date = datetime.now() - timedelta(days=req.days)
    since = since_date.strftime("%Y%m%d")

    claude_raw, opencode_raw = await asyncio.gather(
        loop.run_in_executor(None, lambda: UsageFetcher.fetch_claude(
            report_type="daily", since=since, until=None, breakdown=req.breakdown
        )),
        loop.run_in_executor(None, lambda: UsageFetcher.fetch_opencode(
            days=req.days, by=req.by
        )),
        return_exceptions=True,
    )

    # 处理异常
    if isinstance(claude_raw, Exception):
        logger.warning(f"聚合: claude 获取异常: {claude_raw}")
        claude_raw = {"error": str(claude_raw)}
    if isinstance(opencode_raw, Exception):
        logger.warning(f"聚合: opencode 获取异常: {opencode_raw}")
        opencode_raw = {"error": str(opencode_raw)}

    # 两个都失败，返回 500
    if "error" in claude_raw and "error" in opencode_raw:
        raise HTTPException(
            500,
            detail=f"两个数据源均获取失败: claude={claude_raw['error']}; opencode={opencode_raw['error']}",
        )

    # 3. 分别规范化 + 聚合
    items_a = (
        normalize_entries(claude_raw, req.type) if "error" not in claude_raw else []
    )
    items_b = (
        normalize_entries(opencode_raw, req.type) if "error" not in opencode_raw else []
    )
    items_a = apply_aggregation(items_a, req.type)
    items_b = apply_aggregation(items_b, req.type)

    # 4. 合并
    merged = merge_items(items_a, items_b)
    summary = compute_summary(merged)

    if "error" in claude_raw:
        logger.warning("聚合: 仅使用 opencode 数据（claude 失败）")
    if "error" in opencode_raw:
        logger.warning("聚合: 仅使用 claude 数据（opencode 失败）")

    # 5. 写入缓存
    cache_time = datetime.now().isoformat()
    cache_data = {
        "items": [item.model_dump() for item in merged],
        "summary": summary.model_dump(),
        "cache_time": cache_time,
    }
    set_cached_data(
        source="aggregate",
        report_type=req.type,
        days=req.days,
        data=cache_data,
        since=None,
        until=None,
        breakdown=req.breakdown,
        by=req.by,
    )

    return UsageResponse(
        items=merged,
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
    devices: list[DeviceInfo] = Field(default_factory=list)
    cached: bool = False
    actual_days: Optional[int] = Field(default=None, description="实际查询的天数（当自动扩大时间范围时与请求天数不同）")
    auto_expanded: bool = Field(default=False, description="是否自动扩大了时间范围以获取数据")


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

        # 如果指定时间范围无数据，自动扩大到365天查询
        auto_expanded = False
        actual_days = req.days
        if not items and req.days < 365:
            # 检查该用户在该 source 下是否有任何数据
            source_filter = [TokenUsageRecord.user_id == user_id]
            if req.source != "all":
                source_filter.append(TokenUsageRecord.source == req.source)
            if req.device_id:
                source_filter.append(TokenUsageRecord.device_id == req.device_id)
            has_any_data = db.query(TokenUsageRecord).filter(*source_filter).first() is not None
            if has_any_data:
                # 有数据但不在当前时间范围，自动扩大到365天
                since_date = datetime.now() - timedelta(days=365)
                items = _execute_db_query(db, user_id, req, since_date)
                auto_expanded = True
                actual_days = 365

        # 计算汇总
        summary = compute_summary(items)

        return DbUsageResponse(
            items=items,
            summary=summary,
            devices=devices,
            actual_days=actual_days,
            auto_expanded=auto_expanded,
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


class CleanupRequest(BaseModel):
    scope: str = Field(description="清理范围: device, source, all")
    device_id: Optional[str] = Field(default=None, description="设备 ID，scope=device 时必填")
    source: Optional[str] = Field(default=None, description="数据源: claude, opencode，scope=source 时必填")
    resync: bool = Field(default=True, description="清除后是否自动重新同步")


class CleanupResponse(BaseModel):
    deleted_records: int
    deleted_logs: int
    cache_cleared: bool
    resync_started: bool
    message: str


@router.post("/cleanup", response_model=CleanupResponse)
async def cleanup_token_usage(
    req: CleanupRequest,
    authorization: Optional[str] = Header(None, description="Bearer token"),
):
    """清理 Token Usage 数据库记录和缓存，可按设备/数据源/全量清除，清除后可选重新同步"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    try:
        user_id = get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")

    db = SessionLocal()
    deleted_records = 0
    deleted_logs = 0

    try:
        # 构建 TokenUsageRecord 删除条件
        record_filters = [TokenUsageRecord.user_id == user_id]
        log_filters = [TokenUsageSyncLog.user_id == user_id]

        if req.scope == "device":
            if not req.device_id:
                raise HTTPException(status_code=400, detail="scope=device 时 device_id 不能为空")
            record_filters.append(TokenUsageRecord.device_id == req.device_id)
            log_filters.append(TokenUsageSyncLog.device_id == req.device_id)
        elif req.scope == "source":
            if not req.source:
                raise HTTPException(status_code=400, detail="scope=source 时 source 不能为空")
            if req.source not in ("claude", "opencode"):
                raise HTTPException(status_code=400, detail="source 必须是 claude 或 opencode")
            record_filters.append(TokenUsageRecord.source == req.source)
            log_filters.append(TokenUsageSyncLog.source == req.source)
        elif req.scope == "all":
            pass  # 只按 user_id 删除
        else:
            raise HTTPException(status_code=400, detail=f"不支持的 scope: {req.scope}，可选: device, source, all")

        # 删除 TokenUsageRecord
        deleted_records = db.query(TokenUsageRecord).filter(*record_filters).delete(synchronize_session=False)
        logger.info(f"[cleanup] 用户 {user_id} scope={req.scope} 删除 {deleted_records} 条 TokenUsageRecord")

        # 删除对应的同步日志
        deleted_logs = db.query(TokenUsageSyncLog).filter(*log_filters).delete(synchronize_session=False)
        logger.info(f"[cleanup] 用户 {user_id} scope={req.scope} 删除 {deleted_logs} 条 TokenUsageSyncLog")

        db.commit()

        # 清除 Redis 缓存
        from app.services.token_usage_cache import invalidate_cache
        cache_cleared = invalidate_cache()
        if not cache_cleared:
            logger.warning(f"[cleanup] 用户 {user_id} Redis 缓存清除失败或无缓存")

        # 可选：触发重新同步
        resync_started = False
        if req.resync and deleted_records > 0:
            try:
                sync_result = sync_token_usage(user_id=user_id, days=90)
                resync_started = True
                logger.info(f"[cleanup] 用户 {user_id} 重新同步完成: {sync_result}")
            except Exception as e:
                logger.error(f"[cleanup] 用户 {user_id} 重新同步失败: {e}")

        scope_desc = {
            "device": f"设备 {req.device_id}",
            "source": f"数据源 {req.source}",
            "all": "全部数据",
        }.get(req.scope, req.scope)

        return CleanupResponse(
            deleted_records=deleted_records,
            deleted_logs=deleted_logs,
            cache_cleared=cache_cleared,
            resync_started=resync_started,
            message=f"已清除 {scope_desc}: {deleted_records} 条记录, {deleted_logs} 条同步日志"
            + (", 已触发重新同步" if resync_started else ", 未触发重新同步"),
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"[cleanup] 清理失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")
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

    # total_tokens 始终从四项之和计算，不直接 SUM 存储字段
    total_expr = (
        func.sum(TokenUsageRecord.input_tokens)
        + func.sum(TokenUsageRecord.output_tokens)
        + func.sum(TokenUsageRecord.cache_creation_tokens)
        + func.sum(TokenUsageRecord.cache_read_tokens)
    )

    if req.group_by == "device":
        results = db.query(
            TokenUsageRecord.record_date.label("date"),
            TokenUsageRecord.device_id.label("group_key"),
            func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
            func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
            func.sum(TokenUsageRecord.cache_creation_tokens).label("cache_creation_tokens"),
            func.sum(TokenUsageRecord.cache_read_tokens).label("cache_read_tokens"),
            total_expr.label("total_tokens"),
            func.sum(TokenUsageRecord.total_cost).label("total_cost"),
        ).filter(*base_filter).group_by(
            TokenUsageRecord.record_date, TokenUsageRecord.device_id
        ).order_by(TokenUsageRecord.record_date).all()
    elif req.group_by == "model":
        results = db.query(
            TokenUsageRecord.record_date.label("date"),
            TokenUsageRecord.model.label("group_key"),
            func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
            func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
            func.sum(TokenUsageRecord.cache_creation_tokens).label("cache_creation_tokens"),
            func.sum(TokenUsageRecord.cache_read_tokens).label("cache_read_tokens"),
            total_expr.label("total_tokens"),
            func.sum(TokenUsageRecord.total_cost).label("total_cost"),
        ).filter(*base_filter).group_by(
            TokenUsageRecord.record_date, TokenUsageRecord.model
        ).order_by(TokenUsageRecord.record_date).all()
    else:
        results = db.query(
            TokenUsageRecord.record_date.label("date"),
            func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
            func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
            func.sum(TokenUsageRecord.cache_creation_tokens).label("cache_creation_tokens"),
            func.sum(TokenUsageRecord.cache_read_tokens).label("cache_read_tokens"),
            total_expr.label("total_tokens"),
            func.sum(TokenUsageRecord.total_cost).label("total_cost"),
        ).filter(*base_filter).group_by(
            TokenUsageRecord.record_date
        ).order_by(TokenUsageRecord.record_date).all()

    # 模型明细：所有分组模式都需要
    model_total_expr = (
        func.sum(TokenUsageRecord.input_tokens)
        + func.sum(TokenUsageRecord.output_tokens)
        + func.sum(TokenUsageRecord.cache_creation_tokens)
        + func.sum(TokenUsageRecord.cache_read_tokens)
    )
    model_results = db.query(
        TokenUsageRecord.record_date.label("date"),
        TokenUsageRecord.model,
        func.sum(TokenUsageRecord.input_tokens).label("input_tokens"),
        func.sum(TokenUsageRecord.output_tokens).label("output_tokens"),
        model_total_expr.label("total_tokens"),
        func.sum(TokenUsageRecord.total_cost).label("total_cost"),
    ).filter(*base_filter).group_by(
        TokenUsageRecord.record_date, TokenUsageRecord.model
    ).order_by(TokenUsageRecord.record_date).all()

    model_map: dict[str, list] = {}
    for row in model_results:
        date_str = row.date.isoformat() if isinstance(row.date, date) else str(row.date)
        if date_str not in model_map:
            model_map[date_str] = []
        model_map[date_str].append({
            "model": row.model,
            "inputTokens": row.input_tokens or 0,
            "outputTokens": row.output_tokens or 0,
            "totalTokens": row.total_tokens or 0,
            "cost": float(row.total_cost or 0),
        })

    items = []
    for row in results:
        date_str = row.date.isoformat() if isinstance(row.date, date) else str(row.date)
        # 获取该日期的模型明细
        breakdowns = model_map.get(date_str, [])
        models_list = [m["model"] for m in breakdowns] if breakdowns else []

        item = DbUsageItem(
            date=date_str,
            input_tokens=row.input_tokens or 0,
            output_tokens=row.output_tokens or 0,
            cache_creation_tokens=row.cache_creation_tokens or 0,
            cache_read_tokens=row.cache_read_tokens or 0,
            total_tokens=row.total_tokens or 0,
            total_cost=float(row.total_cost or 0),
            models_used=models_list,
            model_breakdowns=breakdowns,
        )
        if req.group_by != "none":
            item.group_key = row.group_key
        items.append(item)

    return items

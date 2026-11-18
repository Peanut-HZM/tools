"""Agent Hub 路由 — Agent 订阅与供应商中心（cc-switch + magpie 核心能力整合）。

设计文档: docs/plans/2026-11-18-agent-hub-design.md
- 全部路由需登录（切换会写本机 agent 配置文件，属敏感操作）
- 所有响应与日志对 api_key/credential 脱敏（仅前 4 位 + 长度）
- 用量查询错误契约：瞬时失败 → 502（前端可重试保旧值）；确定性失败 → 200 + success=False
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_current_user
from app.models.agent_hub_models import (
    AgentHubProvider,
    AgentHubSubscription,
    AgentHubSwitch,
)
from app.services.agent_hub.presets import PRESETS, SUPPORTED_AGENTS, get_preset
from app.services.agent_hub.usage_queries import (
    CredentialMissing,
    QueryContext,
    UsageQueryError,
    dispatch_query,
)
from app.services.agent_hub.agent_writers import (
    AgentWriterError,
    SUPPORTED_AGENTS as WRITER_AGENTS,
    WriteTarget,
    apply_provider_to_agent,
    preview_changes,
    restore_agent_backups,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agent-hub"])

BATCH_QUERY_CONCURRENCY = 5  # 设计文档 F07：批量查询并发上限


# ---------------------------------------------------------------------------
# 脱敏与序列化
# ---------------------------------------------------------------------------

def mask_secret(value: Optional[str]) -> str:
    if not value:
        return ""
    return f"{value[:4]}****({len(value)})"


def _provider_out(p: AgentHubProvider) -> Dict[str, Any]:
    return {
        "id": p.id, "name": p.name, "kind": p.kind, "app": p.app,
        "base_url": p.base_url or "",
        "api_key_masked": mask_secret(p.api_key),
        "has_api_key": bool(p.api_key),
        "usage_api_key_masked": mask_secret(p.usage_api_key),
        "has_usage_api_key": bool(p.usage_api_key),
        "usage_base_url": p.usage_base_url or "",
        "category": p.category,
        "website_url": p.website_url or "",
        "notes": p.notes or "",
        "enabled": bool(p.enabled),
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


def _subscription_out(s: AgentHubSubscription) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "id": s.id, "provider_id": s.provider_id or "", "name": s.name,
        "kind": s.kind,
        "credential_masked": mask_secret(s.credential),
        "has_credential": bool(s.credential),
        "credential_source": s.credential_source,
        "agent_app": s.agent_app or "",
        "base_url": s.base_url or "",
        "total_quota": s.total_quota or 0,
        "used_quota": s.used_quota or 0,
        "quota_unit": s.quota_unit or "credits",
        "window_type": s.window_type or "none",
        "window_reset_at": s.window_reset_at or "",
        "enabled": bool(s.enabled),
        "last_queried_at": s.last_queried_at or "",
        "extra_json": s.extra_json or "{}",
        "displayable": _is_displayable(s),
    }
    if s.last_query_json:
        try:
            out["last_query"] = json.loads(s.last_query_json)
        except ValueError:
            out["last_query"] = None
    else:
        out["last_query"] = None
    return out


def _is_displayable(s: AgentHubSubscription) -> bool:
    """「只显示已配置且可显示的」：enabled 且凭据就绪（manual 不需要凭据）。"""
    if not s.enabled:
        return False
    if s.kind == "manual":
        return True
    if s.credential:
        return True
    return False  # OAuth/凭据类订阅缺凭据 → 不显示（凭据来源 agent_file 时由查询器判断）


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ProviderIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: str
    app: str = "claude"
    base_url: str = ""
    api_key: str = ""
    usage_api_key: str = ""
    usage_base_url: str = ""
    category: str = "third_party"
    website_url: str = ""
    notes: str = ""
    enabled: bool = True
    extra_json: str = "{}"


class SubscriptionIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: str
    provider_id: str = ""
    credential: str = ""
    credential_source: str = "manual"
    agent_app: str = ""
    base_url: str = ""
    extra_json: str = "{}"
    total_quota: float = 0
    used_quota: float = 0
    quota_unit: str = "credits"
    window_type: str = "none"
    window_reset_at: str = ""
    enabled: bool = True


class QuotaAdjustIn(BaseModel):
    total_quota: Optional[float] = None
    used_quota: Optional[float] = None
    quota_unit: Optional[str] = None
    window_type: Optional[str] = None
    window_reset_at: Optional[str] = None


class SwitchIn(BaseModel):
    provider_id: str


# ---------------------------------------------------------------------------
# 预设
# ---------------------------------------------------------------------------

@router.get("/presets")
def list_presets(current_user: dict = Depends(get_current_user)):
    return {"presets": PRESETS, "agents": WRITER_AGENTS}


# ---------------------------------------------------------------------------
# Providers CRUD
# ---------------------------------------------------------------------------

@router.get("/providers")
def list_providers(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    rows = db.query(AgentHubProvider).order_by(AgentHubProvider.created_at.desc()).all()
    return {"providers": [_provider_out(p) for p in rows]}


@router.post("/providers")
def create_provider(payload: ProviderIn, db: Session = Depends(get_db),
                    current_user: dict = Depends(get_current_user)):
    if get_preset(payload.kind) is None:
        raise HTTPException(400, f"不支持的供应商类型: {payload.kind}")
    row = AgentHubProvider(
        name=payload.name, kind=payload.kind, app=payload.app,
        base_url=payload.base_url, api_key=payload.api_key,
        usage_api_key=payload.usage_api_key, usage_base_url=payload.usage_base_url,
        category=payload.category, website_url=payload.website_url,
        notes=payload.notes, enabled=1 if payload.enabled else 0,
        extra_json=payload.extra_json,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"provider": _provider_out(row)}


@router.put("/providers/{provider_id}")
def update_provider(provider_id: str, payload: ProviderIn,
                    db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = db.query(AgentHubProvider).filter(AgentHubProvider.id == provider_id).first()
    if not row:
        raise HTTPException(404, "供应商不存在")
    for field in ("name", "kind", "app", "base_url", "category", "website_url", "notes", "extra_json"):
        setattr(row, field, getattr(payload, field))
    if payload.api_key:  # 空 = 不修改已存 key
        row.api_key = payload.api_key
    if payload.usage_api_key:
        row.usage_api_key = payload.usage_api_key
    row.enabled = 1 if payload.enabled else 0
    db.commit()
    return {"provider": _provider_out(row)}


@router.delete("/providers/{provider_id}")
def delete_provider(provider_id: str, db: Session = Depends(get_db),
                    current_user: dict = Depends(get_current_user)):
    row = db.query(AgentHubProvider).filter(AgentHubProvider.id == provider_id).first()
    if not row:
        raise HTTPException(404, "供应商不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Subscriptions CRUD + 额度手动调整 ✅
# ---------------------------------------------------------------------------

@router.get("/subscriptions")
def list_subscriptions(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    rows = db.query(AgentHubSubscription).order_by(AgentHubSubscription.created_at.desc()).all()
    return {"subscriptions": [_subscription_out(s) for s in rows]}


@router.post("/subscriptions")
def create_subscription(payload: SubscriptionIn, db: Session = Depends(get_db),
                        current_user: dict = Depends(get_current_user)):
    if get_preset(payload.kind) is None:
        raise HTTPException(400, f"不支持的订阅类型: {payload.kind}")
    row = AgentHubSubscription(
        name=payload.name, kind=payload.kind, provider_id=payload.provider_id,
        credential=payload.credential, credential_source=payload.credential_source,
        agent_app=payload.agent_app, base_url=payload.base_url,
        extra_json=payload.extra_json, total_quota=payload.total_quota,
        used_quota=payload.used_quota, quota_unit=payload.quota_unit,
        window_type=payload.window_type, window_reset_at=payload.window_reset_at,
        enabled=1 if payload.enabled else 0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"subscription": _subscription_out(row)}


@router.put("/subscriptions/{sub_id}")
def update_subscription(sub_id: str, payload: SubscriptionIn,
                        db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    row = db.query(AgentHubSubscription).filter(AgentHubSubscription.id == sub_id).first()
    if not row:
        raise HTTPException(404, "订阅不存在")
    for field in ("name", "kind", "provider_id", "credential_source", "agent_app",
                  "base_url", "extra_json", "quota_unit", "window_type", "window_reset_at"):
        setattr(row, field, getattr(payload, field))
    if payload.credential:
        row.credential = payload.credential
    if payload.kind == "manual":
        row.total_quota = payload.total_quota
        row.used_quota = payload.used_quota
    row.enabled = 1 if payload.enabled else 0
    db.commit()
    return {"subscription": _subscription_out(row)}


@router.put("/subscriptions/{sub_id}/quota")
def adjust_quota(sub_id: str, payload: QuotaAdjustIn,
                 db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """手动调整额度 ✅（额度支持手动增加；仅 manual 类型有意义，其他类型忽略额度字段）。"""
    row = db.query(AgentHubSubscription).filter(AgentHubSubscription.id == sub_id).first()
    if not row:
        raise HTTPException(404, "订阅不存在")
    if payload.total_quota is not None:
        row.total_quota = max(0.0, float(payload.total_quota))
    if payload.used_quota is not None:
        row.used_quota = max(0.0, float(payload.used_quota))
    if payload.quota_unit:
        row.quota_unit = payload.quota_unit
    if payload.window_type is not None:
        row.window_type = payload.window_type
    if payload.window_reset_at is not None:
        row.window_reset_at = payload.window_reset_at
    db.commit()
    return {"subscription": _subscription_out(row)}


@router.delete("/subscriptions/{sub_id}")
def delete_subscription(sub_id: str, db: Session = Depends(get_db),
                        current_user: dict = Depends(get_current_user)):
    row = db.query(AgentHubSubscription).filter(AgentHubSubscription.id == sub_id).first()
    if not row:
        raise HTTPException(404, "订阅不存在")
    db.delete(row)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# 用量查询
# ---------------------------------------------------------------------------

def _build_query_ctx(sub: AgentHubSubscription, db: Session) -> QueryContext:
    provider = None
    if sub.provider_id:
        provider = db.query(AgentHubProvider).filter(
            AgentHubProvider.id == sub.provider_id).first()
    return QueryContext(
        kind=sub.kind,
        api_key=(sub.credential or (provider.api_key if provider else "") or ""),
        base_url=(sub.base_url or (provider.base_url if provider else "") or ""),
        usage_api_key=(provider.usage_api_key if provider else "") or sub.credential,
        usage_base_url=(provider.usage_base_url if provider else "") or (provider.base_url if provider else ""),
        agent_app=sub.agent_app or "",
        extra=json.loads(sub.extra_json or "{}") if sub.extra_json else {},
    )


def _run_single_query(sub: AgentHubSubscription, ctx: QueryContext) -> Dict[str, Any]:
    if sub.kind == "manual":
        return dispatch_query(ctx, total=sub.total_quota or 0,
                              used=sub.used_quota or 0, unit=sub.quota_unit or "credits")
    return dispatch_query(ctx)


def _query_one(sub: AgentHubSubscription, db: Session) -> Dict[str, Any]:
    """查询单订阅：成功/确定性失败写 last_query_json（keep-last-good）；瞬时失败抛 UsageQueryError。"""
    ctx = _build_query_ctx(sub, db)
    if sub.kind != "manual" and not (ctx.api_key or ctx.usage_api_key or sub.credential
                                     or sub.kind in ("claude_official", "codex_official", "gemini_official")):
        return {"id": sub.id, "name": sub.name, "success": False,
                "error": "未配置查询凭据", "not_configured": True, "queried_at": _now_iso()}
    try:
        result = _run_single_query(sub, ctx)
    except CredentialMissing as e:
        result = {"success": False, "error": str(e), "not_configured": True,
                  "queried_at": _now_iso()}
    except UsageQueryError as e:
        raise HTTPException(502, f"{sub.name}: {e}")
    sub.last_query_json = json.dumps(result, ensure_ascii=False)
    sub.last_queried_at = result.get("queried_at") or datetime.utcnow().isoformat()
    db.commit()
    return {"id": sub.id, "name": sub.name, **result}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.post("/subscriptions/{sub_id}/usage")
def query_subscription_usage(sub_id: str, db: Session = Depends(get_db),
                             current_user: dict = Depends(get_current_user)):
    sub = db.query(AgentHubSubscription).filter(AgentHubSubscription.id == sub_id).first()
    if not sub:
        raise HTTPException(404, "订阅不存在")
    if not _is_displayable(sub) and sub.kind != "manual":
        raise HTTPException(400, "订阅未启用或未配置凭据，不参与查询")
    return _query_one(sub, db)


@router.get("/subscriptions/usage/all")
def query_all_usage(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """批量查询全部已启用订阅（并发上限 5；单订阅失败不影响其他）。

    每个线程使用独立 DB Session（并发共享 get_db 的 Session 会导致
    commit 状态冲突 SessionTransactionState.CLOSED）。
    """
    rows = db.query(AgentHubSubscription).filter(AgentHubSubscription.enabled == 1).all()
    sub_ids = [r.id for r in rows]
    results: List[Dict[str, Any]] = []
    if not rows:
        return {"results": results}

    from app.models.base import SessionLocal

    def worker(sub_id: str):
        worker_db = SessionLocal()
        sub_name = ""
        try:
            sub = worker_db.query(AgentHubSubscription).filter(
                AgentHubSubscription.id == sub_id).first()
            if sub is None:
                return {"id": sub_id, "success": False, "error": "订阅已删除",
                        "queried_at": _now_iso()}
            sub_name = sub.name
            return _query_one(sub, worker_db)
        except HTTPException as e:
            return {"id": sub_id, "name": sub_name, "success": False,
                    "error": e.detail, "queried_at": _now_iso()}
        except Exception as e:  # noqa: BLE001
            logger.warning("Agent Hub 订阅查询异常: %s %s", sub_id, e)
            return {"id": sub_id, "name": sub_name, "success": False,
                    "error": str(e), "queried_at": _now_iso()}
        finally:
            worker_db.close()

    with ThreadPoolExecutor(max_workers=BATCH_QUERY_CONCURRENCY) as pool:
        futures = [pool.submit(worker, sid) for sid in sub_ids]
        for future in as_completed(futures):
            results.append(future.result())
    return {"results": results}


# ---------------------------------------------------------------------------
# Agent 切换
# ---------------------------------------------------------------------------

@router.get("/agents")
def list_agents(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    """检测本机各 agent 配置存在性 + 当前激活 provider。"""
    from pathlib import Path

    from app.services.agent_hub.agent_writers import AGENT_FILES, real_home

    home = real_home()
    switches = {s.agent: s for s in db.query(AgentHubSwitch).all()}
    providers = {p.id: p for p in db.query(AgentHubProvider).all()}
    agents = []
    for agent in WRITER_AGENTS:
        switch = switches.get(agent)
        provider_name = ""
        if switch and switch.provider_id and switch.provider_id in providers:
            provider_name = providers[switch.provider_id].name
        agents.append({
            "agent": agent,
            "files": [{"path": str(home / rel), "exists": (home / rel).exists()}
                      for rel in AGENT_FILES[agent]],
            # 主配置文件存在即视为已安装（排除 auth.json 等纯凭据文件；
            # settings.json 是 claude/zcode 的主配置，必须计入）
            "configured": any((home / rel).exists() for rel in AGENT_FILES[agent]
                              if "auth.json" not in rel),
            "current_provider_id": switch.provider_id if switch else "",
            "current_provider_name": provider_name,
            "switched_at": switch.switched_at if switch else "",
        })
    return {"agents": agents, "supported": WRITER_AGENTS}


@router.get("/agents/{agent}/config-preview")
def agent_config_preview(agent: str, provider_id: str,
                         db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    provider = db.query(AgentHubProvider).filter(AgentHubProvider.id == provider_id).first()
    if not provider:
        raise HTTPException(404, "供应商不存在")
    try:
        return preview_changes(agent, WriteTarget(
            agent=agent, name=provider.name, base_url=provider.base_url or "",
            api_key=provider.api_key or "",
            model=(json.loads(provider.extra_json or "{}") or {}).get("model", "")))
    except AgentWriterError as e:
        raise HTTPException(400, str(e))


@router.post("/agents/{agent}/switch")
def switch_agent(agent: str, payload: SwitchIn, db: Session = Depends(get_db),
                 current_user: dict = Depends(get_current_user)):
    if agent not in WRITER_AGENTS:
        raise HTTPException(400, f"不支持的 agent: {agent}")
    provider = db.query(AgentHubProvider).filter(AgentHubProvider.id == payload.provider_id).first()
    if not provider:
        raise HTTPException(404, "供应商不存在")
    try:
        result = apply_provider_to_agent(
            agent, WriteTarget(
                agent=agent, name=provider.name, base_url=provider.base_url or "",
                api_key=provider.api_key or "",
                model=(json.loads(provider.extra_json or "{}") or {}).get("model", "")),
            provider_kind=provider.kind)
    except AgentWriterError as e:
        raise HTTPException(400, str(e))
    switch = db.query(AgentHubSwitch).filter(AgentHubSwitch.agent == agent).first()
    if not switch:
        switch = AgentHubSwitch(agent=agent)
        db.add(switch)
    switch.provider_id = provider.id
    switch.switched_at = datetime.utcnow().isoformat()
    db.commit()
    return {"ok": True, "switch": {"agent": agent, "provider_id": provider.id,
                                   "provider_name": provider.name,
                                   "written": result["written"]}}


@router.post("/agents/{agent}/restore")
def restore_agent(agent: str, current_user: dict = Depends(get_current_user)):
    if agent not in WRITER_AGENTS:
        raise HTTPException(400, f"不支持的 agent: {agent}")
    restored = restore_agent_backups(agent)
    return {"ok": True, "restored": restored}

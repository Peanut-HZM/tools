"""Agent Hub 用量查询器 — 按 kind 分派，端点/鉴权/解析与 cc-switch 对齐。

统一返回（设计文档 §5）:
    {success: bool, plan_name?: str,
     tiers: [{name, used, total, unit, resets_at?, utilization?}],
     balance?: {value, unit}, error?, queried_at}

错误契约（对齐 cc-switch）:
- 瞬时传输失败（网络/超时/非 2xx 网络）→ UsageQueryError（上层转 502，前端可重试保旧值）
- 确定性失败（鉴权 401/403、响应结构不符）→ 返回 success=False + error（前端显示错误但保留旧值）
- 未配置凭据 → CredentialMissing（不参与显示）
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10  # 设计文档 §4：统一 10s 超时
USER_AGENT = "tools-agent-hub/1.0"


class UsageQueryError(Exception):
    """瞬时传输失败（网络/超时/5xx）——上层转 502，前端可重试保旧值。"""


class CredentialMissing(Exception):
    """查询凭据缺失（agent OAuth 文件不存在 / 未手填）——不参与显示。"""


@dataclass
class QueryContext:
    """一次用量查询的凭据与参数。"""
    kind: str
    api_key: str = ""
    base_url: str = ""
    usage_api_key: str = ""
    usage_base_url: str = ""
    agent_app: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_http_url(url: str) -> str:
    """自定义 base_url 仅允许 http(s)（设计文档 §4 密钥安全段）。"""
    lowered = (url or "").strip().lower()
    if not (lowered.startswith("https://") or lowered.startswith("http://")):
        raise UsageQueryError(f"base_url 仅允许 http(s) 协议: {url!r}")
    return url.strip().rstrip("/")


def _get_json(url: str, headers: Dict[str, str], timeout: int = REQUEST_TIMEOUT) -> Dict[str, Any]:
    try:
        resp = requests.get(url, headers={**headers, "User-Agent": USER_AGENT},
                            timeout=timeout, allow_redirects=True)
    except requests.RequestException as e:
        raise UsageQueryError(f"网络请求失败: {e}") from e
    if resp.status_code in (401, 403):
        return {"_http_status": resp.status_code, "_denied": True,
                "_body": (resp.text or "")[:200]}
    if resp.status_code >= 500:
        raise UsageQueryError(f"上游服务错误 HTTP {resp.status_code}")
    try:
        data = resp.json()
    except ValueError as e:
        raise UsageQueryError(f"响应不是合法 JSON: {str(e)[:120]}") from e
    if isinstance(data, dict):
        data.setdefault("_http_status", resp.status_code)
    return data


def _denied(data: Dict[str, Any]) -> bool:
    return bool(data.get("_denied"))


def _tier(name: str, used: float, total: float, unit: str,
          resets_at: str = "") -> Dict[str, Any]:
    utilization = round(used / total * 100, 1) if total else 0.0
    entry = {"name": name, "used": used, "total": total, "unit": unit,
             "utilization": utilization}
    if resets_at:
        entry["resets_at"] = resets_at
    return entry


def _result(tiers: List[Dict[str, Any]], plan_name: str = "",
            balance: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True, "tiers": tiers, "queried_at": _now_iso()}
    if plan_name:
        out["plan_name"] = plan_name
    if balance is not None:
        out["balance"] = balance
    return out


def _denied_result(what: str) -> Dict[str, Any]:
    return {"success": False, "error": f"{what} 鉴权失败（401/403），请检查查询凭据",
            "queried_at": _now_iso(), "credential_expired": True}


# ---------------------------------------------------------------------------
# Coding Plan / 套餐查询器（key 类）
# ---------------------------------------------------------------------------

def query_opendesign(ctx: QueryContext) -> Dict[str, Any]:
    """OpenDesign：控制面 workspace/current → billing/snapshot（designPlanWindows 5h/7d credits）。"""
    key = ctx.usage_api_key or ctx.api_key
    if not key:
        raise CredentialMissing("OpenDesign 需要 AMR 控制面 controlKey（推理 key 会被 401 拒绝）")
    base = _validate_http_url(ctx.usage_base_url or "https://amr-api.open-design.ai")
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    cur = _get_json(f"{base}/api/v1/workspaces/current", headers)
    if _denied(cur):
        return _denied_result("OpenDesign")
    workspace_id = (cur.get("workspace") or cur.get("data") or {}).get("id") or cur.get("id")
    if not workspace_id:
        raise UsageQueryError("workspace/current 响应中未找到 workspace id")
    snap = _get_json(f"{base}/api/v1/workspaces/{workspace_id}/billing/snapshot", headers)
    if _denied(snap):
        return _denied_result("OpenDesign")
    windows = (snap.get("billing") or snap.get("data") or snap).get("designPlanWindows") or []
    tiers = []
    kind_label = {"5h": "5小时窗口", "7d": "7天窗口"}
    for w in windows:
        kind = str(w.get("kind", ""))
        limit = float(w.get("limitCredits") or 0)
        remaining = float(w.get("remainingCredits") or 0)
        if limit <= 0:
            continue
        tiers.append(_tier(kind_label.get(kind, kind or "窗口"),
                           used=round(limit - remaining, 2), total=limit,
                           unit="credits", resets_at=str(w.get("resetsAt") or "")))
    return _result(tiers)


def query_kimi(ctx: QueryContext) -> Dict[str, Any]:
    """Kimi For Coding：/coding/v1/usages（5h detail + 周 usage）。"""
    if not ctx.api_key:
        raise CredentialMissing("Kimi 需要 API key")
    base = _validate_http_url(ctx.base_url or "https://api.kimi.com")
    data = _get_json(f"{base}/coding/v1/usages", {"Authorization": f"Bearer {ctx.api_key}"})
    if _denied(data):
        return _denied_result("Kimi")
    tiers = []
    for lim in data.get("limits") or []:
        detail = lim.get("detail") or {}
        limit, remaining = float(detail.get("limit") or 0), float(detail.get("remaining") or 0)
        if limit > 0:
            tiers.append(_tier("5小时窗口", used=round(limit - remaining, 2), total=limit,
                               unit="requests", resets_at=str(detail.get("resetTime") or "")))
    usage = data.get("usage") or {}
    limit, remaining = float(usage.get("limit") or 0), float(usage.get("remaining") or 0)
    if limit > 0:
        tiers.append(_tier("周额度", used=round(limit - remaining, 2), total=limit,
                           unit="requests", resets_at=str(usage.get("resetTime") or "")))
    return _result(tiers, plan_name=str(data.get("plan") or ""))


def query_zhipu(ctx: QueryContext) -> Dict[str, Any]:
    """智谱 GLM：/api/monitor/usage/quota/limit（Authorization 无 Bearer）；按量账户回落查余额。"""
    if not ctx.api_key:
        raise CredentialMissing("智谱需要 API key")
    base = _validate_http_url(ctx.base_url or "https://open.bigmodel.cn")
    data = _get_json(f"{base}/api/monitor/usage/quota/limit",
                     {"Authorization": ctx.api_key, "Accept-Language": "en-US,en"})
    if _denied(data):
        return _denied_result("智谱")
    payload = data.get("data") or {}
    limits = payload.get("limits") or []
    unit_map = {3: "5小时窗口", 6: "周额度"}
    tiers = []
    for lim in limits:
        unit_code = lim.get("unit")
        if unit_code not in unit_map:
            continue
        percentage = float(lim.get("percentage") or 0)
        tiers.append(_tier(unit_map[unit_code], used=round(percentage, 1), total=100,
                           unit="percent", resets_at=str(lim.get("nextResetTime") or "")))
    if not tiers:
        # 无 coding plan → 回落查余额（cc-switch ZhipuNoPlan 同路径）
        bal = _get_json(f"{base}/api/biz/account/query-customer-account-report",
                        {"Authorization": ctx.api_key})
        if _denied(bal):
            return _denied_result("智谱")
        bdata = bal.get("data") or {}
        available = bdata.get("availableBalance") or bdata.get("balance") or 0
        return _result([], balance={"value": float(available or 0), "unit": "CNY"})
    return _result(tiers, plan_name=str(payload.get("level") or ""))


def query_minimax(ctx: QueryContext) -> Dict[str, Any]:
    """MiniMax：/v1/api/openplatform/coding_plan/remains（general 行）。"""
    if not ctx.api_key:
        raise CredentialMissing("MiniMax 需要 API key")
    base = _validate_http_url(ctx.base_url or "https://api.minimaxi.com")
    data = _get_json(f"{base}/v1/api/openplatform/coding_plan/remains",
                     {"Authorization": f"Bearer {ctx.api_key}"})
    if _denied(data):
        return _denied_result("MiniMax")
    rows = data.get("model_remins") or data.get("model_remaIns") or []
    general = next((r for r in rows if r.get("model_name") == "general"), None)
    if not general:
        return _result([])
    tiers = []
    interval_remaining = general.get("current_interval_remaining_percent")
    if interval_remaining is not None:
        used = round(100 - float(interval_remaining), 1)
        tiers.append(_tier("5小时窗口", used=used, total=100, unit="percent",
                           resets_at=str(general.get("end_time") or "")))
    weekly_remaining = general.get("current_weekly_remaining_percent")
    status = general.get("current_weekly_status")
    if weekly_remaining is not None and status in (1, 2):
        used = round(100 - float(weekly_remaining), 1)
        tiers.append(_tier("周额度", used=used, total=100, unit="percent",
                           resets_at=str(general.get("weekly_end_time") or "")))
    return _result(tiers)


def query_zenmux(ctx: QueryContext) -> Dict[str, Any]:
    """ZenMux：data.quota_5_hour / quota_7_day（usage_percentage + USD）。"""
    if not ctx.api_key:
        raise CredentialMissing("ZenMux 需要 API key")
    base = _validate_http_url(ctx.base_url)
    data = _get_json(base, {"Authorization": f"Bearer {ctx.api_key}"})
    if _denied(data):
        return _denied_result("ZenMux")
    payload = data.get("data") or {}
    tiers = []
    for key, label in (("quota_5_hour", "5小时窗口"), ("quota_7_day", "7天窗口")):
        q = payload.get(key) or {}
        if not q:
            continue
        used_pct = float(q.get("usage_percentage") or 0)
        tiers.append(_tier(label, used=round(used_pct, 1), total=100, unit="percent",
                           resets_at=str(q.get("resets_at") or "")))
    return _result(tiers, plan_name=str((payload.get("plan") or {}).get("tier") or ""))


def query_opencode_go(ctx: QueryContext) -> Dict[str, Any]:
    """OpenCode Go：/zen/go/v1/usage（rolling/weekly/monthly）。"""
    if not ctx.api_key:
        raise CredentialMissing("OpenCode Go 需要 API key")
    base = _validate_http_url(ctx.base_url or "https://opencode.ai")
    data = _get_json(f"{base}/zen/go/v1/usage", {"Authorization": f"Bearer {ctx.api_key}"})
    if _denied(data):
        return _denied_result("OpenCode Go")
    usage = data.get("usage") or {}
    label_map = {"rolling": "5小时窗口", "weekly": "周额度", "monthly": "月额度"}
    tiers = []
    for key, label in label_map.items():
        w = usage.get(key) or {}
        if not w:
            continue
        if w.get("status") == "rate-limited":
            tiers.append(_tier(label, used=100, total=100, unit="percent",
                               resets_at=str(w.get("resetsAt") or "")))
        elif w.get("percent") is not None:
            tiers.append(_tier(label, used=round(float(w["percent"]), 1), total=100,
                               unit="percent", resets_at=str(w.get("resetsAt") or "")))
    return _result(tiers)


# ---------------------------------------------------------------------------
# 余额类查询器
# ---------------------------------------------------------------------------

def query_deepseek(ctx: QueryContext) -> Dict[str, Any]:
    if not ctx.api_key:
        raise CredentialMissing("DeepSeek 需要 API key")
    base = _validate_http_url(ctx.base_url or "https://api.deepseek.com")
    data = _get_json(f"{base}/user/balance", {"Authorization": f"Bearer {ctx.api_key}"})
    if _denied(data):
        return _denied_result("DeepSeek")
    infos = data.get("balance_infos") or []
    entry = next((i for i in infos if float(i.get("total_balance") or 0) > 0), None)
    if not entry and infos:
        entry = infos[0]
    if not entry:
        return _result([], balance={"value": 0, "unit": "CNY"})
    return _result([], balance={"value": float(entry.get("total_balance") or 0),
                                "unit": entry.get("currency", "CNY")})


def query_openrouter(ctx: QueryContext) -> Dict[str, Any]:
    if not ctx.api_key:
        raise CredentialMissing("OpenRouter 需要 API key")
    base = _validate_http_url(ctx.base_url or "https://openrouter.ai")
    data = _get_json(f"{base}/api/v1/credits", {"Authorization": f"Bearer {ctx.api_key}"})
    if _denied(data):
        return _denied_result("OpenRouter")
    payload = data.get("data") or {}
    total = float(payload.get("total_credits") or 0)
    used = float(payload.get("total_usage") or 0)
    return _result([], balance={"value": round(total - used, 4), "unit": "USD"})


def query_siliconflow(ctx: QueryContext) -> Dict[str, Any]:
    if not ctx.api_key:
        raise CredentialMissing("SiliconFlow 需要 API key")
    base = _validate_http_url(ctx.base_url or "https://api.siliconflow.cn")
    data = _get_json(f"{base}/v1/user/info", {"Authorization": f"Bearer {ctx.api_key}"})
    if _denied(data):
        return _denied_result("SiliconFlow")
    payload = data.get("data") or {}
    return _result([], balance={"value": float(payload.get("totalBalance") or 0),
                                "unit": "CNY" if "siliconflow.cn" in base else "USD"})


# ---------------------------------------------------------------------------
# 通用模板查询器（NewAPI / Sub2API / 通用余额）
# ---------------------------------------------------------------------------

def query_newapi(ctx: QueryContext) -> Dict[str, Any]:
    """NewAPI 通用：GET {base_url}/api/user/self + New-Api-User 头（quota÷500000=USD）。"""
    token = ctx.usage_api_key or ctx.api_key
    user_id = str(ctx.extra.get("userId") or "")
    if not token:
        raise CredentialMissing("NewAPI 需要访问令牌（accessToken）")
    base = _validate_http_url(ctx.usage_base_url or ctx.base_url)
    if not base:
        raise CredentialMissing("NewAPI 需要站点 base_url")
    headers = {"Authorization": f"Bearer {token}"}
    if user_id:
        headers["New-Api-User"] = user_id
    data = _get_json(f"{base}/api/user/self", headers)
    if _denied(data):
        return _denied_result("NewAPI")
    payload = data.get("data") or {}
    quota, used_quota = float(payload.get("quota") or 0), float(payload.get("used_quota") or 0)
    total = (quota + used_quota) / 500000.0
    used = used_quota / 500000.0
    return _result([_tier("套餐余额", used=round(used, 4), total=round(total, 4), unit="USD")],
                   plan_name=str(payload.get("group") or ""))


def query_sub2api(ctx: QueryContext) -> Dict[str, Any]:
    if not ctx.api_key:
        raise CredentialMissing("Sub2API 需要 API key")
    base = _validate_http_url(ctx.usage_base_url or ctx.base_url).removesuffix("/v1")
    data = _get_json(f"{base}/v1/usage", {"Authorization": f"Bearer {ctx.api_key}"})
    if _denied(data):
        return _denied_result("Sub2API")
    quota = data.get("quota") or {}
    limit, used = float(quota.get("limit") or 0), float(quota.get("used") or 0)
    return _result([_tier("套餐", used=used, total=limit,
                          unit=str(data.get("unit") or "credits"))],
                   plan_name=str(data.get("planName") or ""))


def query_generic_balance(ctx: QueryContext) -> Dict[str, Any]:
    if not ctx.api_key:
        raise CredentialMissing("通用余额查询需要 API key")
    base = _validate_http_url(ctx.usage_base_url or ctx.base_url)
    data = _get_json(f"{base}/user/balance", {"Authorization": f"Bearer {ctx.api_key}"})
    if _denied(data):
        return _denied_result("余额查询")
    value = None
    for key in ("balance", "total_balance", "data"):
        if isinstance(data.get(key), (int, float)):
            value = float(data[key])
            break
        if isinstance(data.get(key), dict):
            inner = data[key]
            for k2 in ("balance", "total_balance"):
                if isinstance(inner.get(k2), (int, float)):
                    value = float(inner[k2])
                    break
            if value is not None:
                break
    if value is None:
        raise UsageQueryError("响应中未找到 balance/total_balance 字段")
    return _result([], balance={"value": value, "unit": "USD"})


# ---------------------------------------------------------------------------
# 官方 OAuth 查询器（读本机 agent 凭据；凭据路径一律 real_home）
# ---------------------------------------------------------------------------

def _real_home():
    from app.config.config import REAL_HOME
    return __import__("pathlib").Path(REAL_HOME)


def _read_claude_oauth_token() -> str:
    """读本机 Claude Code OAuth access token（credentials.json；缺失/过期自刷新不在 v1 范围）。"""
    candidates = [
        _real_home() / ".claude" / ".credentials.json",
        _real_home() / ".claude" / "credentials.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        oauth = data.get("claudeAiOauth") or data.get("claude.ai_oauth") or {}
        token = oauth.get("accessToken") or data.get("accessToken")
        if token:
            return str(token)
    raise CredentialMissing("未找到本机 Claude Code OAuth 凭据（请先在本机登录 Claude Code）")


def query_claude_official(ctx: QueryContext) -> Dict[str, Any]:
    token = ctx.api_key or _read_claude_oauth_token()
    data = _get_json(
        "https://api.anthropic.com/api/oauth/usage",
        {"Authorization": f"Bearer {token}", "anthropic-beta": "oauth-2025-04-20",
         "Accept": "application/json"},
    )
    if _denied(data):
        return _denied_result("Claude 官方")
    tiers: List[Dict[str, Any]] = []
    label_map = {"five_hour": "5小时窗口", "seven_day": "7天窗口", "seven_day_opus": "7天 Opus",
                 "seven_day_fable": "7天 Fable", "seven_day_sonnet": "7天 Sonnet"}
    for key, label in label_map.items():
        window = data.get(key) or {}
        if window.get("utilization") is not None:
            tiers.append(_tier(label, used=round(float(window["utilization"]), 1), total=100,
                               unit="percent", resets_at=str(window.get("resets_at") or "")))
    # 新版 limits[]（weekly_scoped）
    for lim in data.get("limits") or []:
        if lim.get("kind") == "weekly_scoped" and lim.get("group") == "weekly":
            model_name = ((lim.get("scope") or {}).get("model") or {}).get("display_name") or ""
            utilization = float(lim.get("utilization") or 0)
            tiers.append(_tier(f"7天 {model_name}".strip(), used=round(utilization, 1),
                               total=100, unit="percent",
                               resets_at=str(lim.get("resets_at") or "")))
    extra = data.get("extra_usage") or {}
    if extra.get("is_enabled") and extra.get("monthly_limit"):
        monthly_limit = float(extra["monthly_limit"])
        used_credits = float(extra.get("used_credits") or 0)
        tiers.append(_tier("额外额度", used=used_credits, total=monthly_limit,
                           unit=str(extra.get("currency") or "credits")))
    return _result(tiers)


def _read_codex_auth() -> Dict[str, Any]:
    path = _real_home() / ".codex" / "auth.json"
    if not path.exists():
        raise CredentialMissing("未找到本机 Codex 登录凭据（~/.codex/auth.json），请先在 Codex CLI 登录")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        raise CredentialMissing(f"Codex auth.json 解析失败: {e}") from e
    if (data.get("auth_mode") or "chatgpt") != "chatgpt" or not (data.get("tokens") or {}).get("access_token"):
        raise CredentialMissing("Codex 未以 ChatGPT 模式登录（auth_mode != chatgpt）")
    return data


def query_codex_official(ctx: QueryContext) -> Dict[str, Any]:
    auth = _read_codex_auth()
    tokens = auth.get("tokens") or {}
    token = ctx.api_key or str(tokens.get("access_token") or "")
    account_id = str(tokens.get("account_id") or "")
    headers = {"Authorization": f"Bearer {token}", "User-Agent": "codex-cli",
               "Accept": "application/json"}
    if account_id:
        headers["ChatGPT-Account-Id"] = account_id
    usage = _get_json("https://chatgpt.com/backend-api/wham/usage", headers)
    if _denied(usage):
        return _denied_result("Codex/ChatGPT")
    rate_limit = usage.get("rate_limit") or {}
    label_map = {"primary_window": "5小时窗口", "secondary_window": "周窗口"}
    tiers = []
    for key, label in label_map.items():
        window = rate_limit.get(key) or {}
        used_pct = window.get("used_percent")
        if used_pct is None:
            continue
        tiers.append(_tier(label, used=round(float(used_pct), 1), total=100, unit="percent",
                           resets_at=str(window.get("reset_at") or "")))
    credits = (usage.get("credits") or {}).get("balance")
    if credits is not None:
        tiers.append(_tier("Credits 余额", used=0, total=float(credits), unit="credits"))
    plan_type = str(usage.get("plan_type") or rate_limit.get("plan_type") or "")
    return _result(tiers, plan_name=plan_type)


def query_gemini_official(ctx: QueryContext) -> Dict[str, Any]:
    path = _real_home() / ".gemini" / "oauth_creds.json"
    if not path.exists():
        raise CredentialMissing("未找到本机 Gemini CLI OAuth 凭据（~/.gemini/oauth_creds.json）")
    try:
        creds = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as e:
        raise CredentialMissing(f"Gemini oauth_creds.json 解析失败: {e}") from e
    token = ctx.api_key or str(creds.get("access_token") or "")
    if not token:
        raise CredentialMissing("Gemini OAuth 凭据中无 access_token（可手动填入查询凭据）")
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        resp = requests.post(
            "https://cloudcode-pa.googleapis.com/v1internal:loadCodeAssist",
            json={"metadata": {"ideType": "GEMINI_CLI", "pluginType": "GEMINI"}},
            headers={**headers, "User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        raise UsageQueryError(f"网络请求失败: {e}") from e
    if resp.status_code in (401, 403):
        return _denied_result("Gemini")
    assist = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    project = (assist.get("cloudaicompanionProject")
               or ((assist.get("paidTier") or {}).get("project") or {}))
    try:
        resp2 = requests.post(
            "https://cloudcode-pa.googleapis.com/v1internal:retrieveUserQuota",
            json={"project": project},
            headers={**headers, "User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        raise UsageQueryError(f"网络请求失败: {e}") from e
    if resp2.status_code in (401, 403):
        return _denied_result("Gemini")
    quota = resp2.json() if resp2.headers.get("content-type", "").startswith("application/json") else {}
    buckets = quota.get("buckets") or []
    label_map = {"gemini-3-pro": "Pro", "gemini-2.5-pro": "Pro", "gemini-2.5-flash": "Flash",
                 "gemini-2.5-flash-lite": "Flash Lite"}
    lowest: Dict[str, Dict[str, Any]] = {}
    for b in buckets:
        model_id = str(b.get("modelId") or "")
        label = next((v for k, v in label_map.items() if model_id.startswith(k)), None)
        if label is None:
            continue
        remaining = float(b.get("remainingFraction") or 0)
        if label not in lowest or remaining < lowest[label]["remaining"]:
            lowest[label] = {"remaining": remaining, "reset": str(b.get("resetTime") or "")}
    tiers = []
    for label, info in lowest.items():
        used = round((1 - info["remaining"]) * 100, 1)
        tiers.append(_tier(label, used=used, total=100, unit="percent",
                           resets_at=info["reset"]))
    return _result(tiers)


# ---------------------------------------------------------------------------
# manual（无网络请求；额度用户手动维护 ✅）
# ---------------------------------------------------------------------------

def query_manual(ctx: QueryContext, total: float, used: float, unit: str) -> Dict[str, Any]:
    return _result([_tier("套餐额度", used=used, total=total, unit=unit or "credits")])


QUERY_DISPATCH = {
    "opendesign": query_opendesign,
    "kimi": query_kimi,
    "zhipu": query_zhipu,
    "minimax": query_minimax,
    "zenmux": query_zenmux,
    "opencode_go": query_opencode_go,
    "deepseek": query_deepseek,
    "openrouter": query_openrouter,
    "siliconflow": query_siliconflow,
    "newapi": query_newapi,
    "sub2api": query_sub2api,
    "generic_balance": query_generic_balance,
    "claude_official": query_claude_official,
    "codex_official": query_codex_official,
    "gemini_official": query_gemini_official,
}


def dispatch_query(ctx: QueryContext, total: float = 0, used: float = 0,
                   unit: str = "credits") -> Dict[str, Any]:
    """统一分派入口。manual 走本地计算，其余按 kind 查询器。"""
    if ctx.kind == "manual":
        return query_manual(ctx, total=total, used=used, unit=unit)
    handler = QUERY_DISPATCH.get(ctx.kind)
    if handler is None:
        return {"success": False, "error": f"未知的用量查询类型: {ctx.kind}",
                "queried_at": _now_iso()}
    return handler(ctx)

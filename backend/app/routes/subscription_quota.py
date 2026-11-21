"""订阅套餐额度 API（v2：支持用户自助添加任意供应商）

只返回**已配置**的账号与本机已登录的订阅。
响应中**绝不包含**明文 API Key（只返回掩码）。
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, Field

from app.routes.auth import get_current_user_id
from app.services.subscription_quota.accounts import (
    create_account,
    delete_account,
    get_account,
    list_accounts,
    update_account,
)
from app.services.subscription_quota.registry import (
    MANUAL_PROVIDER_IDS,
    PROVIDER_SPECS,
    SUBSCRIPTION_IDS,
    get_spec,
)
from app.services.subscription_quota.service import (
    TOOL_DISPLAY_NAMES,
    clear_cache,
    describe_credentials,
    query_for_accounts,
    query_subscriptions,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/subscription-quota", tags=["subscription-quota"])


# ---------------------------------------------------------------- 请求模型


class AccountCreateRequest(BaseModel):
    provider_id: str = Field(..., description="供应商 id，见 /providers")
    label: str = Field(default="", description="自定义显示名，例如「工作号」")
    api_key: Optional[str] = Field(default=None, description="API Key（服务端加密存储）")
    extra: dict = Field(default_factory=dict, description="额外字段：region / base_url / control_key 等")
    # 合并 agent-hub 后新增（都有默认值，老调用方不受影响）
    category: Optional[str] = Field(default=None, description="official/aggregator/third_party/custom/manual")
    app: Optional[str] = Field(default=None, description="作用对象 agent")
    notes: Optional[str] = None
    website_url: Optional[str] = None
    manual_total: Optional[float] = Field(default=None, description="手动额度总额")
    manual_used: Optional[float] = Field(default=None, description="手动额度已用")
    quota_unit: Optional[str] = None
    window_type: Optional[str] = None
    window_reset_at: Optional[str] = None


class AccountUpdateRequest(BaseModel):
    label: Optional[str] = None
    api_key: Optional[str] = None
    extra: Optional[dict] = None
    enabled: Optional[bool] = None
    category: Optional[str] = None
    app: Optional[str] = None
    notes: Optional[str] = None
    website_url: Optional[str] = None
    manual_total: Optional[float] = None
    manual_used: Optional[float] = None
    quota_unit: Optional[str] = None
    window_type: Optional[str] = None
    window_reset_at: Optional[str] = None


class QuotaAdjustRequest(BaseModel):
    """手动额度调整（对齐 agent-hub 的「额度支持手动增加」）"""

    total: Optional[float] = Field(default=None, description="新的总额度")
    used: Optional[float] = Field(default=None, description="新的已用额度")
    add: Optional[float] = Field(default=None, description="在现有总额度上增加多少")
    unit: Optional[str] = None
    window_type: Optional[str] = None
    window_reset_at: Optional[str] = None


class QueryRequest(BaseModel):
    account_ids: Optional[List[str]] = Field(
        default=None, description="只查这些账号；为空查全部已启用账号"
    )
    include_subscriptions: bool = Field(default=True, description="是否同时查询本机订阅")
    force_refresh: bool = Field(default=False)


class TestRequest(BaseModel):
    """测试连接时可直接传临时凭据，不必先保存"""

    api_key: Optional[str] = None
    extra: dict = Field(default_factory=dict)


class ImportRequest(BaseModel):
    """从 cc-switch 导入供应商配置"""

    dry_run: bool = Field(default=False, description="只预览不写库")
    #: 默认 False：已存在的账号整条跳过，绝不覆盖用户已有数据（Key / 显示名 / 手工额度）
    overwrite: bool = Field(
        default=False,
        description="已存在时是否更新凭据字段（默认不覆盖，保护用户已有数据）",
    )


#: Agent 切换指针表（从 agent-hub 的 agent_hub_switches 合并；带 user_id 隔离）
#: 与账号表同库同位置 —— 切换指针同样是「本机状态」，不同设备各自独立。
_SWITCH_TABLE = "subscription_quota_switches"
_switch_ready_by_location: set[str] = set()


def _ensure_switch_table() -> None:
    from sqlalchemy import text

    from app.services.subscription_quota.accounts import _get_engine, _storage_location

    location = _storage_location()
    if location in _switch_ready_by_location:
        return
    with _get_engine().begin() as conn:
        conn.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {_SWITCH_TABLE} (
                    user_id     VARCHAR(64) NOT NULL,
                    agent       VARCHAR(32) NOT NULL,
                    provider_id VARCHAR(64) NOT NULL DEFAULT '',
                    switched_at VARCHAR(40) NOT NULL DEFAULT '',
                    PRIMARY KEY (user_id, agent)
                )
                """
            )
        )
    _switch_ready_by_location.add(location)


def _load_switches(user_id: str) -> dict[str, dict]:
    """读取该用户各 agent 的当前切换指针"""
    from sqlalchemy import text

    from app.services.subscription_quota.accounts import _get_engine

    _ensure_switch_table()
    with _get_engine().connect() as conn:
        rows = conn.execute(
            text(
                f"SELECT agent, provider_id, switched_at FROM {_SWITCH_TABLE} WHERE user_id = :uid"
            ),
            {"uid": user_id},
        ).fetchall()
    return {
        row[0]: {"provider_id": row[1] or "", "switched_at": row[2] or ""} for row in rows
    }


def _save_switch(user_id: str, agent: str, provider_id: str) -> None:
    """保存切换指针（provider_id 为空表示已恢复默认）"""
    import time

    from sqlalchemy import text

    from app.services.subscription_quota.accounts import _get_engine

    _ensure_switch_table()
    with _get_engine().begin() as conn:
        conn.execute(
            text(
                f"""
                INSERT INTO {_SWITCH_TABLE} (user_id, agent, provider_id, switched_at)
                VALUES (:uid, :agent, :pid, :at)
                ON CONFLICT (user_id, agent) DO UPDATE
                SET provider_id = EXCLUDED.provider_id, switched_at = EXCLUDED.switched_at
                """
            ),
            {
                "uid": user_id,
                "agent": agent,
                "pid": provider_id or "",
                "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            },
        )


def _require_user(authorization: Optional[str], *, scope: Optional[str] = None) -> str:
    """JWT 或设备 Token（``pat_`` 前缀 + 作用域）鉴权

    * JWT：沿用原有行为（账号全权限）
    * 设备 Token：必须存在且未过期/未撤销；``scope`` 非空时还要求包含该作用域
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    token = authorization[7:] if authorization.startswith("Bearer ") else authorization
    if token.startswith("pat_"):
        from app.services.user_token_service import UserTokenService

        detail = UserTokenService.validate_token_detail(token)
        if not detail:
            raise HTTPException(status_code=401, detail="设备 Token 无效、已过期或已撤销")
        if scope and scope not in detail["scopes"]:
            raise HTTPException(status_code=403, detail=f"设备 Token 缺少作用域 {scope}")
        return detail["userId"]
    try:
        return get_current_user_id(authorization=authorization)
    except HTTPException:
        raise HTTPException(status_code=401, detail="认证失败")


# ---------------------------------------------------------------- 供应商目录


@router.get("/providers")
def list_providers(authorization: Optional[str] = Header(None)):
    """供应商目录：每个供应商需要哪些字段、是否已配置。"""
    user_id = _require_user(authorization)
    accounts = list_accounts(user_id)
    configured: dict[str, int] = {}
    for account in accounts:
        configured[account.provider_id] = configured.get(account.provider_id, 0) + 1

    return {
        "providers": [
            {
                **spec.to_public_dict(),
                "configuredCount": configured.get(spec.id, 0),
                "addable": spec.id in MANUAL_PROVIDER_IDS,
            }
            for spec in PROVIDER_SPECS
        ],
        "displayNames": TOOL_DISPLAY_NAMES,
        "subscriptionIds": list(SUBSCRIPTION_IDS),
        "manualProviderIds": list(MANUAL_PROVIDER_IDS),
    }


@router.post("/import/cc-switch")
async def import_from_ccswitch(
    req: ImportRequest = ImportRequest(),
    authorization: Optional[str] = Header(None),
):
    """从本机 cc-switch 导入供应商配置（含 OpenDesign 的控制面 Key）

    cc-switch 把 **控制面 Key**（OpenDesign 的 `vela_ctrl_…`）存在
    `providers.meta.usage_script.apiKey`，而 `settings_config` 里只有推理 Key。
    推理 Key 查不了账单，所以导入时必须优先取控制面 Key。

    **安全约定：已存在的数据绝不覆盖**

    用户可能已经在页面里手工改过 Key、改过显示名、或手工维护过额度；
    再次点「从 cc-switch 导入」时，这些改动绝不能被 cc-switch 里的旧值冲掉。
    因此：

    * 默认 ``overwrite=False``：已存在的账号**整条跳过**（计入 skipped），
      不改 Key、不改 label、不改 extra，也不动手工额度字段与 keep-last-good 缓存。
    * 只有显式传 ``overwrite=true`` 才更新，且**只更新凭据相关字段**
      （api_key / extra），用户手工维护的 label、manual_*、notes、website_url、
      enabled 仍然保留 —— 这些是用户在页面里改的，cc-switch 并不知道。
    """
    user_id = _require_user(authorization)

    import sys
    from pathlib import Path

    backend_dir = Path(__file__).resolve().parent.parent.parent
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from scripts.import_ccswitch_providers import load_candidates
    from app.services.subscription_quota.usage_import import ccswitch_db_path

    # 统一走 ccswitch_db_path()：它基于 REAL_HOME 解析，
    # 避免 config.py 覆盖 HOME 后把 ~/.cc-switch 解析到缓存目录而误报未找到。
    db_path = ccswitch_db_path()
    if not db_path.exists():
        raise HTTPException(status_code=404, detail=f"未找到 cc-switch 数据库：{db_path}")

    candidates = load_candidates(db_path)
    if not candidates:
        return {"imported": 0, "items": [], "message": "cc-switch 里没有可导入的供应商凭据"}

    # 按 provider 分组：同一供应商在 cc-switch 里常有多条配置（给不同 CLI 各配一份，
    # 或新旧 Key 并存），Key 不一定都有效。这里不打桩取「第一条」，而是**实际探测**
    # 每个候选能否查通额度，只导入可用的那条 —— 否则会把失效 Key 导进来，
    # 卡片永远显示「认证失败 / 不存在 coding plan」。
    grouped: dict[str, list[dict]] = {}
    for item in candidates:
        grouped.setdefault(item["provider_id"], []).append(item)

    from app.services.subscription_quota.credential_probe import pick_working_candidates

    picked: list[dict] = []
    probe_skipped: list[dict] = []
    for pid, group in grouped.items():
        # 同一 provider 可能有多个**不同账号**（如智谱团队版 HZM / LYD），
        # 每个账号是一份独立订阅，都要导入，不能只留一个。
        working = await pick_working_candidates(group)
        if not working:
            probe_skipped.append(
                {
                    "providerId": pid,
                    "reason": f"{len(group)} 个候选凭据均不可用（已验证额度查询失败）",
                }
            )
            continue
        picked.extend(working)

    if not picked and not probe_skipped:
        return {"imported": 0, "items": [], "message": "cc-switch 里没有可导入的供应商凭据"}

    # 按 (provider_id, api_key) 索引已有账号 —— 同一 provider 可有多账号，
    # 用 Key 判重才能区分「同一个账号重复导入」与「同供应商的另一个账号」。
    existing_by_key: dict[tuple[str, str], list] = {}
    for account in list_accounts(user_id):
        existing_by_key.setdefault((account.provider_id, account.api_key or ""), []).append(account)

    items: list[dict] = []
    created = updated = skipped = 0

    for item in picked:
        pid = item["provider_id"]
        extra: dict = {"region": item["region"], "api_key": item["api_key"]}
        # 团队版额度查询必须带组织 / 项目 ID，否则接口无法定位团队套餐
        if item.get("organization_id"):
            extra["organization_id"] = item["organization_id"]
        if item.get("project_id"):
            extra["project_id"] = item["project_id"]
        if pid == "opendesign":
            # 账单接口只认控制面 Key（vela_ctrl_…）。cc-switch 的
            # load_candidates 已优先取 usage_script.apiKey（控制面），
            # 但这里仍做一次形态校验：不是控制面形态就别写进 control_key，
            # 免得把推理 Key 存成"看起来能用"的假凭据。
            from app.services.subscription_quota.opendesign_key import (
                is_control_key,
                pick_control_key,
            )

            extra["base_url"] = "https://amr-api.open-design.ai"
            if is_control_key(item["api_key"]):
                extra["control_key"] = item["api_key"]
            else:
                discovered = pick_control_key()
                if discovered:
                    extra["control_key"] = discovered
        elif item["base_url"]:
            extra["base_url"] = item["base_url"]

        label = f"{item['source_name']}（cc-switch 导入）"
        # 用 Key 判重：同 provider 的同一个 Key = 同一账号（跳过）；
        # 不同 Key = 该供应商的另一个账号（新建）。
        existing = existing_by_key.get((pid, item["api_key"])) or []

        # 决定本条的动作。默认「已存在就跳过」，绝不覆盖用户数据。
        if existing and not req.overwrite:
            action = "skip"
        elif existing:
            action = "update"
        else:
            action = "create"

        items.append(
            {
                "providerId": pid,
                "sourceApp": item["source_app"],
                "sourceName": item["source_name"],
                "fromControlKey": item["from_control_key"],
                "maskedKey": (
                    f"{item['api_key'][:6]}…{item['api_key'][-4:]}"
                    if len(item["api_key"]) > 12
                    else "***"
                ),
                "action": action,
            }
        )

        if req.dry_run:
            continue

        if action == "skip":
            skipped += 1
            continue

        if action == "update":
            # 仅覆盖凭据字段；用户在页面里维护的 label / manual_* / notes /
            # website_url / enabled 一律保留（cc-switch 不知道这些）。
            target = existing[0]
            update_account(user_id, target.id, api_key=item["api_key"], extra=extra)
            updated += 1
        else:
            create_account(user_id, pid, label=label, api_key=item["api_key"], extra=extra)
            created += 1

    if not req.dry_run:
        clear_cache()
        logger.info(
            "用户 %s 从 cc-switch 导入：新建 %d / 更新 %d / 跳过已存在 %d",
            user_id,
            created,
            updated,
            skipped,
        )

    return {
        "imported": 0 if req.dry_run else created + updated,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "dryRun": req.dry_run,
        "items": items,
        # 探测阶段就判定为不可用的供应商（所有候选 Key 都查不通额度），
        # 不写入库，但要让用户知道为什么没导入，而不是静默消失。
        "probeSkipped": probe_skipped,
    }


# ---------------------------------------------------------------- 从 magpie 同步


class MagpieSyncRequest(BaseModel):
    """从 magpie 同步已配置的供应商/账号"""

    dry_run: bool = Field(default=False, description="只预览不写库")
    overwrite: bool = Field(
        default=False,
        description="已存在时是否更新凭据字段（默认不覆盖，保护用户已有数据）",
    )
    include_accounts: bool = Field(
        default=True,
        description="是否同时同步订阅账号（需要 magpie CLI，较慢）",
    )


@router.get("/magpie/status")
def magpie_status(authorization: Optional[str] = Header(None)):
    """magpie 是否可用于同步（只读探测，不写任何文件）"""
    _require_user(authorization)
    from app.services.subscription_quota.magpie_sync import (
        find_magpie_binary,
        magpie_available,
        providers_json_path,
    )

    path = providers_json_path()
    return {
        "available": magpie_available(),
        "providersPath": str(path),
        "providersFileExists": path.exists(),
        "binary": find_magpie_binary() or "",
    }


@router.post("/import/magpie")
async def import_from_magpie(
    req: MagpieSyncRequest = MagpieSyncRequest(),
    authorization: Optional[str] = Header(None),
):
    """从本机 magpie 同步已配置的供应商（+ 可选订阅账号）

    ## 同步什么

    * `~/.config/magpie/providers.json` 里的**每一个**供应商：
      按 preset/id 映射到本工具的 provider_id；映射不到但有 base_url 的
      归到「通用余额接口」；连 base_url 都没有的跳过并说明原因。
    * `magpie accounts --json` 的订阅账号：按 agent 归到对应官方订阅
      （claude / codex / gemini），plan 写进 label，窗口写进 last_good。

    ## 安全约定

    与 cc-switch 导入一致：**已存在的账号默认整条跳过**，绝不覆盖用户
    在页面里改过的 label / 手工额度 / 启停状态。只有显式 ``overwrite=true``
    才更新，且只更新凭据字段。
    """
    user_id = _require_user(authorization)

    from app.services.subscription_quota.magpie_sync import (
        load_accounts,
        load_providers,
    )
    from app.services.subscription_quota.registry import get_spec

    providers = load_providers()
    accounts = load_accounts() if req.include_accounts else []

    if not providers and not accounts:
        return {
            "imported": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "dryRun": req.dry_run,
            "items": [],
            "skippedItems": [],
            "message": "magpie 里没有可同步的供应商或账号（未安装 / 未配置）",
        }

    existing_by_provider: dict[str, list] = {}
    for account in list_accounts(user_id):
        existing_by_provider.setdefault(account.provider_id, []).append(account)

    items: list[dict] = []
    skipped_items: list[dict] = []
    created = updated = skipped = 0

    # ---- 1) 供应商 ----
    for prov in providers:
        pid = prov.provider_id
        if pid is None:
            skipped_items.append(
                {
                    "source": "magpie-provider",
                    "name": prov.name,
                    "preset": prov.preset or prov.id,
                    "reason": "本工具没有对应的供应商类型（无可识别 preset）",
                }
            )
            continue

        spec = get_spec(pid)
        if spec is None:
            skipped_items.append(
                {
                    "source": "magpie-provider",
                    "name": prov.name,
                    "preset": prov.preset or prov.id,
                    "reason": f"映射到的供应商 {pid} 未在注册表中",
                }
            )
            continue

        if not prov.key:
            skipped_items.append(
                {
                    "source": "magpie-provider",
                    "name": prov.name,
                    "preset": prov.preset or prov.id,
                    "reason": "magpie 里这条供应商没有 Key（可能是账号登录型）",
                }
            )
            continue

        extra: dict = {"api_key": prov.key, "source": "magpie"}
        if prov.base_url:
            extra["base_url"] = prov.base_url
        if pid == "opendesign":
            # magpie 的 providers.json 里存的是**推理 Key**（sk-amr-ew__…），
            # 账单接口要的是控制面 Key（vela_ctrl_…）。两者不能混：
            # 只有 magpie 那边确实是控制面 Key 时才写进 control_key，
            # 否则去 cc-switch 库里找真正的控制面 Key（只读发现）。
            from app.services.subscription_quota.opendesign_key import (
                is_control_key,
                pick_control_key,
            )

            if is_control_key(prov.key):
                extra["control_key"] = prov.key
            else:
                discovered = pick_control_key()
                if discovered:
                    extra["control_key"] = discovered

        label = f"{prov.name}（magpie 同步）"
        existing = existing_by_provider.get(pid) or []

        if existing and not req.overwrite:
            action = "skip"
        elif existing:
            action = "update"
        else:
            action = "create"

        items.append(
            {
                "source": "magpie-provider",
                "providerId": pid,
                "sourceName": prov.name,
                "preset": prov.preset or prov.id,
                "maskedKey": prov.masked_key(),
                "action": action,
            }
        )

        if req.dry_run or action == "skip":
            if action == "skip":
                skipped += 1
            continue

        if action == "update":
            update_account(user_id, existing[0].id, api_key=prov.key, extra=extra)
            updated += 1
        else:
            create_account(
                user_id,
                pid,
                label=label,
                api_key=prov.key,
                extra=extra,
                category="aggregator" if pid in ("newapi", "sub2api", "generic_balance") else "official",
                website_url=prov.website,
            )
            created += 1

    # ---- 2) 订阅账号（magpie 的 accounts --json）----
    # agent → 本工具 provider_id（只有官方订阅型）
    agent_to_provider = {
        "claude": "claude",
        "codex": "codex",
        "gemini": "gemini",
    }
    for acc in accounts:
        pid = agent_to_provider.get(acc.agent.lower())
        if pid is None:
            skipped_items.append(
                {
                    "source": "magpie-account",
                    "name": acc.alias or acc.user,
                    "preset": acc.agent,
                    "reason": f"agent {acc.agent} 不是本工具支持的官方订阅类型",
                }
            )
            continue

        label_parts = [acc.alias or acc.user or acc.agent]
        if acc.plan:
            label_parts.append(acc.plan)
        label = " · ".join(part for part in label_parts if part)

        existing = existing_by_provider.get(pid) or []
        if existing and not req.overwrite:
            skipped += 1
            items.append(
                {
                    "source": "magpie-account",
                    "providerId": pid,
                    "sourceName": label,
                    "preset": acc.agent,
                    "maskedKey": "",
                    "action": "skip",
                }
            )
            continue

        # magpie 的订阅账号靠本机登录凭据，不需要我们的 API Key；
        # 把窗口信息存进 extra，供页面展示「最近一次已知额度」。
        extra = {
            "source": "magpie",
            "agent": acc.agent,
            "user": acc.user,
            "plan": acc.plan,
            "windows": acc.windows,
            "balance": acc.balance,
            "lapsed": acc.lapsed,
        }

        items.append(
            {
                "source": "magpie-account",
                "providerId": pid,
                "sourceName": label,
                "preset": acc.agent,
                "maskedKey": "",
                "action": "update" if existing else "create",
            }
        )

        if req.dry_run:
            continue

        if existing:
            update_account(user_id, existing[0].id, extra=extra)
            updated += 1
        else:
            create_account(user_id, pid, label=label, extra=extra, category="official")
            created += 1

    if not req.dry_run:
        clear_cache()
        logger.info(
            "用户 %s 从 magpie 同步：新建 %d / 更新 %d / 跳过已存在 %d / 跳过不可映射 %d",
            user_id,
            created,
            updated,
            skipped,
            len(skipped_items),
        )

    return {
        "imported": 0 if req.dry_run else created + updated,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "dryRun": req.dry_run,
        "items": items,
        "skippedItems": skipped_items,
    }


# ---------------------------------------------------------------- Agent 切换（合并 agent-hub）


class SwitchPreviewRequest(BaseModel):
    model: str = Field(default="", description="可选：同时写入的模型名")


@router.get("/agents")
def list_agents(authorization: Optional[str] = Header(None)):
    """检测本机各 agent 配置是否存在（只读，不写任何文件）"""
    user_id = _require_user(authorization)
    from app.services.subscription_quota.agent_switch import WRITER_AGENTS, list_agent_status

    accounts = {a.id: a for a in list_accounts(user_id)}
    switches = _load_switches(user_id)

    agents = []
    for status in list_agent_status():
        data = status.to_dict()
        switch = switches.get(status.agent) or {}
        provider = accounts.get(switch.get("provider_id", ""))
        data["currentProviderId"] = switch.get("provider_id", "")
        data["currentProviderName"] = provider.label if provider else ""
        data["switchedAt"] = switch.get("switched_at", "")
        agents.append(data)

    return {"agents": agents, "supported": list(WRITER_AGENTS)}


@router.get("/agents/{agent}/config-preview")
def preview_agent_switch(
    agent: str,
    account_id: str,
    model: str = "",
    authorization: Optional[str] = Header(None),
):
    """预览切换会写哪些字段（dry-run，不落盘）"""
    user_id = _require_user(authorization)
    from app.services.subscription_quota.agent_switch import AgentWriterError, preview_switch

    account = get_account(user_id, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="账号不存在")

    spec = get_spec(account.provider_id)
    base_url = str(account.extra.get("base_url") or "")
    try:
        return preview_switch(
            agent,
            name=account.label or (spec.name if spec else account.provider_id),
            base_url=base_url,
            api_key=account.api_key or "",
            model=model,
        )
    except AgentWriterError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/agents/{agent}/switch")
def switch_agent(
    agent: str,
    account_id: str,
    req: SwitchPreviewRequest = SwitchPreviewRequest(),
    authorization: Optional[str] = Header(None),
):
    """把该账号写入本机 CLI 配置（带首写备份，可一键恢复）"""
    user_id = _require_user(authorization)
    from app.services.subscription_quota.agent_switch import AgentWriterError, apply_switch

    account = get_account(user_id, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="账号不存在")

    spec = get_spec(account.provider_id)
    name = account.label or (spec.name if spec else account.provider_id)
    base_url = str(account.extra.get("base_url") or "")
    try:
        result = apply_switch(
            agent,
            name=name,
            base_url=base_url,
            api_key=account.api_key or "",
            model=req.model,
            kind=spec.kind if spec else None,
        )
    except AgentWriterError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _save_switch(user_id, agent, account.id)
    logger.info("用户 %s 把 %s 切换到 %s（写入 %s 个文件）", user_id, agent, name, len(result.get("written") or []))
    return {"ok": True, "agent": agent, "providerName": name, "written": result.get("written") or []}


@router.post("/agents/{agent}/restore")
def restore_agent(agent: str, authorization: Optional[str] = Header(None)):
    """恢复该 agent 的首写备份"""
    user_id = _require_user(authorization)
    from app.services.subscription_quota.agent_switch import AgentWriterError, restore

    try:
        restored = restore(agent)
    except AgentWriterError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    _save_switch(user_id, agent, "")
    logger.info("用户 %s 恢复 %s 的备份，共 %d 个文件", user_id, agent, len(restored))
    return {"ok": True, "restored": restored}


# 注：「用量成本」接口已下线。Token 用量统计有专门的「Token 消耗统计」工具，
# 本工具只负责订阅套餐额度与 Agent 配置切换。
# usage_import 模块仍保留：它的 ccswitch_db_path() 被 cc-switch 导入复用。


@router.get("/subscriptions")
def list_subscriptions(authorization: Optional[str] = Header(None)):
    """本机订阅类凭据状态（Claude / Codex / Gemini）+ 可自动识别的本地凭据"""
    _require_user(authorization)
    from app.services.subscription_quota.local_credentials import local_credential_notes

    return {
        "subscriptions": describe_credentials(),
        "localCredentials": [
            {
                "providerId": note.provider_id,
                "name": note.name,
                "status": note.status,
                "message": note.message,
            }
            for note in local_credential_notes()
        ],
    }


# ---------------------------------------------------------------- 账号 CRUD


@router.get("/accounts")
def get_accounts(authorization: Optional[str] = Header(None)):
    """我的供应商账号（只返回掩码 Key）"""
    user_id = _require_user(authorization)
    return {"accounts": [account.to_public_dict() for account in list_accounts(user_id)]}


@router.post("/accounts")
def add_account(
    req: AccountCreateRequest,
    authorization: Optional[str] = Header(None),
):
    """添加一个供应商账号（一个 API Key 即可）"""
    user_id = _require_user(authorization)
    spec = get_spec(req.provider_id)
    if spec is None:
        raise HTTPException(status_code=400, detail=f"未知供应商: {req.provider_id}")
    if spec.kind == "subscription":
        raise HTTPException(
            status_code=400,
            detail=f"{spec.name} 使用本机 CLI 登录凭据，无需手动添加",
        )

    extra = dict(req.extra or {})
    # api_key 也可以放在 extra 里（部分供应商用 control_key 等命名）
    if req.api_key:
        extra.setdefault("api_key", req.api_key)

    account = create_account(
        user_id,
        req.provider_id,
        label=req.label or spec.name,
        api_key=req.api_key,
        extra=extra,
        category=req.category or "official",
        app=req.app or "",
        notes=req.notes or "",
        website_url=req.website_url or "",
        manual_total=req.manual_total or 0.0,
        manual_used=req.manual_used or 0.0,
        quota_unit=req.quota_unit or "credits",
        window_type=req.window_type or "none",
        window_reset_at=req.window_reset_at or "",
    )
    clear_cache()
    logger.info("用户 %s 添加订阅额度账号 provider=%s", user_id, req.provider_id)
    return {"account": account.to_public_dict()}


@router.put("/accounts/{account_id}")
def edit_account(
    account_id: str,
    req: AccountUpdateRequest,
    authorization: Optional[str] = Header(None),
):
    user_id = _require_user(authorization)
    existing = get_account(user_id, account_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="账号不存在")

    extra = req.extra
    if req.api_key:
        extra = dict(extra if extra is not None else existing.extra)
        # 必须同步覆盖 extra.api_key：查询实现（_bearer / query_zhipu 等）读的是
        # `extra.get("api_key") or account.api_key`，extra 里的历史旧值优先级更高。
        # 只改 api_key 字段而不清 extra 里的副本，会出现「页面显示新 Key、查询仍用旧 Key」
        # 的诡异现象（表现为永远 401 / 不存在 coding plan）。
        extra["api_key"] = req.api_key

    updated = update_account(
        user_id,
        account_id,
        label=req.label,
        api_key=req.api_key,
        extra=extra,
        enabled=req.enabled,
        category=req.category,
        app=req.app,
        notes=req.notes,
        website_url=req.website_url,
        manual_total=req.manual_total,
        manual_used=req.manual_used,
        quota_unit=req.quota_unit,
        window_type=req.window_type,
        window_reset_at=req.window_reset_at,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    clear_cache()
    return {"account": updated.to_public_dict()}


@router.delete("/accounts/{account_id}")
def remove_account(account_id: str, authorization: Optional[str] = Header(None)):
    user_id = _require_user(authorization)
    if not delete_account(user_id, account_id):
        raise HTTPException(status_code=404, detail="账号不存在")
    clear_cache()
    return {"success": True}


@router.put("/accounts/{account_id}/quota")
def adjust_quota(
    account_id: str,
    req: QuotaAdjustRequest,
    authorization: Optional[str] = Header(None),
):
    """手动额度调整（从 agent-hub 合并：额度支持手动增加）

    * ``total`` 直接设为新总额
    * ``add`` 在现有总额上增加（最常用：套餐续期加额度）
    * ``used`` 直接设为新已用
    """
    user_id = _require_user(authorization)
    existing = get_account(user_id, account_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="账号不存在")

    total = req.total
    if req.add is not None:
        total = float(existing.manual_total or 0) + float(req.add)

    updated = update_account(
        user_id,
        account_id,
        manual_total=total,
        manual_used=req.used,
        quota_unit=req.unit,
        window_type=req.window_type,
        window_reset_at=req.window_reset_at,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    clear_cache()
    logger.info(
        "用户 %s 调整手动额度 id=%s total=%s add=%s used=%s",
        user_id,
        account_id,
        total,
        req.add,
        req.used,
    )
    return {"account": updated.to_public_dict()}


@router.post("/accounts/{account_id}/test")
def test_account(
    account_id: str,
    req: TestRequest = TestRequest(),
    authorization: Optional[str] = Header(None),
):
    """测试单个账号是否可查询（可传临时凭据，不落库）"""
    import asyncio

    user_id = _require_user(authorization)
    account = get_account(user_id, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="账号不存在")

    if req.api_key:
        account.api_key = req.api_key
    if req.extra:
        merged = dict(account.extra)
        merged.update(req.extra)
        account.extra = merged

    from app.services.subscription_quota.service import _decorate, _query_account

    # FastAPI 的同步端点里用独立事件循环执行异步查询
    quota = asyncio.run(_query_account(account))
    return {"quota": _decorate(quota, account)}


# ---------------------------------------------------------------- 额度查询


@router.post("/query")
async def query_quotas_endpoint(
    req: Optional[QueryRequest] = None,
    authorization: Optional[str] = Header(None),
):
    """查询已配置账号的额度（只返回已配置项）"""
    req = req or QueryRequest()
    user_id = _require_user(authorization)

    if req.force_refresh:
        clear_cache()

    accounts_quota = await query_for_accounts(
        user_id, req.account_ids, force_refresh=req.force_refresh
    )

    subscriptions: list[dict] = []
    if req.include_subscriptions:
        subscriptions = await query_subscriptions(force_refresh=req.force_refresh)

    # magpie 风格的按供应商聚合视图（多账号 failover 状态 + 推荐账号）
    from app.services.subscription_quota.failover import aggregate_by_provider

    aggregates = aggregate_by_provider(accounts_quota)

    # 「已配置」只统计用户自己添加的账号或本机已登录的订阅（不含虚拟本地账号）
    user_account_count = len([q for q in accounts_quota if not q.get("isLocal")])
    has_subscription = any(s.get("success") or s.get("credentialStatus") != "not_found"
                           for s in subscriptions)
    configured = user_account_count > 0 or has_subscription

    ok = sum(1 for q in accounts_quota if q.get("success")) + sum(
        1 for q in subscriptions if q.get("success")
    )
    logger.info(
        "订阅额度查询: user=%s 账号 %d 个（含本地 %d）/ 订阅 %d 个（成功 %d）",
        user_id,
        len(accounts_quota),
        len(accounts_quota) - user_account_count,
        len(subscriptions),
        ok,
    )

    return {
        "accounts": accounts_quota,
        "subscriptions": subscriptions,
        "aggregates": aggregates,
        "queriedAt": int(time.time() * 1000),
        "configured": configured,
    }


# ---------------------------------------------------------------- 本机订阅同步远程库（agent-subscription-sync）


class SubscriptionSyncRequest(BaseModel):
    """同步本机各 Agent 的订阅服务商信息到远程主库"""

    dry_run: bool = Field(default=False, description="只预览不写库")


@router.post("/subscriptions/sync")
def sync_local_subscriptions_endpoint(
    req: Optional[SubscriptionSyncRequest] = None,
    authorization: Optional[str] = Header(None),
):
    """扫描本机全部 Agent 的订阅配置，按去重规则写入远程主库。

    规则 1：同供应商 + 同 API Key → 跳过（不覆盖不更新，保留原配置）
    规则 2：同供应商 + 同渠道商 + 不同 Key → 新增渠道行，命名以「·Key后4位」消歧
    响应绝不包含明文 API Key（只返回掩码）。
    """
    user_id = _require_user(authorization)
    from app.services.subscription_quota.subscription_sync import sync_local_subscriptions

    return sync_local_subscriptions(user_id, dry_run=bool(req.dry_run if req else False))


@router.get("/subscriptions/cloud")
def list_cloud_subscriptions(authorization: Optional[str] = Header(None)):
    """远程主库中的订阅渠道列表（掩码展示，无明文 Key）"""
    user_id = _require_user(authorization)
    from app.services.subscription_quota.subscription_sync import list_cloud_accounts

    return list_cloud_accounts(user_id)


# ---------------------------------------------------------------- 本机 ↔ 云端（bridge）


class PushItemRequest(BaseModel):
    """一条客户端上传的订阅条目（snake_case：与 addAccount 一致）"""

    provider_id: str = Field(..., description="供应商 id")
    provider_name: str = Field(default="", description="供应商显示名")
    base_url: str = Field(default="", description="订阅调用地址")
    region: str = Field(default="", description="cn / intl")
    channel: str = Field(default="", description="渠道商（base_url host）")
    api_key: str = Field(..., description="API Key（服务端加密入库）")
    source_agents: List[str] = Field(default_factory=list, description="来源（cc-switch / magpie …）")


class PushItemsRequest(BaseModel):
    """批量上传（单次上限 500）"""

    dry_run: bool = Field(default=False, description="只预览不写库")
    items: List[PushItemRequest] = Field(default_factory=list)


#: 导出接口限速：每用户每小时次数（进程内计数即可，单实例部署）
_EXPORT_RATE_LIMIT = 60
_export_calls: dict[str, list[float]] = {}


def _check_export_rate(user_id: str) -> None:
    now = time.time()
    window_start = now - 3600
    calls = [stamp for stamp in _export_calls.get(user_id, []) if stamp >= window_start]
    if len(calls) >= _EXPORT_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail=f"导出过于频繁（上限 {_EXPORT_RATE_LIMIT} 次/小时）",
        )
    calls.append(now)
    _export_calls[user_id] = calls


@router.get("/export/links")
def export_links(
    response: Response,
    target: str = "ccswitch",
    ids: Optional[str] = None,
    authorization: Optional[str] = Header(None),
):
    """生成推送到本机应用的深链（响应含明文 Key：禁止缓存、禁止记日志）

    * ``target``：``ccswitch`` / ``magpie``
    * ``ids``：逗号分隔的账号 id；空 = 全部账号行（不含同步渠道行）
    * 需要设备 Token 作用域 ``subscription:export``（JWT 亦可）
    """
    from app.services.subscription_quota.audit import record as audit_record
    from app.services.subscription_quota.link_builder import (
        build_ccswitch_link,
        build_magpie_link,
    )

    if target not in ("ccswitch", "magpie"):
        raise HTTPException(status_code=400, detail="target 只能是 ccswitch 或 magpie")

    user_id = _require_user(authorization, scope="subscription:export")
    _check_export_rate(user_id)

    # 响应体含明文 Key：禁止任何中间层缓存
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    wanted = {item.strip() for item in (ids or "").split(",") if item.strip()}
    accounts = list_accounts(user_id)
    if wanted:
        accounts = [a for a in accounts if a.id in wanted]
    if len(accounts) > 200:
        raise HTTPException(
            status_code=400, detail="单次最多导出 200 条，请分批（或使用本地桥全量同步）"
        )

    items = []
    for account in accounts:
        if target == "ccswitch":
            result = build_ccswitch_link(
                provider_id=account.provider_id,
                label=account.label,
                base_url=account.base_url,
                api_key=account.api_key or "",
                extra=account.extra,
            )
        else:
            result = build_magpie_link(
                provider_id=account.provider_id,
                label=account.label,
                base_url=account.base_url,
                api_key=account.api_key or "",
                extra=account.extra,
            )
        items.append(
            {
                "accountId": account.id,
                "providerId": account.provider_id,
                "label": account.label,
                "maskedKey": account.masked_key(),
                **result.to_public_dict(),
            }
        )
        if result.url:
            audit_record(
                user_id=user_id,
                account_id=account.id,
                target=target,
                action="export_link",
                masked_key=account.masked_key(),
                url_hash=hashlib.sha256(result.url.encode("utf-8")).hexdigest(),
            )

    return {"target": target, "items": items, "count": len(items)}


@router.get("/export/accounts")
def export_accounts(
    response: Response,
    authorization: Optional[str] = Header(None),
):
    """导出账号明文条目（本地桥 push 用；含 Key，禁止缓存、禁止记日志）

    与 ``/export/links`` 的区别：这里返回结构化字段而非深链，供桥脚本自己决定
    写 Magpie（CLI/admin API）还是 CC Switch（深链）。
    需要设备 Token 作用域 ``subscription:export``。
    """
    from app.services.subscription_quota.audit import record as audit_record

    user_id = _require_user(authorization, scope="subscription:export")
    _check_export_rate(user_id)
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    accounts = list_accounts(user_id)
    items = []
    for account in accounts:
        if not account.api_key:
            continue
        items.append(
            {
                "accountId": account.id,
                "providerId": account.provider_id,
                "label": account.label,
                "baseUrl": account.base_url,
                "region": str((account.extra or {}).get("region") or ""),
                "channel": str((account.extra or {}).get("channel") or ""),
                "maskedKey": account.masked_key(),
                "apiKey": account.api_key,
            }
        )
        audit_record(
            user_id=user_id,
            account_id=account.id,
            target="bridge",
            action="export_account",
            masked_key=account.masked_key(),
            url_hash=hashlib.sha256((account.base_url or "").encode("utf-8")).hexdigest(),
        )
    return {"items": items, "count": len(items)}


@router.post("/subscriptions/push-items")
def push_subscription_items(
    req: PushItemsRequest,
    authorization: Optional[str] = Header(None),
):
    """客户端上传订阅条目（本地桥 pull 用），走与扫描同步相同的去重器"""
    from app.services.subscription_quota.agent_subscription_scan import (
        ScannedSubscription,
        classify_channel,
        host_of,
    )
    from app.services.subscription_quota.subscription_sync import ingest_items

    user_id = _require_user(authorization, scope="subscription:read")

    if len(req.items) > 500:
        raise HTTPException(status_code=400, detail="单次最多 500 条，请分批上传")

    scanned: list[ScannedSubscription] = []
    for item in req.items:
        channel = item.channel or classify_channel(item.provider_id, item.base_url)[0]
        scanned.append(
            ScannedSubscription(
                provider_id=item.provider_id,
                provider_name=item.provider_name or item.provider_id,
                channel=channel or host_of(item.base_url) or "官方",
                base_url=(item.base_url or "").strip(),
                api_key=item.api_key,
                region=item.region or "",
                source_agents=item.source_agents or ["bridge"],
            )
        )

    return ingest_items(user_id, scanned, dry_run=req.dry_run)


@router.get("/subscriptions/duplicates")
def list_subscription_duplicates(authorization: Optional[str] = Header(None)):
    """按 (base_url, Key) 列出现存重复分组（只读，不删除）"""
    from app.services.subscription_quota.subscription_sync import list_duplicates

    user_id = _require_user(authorization)
    return list_duplicates(user_id)

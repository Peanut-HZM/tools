"""供应商注册表（声明式）

一份表描述：供应商 id、显示名、类别（window / balance / subscription）、
需要哪些凭据字段、是否需要用户填 base_url、默认区域。

* ``window``    = 套餐窗口型（5 小时 / 每周 / 每月），结果为档位百分比
* ``balance``   = 预付费钱包型，结果为余额金额
* ``subscription`` = 官方订阅，凭据来自本机 CLI 登录（自动发现，无需填写）

覆盖 cc-switch 的全部 Coding Plan / 余额供应商 + magpie 的预设清单。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class ProviderSpec:
    """一个供应商的定义"""

    id: str
    name: str
    #: window | balance | subscription
    kind: str
    #: 需要的凭据字段（api_key / control_key / access_key + secret_key）
    needs: tuple[str, ...] = ("api_key",)
    #: 是否需要用户提供 base_url
    needs_base_url: bool = False
    #: 是否支持国内/国际两个站点
    regions: tuple[str, ...] = ()
    #: 本机凭据自动发现的来源说明（subscription 类用）
    local_source: Optional[str] = None
    #: 帮助文案
    hint: str = ""
    #: 默认启用（用户添加时预选）
    enabled_by_default: bool = True
    #: 额外字段定义（key -> 中文说明）
    extra_fields: dict[str, str] = field(default_factory=dict)

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "needs": list(self.needs),
            "needsBaseUrl": self.needs_base_url,
            "regions": list(self.regions),
            "localSource": self.local_source,
            "hint": self.hint,
            "extraFields": dict(self.extra_fields),
        }


PROVIDER_SPECS: tuple[ProviderSpec, ...] = (
    # ---------------- 订阅（本机 CLI 登录，自动发现） ----------------
    ProviderSpec(
        id="claude",
        name="Claude Code",
        kind="subscription",
        needs=(),
        local_source="~/.claude/.credentials.json",
        hint="读取 Claude Code 已有登录，查询官方 5 小时 / 每周额度",
    ),
    ProviderSpec(
        id="codex",
        name="Codex (ChatGPT)",
        kind="subscription",
        needs=(),
        local_source="~/.codex/auth.json",
        hint="读取 Codex ChatGPT 登录（auth_mode=chatgpt）",
    ),
    ProviderSpec(
        id="gemini",
        name="Gemini CLI",
        kind="subscription",
        needs=(),
        local_source="~/.gemini/oauth_creds.json",
        hint="读取 Gemini CLI 登录，按 Pro / Flash 分档查询",
    ),
    # ---------------- 套餐窗口型（API Key） ----------------
    ProviderSpec(
        id="kimi",
        name="Kimi For Coding",
        kind="window",
        needs=("api_key",),
        regions=("cn", "intl"),
        hint="API Key 来自 Kimi 开放平台；查询 5 小时 + 每周额度",
    ),
    ProviderSpec(
        id="zhipu",
        name="智谱 GLM",
        kind="window",
        needs=("api_key",),
        regions=("cn", "intl"),
        hint="国内站 bigmodel.cn / 国际站 z.ai，Authorization 不带 Bearer",
    ),
    ProviderSpec(
        id="zhipu_team",
        name="智谱 GLM 团队",
        kind="window",
        needs=("api_key", "organization_id", "project_id"),
        hint="团队版需要额外填组织 ID 与项目 ID",
        extra_fields={
            "organization_id": "组织 ID（bigmodel-organization）",
            "project_id": "项目 ID（bigmodel-project）",
        },
    ),
    ProviderSpec(
        id="minimax",
        name="MiniMax",
        kind="window",
        needs=("api_key",),
        regions=("cn", "intl"),
        hint="国内 api.minimaxi.com / 国际 api.minimax.io",
    ),
    ProviderSpec(
        id="zenmux",
        name="ZenMux",
        kind="window",
        needs=("api_key",),
        needs_base_url=True,
        hint="填写你的 ZenMux 用量地址（直接 GET 该地址）",
    ),
    ProviderSpec(
        id="opencode_go",
        name="OpenCode Go",
        kind="window",
        needs=("api_key",),
        hint="$10/月订阅，查询滚动 / 每周 / 每月三窗口",
    ),
    ProviderSpec(
        id="command_code",
        name="Command Code",
        kind="window",
        needs=("api_key",),
        hint="查询 Claude 端 /provider 的窗口额度",
    ),
    ProviderSpec(
        id="opendesign",
        name="OpenDesign (AMR)",
        kind="window",
        needs=("control_key",),
        hint="需要 AMR 控制面 controlKey（推理 Key sk-amr-ew__ 会被拒）",
        extra_fields={"workspace_id": "工作区 ID（可选，留空自动解析）"},
    ),
    ProviderSpec(
        id="zcode",
        name="ZCode 套餐",
        kind="window",
        needs=("zcode_token",),
        hint="ZCode 套餐额度：可直接使用本机 ZCode 登录自动识别；"
        "也可粘贴 ZCode 的 access token（billing/balance 不可用时回落智谱 GLM 额度接口）",
        extra_fields={"zcode_token": "ZCode access token / API Key"},
    ),
    ProviderSpec(
        id="volcengine",
        name="火山方舟 Agent/Coding Plan",
        kind="window",
        needs=("access_key", "secret_key"),
        hint="用量查询走控制面 OpenAPI，需要账号级 AK/SK（不是推理 Key）",
        extra_fields={"base_url": "推理地址（默认 ark.cn-beijing.volces.com/api/plan）"},
        enabled_by_default=False,
    ),
    # ---------------- 余额型（API Key） ----------------
    ProviderSpec(
        id="deepseek",
        name="DeepSeek",
        kind="balance",
        needs=("api_key",),
        hint="查询账户余额（CNY / USD 钱包）",
    ),
    ProviderSpec(
        id="stepfun",
        name="StepFun",
        kind="balance",
        needs=("api_key",),
        hint="查询账户余额（CNY）",
    ),
    ProviderSpec(
        id="siliconflow",
        name="SiliconFlow",
        kind="balance",
        needs=("api_key",),
        regions=("cn", "intl"),
        hint="国内 api.siliconflow.cn / 国际 api.siliconflow.com",
    ),
    ProviderSpec(
        id="openrouter",
        name="OpenRouter",
        kind="balance",
        needs=("api_key",),
        hint="查询已购额度与已用额度",
    ),
    ProviderSpec(
        id="novita",
        name="Novita AI",
        kind="balance",
        needs=("api_key",),
        hint="查询可用余额（单位 0.0001 USD）",
    ),
    ProviderSpec(
        id="ollama_cloud",
        name="Ollama Cloud",
        kind="balance",
        needs=("api_key",),
        hint="查询 Ollama Cloud 余额（本地 localhost 无额度）",
    ),
    ProviderSpec(
        id="zhipu_payg",
        name="智谱（按量付费）",
        kind="balance",
        needs=("api_key",),
        regions=("cn", "intl"),
        hint="Coding Plan 之外的钱包余额",
    ),
    # ---- 从 agent-hub 合并进来的通用模板（B 独有）----
    ProviderSpec(
        id="newapi",
        name="NewAPI 中转站",
        kind="balance",
        needs=("api_key",),
        needs_base_url=True,
        hint="任意 NewAPI 站点：读 /api/user/self，quota÷500000 = USD",
        extra_fields={"user_id": "站点数字用户 ID（New-Api-User 头，可选）"},
    ),
    ProviderSpec(
        id="sub2api",
        name="Sub2API 中转站",
        kind="balance",
        needs=("api_key",),
        needs_base_url=True,
        hint="任意 Sub2API 站点：读 /v1/usage，返回 quota{limit,used}",
    ),
    ProviderSpec(
        id="generic_balance",
        name="通用余额接口",
        kind="balance",
        needs=("api_key",),
        needs_base_url=True,
        hint="读 {base_url}/user/balance，自动识别 balance / total_balance 字段",
    ),
    ProviderSpec(
        id="manual",
        name="手动额度订阅",
        kind="manual",
        needs=(),
        hint="不查网络：总额度与已用由你自己维护，可随时手动增加",
        extra_fields={
            "quota_unit": "单位（credits/USD/tokens/requests/percent）",
            "window_type": "窗口（none/5h/7d/30d/monthly）",
        },
        enabled_by_default=False,
    ),
)

PROVIDER_BY_ID: dict[str, ProviderSpec] = {spec.id: spec for spec in PROVIDER_SPECS}

#: 所有已知供应商 id（顺序即前端展示顺序）
ALL_PROVIDER_IDS: tuple[str, ...] = tuple(spec.id for spec in PROVIDER_SPECS)

#: 订阅型（本机自动发现，不可手动添加）
SUBSCRIPTION_IDS: tuple[str, ...] = tuple(
    spec.id for spec in PROVIDER_SPECS if spec.kind == "subscription"
)

#: 可手动添加的供应商（需要凭据字段）
MANUAL_PROVIDER_IDS: tuple[str, ...] = tuple(
    spec.id for spec in PROVIDER_SPECS if spec.kind != "subscription"
)


def get_spec(provider_id: str) -> Optional[ProviderSpec]:
    return PROVIDER_BY_ID.get(provider_id)

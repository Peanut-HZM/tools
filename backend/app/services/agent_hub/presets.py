"""Agent Hub 预设清单 — 粘贴一个 apiKey 即可创建的供应商模板。

端点/鉴权细节与 cc-switch 的 coding_plan.rs / balance.rs 对齐（2026-11 分析），
解析实现见 usage_queries.py。
"""
from typing import Any, Dict, List

# kind 查询器分派键（与 agent_hub_subscriptions.kind / usage_queries.py 一致）
SUPPORTED_KINDS = [
    "claude_official", "codex_official", "gemini_official", "manual",
    "opendesign", "kimi", "zhipu", "minimax", "zenmux", "opencode_go",
    "deepseek", "openrouter", "siliconflow", "newapi", "sub2api", "generic_balance",
]

# 需要本机 agent OAuth 凭据的 kind（凭据缺失 → 不显示）
OAUTH_KINDS = ["claude_official", "codex_official", "gemini_official"]

# 作用对象 agent
SUPPORTED_AGENTS = ["claude", "codex", "gemini", "kimi", "opencode", "zcode", "minimax"]

PRESETS: List[Dict[str, Any]] = [
    # ---- 官方订阅（OAuth，读本机 agent 凭据） ----
    {
        "kind": "claude_official", "name": "Claude 官方订阅", "app": "claude",
        "category": "official", "needs_api_key": False, "credential_source": "agent_file",
        "website_url": "https://claude.ai",
        "notes": "读本机 Claude Code 登录凭据查询用量（5h/周窗口），无需填 key",
    },
    {
        "kind": "codex_official", "name": "ChatGPT / Codex 订阅", "app": "codex",
        "category": "official", "needs_api_key": False, "credential_source": "agent_file",
        "website_url": "https://chatgpt.com",
        "notes": "读本机 Codex 登录凭据查询用量（primary/secondary 窗口 + Credits）",
    },
    {
        "kind": "gemini_official", "name": "Gemini 订阅 (Code Assist)", "app": "gemini",
        "category": "official", "needs_api_key": False, "credential_source": "agent_file",
        "website_url": "https://codeassist.google.com",
        "notes": "读本机 Gemini CLI OAuth 凭据查询 Pro/Flash/Lite 配额",
    },
    # ---- Coding Plan 套餐（key 即加） ----
    {
        "kind": "opendesign", "name": "OpenDesign", "app": "claude",
        "category": "aggregator", "needs_api_key": True,
        "website_url": "https://open-design.ai",
        "base_url": "https://amr-api.open-design.ai",
        "usage_api_key_hint": "填 AMR 控制面 controlKey（推理 key sk-amr-ew__ 开头会被 401 拒绝）",
        "notes": "5h/7d 两个窗口的 credits 用量（limit/remaining/resetsAt）",
    },
    {
        "kind": "kimi", "name": "Kimi For Coding", "app": "kimi",
        "category": "official", "needs_api_key": True,
        "website_url": "https://platform.kimi.ai",
        "base_url": "https://api.kimi.com",
        "notes": "5h 窗口 + 周额度（limits[].detail / usage）",
    },
    {
        "kind": "zhipu", "name": "智谱 GLM Coding Plan", "app": "claude",
        "category": "official", "needs_api_key": True,
        "website_url": "https://open.bigmodel.cn",
        "base_url": "https://open.bigmodel.cn",
        "notes": "5h/周额度（unit=3/6），按量账户自动回落查余额",
    },
    {
        "kind": "minimax", "name": "MiniMax Coding Plan", "app": "minimax",
        "category": "official", "needs_api_key": True,
        "website_url": "https://www.minimaxi.com",
        "base_url": "https://api.minimaxi.com",
        "notes": "5h + 周窗口（general 模型行）",
    },
    {
        "kind": "zenmux", "name": "ZenMux", "app": "claude",
        "category": "aggregator", "needs_api_key": True,
        "website_url": "https://zenmux.ai",
        "notes": "quota_5_hour / quota_7_day（usage_percentage + USD 金额）",
    },
    {
        "kind": "opencode_go", "name": "OpenCode Go", "app": "opencode",
        "category": "official", "needs_api_key": True,
        "website_url": "https://opencode.ai",
        "notes": "rolling/weekly/monthly 三窗口（percent + resetsAt）",
    },
    # ---- 余额类（按量付费） ----
    {
        "kind": "deepseek", "name": "DeepSeek", "app": "opencode",
        "category": "official", "needs_api_key": True,
        "website_url": "https://platform.deepseek.com",
        "base_url": "https://api.deepseek.com",
        "notes": "余额（多币种钱包取有效值）",
    },
    {
        "kind": "openrouter", "name": "OpenRouter", "app": "opencode",
        "category": "aggregator", "needs_api_key": True,
        "website_url": "https://openrouter.ai",
        "base_url": "https://openrouter.ai",
        "notes": "credits 总额 - 已用",
    },
    {
        "kind": "siliconflow", "name": "SiliconFlow 硅基流动", "app": "opencode",
        "category": "official", "needs_api_key": True,
        "website_url": "https://siliconflow.cn",
        "base_url": "https://api.siliconflow.cn",
        "notes": "totalBalance（cn 站 CNY / com 站 USD）",
    },
    # ---- 通用模板（任意 NewAPI / Sub2API 中转站，key + 站点即加） ----
    {
        "kind": "newapi", "name": "NewAPI 中转站（通用）", "app": "claude",
        "category": "third_party", "needs_api_key": True,
        "notes": "GET {base_url}/api/user/self + New-Api-User 头；quota÷500000=USD",
    },
    {
        "kind": "sub2api", "name": "Sub2API 中转站（通用）", "app": "claude",
        "category": "third_party", "needs_api_key": True,
        "notes": "GET {base_url}/v1/usage，返回 quota{limit,used}",
    },
    {
        "kind": "generic_balance", "name": "通用余额（/user/balance）", "app": "claude",
        "category": "custom", "needs_api_key": True,
        "notes": "GET {base_url}/user/balance，自动探测 balance/total_balance 字段",
    },
    # ---- 手动额度（无 API，用户自己维护 ✅ 额度支持手动增加） ----
    {
        "kind": "manual", "name": "手动额度订阅", "app": "claude",
        "category": "manual", "needs_api_key": False,
        "notes": "手动维护总额度/已用（额度支持随时手动增加），可选填重置时间",
    },
]


def get_preset(kind: str) -> Dict[str, Any] | None:
    for preset in PRESETS:
        if preset["kind"] == kind:
            return preset
    return None

"""订阅 → 本机应用深链生成器（CC Switch / Magpie）

设计依据：``specs/agent-subscription-bridge-design.md`` §4.6 / §6.2 / §6.3

两条目标应用的官方写入方式都是从源码确认过的：

* CC Switch：``ccswitch://v1/import?resource=provider&app=…``
  （``src-tauri/src/deeplink/parser.rs`` + ``deeplink/provider.rs``）
* Magpie：``magpie://import?preset=…&key=…`` 或 ``name=…&anthropic=…&key=…``
  （``internal/provider/importurl.go``）

安全约定：链接里必然带明文 Key（协议规定），因此
* 本模块不写任何日志；
* 调用方必须给响应加 ``Cache-Control: no-store``，且审计只存掩码 + 链接哈希。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlencode

#: provider_id → CC Switch app（只需覆盖不需要 model 的四个 app）
_CCSWITCH_ANTHROPIC = {"anthropic", "claude"}
_CCSWITCH_OPENAI = {"openai", "codex", "deepseek", "qwen", "alibaba", "alibaba-cn"}
_CCSWITCH_GEMINI = {"gemini", "google"}

#: 确认走 Anthropic Messages 协议的供应商（地址看不出来时用这份兜底）
_ANTHROPIC_PROTOCOL = {
    "anthropic",
    "claude",
    "kimi",
    "zhipu",
    "zhipu_team",
    "minimax",
    "opendesign",
}

#: provider_id → Magpie preset（region 差异在 _magpie_preset 内处理）
_MAGPIE_PRESETS: dict[str, str] = {
    "kimi": "kimi-code",
    "codex": "openai",
    "openai": "openai",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "gemini": "google",
    "google": "google",
    "deepseek": "deepseek",
    "zhipu": "zhipu",
    "minimax": "minimax",
    "qwen": "qwen",
    "alibaba": "qwen",
    "alibaba-cn": "qwen-cn",
    "siliconflow": "siliconflow",
    "openrouter": "openrouter",
    "volcengine": "volcengine",
    "stepfun": "stepfun",
    "moonshot": "moonshot",
    "opencode_go": "opencode-go",
    "opencode-go": "opencode-go",
}

#: 区域化 preset（key: (国内, 国际)）
_MAGPIE_REGION_PRESETS: dict[str, tuple[str, str]] = {
    "kimi": ("kimi-code-cn", "kimi-code"),
    "zhipu": ("zhipu", "zai"),
    "minimax": ("minimax-cn", "minimax"),
    "qwen": ("qwen-cn", "qwen"),
}

#: provider_id → 默认 endpoint（设计 §4.6；空 base_url 时用）
DEFAULT_ENDPOINTS: dict[str, str] = {
    "anthropic": "https://api.anthropic.com",
    "claude": "https://api.anthropic.com",
    "openai": "https://api.openai.com/v1",
    "codex": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com",
    "google": "https://generativelanguage.googleapis.com",
    "deepseek": "https://api.deepseek.com/v1",
    "zhipu": "https://open.bigmodel.cn/api/anthropic",
    "kimi": "https://api.kimi.com/coding/v1",
    "minimax": "https://api.minimaxi.com/anthropic",
    "qwen": "https://coding.dashscope.aliyuncs.com/v1",
    "alibaba": "https://coding.dashscope.aliyuncs.com/v1",
    "opencode_go": "https://opencode.ai/zen/go",
    "opendesign": "https://amr-api.open-design.ai",
}

#: 国际站覆盖（region=intl 时替换默认 endpoint）
_DEFAULT_ENDPOINTS_INTL: dict[str, str] = {
    "zhipu": "https://api.z.ai/api/anthropic",
}

#: CC Switch 深链必须带 model 的 app —— 本工具无模型元数据，一律不选它们
#: （``app`` 只会从上面的三组映射里选出 claude/codex/gemini/opencode，本常量仅作文档约束）
_CCSWITCH_NEEDS_MODEL = {"pi", "mcode", "kimi", "dsh", "omp"}


@dataclass(frozen=True)
class LinkResult:
    """一条订阅的深链生成结果"""

    target: str  # ccswitch | magpie
    url: Optional[str]
    app_or_preset: str
    warnings: tuple[str, ...] = ()

    def to_public_dict(self) -> dict:
        return {
            "target": self.target,
            "url": self.url,
            "app": self.app_or_preset,
            "warnings": list(self.warnings),
        }


def _region(extra: dict) -> str:
    region = str((extra or {}).get("region") or "").strip().lower()
    if region in ("intl", "international", "global", "overseas"):
        return "intl"
    if region in ("cn", "china", "domestic"):
        return "cn"
    return ""


def resolve_endpoint(provider_id: str, base_url: str, extra: dict) -> Optional[str]:
    """链接用的 endpoint：账号 base_url 优先，其次按 provider 默认值（可 region 覆盖）"""
    explicit = (base_url or "").strip()
    if explicit:
        return explicit
    region = _region(extra)
    if region == "intl" and provider_id in _DEFAULT_ENDPOINTS_INTL:
        return _DEFAULT_ENDPOINTS_INTL[provider_id]
    return DEFAULT_ENDPOINTS.get(provider_id)


def _ccswitch_app(provider_id: str, endpoint: str) -> tuple[Optional[str], tuple[str, ...]]:
    if provider_id in _CCSWITCH_ANTHROPIC:
        return "claude", ()
    if provider_id in _CCSWITCH_OPENAI:
        return "codex", ()
    if provider_id in _CCSWITCH_GEMINI:
        return "gemini", ()
    lowered = (endpoint or "").lower()
    if "anthropic" in lowered:
        return "opencode", ()
    return "opencode", ()


def _is_anthropic(provider_id: str, endpoint: str) -> bool:
    """该订阅是否走 Anthropic Messages 协议（决定 opencode 的 apiFormat）"""
    if provider_id in _ANTHROPIC_PROTOCOL:
        return True
    return "anthropic" in (endpoint or "").lower()


def _account_label(label: str) -> str:
    """去掉同步时追加的消歧后缀（·abcd / -2）作为应用里的显示名"""
    name = (label or "").strip()
    for sep in ("·", "-"):
        idx = name.rfind(sep)
        if idx > 0 and len(name) - idx <= 6 and any(ch.isdigit() or ch.isalpha() for ch in name[idx + 1 :]):
            # 只裁剪看起来像消歧后缀的短尾（Key 后 4 位 / 递增序号）
            tail = name[idx + 1 :]
            if len(tail) == 4 or tail.isdigit():
                name = name[:idx]
                break
    return name or "subscription"


def build_ccswitch_link(
    *, provider_id: str, label: str, base_url: str, api_key: str, extra: dict
) -> LinkResult:
    """生成 CC Switch 导入深链（``enabled=false``：导入但不改动当前供应商）"""
    if not api_key:
        return LinkResult("ccswitch", None, "", ("缺少 API Key，无法生成导入链接",))

    endpoint = resolve_endpoint(provider_id, base_url, extra)
    if not endpoint:
        return LinkResult(
            "ccswitch",
            None,
            "",
            ("缺少 endpoint（base_url 为空且该供应商无默认地址），请先编辑账号填写调用地址",),
        )

    app, warnings = _ccswitch_app(provider_id, endpoint)

    params = {
        "resource": "provider",
        "app": app,
        "name": _account_label(label),
        "endpoint": endpoint,
        "apiKey": api_key,
        "notes": "来自订阅中心",
        # Rust bool::from_str 只认小写 true/false（"False" 会被忽略）
        "enabled": "false",
    }
    if app == "opencode":
        params["apiFormat"] = "anthropic" if _is_anthropic(provider_id, endpoint) else "openai_chat"

    return LinkResult("ccswitch", f"ccswitch://v1/import?{urlencode(params)}", app, warnings)


def _magpie_preset(provider_id: str, extra: dict) -> Optional[str]:
    if provider_id in _MAGPIE_REGION_PRESETS:
        cn, intl = _MAGPIE_REGION_PRESETS[provider_id]
        return cn if _region(extra) == "cn" else intl
    return _MAGPIE_PRESETS.get(provider_id)


def build_magpie_link(
    *, provider_id: str, label: str, base_url: str, api_key: str, extra: dict
) -> LinkResult:
    """生成 Magpie 导入深链（有 preset 走 preset，否则用 name + 协议地址）"""
    if not api_key:
        return LinkResult("magpie", None, "", ("缺少 API Key，无法生成导入链接",))

    preset = _magpie_preset(provider_id, extra)
    if preset:
        params = {"preset": preset, "key": api_key, "name": _account_label(label)}
        return LinkResult("magpie", f"magpie://import?{urlencode(params)}", preset)

    endpoint = resolve_endpoint(provider_id, base_url, extra)
    if not endpoint:
        return LinkResult(
            "magpie",
            None,
            "",
            ("该供应商无 Magpie preset 且缺少调用地址，无法生成导入链接",),
        )

    # 自定义中转：按协议归属选字段（magpie 只认这四个之一）
    if _is_anthropic(provider_id, endpoint):
        endpoint_param = {"anthropic": endpoint}
    elif provider_id in _CCSWITCH_GEMINI or "generativelanguage" in endpoint.lower():
        endpoint_param = {"gemini": endpoint}
    else:
        endpoint_param = {"chat": endpoint}

    params = {
        "name": _account_label(label),
        "key": api_key,
        **endpoint_param,
    }
    return LinkResult("magpie", f"magpie://import?{urlencode(params)}", "custom")
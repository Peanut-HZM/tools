"""网关的上游端点表

每个供应商的「推理地址」不同（Anthropic 兼容 / OpenAI 兼容），网关据此转发。

与 cc-switch 的 `codingPlanProviders.ts` 及各 CLI 配置保持一致。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Upstream:
    """一个供应商的推理入口"""

    #: Anthropic Messages 兼容入口（None 表示不支持）
    anthropic_base: Optional[str] = None
    #: OpenAI Chat Completions 兼容入口（None 表示不支持）
    openai_base: Optional[str] = None
    #: 鉴权头风格：bearer = Authorization: Bearer，x-api-key = Anthropic 风格
    auth_style: str = "bearer"
    #: Anthropic 需要的 beta 头（官方 Claude 用）
    anthropic_beta: Optional[str] = None


#: provider_id → 上游入口
UPSTREAMS: dict[str, Upstream] = {
    # ---- Anthropic 兼容的编程套餐 ----
    "kimi": Upstream(
        anthropic_base="https://api.kimi.com/coding",
        openai_base="https://api.kimi.com/coding/v1",
    ),    "zhipu": Upstream(
        anthropic_base="https://open.bigmodel.cn/api/anthropic",
        openai_base="https://open.bigmodel.cn/api/paas/v4",
    ),
    "minimax": Upstream(
        anthropic_base="https://api.minimaxi.com/anthropic",
        openai_base="https://api.minimaxi.com/v1",
    ),
    "deepseek": Upstream(
        anthropic_base="https://api.deepseek.com/anthropic",
        openai_base="https://api.deepseek.com/v1",
    ),
    "opendesign": Upstream(
        anthropic_base="https://amr-link.open-design.ai",
        openai_base="https://amr-link.open-design.ai/v1",
    ),
    "zhipu_payg": Upstream(
        anthropic_base="https://open.bigmodel.cn/api/anthropic",
        openai_base="https://open.bigmodel.cn/api/paas/v4",
    ),
    # ---- OpenAI 兼容的普通供应商 ----
    "zenmux": Upstream(openai_base=None),  # 用账号自填 base_url
    "opencode_go": Upstream(
        anthropic_base="https://opencode.ai/inference/go/anthropic",
        openai_base="https://opencode.ai/inference/go/v1",
    ),
    "command_code": Upstream(
        openai_base="https://api.commandcode.ai/provider/v1",
    ),
    "siliconflow": Upstream(openai_base="https://api.siliconflow.cn/v1"),
    "openrouter": Upstream(openai_base="https://openrouter.ai/api/v1"),
    "novita": Upstream(openai_base="https://api.novita.ai/v3/openai"),
    "stepfun": Upstream(openai_base="https://api.stepfun.com/v1"),
    "ollama_cloud": Upstream(openai_base="https://ollama.com/v1"),
    # ---- 官方订阅（Anthropic 官方 / OpenAI 官方）----
    "claude": Upstream(
        anthropic_base="https://api.anthropic.com",
        auth_style="bearer",
        anthropic_beta="oauth-2025-04-20",
    ),
    "codex": Upstream(openai_base="https://chatgpt.com/backend-api/codex"),
    "gemini": Upstream(),  # Gemini 走独立协议，网关暂不透传
}


def get_upstream(provider_id: str) -> Optional[Upstream]:
    return UPSTREAMS.get(provider_id)


def resolve_base(provider_id: str, account_extra: dict | None, kind: str) -> Optional[str]:
    """解析实际使用的上游地址。

    优先级（重要）：
    1. ``{kind}_base``（显式协议级覆盖，如 ``openai_base``）
    2. 供应商内置的该协议地址
    3. ``base_url``（通用覆盖，仅在内置缺失时使用）

    第 3 条排在内置之后是有原因的：cc-switch 导入来的账号会带一个
    ``base_url``（它存的是 **Anthropic** 地址，如 ``https://api.kimi.com/coding``），
    如果让它覆盖 OpenAI 协议地址，就会拼出 ``/coding/chat/completions`` → 404。
    """
    extra = account_extra or {}
    spec = get_upstream(provider_id)

    explicit = extra.get(f"{kind}_base")
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip().rstrip("/")

    if spec is not None:
        builtin = spec.anthropic_base if kind == "anthropic" else spec.openai_base
        if builtin:
            return builtin.rstrip("/")
        # 内置缺该协议时才回落到通用 base_url
        fallback = spec.anthropic_base if kind != "anthropic" else spec.openai_base
        generic = extra.get("base_url")
        if isinstance(generic, str) and generic.strip():
            return generic.strip().rstrip("/")
        return fallback.rstrip("/") if fallback else None

    generic = extra.get("base_url")
    if isinstance(generic, str) and generic.strip():
        return generic.strip().rstrip("/")
    return None

"""本机各 AI 编程 Agent 的订阅服务商信息扫描器（agent-subscription-sync）

只做**只读**扫描：把各 Agent 本机配置里的「供应商 + 渠道商(base_url) + API Key」
收集为统一条目，供 subscription_sync 写入远程主库。

安全约束（密钥暴露面规则）：
* 明文 Key 只在本模块与调用方（服务端进程内存）之间流转，**绝不写日志**；
* 日志只记 agent 名、条目数量与跳过原因，不记任何 Key 片段 / base_url 全量凭据；
* 路径解析全部基于真实家目录（real_home / expand_user_path），遵守
  「用户目录访问必须使用真实家目录」规则（config.py 会覆盖 HOME）。

各来源格式（均为本机实测路径，REAL_HOME 展开）：
* cc-switch   : ~/.cc-switch/cc-switch.db（复用 scripts.import_ccswitch_providers）
* claude      : ~/.claude/settings.json → env.{ANTHROPIC_AUTH_TOKEN|ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL}
* codex       : ~/.codex/auth.json（OPENAI_API_KEY）+ config.toml [model_providers.*].base_url
* opencode    : ~/.local/share/opencode/auth.json + ~/.config/opencode/opencode.json provider 块
* zcode       : provider_config.json（复用 zcode_provider_config.read_provider_keys）
* kimi / minimax / gemini / pi / copilot：OAuth 登录态或无 Key → 仅报告（reportOnly），不入库
"""

from __future__ import annotations

import json
import logging
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from app.utils.agent_readers.base import real_home
from app.utils.path_utils import expand_user_path as expand_user_path_str

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- 数据结构


@dataclass
class ScannedSubscription:
    """一条待同步的订阅渠道（api_key 仅服务端内存使用，禁止序列化外泄）"""

    provider_id: str
    provider_name: str
    #: 渠道商（base_url host）；官方直连为 "官方"
    channel: str
    base_url: str = ""
    api_key: str = ""
    region: str = "cn"
    #: 发现该条目的来源 agent 列表（批内去重时合并）
    source_agents: list[str] = field(default_factory=list)


@dataclass
class AgentScanResult:
    """单个来源 agent 的扫描结果（对外安全：无任何 Key）"""

    agent: str
    discovered: int = 0
    report_only: int = 0
    error: Optional[str] = None


@dataclass
class ScanReport:
    agents: list[AgentScanResult] = field(default_factory=list)
    items: list[ScannedSubscription] = field(default_factory=list)


# ---------------------------------------------------------------- 官方域名映射（设计 §5.2，一处定义）

OFFICIAL_HOSTS: dict[str, tuple[str, ...]] = {
    "anthropic": ("api.anthropic.com", "api.claude.ai"),
    "openai": ("api.openai.com",),
    "zhipu": ("open.bigmodel.cn",),
    "deepseek": ("api.deepseek.com",),
    "kimi": ("api.moonshot.cn", "api.moonshot.ai"),
    "moonshot": ("api.moonshot.cn", "api.moonshot.ai"),
    "minimax": ("api.minimax.chat", "api.minimaxi.com"),
    "gemini": ("generativelanguage.googleapis.com",),
    "qwen": ("dashscope.aliyuncs.com",),
    "opendesign": ("amr-api.open-design.ai",),
}

#: host → provider_id 的反查表（构建一次）
_HOST_TO_PROVIDER: dict[str, str] = {
    host: pid for pid, hosts in OFFICIAL_HOSTS.items() for host in hosts
}


def host_of(url: str) -> str:
    """提取 base_url 的 host；非 URL 形态原样返回（去空白）。"""
    value = (url or "").strip()
    if not value:
        return ""
    if "://" in value:
        return (urlparse(value).hostname or "").lower()
    # 无 scheme 的裸 host（如 "api.example.com/v1"）
    return value.split("/")[0].lower()


def official_provider_of_host(host: str) -> Optional[str]:
    """host 命中官方域名清单时返回对应 provider_id（支持子域名后缀匹配）。

    例如清单条目 ``dashscope.aliyuncs.com`` 需能命中 ``coding.dashscope.aliyuncs.com``
    （阿里云百炼的 coding 子域），精确匹配会漏掉这类子域名（2026-11-20 审计实锤）。
    """
    h = (host or "").lower().strip(".")
    if not h:
        return None
    if h in _HOST_TO_PROVIDER:
        return _HOST_TO_PROVIDER[h]
    for entry, pid in _HOST_TO_PROVIDER.items():
        if h.endswith("." + entry):
            return pid
    return None


def classify_channel(provider_id: str, base_url: str) -> tuple[str, str]:
    """返回 (渠道名, category)。

    官方直连（无 base_url 或 host 命中该供应商官方域名，含子域名）→ ("官方", "official")；
    其余 → (host, "third_party")。
    """
    host = host_of(base_url)
    if not host or official_provider_of_host(host) == provider_id:
        return "官方", "official"
    return host, "third_party"


def is_local_gateway_url(base_url: str) -> bool:
    """是否指向本地网关回路（127.0.0.1 / localhost / [::1]）——不是外部订阅渠道。"""
    host = host_of(base_url)
    return host in ("127.0.0.1", "localhost", "::1", "0.0.0.0")


def looks_like_oauth_token(value: str) -> bool:
    """OAuth JWT 等登录态令牌（eyJ 开头或超长）——会自动轮换，按设计不入库。"""
    return value.startswith("eyJ") or len(value) > 500


def looks_like_config_identifier(value: str) -> bool:
    """是否为配置字段值被误判成 Key（如 pi 配置的 ``compat.maxTokensField``）。

    事故样本（2026-11-20）：``_pick_key`` 按字段名含 ``token`` 误抓了
    ``max_completion_tokens`` 这类 snake_case 配置标识符（字段名含 token ≠ 值是凭据）。
    真实 API Key 几乎必含大写/数字/符号；纯小写字母+下划线且无数字的串按配置值拒收。
    """
    return bool(value) and value == value.lower() and value.replace("_", "").isalpha()


# ---------------------------------------------------------------- 路径解析（真实家目录）


def _home_path(*parts: str) -> Path:
    return real_home().joinpath(*parts)


# ---------------------------------------------------------------- 各来源扫描


def _scan_cc_switch(items: list[ScannedSubscription]) -> AgentScanResult:
    """cc-switch 数据库：多供应商/多渠道/多 Key 的权威来源（元数据最完整）。

    两段式：
    1. 复用 ``load_candidates``（成熟解析：控制面 Key 优先、usage_script 归类）
    2. **救援通道**：对被 load_candidates 丢弃的条目（其 ``_match_provider``
       按名字+URL 匹配，覆盖面有限——2026-11-20 审计发现 qwen3.6-plus 被漏），
       用 Key + base_url host 后缀匹配重新识别：
       - 无 Key / OAuth JWT（eyJ 开头或超长）→ 不入库（reportOnly）
       - base_url 指向本地网关（127.0.0.1 等）→ 不入库（reportOnly）
       - host 命中官方域名清单（含子域）→ 对应 provider 入库
       - 其余 → provider_id=custom、显示名取 host 入库
    """
    result = AgentScanResult(agent="cc-switch")
    try:
        from app.services.subscription_quota.usage_import import ccswitch_db_path
        from scripts.import_ccswitch_providers import (
            _collect_secrets,
            _collect_urls,
            _match_provider,
            _pick_key,
            load_candidates,
        )

        db_path = ccswitch_db_path()
        if not db_path.exists():
            result.report_only = 1  # 未安装 cc-switch，属正常状态而非错误
            return result

        before = len(items)
        candidates = load_candidates(db_path)
        for cand in candidates:
            key = (cand.get("api_key") or "").strip()
            if not key:
                continue
            provider_id = cand.get("provider_id") or "custom"
            channel, _category = classify_channel(provider_id, cand.get("base_url") or "")
            items.append(
                ScannedSubscription(
                    provider_id=provider_id,
                    provider_name=cand.get("source_name") or provider_id,
                    channel=channel,
                    base_url=(cand.get("base_url") or "").strip(),
                    api_key=key,
                    region=cand.get("region") or "cn",
                    source_agents=["cc-switch"],
                )
            )
        matched_names = {(c.get("source_name") or "") for c in candidates}

        # ---- 救援通道：只处理 load_candidates 丢弃的条目 ----
        import json as _json
        import sqlite3

        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            raw_rows = conn.execute(
                "SELECT name, app_type, settings_config FROM providers"
            ).fetchall()
        finally:
            conn.close()
        for row in raw_rows:
            name = row["name"] or ""
            if name in matched_names:
                continue
            try:
                cfg = _json.loads(row["settings_config"] or "{}")
            except (ValueError, TypeError):
                cfg = {}
            secrets = _collect_secrets(cfg)
            key = _pick_key(secrets)
            if not isinstance(key, str) or not key.strip():
                result.report_only += 1  # 无真实凭据（OAuth 登录态 / 空配置）
                continue
            key = key.strip()
            if looks_like_oauth_token(key):
                result.report_only += 1  # OAuth JWT 会自动轮换，按设计不入库
                continue
            if looks_like_config_identifier(key):
                result.report_only += 1  # 配置字段值被误判成 Key（如 maxTokensField），不入库
                continue
            urls = [u for u in _collect_urls(cfg) if isinstance(u, str)]
            base_url = urls[0] if urls else ""
            if is_local_gateway_url(base_url):
                result.report_only += 1  # 本地网关回路（127.0.0.1），非外部订阅渠道
                continue
            provider_id = _match_provider(name, " ".join(urls))
            if not provider_id:
                provider_id = official_provider_of_host(host_of(base_url)) or "custom"
            provider_name = name if provider_id != "custom" else (host_of(base_url) or name)
            channel, _category = classify_channel(provider_id, base_url)
            items.append(
                ScannedSubscription(
                    provider_id=provider_id,
                    provider_name=provider_name or provider_id,
                    channel=channel,
                    base_url=base_url,
                    api_key=key,
                    source_agents=["cc-switch"],
                )
            )
            logger.info("cc-switch 救援通道识别条目: name=%s provider=%s", name, provider_id)
        result.discovered = len(items) - before
    except Exception as exc:  # 单源失败隔离：不影响其他来源
        logger.warning("扫描 cc-switch 失败: %s", exc)
        result.error = f"扫描失败: {exc}"
    return result


def _scan_claude(items: list[ScannedSubscription]) -> AgentScanResult:
    """Claude Code：~/.claude/settings.json 的 env 块（cc-switch 切换写入处）。"""
    result = AgentScanResult(agent="claude")
    try:
        configured = (os.environ.get("CLAUDE_CONFIG_DIR") or "").strip()
        if configured:
            settings_path = Path(expand_user_path_str(configured)) / "settings.json"
        else:
            settings_path = _home_path(".claude", "settings.json")
        if not settings_path.is_file():
            result.report_only = 1
            return result
        data = json.loads(settings_path.read_text(encoding="utf-8", errors="replace"))
        env = data.get("env") if isinstance(data.get("env"), dict) else {}
        key = (env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY") or "").strip()
        if not key:
            result.report_only = 1  # 未配置 API Key（可能是订阅登录态）
            return result
        base_url = (env.get("ANTHROPIC_BASE_URL") or "").strip()
        channel, _category = classify_channel("anthropic", base_url)
        items.append(
            ScannedSubscription(
                provider_id="anthropic",
                provider_name="Anthropic Claude",
                channel=channel,
                base_url=base_url,
                api_key=key,
                source_agents=["claude"],
            )
        )
        result.discovered = 1
    except Exception as exc:
        logger.warning("扫描 claude 配置失败: %s", exc)
        result.error = f"扫描失败: {exc}"
    return result


def _codex_roots() -> list[Path]:
    configured = (os.environ.get("CODEX_HOME") or "").strip()
    if configured:
        return [Path(expand_user_path_str(configured))]
    return [_home_path(".codex")]


def _scan_codex(items: list[ScannedSubscription]) -> AgentScanResult:
    """Codex CLI：auth.json 的 OPENAI_API_KEY + config.toml 当前供应商 base_url。"""
    result = AgentScanResult(agent="codex")
    try:
        for root in _codex_roots():
            if not root.is_dir():
                continue
            auth_path = root / "auth.json"
            if not auth_path.is_file():
                result.report_only = 1  # 未登录/无 Key
                continue
            auth = json.loads(auth_path.read_text(encoding="utf-8", errors="replace"))
            key = (auth.get("OPENAI_API_KEY") or "").strip()
            if not key:
                result.report_only = 1
                continue
            base_url = ""
            config_path = root / "config.toml"
            if config_path.is_file():
                config = tomllib.loads(config_path.read_text(encoding="utf-8", errors="replace"))
                active = (config.get("model_provider") or "openai").strip()
                providers = config.get("model_providers")
                if isinstance(providers, dict):
                    spec = providers.get(active)
                    if isinstance(spec, dict):
                        base_url = (spec.get("base_url") or "").strip()
            provider_id = "openai"
            host = host_of(base_url)
            mapped = official_provider_of_host(host)
            if mapped:
                provider_id = mapped
            channel, _category = classify_channel(provider_id, base_url)
            items.append(
                ScannedSubscription(
                    provider_id=provider_id,
                    provider_name="OpenAI Codex",
                    channel=channel,
                    base_url=base_url,
                    api_key=key,
                    region="global",
                    source_agents=["codex"],
                )
            )
            result.discovered = 1
    except Exception as exc:
        logger.warning("扫描 codex 配置失败: %s", exc)
        result.error = f"扫描失败: {exc}"
    return result


def _scan_opencode(items: list[ScannedSubscription]) -> AgentScanResult:
    """OpenCode：auth.json（各供应商 Key）+ opencode.json 自定义 provider 块。"""
    result = AgentScanResult(agent="opencode")
    try:
        # OPENCODE_DATA_DIR 指向数据目录本身；XDG_CONFIG_HOME 是配置基目录（如 ~/.config）
        data_dir_env = (os.environ.get("OPENCODE_DATA_DIR") or "").strip()
        if data_dir_env:
            auth_path = Path(expand_user_path_str(data_dir_env)) / "auth.json"
        else:
            auth_path = _home_path(".local", "share", "opencode", "auth.json")
        xdg_env = (os.environ.get("XDG_CONFIG_HOME") or "").strip()
        if xdg_env:
            config_path = Path(expand_user_path_str(xdg_env)) / "opencode" / "opencode.json"
        else:
            config_path = _home_path(".config", "opencode", "opencode.json")
        entries: list[tuple[str, str, str]] = []  # (provider_id_hint, base_url, key)

        if auth_path.is_file():
            auth = json.loads(auth_path.read_text(encoding="utf-8", errors="replace"))
            if isinstance(auth, dict):
                for provider, payload in auth.items():
                    if not isinstance(payload, dict):
                        continue
                    key = (payload.get("key") or "").strip()
                    if key:
                        entries.append((provider, "", key))

        if config_path.is_file():
            config = json.loads(config_path.read_text(encoding="utf-8", errors="replace"))
            providers = config.get("provider") if isinstance(config, dict) else None
            if isinstance(providers, dict):
                for provider, spec in providers.items():
                    if not isinstance(spec, dict):
                        continue
                    options = spec.get("options") if isinstance(spec.get("options"), dict) else {}
                    key = (options.get("apiKey") or "").strip()
                    base_url = (options.get("baseURL") or options.get("base_url") or "").strip()
                    if key:
                        # opencode.json 内嵌 Key 优先（含 base_url 上下文），覆盖 auth.json 同名项
                        entries = [
                            e for e in entries if e[0] != provider
                        ] + [(provider, base_url, key)]

        if not entries:
            result.report_only = 1
            return result

        for hint, base_url, key in entries:
            host = host_of(base_url)
            provider_id = official_provider_of_host(host) or hint or "custom"
            channel, _category = classify_channel(provider_id, base_url)
            items.append(
                ScannedSubscription(
                    provider_id=provider_id,
                    provider_name=hint or provider_id,
                    channel=channel,
                    base_url=base_url,
                    api_key=key,
                    source_agents=["opencode"],
                )
            )
        result.discovered = len(entries)
    except Exception as exc:
        logger.warning("扫描 opencode 配置失败: %s", exc)
        result.error = f"扫描失败: {exc}"
    return result


def _scan_zcode(items: list[ScannedSubscription]) -> AgentScanResult:
    """ZCode：provider_config.json 的明文 Key（复用既有读取器）。"""
    result = AgentScanResult(agent="zcode")
    try:
        from app.services.subscription_quota.zcode_provider_config import read_provider_keys

        discovered = read_provider_keys()
        for item in discovered:
            key = (item.api_key or "").strip()
            if not key:
                continue
            channel, _category = classify_channel(item.provider_id, item.base_url or "")
            items.append(
                ScannedSubscription(
                    provider_id=item.provider_id,
                    provider_name=item.label or item.provider_id,
                    channel=channel,
                    base_url=(item.base_url or "").strip(),
                    api_key=key,
                    region=getattr(item, "region", "cn") or "cn",
                    source_agents=["zcode"],
                )
            )
        result.discovered = len(items)
        if not discovered:
            result.report_only = 1
    except Exception as exc:
        logger.warning("扫描 zcode 配置失败: %s", exc)
        result.error = f"扫描失败: {exc}"
    return result


#: OAuth 登录态 / 无独立 API Key 的来源：仅报告存在性（设计 §11：不入库）
_REPORT_ONLY_SOURCES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("kimi", (".kimi-code", "credentials")),
    ("minimax", (".minimax",)),
    ("gemini", (".gemini",)),
    ("pi", (".pi", "agent")),
    ("copilot", (".copilot",)),
)


def _scan_report_only() -> list[AgentScanResult]:
    results: list[AgentScanResult] = []
    for agent, parts in _REPORT_ONLY_SOURCES:
        entry = AgentScanResult(agent=agent)
        try:
            path = real_home().joinpath(*parts)
            entry.report_only = 1 if path.exists() else 0
        except Exception as exc:
            logger.warning("探测 %s 目录失败: %s", agent, exc)
            entry.error = f"探测失败: {exc}"
        results.append(entry)
    return results


# ---------------------------------------------------------------- 主入口


def scan_local_subscriptions() -> ScanReport:
    """扫描本机全部来源。单源异常只记录到该来源结果，不影响其他来源。"""
    report = ScanReport()

    def _run(scanner) -> None:
        before = len(report.items)
        result = scanner(report.items)
        result.discovered = len(report.items) - before  # 以新增条目数为准，统一口径
        report.agents.append(result)

    _run(_scan_cc_switch)
    _run(_scan_claude)
    _run(_scan_codex)
    _run(_scan_opencode)
    _run(_scan_zcode)
    report.agents.extend(_scan_report_only())

    logger.info(
        "本机订阅扫描完成：条目 %d，来源 %s",
        len(report.items),
        {a.agent: a.discovered for a in report.agents},
    )
    return report

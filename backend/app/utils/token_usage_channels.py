"""调用渠道（Token Usage channel）解析与展示名注册表

职责：
1. 把各 Agent 的原始渠道标识（providerID / provider_id / 模型前缀 / provider）
   归一化为稳定的渠道 id；
2. 把 ``base_url`` host 映射为渠道 id（用于没有逐条渠道的 Agent）；
3. 为没有逐条渠道的 Agent 读取**本机当前配置**（Claude / Codex / MiniMax /
   cc-switch 当前项）解析渠道；
4. 提供渠道展示名（原始 id 入库，展示名集中在这里计算，改名不用重采集）。

边界（用户明确要求）：
* 聚合网关（peanut / magpie 等）只统计到网关本身，**不**深挖上游真实账号；
* 拿不到就返回 ``unknown``，不猜测、不编造。

注意：本模块只读取配置中的 ``base_url`` / provider 名称等非敏感字段，
绝不读取或打印 API Key。
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import urllib.parse
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

UNKNOWN_CHANNEL = "unknown"

#: 渠道原始 id → 展示名
CHANNEL_DISPLAY: dict[str, str] = {
    "peanut": "花生 TokenProxy",
    "aliyun-bailian": "阿里云百炼",
    "opencode": "OpenCode 官方",
    "deepseek": "DeepSeek 官方",
    "alibaba-coding-plan-cn": "阿里云 Coding Plan",
    "minimax-cn-coding-plan": "MiniMax Coding Plan",
    "magpie": "Magpie 本地网关",
    "open-design": "OpenDesign",
    "kimi-code": "Kimi 官方",
    "zhipu": "智谱 GLM 官方",
    "new-provider": "其他供应商（ZCode）",
    "claude-official": "Claude 官方",
    "codex-official": "Codex 官方",
    "copilot-official": "GitHub Copilot",
    "gemini-official": "Gemini 官方",
    "minimax-official": "MiniMax 官方",
    "local-gateway": "本地网关",
    UNKNOWN_CHANNEL: "未知渠道",
}

#: 各 Agent 没有逐条渠道时的官方默认渠道
SOURCE_DEFAULT_CHANNEL: dict[str, str] = {
    "claude": "claude-official",
    "codex": "codex-official",
    "copilot": "copilot-official",
    "gemini": "gemini-official",
    "minimax": "minimax-official",
    "kimi": "kimi-code",
    "zcode": "zhipu",
    "opencode": "opencode",
    "paseo": UNKNOWN_CHANNEL,
    "openclaw": UNKNOWN_CHANNEL,
}

#: 原始 provider 值（大小写不敏感）→ 渠道 id
_PROVIDER_ALIASES: dict[str, str] = {
    # 官方 / 常见 provider id
    "anthropic": "claude-official",
    "claude": "claude-official",
    "openai": "codex-official",
    "codex": "codex-official",
    "google": "gemini-official",
    "gemini": "gemini-official",
    "github": "copilot-official",
    "github-copilot": "copilot-official",
    "copilot": "copilot-official",
    "moonshot": "kimi-code",
    "moonshot-cn": "kimi-code",
    "kimi": "kimi-code",
    "kimi-code": "kimi-code",
    "kimi-code-cn": "kimi-code",
    "zhipu": "zhipu",
    "z-ai": "zhipu",
    "zai": "zhipu",
    "bigmodel": "zhipu",
    "deepseek": "deepseek",
    "minimax": "minimax-official",
    "minimax-cn": "minimax-official",
    "opencode": "opencode",
    "opencode-go": "opencode",
    "peanut": "peanut",
    "aliyun-bailian": "aliyun-bailian",
    "bailian": "aliyun-bailian",
    "dashscope": "aliyun-bailian",
    "alibaba-coding-plan-cn": "alibaba-coding-plan-cn",
    "minimax-cn-coding-plan": "minimax-cn-coding-plan",
    "magpie": "magpie",
    "open-design": "open-design",
    "opendesign": "open-design",
}

#: base_url host 后缀 → 渠道 id（按顺序匹配）
_HOST_CHANNELS: tuple[tuple[str, str], ...] = (
    ("tokenproxy.peanuthzm.com.cn", "peanut"),
    ("aliyuncs.com", "aliyun-bailian"),
    ("dashscope.aliyun.com", "aliyun-bailian"),
    ("api.kimi.com", "kimi-code"),
    ("api.moonshot.cn", "kimi-code"),
    ("api.moonshot.ai", "kimi-code"),
    ("open.bigmodel.cn", "zhipu"),
    ("api.z.ai", "zhipu"),
    ("opencode.ai", "opencode"),
    ("api.deepseek.com", "deepseek"),
    ("api.minimaxi.com", "minimax-official"),
    ("api.minimax.io", "minimax-official"),
    ("amr-link.open-design.ai", "open-design"),
    ("open-design.ai", "open-design"),
)

#: cc-switch 供应商名称关键词 → 渠道 id（只用于当前生效项的兜底）
_NAME_HINTS: tuple[tuple[str, str], ...] = (
    ("peanut", "peanut"),
    ("kimi", "kimi-code"),
    ("zhipu", "zhipu"),
    ("glm", "zhipu"),
    ("minimax", "minimax-official"),
    ("deepseek", "deepseek"),
    ("opendesign", "open-design"),
    ("open-design", "open-design"),
    ("bailian", "aliyun-bailian"),
    ("百炼", "aliyun-bailian"),
    ("opencode", "opencode"),
)

_MAX_CHANNEL_LEN = 64

#: 单次同步内的配置解析缓存（同步开始时 reset，配置变化后下一轮重新读取）
_config_channel_cache: dict[str, str] = {}


def reset_channel_cache() -> None:
    """清空配置解析缓存（每次同步开始时调用）。"""
    _config_channel_cache.clear()


def normalize_channel(value: Optional[str], source: Optional[str] = None) -> str:
    """把原始渠道标识归一化为渠道 id。

    规则：
    * 空值 → ``SOURCE_DEFAULT_CHANNEL[source]``，无 source 时 ``unknown``；
    * 命中别名表 → 对应渠道 id；
    * 其余原样保留（截断到 64 字符），保证可追溯。
    """
    raw = (value or "").strip()
    if not raw:
        return SOURCE_DEFAULT_CHANNEL.get(source or "", UNKNOWN_CHANNEL)

    alias = _PROVIDER_ALIASES.get(raw.lower())
    if alias:
        return alias

    # ZCode 的 account:bigmodel-* 是账号级套餐，统一归为 zhipu，
    # 展示名再由 channel_display_name 展开套餐后缀。
    if raw.lower().startswith("account:bigmodel"):
        return raw[:_MAX_CHANNEL_LEN]

    return raw[:_MAX_CHANNEL_LEN]


def channel_display_name(channel: Optional[str]) -> str:
    """渠道展示名：注册表优先，原始 id 兜底。"""
    raw = (channel or "").strip()
    if not raw or raw == UNKNOWN_CHANNEL:
        return CHANNEL_DISPLAY[UNKNOWN_CHANNEL]
    if raw in CHANNEL_DISPLAY:
        return CHANNEL_DISPLAY[raw]
    if raw.lower().startswith("account:bigmodel"):
        suffix = raw.split(":", 1)[1]
        suffix = suffix[len("bigmodel"):].lstrip("-")
        return f"智谱 GLM（{suffix or '官方套餐'}）"
    return raw


def channel_from_base_url(base_url: Optional[str]) -> Optional[str]:
    """从 base_url 解析渠道 id；无法解析返回 None。"""
    if not base_url or not isinstance(base_url, str):
        return None
    text = base_url.strip()
    if not text:
        return None
    try:
        host = urllib.parse.urlparse(text).hostname or ""
    except ValueError:
        return None
    host = host.lower()
    if not host:
        return None
    if host in ("localhost", "127.0.0.1", "::1"):
        return "local-gateway"
    for suffix, channel in _HOST_CHANNELS:
        if host == suffix or host.endswith("." + suffix) or host.endswith(suffix):
            return channel
    return None


def _real_home() -> Path:
    from app.config.config import REAL_HOME

    return Path(REAL_HOME)


def _read_json(path: Path) -> Optional[dict]:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _iter_base_urls(value) -> list[str]:
    """递归提取配置中的 base_url 类字段（只取 URL，不碰 Key）。"""
    urls: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in ("base_url", "baseurl", "base-url") and isinstance(item, str):
                urls.append(item)
            else:
                urls.extend(_iter_base_urls(item))
    elif isinstance(value, list):
        for item in value:
            urls.extend(_iter_base_urls(item))
    return urls


def _channel_from_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    lowered = name.lower()
    for hint, channel in _NAME_HINTS:
        if hint in lowered:
            return channel
    return None


def _ccswitch_db_path() -> Path:
    configured = os.environ.get("CCSWITCH_DB", "").strip()
    if configured:
        return Path(configured)
    return _real_home() / ".cc-switch" / "cc-switch.db"


def _resolve_from_ccswitch(app_type: str) -> Optional[str]:
    """读取 cc-switch 当前生效项（只读、只取名称/base_url）。"""
    path = _ccswitch_db_path()
    if not path.is_file():
        return None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=3)
    except sqlite3.Error:
        return None
    try:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT name, settings_config FROM providers "
            "WHERE app_type = ? AND is_current = 1 LIMIT 1",
            (app_type,),
        ).fetchone()
        if not row:
            return None
        settings = None
        try:
            settings = json.loads(row["settings_config"] or "{}")
        except (TypeError, ValueError):
            settings = None
        for url in _iter_base_urls(settings):
            channel = channel_from_base_url(url)
            if channel:
                return channel
        return _channel_from_name(row["name"])
    except sqlite3.Error as exc:
        logger.debug("[channel] 读取 cc-switch 失败: %s", exc)
        return None
    finally:
        conn.close()


def _resolve_claude() -> str:
    home = _real_home()
    settings = _read_json(home / ".claude" / "settings.json") or {}
    env = settings.get("env") if isinstance(settings.get("env"), dict) else {}
    channel = channel_from_base_url(env.get("ANTHROPIC_BASE_URL"))
    if channel:
        return channel
    return _resolve_from_ccswitch("claude") or "claude-official"


def _resolve_codex() -> str:
    home = _real_home()
    config_path = home / ".codex" / "config.toml"
    if config_path.is_file():
        try:
            try:
                import tomllib  # Python 3.11+
            except ImportError:  # pragma: no cover
                tomllib = None  # type: ignore[assignment]
            if tomllib is not None:
                with config_path.open("rb") as handle:
                    config = tomllib.load(handle)
                provider_id = config.get("model_provider")
                providers = config.get("model_providers")
                if isinstance(providers, dict):
                    if provider_id and isinstance(providers.get(provider_id), dict):
                        channel = channel_from_base_url(
                            providers[provider_id].get("base_url")
                        )
                        if channel:
                            return channel
                    for provider in providers.values():
                        if isinstance(provider, dict):
                            channel = channel_from_base_url(provider.get("base_url"))
                            if channel:
                                return channel
        except (OSError, ValueError, TypeError) as exc:
            logger.debug("[channel] 读取 codex 配置失败: %s", exc)
    return _resolve_from_ccswitch("codex") or "codex-official"


def _resolve_minimax() -> str:
    home = _real_home()
    config_path = home / ".minimax" / "config.yaml"
    if config_path.is_file():
        try:
            import yaml  # type: ignore

            with config_path.open("r", encoding="utf-8", errors="replace") as handle:
                config = yaml.safe_load(handle) or {}
            for url in _iter_base_urls(config):
                channel = channel_from_base_url(url)
                if channel:
                    return channel
        except (OSError, ValueError, TypeError, ImportError) as exc:
            logger.debug("[channel] 读取 minimax 配置失败: %s", exc)
    return "minimax-official"


def _resolve_kimi_default() -> str:
    """Kimi 配置里的 default_model 前缀（无逐条前缀时的兜底）。"""
    home = _real_home()
    config_path = home / ".kimi-code" / "config.toml"
    if config_path.is_file():
        try:
            try:
                import tomllib
            except ImportError:  # pragma: no cover
                tomllib = None  # type: ignore[assignment]
            if tomllib is not None:
                with config_path.open("rb") as handle:
                    config = tomllib.load(handle)
                default_model = config.get("default_model")
                if isinstance(default_model, str) and "/" in default_model:
                    prefix = default_model.split("/", 1)[0]
                    return normalize_channel(prefix, "kimi")
        except (OSError, ValueError, TypeError) as exc:
            logger.debug("[channel] 读取 kimi 配置失败: %s", exc)
    return "kimi-code"


def resolve_config_channel(source: str) -> str:
    """解析没有逐条渠道的 Agent 的当前渠道（带单次同步缓存）。"""
    source = (source or "").lower()
    if source in _config_channel_cache:
        return _config_channel_cache[source]

    try:
        if source == "claude":
            channel = _resolve_claude()
        elif source == "codex":
            channel = _resolve_codex()
        elif source == "minimax":
            channel = _resolve_minimax()
        elif source == "kimi":
            channel = _resolve_kimi_default()
        else:
            channel = SOURCE_DEFAULT_CHANNEL.get(source, UNKNOWN_CHANNEL)
    except Exception as exc:  # 配置读取失败不阻断同步
        logger.warning("[channel] %s 渠道解析失败，按 unknown 处理: %s", source, exc)
        channel = UNKNOWN_CHANNEL

    _config_channel_cache[source] = channel
    return channel


def split_model_provider_prefix(model: str, source: str) -> tuple[str, str]:
    """拆分 ``provider/model`` 形式的模型名，返回 ``(channel, model)``。

    仅用于 Kimi：其 wire 记录用模型名前缀表示渠道（如 ``peanut/claude-opus-5.0``）。
    没有前缀时按 source 默认渠道处理。
    """
    raw = (model or "").strip()
    if "/" in raw:
        prefix, rest = raw.split("/", 1)
        rest = rest.strip()
        if prefix and rest:
            return normalize_channel(prefix, source), rest
    return normalize_channel(None, source), raw
"""从 ZCode 的 provider_config.json 发现明文 API Key

ZCode 在 `~/.zcode/v2/provider_config.json` 里保存它自己配置的供应商：

```json
{"config": {"providerConfigRules": {"providerRules": [
  {"providerId": "kimi-code-cn", "providerName": "Kimi Code（国内）",
   "config": {"access": {"type": "api-key", "apiKey": "..."},
              "api": {"type": "openai-responses", "baseUrl": "https://..."}}}
]}}}
```

这些 Key 是**明文**（不像 credentials.json 里那样加密），因此即使后端以
服务账户（LocalSystem）运行也能读到 —— 这是「本机 ZCode 已配置即可查额度」
最可靠的一条路径。

只做只读取；映射到本工具的供应商注册表 id。
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

#: ZCode providerId / providerName 关键词 → 本工具 registry 的 provider_id
_PROVIDER_HINTS: tuple[tuple[str, str], ...] = (
    ("kimi", "kimi"),
    ("minimax", "minimax"),
    ("open-design", "opendesign"),
    ("opendesign", "opendesign"),
    ("bigmodel", "zhipu"),
    ("zhipu", "zhipu"),
    ("siliconflow", "siliconflow"),
    ("openrouter", "openrouter"),
    ("deepseek", "deepseek"),
    ("stepfun", "stepfun"),
    ("novita", "novita"),
    ("ollama", "ollama_cloud"),
    ("zenmux", "zenmux"),
    ("commandcode", "command_code"),
)


@dataclass
class DiscoveredKey:
    """一条从 ZCode 配置里读到的 Key"""

    provider_id: str
    zcode_provider_id: str
    label: str
    api_key: str
    base_url: Optional[str] = None
    region: str = "cn"


def _config_path() -> Path:
    from app.config.config import REAL_HOME

    return Path(REAL_HOME) / ".zcode" / "v2" / "provider_config.json"


def _match_provider(*candidates: str) -> Optional[str]:
    """按关键词把 ZCode 的 provider 映射到本工具的 provider_id"""
    for text in candidates:
        if not text:
            continue
        lowered = str(text).lower()
        for hint, provider_id in _PROVIDER_HINTS:
            if hint in lowered:
                return provider_id
    return None


def _region_of(base_url: Optional[str], provider_hint: str) -> str:
    text = f"{base_url or ''} {provider_hint}".lower()
    if "minimax.io" in text or "kimi.ai" in text or "api.z.ai" in text or "siliconflow.com" in text:
        return "intl"
    return "cn"


def read_provider_keys() -> list[DiscoveredKey]:
    """读取 ZCode provider_config.json 里所有明文 Key。

    返回去重后的列表（同一 provider 只保留第一条有效 Key）。
    """
    path = _config_path()
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("读取 ZCode provider_config.json 失败: %s", exc)
        return []

    rules = (
        data.get("config", {}).get("providerConfigRules", {}).get("providerRules", [])
        if isinstance(data, dict)
        else []
    )
    if not isinstance(rules, list):
        return []

    discovered: list[DiscoveredKey] = []
    seen: set[str] = set()

    for rule in rules:
        if not isinstance(rule, dict):
            continue
        zcode_id = str(rule.get("providerId") or "")
        zcode_name = str(rule.get("providerName") or "")
        cfg = rule.get("config") or {}
        if not isinstance(cfg, dict):
            continue

        access = cfg.get("access")
        if not isinstance(access, dict):
            continue
        if str(access.get("type") or "") not in ("api-key", "api_key", ""):
            continue
        api_key = access.get("apiKey")
        if not isinstance(api_key, str) or not api_key.strip():
            continue

        provider_id = _match_provider(zcode_id, zcode_name)
        if provider_id is None:
            logger.debug("ZCode provider %s 未匹配到本工具的供应商，跳过", zcode_id)
            continue
        if provider_id in seen:
            continue

        api = cfg.get("api") if isinstance(cfg.get("api"), dict) else {}
        base_url = api.get("baseUrl") if isinstance(api.get("baseUrl"), str) else None

        seen.add(provider_id)
        discovered.append(
            DiscoveredKey(
                provider_id=provider_id,
                zcode_provider_id=zcode_id,
                label=f"{zcode_name or provider_id}（ZCode 配置）",
                api_key=api_key.strip(),
                base_url=base_url,
                region=_region_of(base_url, zcode_id),
            )
        )

    logger.info("从 ZCode 配置发现 %d 个可用供应商: %s", len(discovered), [d.provider_id for d in discovered])
    return discovered

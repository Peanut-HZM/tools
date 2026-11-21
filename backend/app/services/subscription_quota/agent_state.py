"""读回 agent 的**真实当前配置**（用于判断切换是否真的生效）

为什么需要它：切换后如果只看我们自己的「切换记录表」，配置被人手改回去、
或写入字段没被 agent 采用时，页面仍会显示成功——那就是假切换。
本模块直接解析 agent 的配置文件，取出 base_url / api_key / model，
再用统一的 (base_url_norm, sha256(api_key)) 去重键与订阅账号比对，
从而回答「这台机器上该 agent 现在真正在用哪一条订阅」。

只读实现：不写任何文件；解析失败只返回 error，不抛异常。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

from app.services.agent_hub.agent_writers import (
    claude_settings_path,
    codex_home_dir,
    hermes_config_path,
    real_home,
)
from app.services.subscription_quota.url_norm import normalize_base_url

try:  # 与写入器共用同一套解析库（缺库时降级为空结果，不阻断页面）
    import tomlkit
except Exception:  # pragma: no cover - 依赖缺失时降级
    tomlkit = None

try:
    from ruamel.yaml import YAML
except Exception:  # pragma: no cover
    YAML = None


@dataclass
class AgentCurrent:
    """agent 真实的当前配置（已脱敏：api_key 不回传前端）"""

    agent: str
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    source_files: list[str] = field(default_factory=list)
    error: str = ""

    def to_public_dict(self) -> dict:
        return {
            "agent": self.agent,
            "baseUrl": self.base_url,
            "hasKey": bool(self.api_key),
            "model": self.model,
            "sourceFiles": list(self.source_files),
            "error": self.error,
        }


def _read_json(path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"解析 {path.name} 失败: {exc}") from exc


def _read_toml(path):
    if tomlkit is None:
        raise ValueError("缺少 tomlkit，无法解析 TOML")
    try:
        return tomlkit.parse(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"解析 {path.name} 失败: {exc}") from exc


def _read_env(path) -> dict:
    out: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            out[key.strip()] = value.strip().strip('"').strip("'")
    except Exception as exc:
        raise ValueError(f"解析 {path.name} 失败: {exc}") from exc
    return out


def _claude_desktop_path():
    from app.services.subscription_quota.agent_catalog import claude_desktop_config_path

    return claude_desktop_config_path()


def read_agent_current(agent: str) -> AgentCurrent:
    """解析该 agent 的配置文件，返回真实 base_url / api_key / model"""
    home = real_home()
    current = AgentCurrent(agent=agent)
    try:
        if agent == "claude":
            path = claude_settings_path()
            if not path.exists():
                current.error = f"未找到 {path}"
                return current
            data = _read_json(path)
            env = data.get("env") if isinstance(data.get("env"), dict) else {}
            current.base_url = str(env.get("ANTHROPIC_BASE_URL") or "")
            current.api_key = str(env.get("ANTHROPIC_AUTH_TOKEN") or env.get("ANTHROPIC_API_KEY") or "")
            model = data.get("model")
            current.model = str(model) if isinstance(model, str) else ""
            current.source_files = [str(path)]

        elif agent == "claude-desktop":
            path = _claude_desktop_path()
            if not path.exists():
                current.error = "未找到 claude_desktop_config.json"
                return current
            data = _read_json(path)
            mode = str(data.get("deploymentMode") or "")
            cfg = data.get("enterpriseConfig") if isinstance(data.get("enterpriseConfig"), dict) else {}
            current.base_url = str(cfg.get("baseUrl") or cfg.get("base_url") or "")
            current.api_key = str(cfg.get("apiKey") or cfg.get("api_key") or "")
            current.model = mode
            current.source_files = [str(path)]

        elif agent == "codex":
            codex_dir = codex_home_dir()
            toml_path = codex_dir / "config.toml"
            auth_path = codex_dir / "auth.json"
            if not toml_path.exists():
                current.error = f"未找到 {toml_path}"
                return current
            doc = _read_toml(toml_path)
            provider_id = str(doc.get("model_provider") or "")
            providers = doc.get("model_providers") or {}
            node = providers.get(provider_id) if provider_id else None
            if node is not None:
                current.base_url = str(node.get("base_url") or "")
            current.model = str(doc.get("model") or "")
            if auth_path.exists():
                try:
                    auth = _read_json(auth_path)
                    current.api_key = str(auth.get("OPENAI_API_KEY") or "")
                except ValueError:
                    pass
            current.source_files = [str(toml_path), str(auth_path)]

        elif agent == "gemini":
            env_path = home / ".gemini" / ".env"
            if not env_path.exists():
                current.error = "未找到 ~/.gemini/.env"
                return current
            env = _read_env(env_path)
            current.base_url = str(env.get("GOOGLE_GEMINI_BASE_URL") or "")
            current.api_key = str(env.get("GEMINI_API_KEY") or "")
            current.source_files = [str(env_path)]

        elif agent == "kimi":
            path = home / ".kimi-code" / "config.toml"
            if not path.exists():
                current.error = "未找到 ~/.kimi-code/config.toml"
                return current
            doc = _read_toml(path)
            providers = doc.get("providers") or {}
            if providers:
                first_key = next(iter(providers.keys()))
                block = providers[first_key]
                current.api_key = str(block.get("api_key") or "")
                current.base_url = str(block.get("base_url") or "")
            current.model = str(doc.get("model") or "")
            current.source_files = [str(path)]

        elif agent == "opencode":
            path = home / ".config" / "opencode" / "opencode.json"
            if not path.exists():
                current.error = "未找到 ~/.config/opencode/opencode.json"
                return current
            data = _read_json(path)
            model = str(data.get("model") or "")
            provider_id = model.split("/", 1)[0] if "/" in model else ""
            providers = data.get("provider") if isinstance(data.get("provider"), dict) else {}
            node = providers.get(provider_id) if provider_id else None
            if node is None and providers:
                node = providers.get(next(iter(providers.keys())))
            if isinstance(node, dict):
                options = node.get("options") if isinstance(node.get("options"), dict) else {}
                current.base_url = str(options.get("baseURL") or options.get("base_url") or "")
                current.api_key = str(options.get("apiKey") or options.get("api_key") or "")
            current.model = model
            current.source_files = [str(path)]

        elif agent == "minimax":
            path = home / ".minimax" / "config.yaml"
            if not path.exists() or YAML is None:
                current.error = "未找到 ~/.minimax/config.yaml（或缺 ruamel.yaml）"
                return current
            yaml_rt = YAML()
            data = yaml_rt.load(path.read_text(encoding="utf-8")) or {}
            model = str(data.get("model") or "")
            provider_id = model.split("/", 1)[0] if "/" in model else ""
            providers = data.get("provider") if isinstance(data.get("provider"), dict) else {}
            node = providers.get(provider_id) if provider_id else None
            if node is None and providers:
                node = providers.get(next(iter(providers.keys())))
            if isinstance(node, dict):
                options = node.get("options") if isinstance(node.get("options"), dict) else {}
                current.base_url = str(options.get("baseURL") or "")
                current.api_key = str(options.get("apiKey") or "")
            current.model = model
            current.source_files = [str(path)]

        elif agent == "pi":
            pi_dir = home / ".pi" / "agent"
            models_path = pi_dir / "models.json"
            settings_path = pi_dir / "settings.json"
            current.source_files = [str(p) for p in (models_path, settings_path) if p.exists()]
            if not models_path.exists():
                current.error = "未找到 ~/.pi/agent/models.json"
                return current
            data = _read_json(models_path)
            settings = {}
            if settings_path.exists():
                try:
                    settings = _read_json(settings_path)
                except ValueError:
                    settings = {}
            provider_id = str(settings.get("defaultProvider") or "")
            current.model = str(settings.get("defaultModel") or "")
            providers = data.get("providers") if isinstance(data.get("providers"), dict) else {}
            node = providers.get(provider_id) if provider_id else None
            if not isinstance(node, dict) and providers:
                node = providers.get(next(iter(providers.keys())))
            if isinstance(node, dict):
                current.base_url = str(node.get("baseUrl") or node.get("base_url") or "")
                current.api_key = str(node.get("apiKey") or node.get("api_key") or "")

        elif agent == "hermes":
            path = hermes_config_path()
            if not path.exists() or YAML is None:
                current.error = "未找到 Hermes config.yaml（或缺 ruamel.yaml）"
                return current
            yaml_rt = YAML()
            data = yaml_rt.load(path.read_text(encoding="utf-8")) or {}
            providers = data.get("providers") if isinstance(data.get("providers"), dict) else {}
            node = providers.get("agent-hub")
            if not isinstance(node, dict) and providers:
                node = providers.get(next(iter(providers.keys())))
            if isinstance(node, dict):
                current.base_url = str(node.get("base_url") or node.get("baseUrl") or "")
                current.api_key = str(node.get("api_key") or node.get("apiKey") or "")
                models = node.get("models")
                if isinstance(models, list) and models:
                    current.model = str((models[0] or {}).get("id") or "")
            current.source_files = [str(path)]

        elif agent == "kiro":
            kiro_dir = home / ".kiro"
            current.source_files = [str(kiro_dir)] if kiro_dir.exists() else []
            current.error = "Kiro 使用 AWS 登录，无 API Key 配置"

        else:
            current.error = f"未支持的 agent: {agent}"
    except ValueError as exc:
        current.error = str(exc)
    except Exception as exc:  # 任何解析异常都不影响其他卡片
        current.error = f"读取失败: {exc}"
    return current


def match_account(current: AgentCurrent, accounts) -> Optional[dict]:
    """把真实配置匹配到订阅账号（同 base_url + 同 Key 才算命中）"""
    if not current.api_key:
        return None
    from app.services.subscription_quota.dedupe import sha256_hex

    target_key = (normalize_base_url(current.base_url), sha256_hex(current.api_key))
    for account in accounts:
        if not account.api_key:
            continue
        candidate = (normalize_base_url(account.base_url), sha256_hex(account.api_key))
        if candidate == target_key:
            return {
                "accountId": account.id,
                "providerId": account.provider_id,
                "label": account.label,
                "matched": True,
            }
    return None
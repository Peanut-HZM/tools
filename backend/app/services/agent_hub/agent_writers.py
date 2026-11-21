"""Agent Hub 配置写入器 — 把选中的 provider 写入各 agent 的本地配置。

设计原则（对齐 cc-switch 的 "floor" 概念 + magpie 的原子改写）：
- 只改关键字段（floor），其余内容不动（TOML/YAML 用保格式库 round-trip）
- 首写备份：每个文件第一次被改前完整备份，之后不再覆盖（保留最初状态，可一键恢复）
- 原子写：临时文件 + os.replace
- 凭据路径一律 REAL_HOME（config.py 覆盖 HOME 的场景下仍取真实家目录）
"""
import json
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import tomlkit
except ImportError:  # pragma: no cover - requirements 已声明，测试环境兜底提示
    tomlkit = None

try:
    from ruamel.yaml import YAML
except ImportError:  # pragma: no cover
    YAML = None


class AgentWriterError(Exception):
    """写入失败（文件缺失/格式错误/库缺失）。"""


@dataclass
class WriteTarget:
    """一次切换的输入。"""
    agent: str
    name: str          # 供应商展示名
    base_url: str
    api_key: str
    model: str = ""    # 可选：模型名（空则不改模型字段）


SUPPORTED_AGENTS = ["claude", "codex", "gemini", "kimi", "opencode", "minimax"]

# agent -> 需要备份/写入的文件（相对 REAL_HOME）
AGENT_FILES: Dict[str, List[str]] = {
    "claude": [".claude/settings.json"],
    "codex": [".codex/config.toml", ".codex/auth.json"],
    "gemini": [".gemini/.env", ".gemini/settings.json"],
    "kimi": [".kimi-code/config.toml"],
    "opencode": [".config/opencode/opencode.json"],
    "minimax": [".minimax/config.yaml"],
}


def real_home() -> Path:
    from app.config.config import REAL_HOME
    return Path(REAL_HOME)


def claude_config_dir() -> Path:
    """Claude Code 配置目录：遵循 ``CLAUDE_CONFIG_DIR``（否则 ~/.claude）

    很多用户（含本机）把配置放在别的盘，写死 ~/.claude 会变成「假切换」。
    """
    raw = (os.environ.get("CLAUDE_CONFIG_DIR") or "").strip()
    return Path(raw) if raw else real_home() / ".claude"


def claude_settings_path() -> Path:
    return claude_config_dir() / "settings.json"


def codex_home_dir() -> Path:
    """Codex 配置目录：遵循 ``CODEX_HOME``（否则 ~/.codex）"""
    raw = (os.environ.get("CODEX_HOME") or "").strip()
    return Path(raw) if raw else real_home() / ".codex"


def _backup_dir() -> Path:
    """备份根目录：backend/data/agent_hub/backups/（数据目录，不入库）。"""
    base = Path(__file__).resolve().parents[3] / "data" / "agent_hub" / "backups"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _first_write_backup(
    agent: str, rel_path: str, content: bytes, source_path: Optional[Path] = None
) -> Optional[str]:
    """首写备份：同 agent+文件只备份一次（保留最初原始状态）。

    ``source_path`` 记录原始绝对路径（配置可能在 CLAUDE_CONFIG_DIR / CODEX_HOME 等
    非默认位置），恢复时优先按它写回；未提供时退回按 ``rel_path`` 拼 REAL_HOME（旧行为）。
    """
    backup_root = _backup_dir() / agent
    backup_root.mkdir(parents=True, exist_ok=True)
    safe_name = rel_path.replace("/", "__").replace("\\", "__").replace(":", "_")
    target = backup_root / safe_name
    if target.exists():
        return None
    target.write_bytes(content)
    if source_path is not None:
        target.with_name(target.name + ".src").write_text(str(source_path), encoding="utf-8")
    return str(target)


def _atomic_write(path: Path, text: str) -> None:
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        os.replace(tmp_name, path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def restore_agent_backups(agent: str) -> List[str]:
    """把该 agent 的首写备份恢复回原位。返回恢复的文件清单。"""
    backup_root = _backup_dir() / agent
    restored: List[str] = []
    if not backup_root.exists():
        return restored
    home = real_home()
    for backup_file in backup_root.iterdir():
        if backup_file.name.endswith(".src"):
            continue
        src_file = backup_file.with_name(backup_file.name + ".src")
        if src_file.exists():
            target = Path(src_file.read_text(encoding="utf-8").strip())
        else:
            rel_path = backup_file.name.replace("__", "/")
            target = home / rel_path
        if not target.parent.exists():
            continue
        shutil.copy2(backup_file, target)
        restored.append(str(target))
    return restored


def preview_changes(agent: str, target: WriteTarget) -> Dict[str, Any]:
    """切换前预览：目标文件、是否存在、将要写入的关键字段（dry-run 不落盘）。"""
    home = real_home()
    files = AGENT_FILES.get(agent)
    if files is None:
        raise AgentWriterError(f"不支持的 agent: {agent}")
    out: Dict[str, Any] = {"agent": agent, "files": [], "floor": _floor_preview(agent, target)}
    for rel in files:
        path = home / rel
        out["files"].append({
            "path": str(path),
            "exists": path.exists(),
            "backed_up": (_backup_dir() / agent / rel.replace("/", "__").replace("\\", "__")).exists(),
        })
    return out


def _floor_preview(agent: str, target: WriteTarget) -> Dict[str, Any]:
    if agent == "claude":
        return {"env.ANTHROPIC_BASE_URL": target.base_url,
                "env.ANTHROPIC_AUTH_TOKEN": "***", "env.ANTHROPIC_API_KEY": "(移除)"}
    if agent == "codex":
        return {"config.toml:model_provider": "custom",
                "config.toml:model_providers.custom.base_url": target.base_url,
                "auth.json:OPENAI_API_KEY": "***"}
    if agent == "gemini":
        return {".env:GEMINI_API_KEY": "***", ".env:GOOGLE_GEMINI_BASE_URL": target.base_url}
    if agent == "kimi":
        return {"config.toml:providers.<managed>.api_key": "***",
                "config.toml:providers.<managed>.base_url": target.base_url}
    if agent == "opencode":
        return {"provider.<id>.options.baseURL": target.base_url,
                "provider.<id>.options.apiKey": "***"}
    if agent == "minimax":
        return {"provider.<id>.options.baseURL": target.base_url,
                "provider.<id>.options.apiKey": "***"}
    return {}


# ---------------------------------------------------------------------------
# 各格式小工具
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _dump_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _load_toml(path: Path) -> "tomlkit.TOMLDocument":
    if tomlkit is None:
        raise AgentWriterError("缺少 tomlkit 依赖（requirements.txt 已声明），请先安装")
    return tomlkit.parse(path.read_text(encoding="utf-8"))


def _patch_env_lines(text: str, updates: Dict[str, str]) -> str:
    """逐行替换 .env 中指定键的值（保序保留其余行）；缺失键追加到末尾。"""
    seen = set()
    lines = text.splitlines()
    out = []
    for line in lines:
        stripped = line.strip()
        key = stripped.split("=", 1)[0].strip() if "=" in stripped and not stripped.startswith("#") else None
        if key and key in updates:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={value}")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# 各 agent 写入器
# ---------------------------------------------------------------------------

def _write_claude(target: WriteTarget) -> List[str]:
    path = claude_settings_path()
    if not path.exists():
        raise AgentWriterError(f"未找到 {path}，请先安装/初始化 Claude Code")
    original = path.read_bytes()
    _first_write_backup("claude", str(path), original, source_path=path)
    data = _load_json(path)
    env = data.setdefault("env", {})
    if target.base_url:
        env["ANTHROPIC_BASE_URL"] = target.base_url
    env["ANTHROPIC_AUTH_TOKEN"] = target.api_key
    env.pop("ANTHROPIC_API_KEY", None)  # AUTH_TOKEN 与 API_KEY 互斥（中转站用 AUTH_TOKEN）
    _atomic_write(path, _dump_json(data))
    return [str(path)]


def _write_codex(target: WriteTarget) -> List[str]:
    home = real_home()
    codex_dir = codex_home_dir()
    written: List[str] = []
    toml_path = codex_dir / "config.toml"
    if not toml_path.exists():
        raise AgentWriterError(f"未找到 {toml_path}，请先安装/初始化 Codex CLI")
    original = toml_path.read_bytes()
    _first_write_backup("codex", "config.toml", original, source_path=toml_path)
    doc = _load_toml(toml_path)
    doc["model_provider"] = "custom"
    if target.model:
        doc["model"] = target.model
    providers = doc.setdefault("model_providers", {})
    custom = providers.get("custom")
    if custom is None or not hasattr(custom, "append"):
        from tomlkit.items import Table
        custom = tomlkit.table()
        providers["custom"] = custom
    custom["name"] = target.name
    custom["base_url"] = target.base_url
    custom["wire_api"] = "responses"
    custom["requires_openai_auth"] = False
    _atomic_write(toml_path, tomlkit.dumps(doc))
    written.append(str(toml_path))

    # auth.json：第三方 key 写 OPENAI_API_KEY（官方 OAuth 场景 cc-switch 会暂存，v1 仅在
    # 用户显式切换到第三方时写入，并已有首写备份可恢复官方登录态）
    auth_path = codex_dir / "auth.json"
    auth_data: Dict[str, Any] = {}
    if auth_path.exists():
        _first_write_backup("codex", "auth.json", auth_path.read_bytes(), source_path=auth_path)
        try:
            auth_data = _load_json(auth_path)
        except ValueError:
            auth_data = {}
    auth_data["OPENAI_API_KEY"] = target.api_key
    _atomic_write(auth_path, _dump_json(auth_data))
    written.append(str(auth_path))
    return written


def _write_gemini(target: WriteTarget) -> List[str]:
    home = real_home()
    env_path = home / ".gemini" / ".env"
    if env_path.exists():
        _first_write_backup("gemini", ".gemini/.env", env_path.read_bytes(), source_path=env_path)
        text = env_path.read_text(encoding="utf-8")
    else:
        text = ""
    updates: Dict[str, str] = {}
    if target.api_key:
        updates["GEMINI_API_KEY"] = target.api_key
    if target.base_url:
        updates["GOOGLE_GEMINI_BASE_URL"] = target.base_url
    if not updates:
        raise AgentWriterError("gemini 切换需要 api_key 或 base_url")
    _atomic_write(env_path, _patch_env_lines(text, updates))
    return [str(env_path)]


def _write_kimi(target: WriteTarget) -> List[str]:
    path = real_home() / ".kimi-code" / "config.toml"
    if not path.exists():
        raise AgentWriterError(f"未找到 {path}，请先安装/初始化 Kimi Code")
    original = path.read_bytes()
    _first_write_backup("kimi", ".kimi-code/config.toml", original, source_path=path)
    doc = _load_toml(path)
    providers = doc.get("providers") or {}
    if not providers:
        raise AgentWriterError("kimi config.toml 中未找到 providers 段")
    # floor：更新第一个 provider 块的 api_key/base_url（保留其余字段与 oauth）
    updated = False
    first_key = ""
    for _key, block in providers.items():
        if hasattr(block, "append") or isinstance(block, dict):
            block["api_key"] = target.api_key
            block["base_url"] = target.base_url
            first_key = str(_key)
            updated = True
            break
    if not updated:
        raise AgentWriterError("kimi providers 段结构不符合预期")
    # 指定了模型就同时选中它（kimi 的模型键形如 "<provider>/<model>"）
    if target.model:
        doc["model"] = target.model if "/" in target.model else f"{first_key}/{target.model}"
    _atomic_write(path, tomlkit.dumps(doc))
    return [str(path)]


_OPENCODE_NPM_BY_FORMAT = {
    "anthropic": "@ai-sdk/anthropic",
    "openai": "@ai-sdk/openai-compatible",
    "openai_chat": "@ai-sdk/openai-compatible",
}


def _write_opencode(target: WriteTarget, provider_kind: str = "") -> List[str]:
    path = real_home() / ".config" / "opencode" / "opencode.json"
    if not path.exists():
        raise AgentWriterError(f"未找到 {path}，请先安装/初始化 OpenCode")
    original = path.read_bytes()
    _first_write_backup("opencode", ".config/opencode/opencode.json", original, source_path=path)
    data = _load_json(path)
    providers = data.setdefault("provider", {})
    provider_id = "agent-hub"
    node = providers.get(provider_id)
    if node is None:
        node = {}
        providers[provider_id] = node
    node.setdefault("name", target.name)
    node["npm"] = _OPENCODE_NPM_BY_FORMAT.get(provider_kind, "@ai-sdk/anthropic")
    options = node.setdefault("options", {})
    if target.base_url:
        options["baseURL"] = target.base_url
    options["apiKey"] = target.api_key
    # 只写 provider 段不选模型 = 切换不生效（OpenCode 仍用旧 model）。
    # 因此这里必须把顶层 model 指向本 provider，否则按「假切换」拒绝执行。
    if not target.model:
        raise AgentWriterError(
            "OpenCode 切换必须同时指定模型名（会写成 model=<provider>/<model>），否则不会真正生效"
        )
    data["model"] = f"{provider_id}/{target.model}"
    _atomic_write(path, _dump_json(data))
    return [str(path)]


def _write_minimax(target: WriteTarget) -> List[str]:
    if YAML is None:
        raise AgentWriterError("缺少 ruamel.yaml 依赖（requirements.txt 已声明），请先安装")
    path = real_home() / ".minimax" / "config.yaml"
    if not path.exists():
        raise AgentWriterError(f"未找到 {path}，请先安装/初始化 MiniMax Code")
    original = path.read_bytes()
    _first_write_backup("minimax", ".minimax/config.yaml", original, source_path=path)
    yaml_rt = YAML()
    yaml_rt.preserve_quotes = True
    data = yaml_rt.load(path.read_text(encoding="utf-8"))
    providers = data.get("provider") or {}
    if not providers:
        raise AgentWriterError("minimax config.yaml 中未找到 provider 段")
    first_key = next(iter(providers.keys()))
    options = providers[first_key].get("options") or {}
    if target.base_url:
        options["baseURL"] = target.base_url
    options["apiKey"] = target.api_key
    # 同 OpenCode：不设置默认模型 = 不生效
    if not target.model:
        raise AgentWriterError(
            "MiniMax Code 切换必须同时指定模型名（会写成 model=<provider>/<model>），否则不会真正生效"
        )
    if "options" not in providers[first_key]:
        providers[first_key]["options"] = options
    data["model"] = f"{first_key}/{target.model}"
    import io
    buf = io.StringIO()
    yaml_rt.dump(data, buf)
    _atomic_write(path, buf.getvalue())
    return [str(path)]


def apply_provider_to_agent(agent: str, target: WriteTarget,
                            provider_kind: str = "") -> Dict[str, Any]:
    """统一入口：切换前备份 → 只写 floor 字段 → 原子写。返回写入文件清单。"""
    if agent not in SUPPORTED_AGENTS:
        raise AgentWriterError(f"不支持的 agent: {agent}（支持: {', '.join(SUPPORTED_AGENTS)}）")
    handlers = {
        "claude": _write_claude,
        "codex": _write_codex,
        "gemini": _write_gemini,
        "kimi": _write_kimi,
        "opencode": lambda t: _write_opencode(t, provider_kind),
        "minimax": _write_minimax,
    }
    written = handlers[agent](target)
    logger.info("Agent Hub 切换完成: agent=%s 写入=%s", agent, written)
    return {"agent": agent, "written": written}

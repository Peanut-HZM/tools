"""Agent 目录：哪些 agent 本机真的装了、各自能否写入

设计目标（用户 2026-11-21 要求）：

* **只列出已安装的** agent；未安装的只作为「添加 Agent」里的可选项
* Claude Code 的 **CLI 与桌面端分开**（两者配置文件不同）
* Codex 的桌面端与 CLI **共用 `~/.codex`** → 只保留一个条目（不拆）
* 能写入的才给「切换」；只能读的明确标注「仅检测」，绝不做假切换

检测路径全部基于 ``REAL_HOME``（config.py 覆盖 HOME 的场景下仍取真实家目录）。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from app.services.agent_hub.agent_writers import AGENT_FILES, real_home


@dataclass(frozen=True)
class AgentSpec:
    """一个 agent 的静态描述"""

    id: str
    name: str
    #: cli | desktop
    kind: str
    #: 判定「已安装」的路径（相对 REAL_HOME 或绝对路径；任一存在即算装了）
    detect: tuple[str, ...]
    #: 能否写入切换（False = 仅检测/仅展示）
    writable: bool = True
    #: 仅检测的原因（writable=False 时展示）
    readonly_reason: str = ""
    #: 说明（展示在卡片上）
    hint: str = ""
    #: 额外展示字段
    extra: dict = field(default_factory=dict)

    def to_public_dict(self) -> dict:
        return {
            "agent": self.id,
            "name": self.name,
            "kind": self.kind,
            "writable": self.writable,
            "readonlyReason": self.readonly_reason,
            "hint": self.hint,
            "files": list(AGENT_FILES.get(self.id, ())),
            "extra": dict(self.extra),
        }


#: Windows 下 Claude Desktop 的配置目录（相对 APPDATA）
_CLAUDE_DESKTOP_APPDATA = os.path.join("Claude", "claude_desktop_config.json")


def claude_desktop_config_path() -> "Path":
    """Claude Desktop 配置文件路径

    优先 ``APPDATA``（仅当它在真实家目录下，便于测试隔离）；
    否则回退 ``<REAL_HOME>/AppData/Roaming/Claude/...``。
    """
    home = Path(real_home())
    appdata = os.environ.get("APPDATA") or ""
    if appdata:
        appdata_path = Path(appdata)
        try:
            inside = appdata_path.is_relative_to(home)
        except AttributeError:  # Python < 3.9
            inside = str(appdata_path).lower().startswith(str(home).lower())
        if inside:
            return appdata_path / "Claude" / "claude_desktop_config.json"
    return home / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json"


def _desktop_config_abs() -> str:
    return str(claude_desktop_config_path())


def agent_specs() -> tuple[AgentSpec, ...]:
    """agent 目录（顺序即前端展示顺序）"""
    specs: list[AgentSpec] = [
        AgentSpec(
            id="claude",
            name="Claude Code CLI",
            kind="cli",
            detect=(".claude/settings.json", ".claude.json"),
            hint="写入 ~/.claude/settings.json 的 env（ANTHROPIC_BASE_URL / AUTH_TOKEN）",
        ),
        AgentSpec(
            id="claude-desktop",
            name="Claude Desktop",
            kind="desktop",
            detect=(_desktop_config_abs(),),
            writable=False,
            readonly_reason="桌面端第三方供应商需要 deploymentMode + enterpriseConfig，改错会导致桌面端无法启动；本次仅检测展示",
            hint="与 CLI 是两套配置（%APPDATA%\\Claude\\claude_desktop_config.json）",
            extra={"configPath": _desktop_config_abs()},
        ),
        AgentSpec(
            id="codex",
            name="Codex（CLI + 桌面端共用）",
            kind="cli",
            detect=(".codex/config.toml", ".codex/auth.json"),
            hint="桌面端与 CLI 共用 ~/.codex，无需分开；写入 model_provider + auth.json",
        ),
        AgentSpec(
            id="kimi",
            name="Kimi Code",
            kind="cli",
            detect=(".kimi-code/config.toml",),
            hint="写入 config.toml 的 providers 段并选中该供应商的模型",
        ),
        AgentSpec(
            id="opencode",
            name="OpenCode",
            kind="cli",
            detect=(".config/opencode/opencode.json", ".local/share/opencode/auth.json"),
            hint="写入 provider 段并设置顶层 model，确保真正生效",
        ),
        AgentSpec(
            id="minimax",
            name="MiniMax Code",
            kind="cli",
            detect=(".minimax/config.yaml", ".minimax"),
            hint="写入 provider options 并设置默认模型",
        ),
        AgentSpec(
            id="gemini",
            name="Gemini CLI",
            kind="cli",
            detect=(".gemini/.env", ".gemini/settings.json"),
            hint="写入 .gemini/.env 的 GEMINI_API_KEY / GOOGLE_GEMINI_BASE_URL",
        ),
        AgentSpec(
            id="pi",
            name="Pi",
            kind="cli",
            detect=(".pi", ".pi/oh-my-pi.jsonc"),
            writable=False,
            readonly_reason="Pi 使用 oh-my-pi.jsonc（JSONC 带注释），自动改写易破坏用户配置；本次仅检测展示",
            hint="检测到 .pi 即视为已安装",
        ),
        AgentSpec(
            id="kiro",
            name="Kiro",
            kind="cli",
            detect=(".kiro", ".kiro/settings"),
            writable=False,
            readonly_reason="Kiro 走 AWS 登录（非 API Key 供应商），不支持按 Key 切换",
            hint="检测到 .kiro 即视为已安装",
        ),
    ]
    return tuple(specs)


def _path_exists(raw: str) -> bool:
    if not raw:
        return False
    home = real_home()
    candidate = raw if os.path.isabs(raw) else str(home / raw)
    return os.path.exists(candidate)


def is_installed(spec: AgentSpec) -> bool:
    return any(_path_exists(path) for path in spec.detect)


def installed_agents() -> list[AgentSpec]:
    return [spec for spec in agent_specs() if is_installed(spec)]


def available_agents() -> list[AgentSpec]:
    return [spec for spec in agent_specs() if not is_installed(spec)]


def get_agent_spec(agent: str) -> Optional[AgentSpec]:
    for spec in agent_specs():
        if spec.id == agent:
            return spec
    return None
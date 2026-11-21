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

from app.services.agent_hub.agent_writers import (
    AGENT_FILES,
    claude_settings_path,
    codex_home_dir,
    real_home,
)


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


def claude_desktop_config_paths() -> tuple["Path", ...]:
    """Claude Desktop 配置文件的所有候选路径

    magpie 用 ``%LOCALAPPDATA%\\Claude``，旧版/部分安装用 ``%APPDATA%\\Claude``，
    两处都要检测，避免「装了却显示未安装」。
    """
    home = Path(real_home())
    candidates: list[Path] = []
    for env_key, default_rel in (
        ("LOCALAPPDATA", "AppData/Local/Claude/claude_desktop_config.json"),
        ("APPDATA", "AppData/Roaming/Claude/claude_desktop_config.json"),
    ):
        raw = os.environ.get(env_key) or ""
        # 只在环境变量位于真实家目录下时采信（测试/沙箱里 home 被替换时仍能隔离）
        if raw and _is_under(Path(raw), home):
            candidates.append(Path(raw) / "Claude" / "claude_desktop_config.json")
        else:
            candidates.append(home / default_rel)
    return tuple(candidates)


def _is_under(path: "Path", parent: "Path") -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except Exception:
        return False


def claude_desktop_config_path() -> "Path":
    """优先返回已存在的那个路径，否则返回第一个候选"""
    for candidate in claude_desktop_config_paths():
        if candidate.exists():
            return candidate
    return claude_desktop_config_paths()[0]


def _desktop_config_abs() -> str:
    return str(claude_desktop_config_path())


def _home(rel: str) -> str:
    """相对 REAL_HOME 的绝对路径（检测用）"""
    return str(real_home() / rel)


def agent_specs() -> tuple[AgentSpec, ...]:
    """agent 目录（顺序即前端展示顺序）

    覆盖范围对齐 magpie / cc-switch 的 agent 清单：能可靠写入的标 writable，
    其余只做**检测展示**（只读），绝不给假切换按钮。
    """
    specs: list[AgentSpec] = [
        AgentSpec(
            id="claude",
            name="Claude Code CLI",
            kind="cli",
            # 遵循 CLAUDE_CONFIG_DIR（本机就指向 D:\DevCache\claude）
            detect=(str(claude_settings_path()), _home(".claude.json")),
            hint="写入 settings.json 的 env（ANTHROPIC_BASE_URL / AUTH_TOKEN）；遵循 CLAUDE_CONFIG_DIR",
        ),
        AgentSpec(
            id="claude-desktop",
            name="Claude Desktop",
            kind="desktop",
            detect=tuple(str(path) for path in claude_desktop_config_paths()),
            writable=False,
            readonly_reason="桌面端第三方供应商需要 deploymentMode + enterpriseConfig，改错会导致桌面端无法启动；本次仅检测展示",
            hint="与 CLI 是两套配置（%LOCALAPPDATA%\\Claude\\claude_desktop_config.json）",
            extra={"configPath": str(claude_desktop_config_path())},
        ),
        AgentSpec(
            id="codex",
            name="Codex（CLI + 桌面端共用）",
            kind="cli",
            # 遵循 CODEX_HOME（本机指向 D:\DevCache\codex）
            detect=(
                str(codex_home_dir() / "config.toml"),
                str(codex_home_dir() / "auth.json"),
            ),
            hint="桌面端与 CLI 共用同一配置目录；写入 model_provider + auth.json",
        ),
        AgentSpec(
            id="kimi",
            name="Kimi Code",
            kind="cli",
            detect=(_home(".kimi-code/config.toml"),),
            hint="写入 config.toml 的 providers 段并选中该供应商的模型",
        ),
        AgentSpec(
            id="opencode",
            name="OpenCode",
            kind="cli",
            detect=(_home(".config/opencode/opencode.json"), _home(".local/share/opencode/auth.json")),
            hint="写入 provider 段并设置顶层 model，确保真正生效",
        ),
        AgentSpec(
            id="minimax",
            name="MiniMax Code",
            kind="cli",
            detect=(_home(".minimax/config.yaml"), _home(".minimax")),
            hint="写入 provider options 并设置默认模型",
        ),
        AgentSpec(
            id="gemini",
            name="Gemini CLI",
            kind="cli",
            detect=(_home(".gemini/.env"), _home(".gemini/settings.json")),
            hint="写入 .gemini/.env 的 GEMINI_API_KEY / GOOGLE_GEMINI_BASE_URL",
        ),
        # ---- 以下为「检测展示」：magpie / cc-switch 支持、但写入器尚未实现 ----
        AgentSpec(
            id="pi",
            name="Pi",
            kind="cli",
            detect=(_home(".pi/agent/settings.json"), _home(".pi")),
            writable=False,
            readonly_reason="Pi 的供应商在 ~/.pi/agent/models.json（大结构、magpie 会重写），自动改写风险高；本次仅检测",
            hint="检测到 .pi 即视为已安装",
        ),
        AgentSpec(
            id="grokbuild",
            name="Grok Build",
            kind="cli",
            detect=(_home(".grok/config.toml"),),
            writable=False,
            readonly_reason="Grok Build 配置结构未在本工具实现写入器；本次仅检测",
            hint="对齐 cc-switch 的 grokbuild 应用",
        ),
        AgentSpec(
            id="zcode",
            name="ZCode",
            kind="cli",
            detect=(_home(".zcode/v2/config.json"),),
            writable=False,
            readonly_reason="ZCode 走自有登录/配置结构；本次仅检测",
            hint="本机已安装时可直接用它的订阅额度",
        ),
        AgentSpec(
            id="dsh",
            name="DeepSeek Harness",
            kind="cli",
            detect=(_home(".dsh"),),
            writable=False,
            readonly_reason="DSH 使用 profiles 补丁式配置（cordis.patch.yml），自动改写风险高；本次仅检测",
            hint="对齐 cc-switch 的 dsh 应用",
        ),
        AgentSpec(
            id="workbuddy",
            name="WorkBuddy",
            kind="cli",
            detect=(_home(".workbuddy/models.json"),),
            writable=False,
            readonly_reason="WorkBuddy 配置结构未实现写入器；本次仅检测",
            hint="对齐 cc-switch 的 workbuddy 应用",
        ),
        AgentSpec(
            id="hermes",
            name="Hermes Agent",
            kind="cli",
            detect=(_home("AppData/Local/hermes/config.yaml"), _home(".hermes")),
            writable=False,
            readonly_reason="Hermes 配置结构未实现写入器；本次仅检测",
            hint="对齐 cc-switch 的 hermes 应用",
        ),
        AgentSpec(
            id="copilot",
            name="Copilot CLI",
            kind="cli",
            detect=(_home(".copilot"),),
            writable=False,
            readonly_reason="Copilot 走 GitHub 登录（OAuth），不支持按 API Key 切换；本次仅检测",
            hint="对齐 cc-switch 的 copilot 应用",
        ),
        AgentSpec(
            id="openclaw",
            name="OpenClaw",
            kind="cli",
            detect=(_home(".openclaw"),),
            writable=False,
            readonly_reason="OpenClaw 配置结构未实现写入器；本次仅检测",
            hint="对齐 cc-switch 的 openclaw 应用",
        ),
        AgentSpec(
            id="kiro",
            name="Kiro",
            kind="cli",
            detect=(_home(".kiro"), _home(".kiro/settings")),
            writable=False,
            readonly_reason="Kiro 走 AWS 登录（非 API Key 供应商），不支持按 Key 切换",
            hint="检测到 .kiro 即视为已安装",
        ),
        AgentSpec(
            id="qwen",
            name="Qwen Code",
            kind="cli",
            detect=(_home(".qwen"),),
            writable=False,
            readonly_reason="Qwen Code 配置结构未实现写入器；本次仅检测",
            hint="对齐 magpie 的 qwen 条目",
        ),
        AgentSpec(
            id="crush",
            name="Crush",
            kind="cli",
            detect=(_home(".crush"),),
            writable=False,
            readonly_reason="Crush 配置结构未实现写入器；本次仅检测",
            hint="对齐 magpie 的 crush 条目",
        ),
        AgentSpec(
            id="goose",
            name="Goose",
            kind="cli",
            detect=(_home(".config/goose"),),
            writable=False,
            readonly_reason="Goose 配置结构未实现写入器；本次仅检测",
            hint="对齐 magpie 的 goose 条目",
        ),
        AgentSpec(
            id="cursor",
            name="Cursor CLI",
            kind="cli",
            detect=(_home(".cursor"), _home("AppData/Roaming/Cursor")),
            writable=False,
            readonly_reason="Cursor 走自有登录；本次仅检测",
            hint="对齐 magpie 的 cursor 条目",
        ),
    ]
    return tuple(specs)


def _path_exists(raw: str) -> bool:
    if not raw:
        return False
    home = real_home()
    candidate = Path(raw) if os.path.isabs(raw) else home / raw
    return candidate.exists()


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
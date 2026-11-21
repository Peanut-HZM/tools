"""Agent 切换（从 agent-hub 合并）

把「订阅额度工具」选中的账号写进本机 CLI 配置，让该 agent 直接使用这个供应商。

安全设计（沿用 agent-hub 的实现，逐条保留）：

* **只改关键字段（floor）**，其余内容不动；TOML/YAML 用保格式库 round-trip
* **首写备份**：每个文件第一次被改前完整备份，之后不再覆盖（保留最初状态）
* **原子写**：临时文件 + os.replace
* **可一键恢复**：把首写备份复制回原位
* **凭据路径一律 REAL_HOME**（config.py 覆盖 HOME 的场景下仍取真实家目录）
* **写入前可预览**（dry-run 看将写哪些字段，不落盘）

这里只**复用** agent_hub 的写入器，不复制实现，避免两份逻辑漂移。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Optional

from app.services.agent_hub.agent_writers import (
    AGENT_FILES,
    AgentWriterError,
    SUPPORTED_AGENTS,
    WriteTarget,
    apply_provider_to_agent,
    preview_changes,
    real_home,
    restore_agent_backups,
)
from app.services.subscription_quota.agent_catalog import (
    AgentSpec,
    _path_exists,
    available_agents,
    get_agent_spec,
    installed_agents,
)
from app.services.subscription_quota.agent_state import match_account, read_agent_current

logger = logging.getLogger(__name__)

#: 可切换的 agent（与 agent_writers 保持一致）
WRITER_AGENTS: tuple[str, ...] = tuple(SUPPORTED_AGENTS)


@dataclass
class AgentStatus:
    """一个 agent 的当前状态"""

    agent: str
    files: list[dict]
    configured: bool
    current_provider_id: str = ""
    current_provider_name: str = ""
    switched_at: str = ""

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "files": self.files,
            "configured": self.configured,
            "currentProviderId": self.current_provider_id,
            "currentProviderName": self.current_provider_name,
            "switchedAt": self.switched_at,
        }


def list_agent_status() -> list[AgentStatus]:
    """检测本机各 agent 的配置文件是否存在（只读）"""
    home = real_home()
    out: list[AgentStatus] = []
    for agent in WRITER_AGENTS:
        files = [
            {"path": str(home / rel), "exists": (home / rel).exists()}
            for rel in AGENT_FILES[agent]
        ]
        # 主配置文件存在即视为已安装（auth.json 这类纯凭据文件不计入）
        configured = any(
            item["exists"]
            for item, rel in zip(files, AGENT_FILES[agent])
            if "auth.json" not in rel
        )
        out.append(AgentStatus(agent=agent, files=files, configured=configured))
    return out


def preview_switch(
    agent: str,
    *,
    name: str,
    base_url: str,
    api_key: str,
    model: str = "",
) -> dict:
    """切换预览（不落盘）"""
    if agent not in WRITER_AGENTS:
        raise AgentWriterError(f"不支持的 agent: {agent}")
    target = WriteTarget(agent=agent, name=name, base_url=base_url, api_key=api_key, model=model)
    return preview_changes(agent, target)


def apply_switch(
    agent: str,
    *,
    name: str,
    base_url: str,
    api_key: str,
    model: str = "",
    kind: Optional[str] = None,
) -> dict:
    """执行切换（写入本机配置文件，带首写备份）"""
    if agent not in WRITER_AGENTS:
        raise AgentWriterError(f"不支持的 agent: {agent}")
    if not api_key:
        raise AgentWriterError(f"该账号没有可写入的 API Key（{name}）")
    target = WriteTarget(agent=agent, name=name, base_url=base_url, api_key=api_key, model=model)
    logger.info("切换 agent=%s -> provider=%s base_url=%s", agent, name, base_url or "(默认)")
    return apply_provider_to_agent(agent, target, provider_kind=kind or "")


def restore(agent: str) -> list[str]:
    """把该 agent 的首写备份恢复回原位"""
    if agent not in WRITER_AGENTS:
        raise AgentWriterError(f"不支持的 agent: {agent}")
    restored = restore_agent_backups(agent)
    logger.info("恢复 agent=%s 的备份，共 %d 个文件", agent, len(restored))
    return restored


def agent_files(agent: str) -> list[str]:
    return list(AGENT_FILES.get(agent, []))


def list_installed_status(accounts) -> tuple[list[dict], list[dict]]:
    """返回 (已安装 agent 状态, 未安装可选 agent 目录)

    * 已安装：附带**真实**当前配置（解析配置文件）与命中的账号
    * 未安装：只给目录信息，供「添加 Agent」弹窗选择
    """
    installed: list[dict] = []
    for spec in installed_agents():
        data = spec.to_public_dict()
        current = read_agent_current(spec.id)
        matched = match_account(current, accounts)
        data["current"] = current.to_public_dict()
        data["currentAccount"] = matched
        # 展示用：直接用检测路径（Desktop / Pi / Kiro 没有 AGENT_FILES 条目）
        data["files"] = [
            {"path": path if os.path.isabs(path) else str(real_home() / path), "exists": _path_exists(path)}
            for path in spec.detect
        ]
        installed.append(data)

    available = [spec.to_public_dict() for spec in available_agents()]
    return installed, available


def verify_switch(agent: str, account) -> dict:
    """切换后校验：重新解析配置文件，确认真的指向该账号"""
    current = read_agent_current(agent)
    matched = match_account(current, [account] if account else [])
    return {
        "verified": bool(matched),
        "current": current.to_public_dict(),
        "matchedAccountId": matched.get("accountId") if matched else None,
    }


def apply_switch_verified(
    agent: str,
    *,
    name: str,
    base_url: str,
    api_key: str,
    model: str = "",
    kind: Optional[str] = None,
    account=None,
) -> dict:
    """执行切换 + 立即回读校验（验证失败如实返回 verified=False，不谎报成功）"""
    result = apply_switch(
        agent, name=name, base_url=base_url, api_key=api_key, model=model, kind=kind
    )
    result.update(verify_switch(agent, account))
    return result

"""Agent 目录 / 真实状态读回 单测

覆盖用户要求：
* 只列出已安装（未安装的进 available）
* Claude Desktop 与 Claude Code CLI 分开；Codex 只有一个条目
* 当前供应商来自**真实配置文件解析**（不是我们的切换记录）
* 匹配账号按 (base_url, Key) 判定
"""

from __future__ import annotations

import json
import uuid

import pytest

from app.services.subscription_quota import agent_catalog, agent_state
from app.services.subscription_quota.accounts import QuotaAccount


def _zztest_user() -> str:
    return f"zztest-{uuid.uuid4()}"


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """把 REAL_HOME 指到临时目录（catalog 与 state 两处都要打补丁）"""
    monkeypatch.setattr(agent_catalog, "real_home", lambda: tmp_path)
    monkeypatch.setattr(agent_state, "real_home", lambda: tmp_path)
    return tmp_path


def _write(path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------- 目录与安装检测


def test_catalog_keeps_claude_and_desktop_separate_but_codex_single(fake_home):
    specs = {spec.id: spec for spec in agent_catalog.agent_specs()}
    assert specs["claude"].kind == "cli"
    assert specs["claude-desktop"].kind == "desktop"
    # Claude Desktop 暂不支持自动切换，必须显式标注原因
    assert specs["claude-desktop"].writable is False
    assert specs["claude-desktop"].readonly_reason
    # Codex 桌面端与 CLI 共用 ~/.codex → 只有一个条目
    assert "codex" in specs
    assert not any(key.startswith("codex-desktop") for key in specs)


def test_installed_only_lists_present_agents(fake_home):
    _write(fake_home / ".claude" / "settings.json", "{}")
    _write(fake_home / ".codex" / "config.toml", "")
    installed = {spec.id for spec in agent_catalog.installed_agents()}
    available = {spec.id for spec in agent_catalog.available_agents()}
    assert installed == {"claude", "codex"}
    assert "kimi" in available
    assert installed & available == set()


def test_detect_accepts_directory_paths(fake_home):
    (fake_home / ".pi").mkdir()
    installed = {spec.id for spec in agent_catalog.installed_agents()}
    assert "pi" in installed


# ---------------------------------------------------------------- 真实状态读回


def test_read_claude_cli_settings(fake_home):
    _write(
        fake_home / ".claude" / "settings.json",
        json.dumps({"env": {"ANTHROPIC_BASE_URL": "https://relay.example.com", "ANTHROPIC_AUTH_TOKEN": "sk-x"}}),
    )
    current = agent_state.read_agent_current("claude")
    assert current.base_url == "https://relay.example.com"
    assert current.api_key == "sk-x"
    assert current.error == ""


def test_read_opencode_reports_real_model(fake_home):
    _write(
        fake_home / ".config" / "opencode" / "opencode.json",
        json.dumps(
            {
                "model": "agent-hub/k3",
                "provider": {
                    "agent-hub": {
                        "options": {"baseURL": "https://api.kimi.com/coding/v1", "apiKey": "sk-oc"}
                    }
                },
            }
        ),
    )
    current = agent_state.read_agent_current("opencode")
    assert current.model == "agent-hub/k3"
    assert current.base_url == "https://api.kimi.com/coding/v1"
    assert current.api_key == "sk-oc"


def test_read_kimi_toml(fake_home):
    _write(
        fake_home / ".kimi-code" / "config.toml",
        '[providers."managed:kimi-code"]\napi_key = "sk-kimi"\nbase_url = "https://api.kimi.com/coding/v1"\n',
    )
    current = agent_state.read_agent_current("kimi")
    assert current.api_key == "sk-kimi"
    assert current.base_url == "https://api.kimi.com/coding/v1"


def test_read_missing_config_reports_error(fake_home):
    current = agent_state.read_agent_current("claude")
    assert current.error  # 如实报错，不假装成功


# ---------------------------------------------------------------- 账号匹配（去重键同源）


def _account(label: str, base_url: str, api_key: str) -> QuotaAccount:
    return QuotaAccount(
        id=f"acc-{uuid.uuid4()}", user_id=_zztest_user(), provider_id="kimi",
        label=label, api_key=api_key, base_url=base_url,
    )


def test_match_account_by_url_and_key():
    account = _account("Kimi", "https://api.kimi.com/coding/v1", "sk-match")
    current = agent_state.AgentCurrent(
        agent="kimi", base_url="https://api.kimi.com/coding", api_key="sk-match"
    )
    matched = agent_state.match_account(current, [account])
    assert matched and matched["accountId"] == account.id


def test_match_account_rejects_different_url():
    account = _account("Kimi", "https://api.kimi.com/coding/v1", "sk-match")
    current = agent_state.AgentCurrent(
        agent="kimi", base_url="https://relay.example.com/v1", api_key="sk-match"
    )
    assert agent_state.match_account(current, [account]) is None


def test_match_account_rejects_different_key():
    account = _account("Kimi", "https://api.kimi.com/coding/v1", "sk-a")
    current = agent_state.AgentCurrent(
        agent="kimi", base_url="https://api.kimi.com/coding/v1", api_key="sk-b"
    )
    assert agent_state.match_account(current, [account]) is None
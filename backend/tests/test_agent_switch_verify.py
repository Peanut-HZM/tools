"""Agent 切换「真实有效」单测（临时 HOME，不碰真实配置）

验证点：
* 切换后配置文件里真的出现目标 base_url / Key（不是只写记录表）
* OpenCode / MiniMax 不指定模型时拒绝执行（否则不会生效，属假切换）
* 回读校验（apply_switch_verified）能识别成功与失败
* 首写备份可恢复
"""

from __future__ import annotations

import json
import uuid

import pytest

from app.services.agent_hub import agent_writers
from app.services.subscription_quota import agent_state, agent_switch
from app.services.subscription_quota.accounts import QuotaAccount


@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """把写入目标与回读目标都指到临时目录"""
    monkeypatch.setattr(agent_writers, "real_home", lambda: tmp_path)
    monkeypatch.setattr(agent_state, "real_home", lambda: tmp_path)
    monkeypatch.setattr(agent_switch, "real_home", lambda: tmp_path)
    # 配置目录可能被环境变量覆盖（CLAUDE_CONFIG_DIR / CODEX_HOME），测试里必须清空
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    monkeypatch.delenv("CODEX_HOME", raising=False)
    # 备份目录也从数据目录挪到临时目录，避免污染仓库
    monkeypatch.setattr(agent_writers, "_backup_dir", lambda: tmp_path / "_backups")
    return tmp_path


def _account(base_url: str, api_key: str) -> QuotaAccount:
    return QuotaAccount(
        id=f"acc-{uuid.uuid4()}",
        user_id=f"zztest-{uuid.uuid4()}",
        provider_id="kimi",
        label="Kimi Code",
        api_key=api_key,
        base_url=base_url,
    )


def test_opencode_switch_writes_model_and_verifies(temp_home):
    cfg = temp_home / ".config" / "opencode" / "opencode.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"model": "old/model", "provider": {"old": {}}}), encoding="utf-8")

    account = _account("https://api.kimi.com/coding/v1", "sk-verify-1")
    result = agent_switch.apply_switch_verified(
        "opencode",
        name="Kimi Code",
        base_url=account.base_url,
        api_key=account.api_key,
        model="k3",
        kind="window",
        account=account,
    )

    assert result["verified"] is True
    data = json.loads(cfg.read_text(encoding="utf-8"))
    # 真的写进了 provider 段
    assert data["provider"]["agent-hub"]["options"]["apiKey"] == "sk-verify-1"
    assert data["provider"]["agent-hub"]["options"]["baseURL"] == "https://api.kimi.com/coding/v1"
    # 并且真的选中了它（这才是「切换生效」的关键）
    assert data["model"] == "agent-hub/k3"


def test_opencode_without_model_is_rejected(temp_home):
    cfg = temp_home / ".config" / "opencode" / "opencode.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"model": "old/model"}), encoding="utf-8")

    with pytest.raises(agent_writers.AgentWriterError) as exc:
        agent_switch.apply_switch(
            "opencode", name="X", base_url="https://a.example.com", api_key="sk-x", model=""
        )
    assert "模型" in str(exc.value)
    # 拒绝执行时文件不应被改
    assert json.loads(cfg.read_text(encoding="utf-8")) == {"model": "old/model"}


def test_codex_switch_writes_provider_and_auth(temp_home):
    toml_path = temp_home / ".codex" / "config.toml"
    toml_path.parent.mkdir(parents=True)
    toml_path.write_text('model = "gpt-5"\n', encoding="utf-8")

    account = _account("https://relay.example.com/v1", "sk-codex")
    result = agent_switch.apply_switch_verified(
        "codex",
        name="Relay",
        base_url=account.base_url,
        api_key=account.api_key,
        model="",
        account=account,
    )
    assert result["verified"] is True
    text = toml_path.read_text(encoding="utf-8")
    assert 'model_provider = "custom"' in text
    assert "https://relay.example.com/v1" in text
    auth = json.loads((temp_home / ".codex" / "auth.json").read_text(encoding="utf-8"))
    assert auth["OPENAI_API_KEY"] == "sk-codex"


def test_claude_switch_writes_env(temp_home):
    settings = temp_home / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({"theme": "dark", "env": {}}), encoding="utf-8")

    account = _account("https://relay.example.com", "sk-claude")
    result = agent_switch.apply_switch_verified(
        "claude",
        name="Relay",
        base_url=account.base_url,
        api_key=account.api_key,
        account=account,
    )
    assert result["verified"] is True
    data = json.loads(settings.read_text(encoding="utf-8"))
    assert data["theme"] == "dark"  # floor：其余字段不动
    assert data["env"]["ANTHROPIC_BASE_URL"] == "https://relay.example.com"
    assert data["env"]["ANTHROPIC_AUTH_TOKEN"] == "sk-claude"
    assert "ANTHROPIC_API_KEY" not in data["env"]


def test_verify_detects_manual_revert(temp_home):
    """切换后有人把配置改回去 → 回读校验必须报 verified=False（不能谎报成功）"""
    settings = temp_home / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({"env": {}}), encoding="utf-8")

    account = _account("https://relay.example.com", "sk-claude")
    agent_switch.apply_switch_verified(
        "claude", name="Relay", base_url=account.base_url, api_key=account.api_key, account=account
    )
    # 人工改回
    settings.write_text(json.dumps({"env": {"ANTHROPIC_BASE_URL": "https://other.example.com"}}), encoding="utf-8")

    verify = agent_switch.verify_switch("claude", account)
    assert verify["verified"] is False


def test_restore_brings_original_back(temp_home):
    settings = temp_home / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True)
    original = {"env": {"ANTHROPIC_BASE_URL": "https://original.example.com"}}
    settings.write_text(json.dumps(original), encoding="utf-8")

    agent_switch.apply_switch(
        "claude", name="Relay", base_url="https://relay.example.com", api_key="sk-new"
    )
    restored = agent_switch.restore("claude")
    assert restored
    assert json.loads(settings.read_text(encoding="utf-8")) == original


# ---------------------------------------------------------------- Pi / Hermes（本轮新增）


def test_pi_switch_writes_provider_and_selection(temp_home):
    models_path = temp_home / ".pi" / "agent" / "models.json"
    models_path.parent.mkdir(parents=True)
    models_path.write_text(json.dumps({"providers": {}}), encoding="utf-8")
    settings_path = temp_home / ".pi" / "agent" / "settings.json"
    settings_path.write_text(json.dumps({"defaultProvider": "magpie", "defaultModel": "k3"}), encoding="utf-8")

    account = _account("https://api.kimi.com/coding/v1", "sk-pi")
    result = agent_switch.apply_switch_verified(
        "pi",
        name="Kimi Code",
        base_url=account.base_url,
        api_key=account.api_key,
        model="kimi-for-coding",
        kind="window",
        account=account,
    )

    assert result["verified"] is True
    models = json.loads(models_path.read_text(encoding="utf-8"))
    node = models["providers"]["agent-hub"]
    assert node["apiKey"] == "sk-pi"
    assert node["baseUrl"] == "https://api.kimi.com/coding/v1"
    assert any(m["id"] == "kimi-for-coding" for m in node["models"])
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    # 真正生效的关键：settings 指向新 provider/模型
    assert settings["defaultProvider"] == "agent-hub"
    assert settings["defaultModel"] == "kimi-for-coding"


def test_pi_without_model_is_rejected(temp_home):
    models_path = temp_home / ".pi" / "agent" / "models.json"
    models_path.parent.mkdir(parents=True)
    models_path.write_text(json.dumps({"providers": {}}), encoding="utf-8")

    with pytest.raises(agent_writers.AgentWriterError) as exc:
        agent_switch.apply_switch(
            "pi", name="X", base_url="https://a.example.com", api_key="sk-x", model=""
        )
    assert "模型" in str(exc.value)


def test_hermes_switch_writes_provider(temp_home):
    hermes_dir = temp_home / ".hermes"
    hermes_dir.mkdir(parents=True)
    (hermes_dir / "config.yaml").write_text("providers: {}\n", encoding="utf-8")

    account = _account("https://relay.example.com/v1", "sk-hermes")
    result = agent_switch.apply_switch_verified(
        "hermes",
        name="Relay",
        base_url=account.base_url,
        api_key=account.api_key,
        model="some-model",
        account=account,
    )

    assert result["verified"] is True
    current = agent_state.read_agent_current("hermes")
    assert current.base_url == "https://relay.example.com/v1"
    assert current.api_key == "sk-hermes"
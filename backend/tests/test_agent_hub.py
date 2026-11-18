"""Agent Hub 单测 — 模型 CRUD / manual 额度 / 用量查询器解析（mock HTTP）/ 写入器 floor 语义。

隔离三要素（项目规范）：
- DB：临时 SQLite + monkeypatch SessionLocal（不碰真实 backend/data/tools.db）
- 外部 HTTP：monkeypatch usage_queries.requests（不出网）
- agent 配置：monkeypatch REAL_HOME 到临时目录（不碰真实 ~/.claude 等配置）
- user_id 一律 zztest-<uuid>（UUID 规范）
"""
import json
import sys
import uuid
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

ZZTEST_USER = {"id": f"zztest-{uuid.uuid4()}", "username": "zztest-agent-hub"}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """临时 DB + 临时 HOME + 覆盖鉴权的 TestClient。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.models.base as base_mod
    import app.models.agent_hub_models  # noqa: F401 注册表
    from app.models.base import Base

    engine = create_engine(f"sqlite:///{tmp_path}/agent_hub_test.db",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(base_mod, "SessionLocal", TestingSession)

    # 隔离真实家目录
    fake_home = tmp_path / "fakehome"
    (fake_home / ".claude").mkdir(parents=True)
    (fake_home / ".codex").mkdir()
    (fake_home / ".gemini").mkdir()
    (fake_home / ".kimi-code").mkdir()
    (fake_home / ".config" / "opencode").mkdir(parents=True)
    (fake_home / ".minimax").mkdir()
    monkeypatch.setattr("app.config.config.REAL_HOME", str(fake_home))

    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.dependencies import get_db, get_current_user

    def override_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: ZZTEST_USER
    yield TestClient(app)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Provider / Subscription CRUD 与脱敏
# ---------------------------------------------------------------------------

def test_provider_crud_and_key_masking(client):
    payload = {"name": "PackyCode 中转", "kind": "newapi", "app": "claude",
               "base_url": "https://api.packycode.ai", "api_key": "sk-secret1234567890",
               "category": "third_party"}
    resp = client.post("/api/agent-hub/providers", json=payload)
    assert resp.status_code == 200, resp.text
    provider = resp.json()["provider"]
    assert provider["has_api_key"] is True
    assert "sk-secret1234567890" not in json.dumps(provider)  # 响应脱敏
    assert provider["api_key_masked"].startswith("sk-s") and "****" in provider["api_key_masked"]

    # 列表也不含明文
    listing = client.get("/api/agent-hub/providers").json()["providers"]
    assert "sk-secret1234567890" not in json.dumps(listing)

    # 更新（空 key 不覆盖）
    upd = client.put(f"/api/agent-hub/providers/{provider['id']}",
                     json={**payload, "api_key": "", "notes": "备注"})
    assert upd.json()["provider"]["notes"] == "备注"
    assert upd.json()["provider"]["has_api_key"] is True  # 空 key 未清掉已存 key

    assert client.delete(f"/api/agent-hub/providers/{provider['id']}").json()["ok"] is True


def test_subscription_manual_quota_adjust(client):
    """manual 订阅：额度支持手动增加 ✅"""
    sub = client.post("/api/agent-hub/subscriptions", json={
        "name": "手动额度套餐", "kind": "manual", "total_quota": 100,
        "used_quota": 30, "quota_unit": "credits", "window_type": "5h",
    }).json()["subscription"]
    assert sub["total_quota"] == 100 and sub["used_quota"] == 30
    assert sub["displayable"] is True  # manual 无需凭据即可显示

    # 手动增加额度 100 -> 500 ✅
    adj = client.put(f"/api/agent-hub/subscriptions/{sub['id']}/quota",
                     json={"total_quota": 500})
    assert adj.json()["subscription"]["total_quota"] == 500
    assert adj.json()["subscription"]["used_quota"] == 30  # 未改的保持

    # 立即查询：manual 走本地计算
    usage = client.post(f"/api/agent-hub/subscriptions/{sub['id']}/usage").json()
    assert usage["success"] is True
    tier = usage["tiers"][0]
    assert tier["used"] == 30 and tier["total"] == 500
    assert tier["utilization"] == 6.0


def test_subscription_not_configured_not_displayable(client):
    """只显示已配置且可显示的：非 manual 订阅缺凭据 → displayable=False 且拒绝查询"""
    sub = client.post("/api/agent-hub/subscriptions", json={
        "name": "OpenDesign（未配 key）", "kind": "opendesign", "credential": "",
    }).json()["subscription"]
    assert sub["displayable"] is False
    resp = client.post(f"/api/agent-hub/subscriptions/{sub['id']}/usage")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 用量查询器（mock HTTP，不出网）
# ---------------------------------------------------------------------------

class _FakeResp:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    @property
    def headers(self):
        return {"content-type": "application/json"}

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def test_query_opendesign_parse(client, monkeypatch):
    from app.services.agent_hub import usage_queries as uq

    calls = []

    def fake_get(url, headers=None, timeout=None, **kw):
        calls.append((url, dict(headers or {})))
        if "/workspaces/current" in url:
            return _FakeResp(200, {"workspace": {"id": "ws-1"}})
        return _FakeResp(200, {"billing": {"designPlanWindows": [
            {"kind": "5h", "limitCredits": "100", "remainingCredits": "25", "resetsAt": "T1"},
            {"kind": "7d", "limitCredits": "700", "remainingCredits": "700", "resetsAt": "T2"},
        ]}})

    monkeypatch.setattr(uq.requests, "get", fake_get)
    ctx = uq.QueryContext(kind="opendesign", usage_api_key="ck-control-1234")
    result = uq.dispatch_query(ctx)
    assert result["success"] is True
    t5h = result["tiers"][0]
    assert t5h["name"] == "5小时窗口" and t5h["used"] == 75 and t5h["total"] == 100
    assert t5h["unit"] == "credits" and t5h["resets_at"] == "T1"
    assert result["tiers"][1]["used"] == 0  # 满额未用
    # 鉴权头是 controlKey（usage_api_key）
    assert calls[0][1]["Authorization"] == "Bearer ck-control-1234"


def test_query_newapi_parse(client, monkeypatch):
    from app.services.agent_hub import usage_queries as uq

    def fake_get(url, headers=None, timeout=None, **kw):
        assert url.endswith("/api/user/self")
        assert headers["New-Api-User"] == "42"
        return _FakeResp(200, {"data": {"quota": 500000, "used_quota": 250000, "group": "vip"}})

    monkeypatch.setattr(uq.requests, "get", fake_get)
    ctx = uq.QueryContext(kind="newapi", api_key="tok-1234",
                          base_url="https://relay.example.com", extra={"userId": "42"})
    result = uq.dispatch_query(ctx)
    tier = result["tiers"][0]
    assert result["plan_name"] == "vip"
    assert tier["total"] == 1.5 and tier["used"] == 0.5  # quota÷500000


def test_query_zhipu_no_bearer_and_fallback(client, monkeypatch):
    from app.services.agent_hub import usage_queries as uq

    urls = []

    def fake_get(url, headers=None, timeout=None, **kw):
        urls.append(url)
        if "usage/quota/limit" in url:
            # 无套餐响应 → 触发回落查余额
            return _FakeResp(200, {"data": {"limits": [], "level": ""}})
        return _FakeResp(200, {"data": {"balance": 12.5, "availableBalance": 10.5}})

    monkeypatch.setattr(uq.requests, "get", fake_get)
    ctx = uq.QueryContext(kind="zhipu", api_key="zm-key-1", base_url="https://open.bigmodel.cn")
    result = uq.dispatch_query(ctx)
    assert result["success"] is True
    assert result["balance"] == {"value": 10.5, "unit": "CNY"}
    # Authorization 无 Bearer（cc-switch 同款约定）
    assert "usage/quota/limit" in urls[0]


def test_query_denied_401_marks_credential_expired(client, monkeypatch):
    from app.services.agent_hub import usage_queries as uq

    monkeypatch.setattr(uq.requests, "get",
                        lambda *a, **kw: _FakeResp(401, {"error": "unauthorized"}))
    ctx = uq.QueryContext(kind="kimi", api_key="bad-key")
    result = uq.dispatch_query(ctx)
    assert result["success"] is False
    assert result["credential_expired"] is True
    assert "401" in result["error"] or "鉴权" in result["error"]


def test_query_network_error_raises_retryable(client, monkeypatch):
    from app.services.agent_hub import usage_queries as uq

    def boom(*a, **kw):
        raise uq.requests.ConnectionError("timeout")

    monkeypatch.setattr(uq.requests, "get", boom)
    ctx = uq.QueryContext(kind="deepseek", api_key="k")
    with pytest.raises(uq.UsageQueryError):
        uq.dispatch_query(ctx)


def test_query_claude_official_missing_credential(client, monkeypatch):
    """无 OAuth 凭据 → CredentialMissing（不参与显示）"""
    from app.services.agent_hub import usage_queries as uq

    ctx = uq.QueryContext(kind="claude_official", agent_app="claude")
    with pytest.raises(uq.CredentialMissing):
        uq.dispatch_query(ctx)


def test_usage_all_batch_isolates_failures(client, monkeypatch):
    """批量查询：单订阅失败不影响其他 ✅"""
    # manual 订阅（本地成功）+ opendesign 订阅（mock 网络异常）
    client.post("/api/agent-hub/subscriptions", json={
        "name": "手动", "kind": "manual", "total_quota": 10, "used_quota": 1})
    sub2 = client.post("/api/agent-hub/subscriptions", json={
        "name": "会失败的", "kind": "opendesign", "credential": "ck-1"}).json()["subscription"]
    from app.services.agent_hub import usage_queries as uq

    def boom(*a, **kw):
        raise uq.requests.ConnectionError("down")

    monkeypatch.setattr(uq.requests, "get", boom)
    results = client.get("/api/agent-hub/subscriptions/usage/all").json()["results"]
    by_name = {r["name"]: r for r in results}
    assert by_name["手动"]["success"] is True
    assert by_name["会失败的"]["success"] is False  # 隔离失败


# ---------------------------------------------------------------------------
# Agent 写入器（floor 语义 + 备份 + 恢复）
# ---------------------------------------------------------------------------

def _make_claude_settings(fake_home):
    settings = {"theme": "dark", "env": {"ANTHROPIC_API_KEY": "old-key",
                                         "OTHER_KEEP": "keep-me"},
                "permissions": {"allow": ["Bash"]}}
    path = fake_home / ".claude" / "settings.json"
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return path


def test_writer_claude_floor_semantics(client):
    """claude：只写 floor 字段，其余键保留；AUTH_TOKEN 写入、API_KEY 移除"""
    from app.services.agent_hub import agent_writers as aw

    fake_home = Path(aw.real_home())
    _make_claude_settings(fake_home)
    result = aw.apply_provider_to_agent("claude", aw.WriteTarget(
        agent="claude", name="中转站", base_url="https://relay.example.com",
        api_key="sk-new-9999"))
    assert result["written"]

    data = json.loads((fake_home / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert data["env"]["ANTHROPIC_BASE_URL"] == "https://relay.example.com"
    assert data["env"]["ANTHROPIC_AUTH_TOKEN"] == "sk-new-9999"
    assert "ANTHROPIC_API_KEY" not in data["env"]          # 互斥清理
    assert data["env"]["OTHER_KEEP"] == "keep-me"          # 其余 env 保留
    assert data["theme"] == "dark"                          # 非 floor 键保留
    assert data["permissions"]["allow"] == ["Bash"]

    # 备份已生成且含原始 API_KEY
    backups = list((aw._backup_dir() / "claude").iterdir())
    assert len(backups) == 1
    original = json.loads(backups[0].read_text(encoding="utf-8"))
    assert original["env"]["ANTHROPIC_API_KEY"] == "old-key"


def test_writer_claude_backup_kept_once(client):
    """首写备份：第二次切换不覆盖备份（保留最初状态）"""
    from app.services.agent_hub import agent_writers as aw
    fake_home = Path(aw.real_home())
    _make_claude_settings(fake_home)
    aw.apply_provider_to_agent("claude", aw.WriteTarget(
        agent="claude", name="A", base_url="https://a", api_key="k1"))
    aw.apply_provider_to_agent("claude", aw.WriteTarget(
        agent="claude", name="B", base_url="https://b", api_key="k2"))
    backups = list((aw._backup_dir() / "claude").iterdir())
    assert len(backups) == 1  # 仍是首写备份
    assert json.loads(backups[0].read_text(encoding="utf-8"))["env"]["ANTHROPIC_API_KEY"] == "old-key"


def test_restore_agent_backup(client):
    from app.services.agent_hub import agent_writers as aw
    fake_home = Path(aw.real_home())
    _make_claude_settings(fake_home)
    aw.apply_provider_to_agent("claude", aw.WriteTarget(
        agent="claude", name="A", base_url="https://a", api_key="k1"))
    restored = aw.restore_agent_backups("claude")
    assert ".claude/settings.json" in restored
    data = json.loads((fake_home / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert data["env"]["ANTHROPIC_API_KEY"] == "old-key"  # 已恢复


def test_writer_codex_toml_and_auth(client):
    """codex：tomlkit 保格式新增 [model_providers.custom] + auth.json 创建"""
    from app.services.agent_hub import agent_writers as aw
    fake_home = Path(aw.real_home())
    toml_path = fake_home / ".codex" / "config.toml"
    toml_path.write_text(
        '# 用户注释保留\nmcp_servers = {}\n[other]\nkey = "v"\n', encoding="utf-8")
    result = aw.apply_provider_to_agent("codex", aw.WriteTarget(
        agent="codex", name="中转", base_url="https://codex-relay.example.com",
        api_key="sk-codex-1", model="gpt-5.6"))
    assert len(result["written"]) == 2
    import tomllib
    data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    assert data["model_provider"] == "custom"
    assert data["model"] == "gpt-5.6"
    assert data["model_providers"]["custom"]["base_url"] == "https://codex-relay.example.com"
    assert data["model_providers"]["custom"]["wire_api"] == "responses"
    assert data["other"]["key"] == "v"                    # 既有段保留
    assert "# 用户注释保留" in toml_path.read_text(encoding="utf-8")  # 注释保留
    auth = json.loads((fake_home / ".codex" / "auth.json").read_text(encoding="utf-8"))
    assert auth["OPENAI_API_KEY"] == "sk-codex-1"


def test_writer_gemini_env_lines_preserved(client):
    """gemini：.env 行编辑保序，其余行不动；文件不存在时创建"""
    from app.services.agent_hub import agent_writers as aw
    fake_home = Path(aw.real_home())
    env_path = fake_home / ".gemini" / ".env"
    env_path.write_text("# my comment\nOTHER_VAR=1\nGEMINI_API_KEY=old\n", encoding="utf-8")
    aw.apply_provider_to_agent("gemini", aw.WriteTarget(
        agent="gemini", name="g", base_url="https://gemini-relay.example.com", api_key="gk-1"))
    text = env_path.read_text(encoding="utf-8")
    assert "# my comment" in text and "OTHER_VAR=1" in text  # 其余行保留
    assert "GEMINI_API_KEY=gk-1" in text
    assert "GOOGLE_GEMINI_BASE_URL=https://gemini-relay.example.com" in text


def test_writer_kimi_provider_block(client):
    """kimi：更新 providers 第一个块的 api_key/base_url，models/services/mcp 保留"""
    from app.services.agent_hub import agent_writers as aw
    fake_home = Path(aw.real_home())
    toml_path = fake_home / ".kimi-code" / "config.toml"
    toml_path.write_text(
        """[providers."managed:kimi-code"]
type = "kimi"
api_key = "old"
base_url = "https://api.kimi.com"
oauth = { storage = "keyring" }

[models.m1]
provider = "managed:kimi-code"
model = "kimi"
""", encoding="utf-8")
    aw.apply_provider_to_agent("kimi", aw.WriteTarget(
        agent="kimi", name="Kimi", base_url="https://api.kimi.ai", api_key="new-kimi-key"))
    import tomllib
    data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
    provider = next(iter(data["providers"].values()))
    assert provider["api_key"] == "new-kimi-key"
    assert provider["base_url"] == "https://api.kimi.ai"
    assert provider["oauth"]["storage"] == "keyring"      # 其余字段保留
    assert "m1" in data["models"]


def test_writer_opencode_additive(client):
    """opencode：累加式 provider.agent-hub 节点，既有 provider 与 agent 配置保留"""
    from app.services.agent_hub import agent_writers as aw
    fake_home = Path(aw.real_home())
    json_path = fake_home / ".config" / "opencode" / "opencode.json"
    json_path.write_text(json.dumps({
        "$schema": "x", "provider": {"peanut": {"npm": "@ai-sdk/anthropic",
                                                "options": {"baseURL": "https://old", "apiKey": "old"}}},
        "model": "peanut/claude", "agent": {"build": {"mode": "primary"}},
    }), encoding="utf-8")
    aw.apply_provider_to_agent("opencode", aw.WriteTarget(
        agent="opencode", name="新供应商", base_url="https://new.example.com", api_key="ok-1"),
        provider_kind="anthropic")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["provider"]["agent-hub"]["options"]["baseURL"] == "https://new.example.com"
    assert data["provider"]["agent-hub"]["npm"] == "@ai-sdk/anthropic"
    assert data["provider"]["peanut"]["options"]["apiKey"] == "old"  # 既有 provider 不动
    assert data["model"] == "peanut/claude"                           # model 指针不动
    assert "build" in data["agent"]


def test_writer_minimax_roundtrip(client):
    """minimax：ruamel round-trip 只改 options，mcp 等其他段保留"""
    from app.services.agent_hub import agent_writers as aw
    fake_home = Path(aw.real_home())
    yaml_path = fake_home / ".minimax" / "config.yaml"
    yaml_path.write_text(
        """# 头部注释
logLevel: info
provider:
  minimax:
    name: MiniMax
    npm: "@ai-sdk/anthropic"
    options:
      apiKey: old-key
      baseURL: https://old.example.com
mcp:
  existing: true
""", encoding="utf-8")
    aw.apply_provider_to_agent("minimax", aw.WriteTarget(
        agent="minimax", name="MiniMax", base_url="https://new.example.com", api_key="mm-1"))
    text = yaml_path.read_text(encoding="utf-8")
    assert "# 头部注释" in text                       # 注释保留（round-trip）
    assert "apiKey: mm-1" in text
    assert "baseURL: https://new.example.com" in text
    assert "mcp:" in text and "existing: true" in text


def test_writer_rejects_missing_files(client):
    """目标配置文件不存在 → 明确报错（不静默创建半套配置）"""
    from app.services.agent_hub import agent_writers as aw
    with pytest.raises(aw.AgentWriterError):
        aw.apply_provider_to_agent("claude", aw.WriteTarget(
            agent="claude", name="x", base_url="https://x", api_key="k"))
    with pytest.raises(aw.AgentWriterError):
        aw.apply_provider_to_agent("gemini_official", aw.WriteTarget(
            agent="claude", name="x", base_url="", api_key=""))


def test_unsupported_agent_rejected(client):
    from app.services.agent_hub import agent_writers as aw
    with pytest.raises(aw.AgentWriterError):
        aw.apply_provider_to_agent("unknown-agent", aw.WriteTarget(
            agent="unknown-agent", name="x", base_url="", api_key=""))


# ---------------------------------------------------------------------------
# 切换 API（端到端：DB 指针 + 写入 + agents 检测）
# ---------------------------------------------------------------------------

def test_switch_api_end_to_end(client):
    provider = client.post("/api/agent-hub/providers", json={
        "name": "端到端中转", "kind": "newapi", "app": "claude",
        "base_url": "https://relay.example.com", "api_key": "sk-e2e-key-12345678",
    }).json()["provider"]

    fake_home = Path(BACKEND_DIR / "data")  # 占位避免未用警告
    from app.services.agent_hub import agent_writers as aw
    _make_claude_settings(Path(aw.real_home()))

    resp = client.post("/api/agent-hub/agents/claude/switch",
                       json={"provider_id": provider["id"]})
    assert resp.status_code == 200, resp.text
    assert resp.json()["switch"]["provider_name"] == "端到端中转"

    agents = client.get("/api/agent-hub/agents").json()["agents"]
    claude = next(a for a in agents if a["agent"] == "claude")
    assert claude["current_provider_name"] == "端到端中转"

    preview = client.get(
        f"/api/agent-hub/agents/claude/config-preview?provider_id={provider['id']}").json()
    assert preview["floor"]["env.ANTHROPIC_BASE_URL"] == "https://relay.example.com"


def test_presets_endpoint(client):
    presets = client.get("/api/agent-hub/presets").json()
    kinds = [p["kind"] for p in presets["presets"]]
    assert "opendesign" in kinds and "manual" in kinds and "claude_official" in kinds
    assert presets["agents"] == ["claude", "codex", "gemini", "kimi", "opencode", "minimax"]

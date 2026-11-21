"""agent-subscription-sync 单测（设计 §9）

覆盖：去重规则 1/2、批内去重与 label 消歧、归一化（空 Key/自定义 provider/官方域名）、
扫描器解析（claude/codex/opencode，全部 tmp_path 伪造，不读真实凭据）、
响应无明文 Key、dry_run 不落库。

同步逻辑测试通过 patch ``subscription_sync._server_engine`` 指向临时 SQLite，
绝不触碰生产库；user_id 使用 ``zztest-`` 前缀 UUID（验收测试数据规则）。
"""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine, text

import app.services.subscription_quota.subscription_sync as sync_mod
from app.services.subscription_quota.agent_subscription_scan import (
    AgentScanResult,
    ScanReport,
    ScannedSubscription,
    _scan_claude,
    _scan_codex,
    _scan_opencode,
    classify_channel,
)
from app.services.subscription_quota.subscription_sync import (
    _hash_key,
    _normalize,
    sync_local_subscriptions,
)

# ---------------------------------------------------------------- fixture


def _zztest_user() -> str:
    return f"zztest-{uuid.uuid4()}"


def _item(provider_id: str, key: str, *, channel: str = "官方", base_url: str = "",
          agent: str = "claude", provider_name: str = "") -> ScannedSubscription:
    return ScannedSubscription(
        provider_id=provider_id,
        provider_name=provider_name or provider_id,
        channel=channel,
        base_url=base_url,
        api_key=key,
        source_agents=[agent],
    )


def _report(*items: ScannedSubscription) -> ScanReport:
    return ScanReport(agents=[AgentScanResult(agent="claude", discovered=len(items))], items=list(items))


@pytest.fixture()
def sync_engine(tmp_path, monkeypatch):
    """临时 SQLite 作为远程库目标；重置模块级 schema 标记。"""
    engine = create_engine(f"sqlite:///{tmp_path / 'sync_test.db'}")
    monkeypatch.setattr(sync_mod, "_server_engine", lambda: engine)
    monkeypatch.setattr(sync_mod, "_schema_ready", False)
    yield engine
    engine.dispose()


def _rows(engine, user_id: str):
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT id, provider_id, label, api_key_hash, category, app, extra_json, is_channel "
                "FROM subscription_quota_accounts WHERE user_id = :uid ORDER BY sort_order"
            ),
            {"uid": user_id},
        ).fetchall()


# ---------------------------------------------------------------- 渠道分类（设计 §5.2）


def test_classify_channel_official():
    """无 base_url 或官方域名 → 渠道名「官方」+ official"""
    assert classify_channel("anthropic", "") == ("官方", "official")
    assert classify_channel("anthropic", "https://api.anthropic.com") == ("官方", "official")
    assert classify_channel("zhipu", "https://open.bigmodel.cn/paas/v4") == ("官方", "official")


def test_classify_channel_third_party():
    """中转 host → 渠道名 = host + third_party"""
    assert classify_channel("anthropic", "https://api.gptsapi.net/v1") == (
        "api.gptsapi.net",
        "third_party",
    )


# ---------------------------------------------------------------- 归一化与批内去重（§5.1）


def test_normalize_dedup_same_key_multi_source():
    """同 provider 同 Key 多来源 → 只保留一条，来源合并，cc-switch 元数据优先"""
    a = _item("anthropic", "sk-ant-shared-key-0001", agent="claude", base_url="https://relay.example.com")
    b = _item("anthropic", "sk-ant-shared-key-0001", agent="cc-switch", channel="官方")
    merged = _normalize(_report(b, a))  # claude 先扫到，cc-switch 后到
    assert len(merged) == 1
    assert merged[0].source_agents == ["cc-switch", "claude"]
    assert merged[0].channel == "官方"  # cc-switch 优先级更高，元数据胜出


def test_normalize_drops_empty_key_and_names_custom_provider():
    """空 Key 剔除；custom provider 显示名取 base_url host"""
    empty = _item("openai", "   ")
    custom = _item("custom", "sk-relay-key-123", base_url="https://api.example.com/v1")
    merged = _normalize(_report(empty, custom))
    assert len(merged) == 1
    assert merged[0].provider_name == "api.example.com"


# ---------------------------------------------------------------- 规则 1：同 provider + 同 Key 跳过


def test_rule1_same_provider_same_key_skipped(sync_engine, monkeypatch):
    """二次同步全 skip；label/extra 等原配置字段不被覆盖"""
    user = _zztest_user()
    key = "sk-ant-rule1-aaaaaaaa"
    monkeypatch.setattr(sync_mod, "scan_local_subscriptions", lambda: _report(_item("anthropic", key)))

    first = sync_local_subscriptions(user)
    assert first["created"] == 1 and first["skipped"] == 0

    second = sync_local_subscriptions(user)
    assert second["created"] == 0
    assert second["skipped"] == 1
    assert all(i["action"] == "skip" for i in second["items"])

    rows = _rows(sync_engine, user)
    assert len(rows) == 1  # 不重复插入


def test_rule1_backfills_hash_only(sync_engine, monkeypatch):
    """命中存量空 hash 行 → 仅回填 api_key_hash，其他字段原样"""
    from app.core.security import encrypt_api_key

    user = _zztest_user()
    key = "sk-ant-backfill-bbbb"
    sync_mod._ensure_schema()  # 手工造数前先建表（sync 主流程内部也会幂等建表）
    # 手工构造一条「老数据」：无 hash，label/extra 为用户自定义值
    with sync_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO subscription_quota_accounts "
                "(id, user_id, provider_id, label, api_key_enc, extra_json, api_key_hash) "
                "VALUES ('legacy-1', :uid, 'anthropic', '我的自定义名', :enc, '{\"user\":\"field\"}', '')"
            ),
            {"uid": user, "enc": encrypt_api_key(key)},
        )

    monkeypatch.setattr(sync_mod, "scan_local_subscriptions", lambda: _report(_item("anthropic", key)))
    result = sync_local_subscriptions(user)

    assert result["backfilled"] == 1
    assert result["created"] == 0
    row = _rows(sync_engine, user)[0]
    assert row.label == "我的自定义名"  # 用户配置未被覆盖
    assert json.loads(row.extra_json) == {"user": "field"}
    assert row.api_key_hash == _hash_key(key)  # 仅回填 hash


# ---------------------------------------------------------------- 规则 2：同 provider 同渠道不同 Key


def test_rule2_same_channel_different_keys_new_channel_rows(sync_engine, monkeypatch):
    """同渠道两条不同 Key → 两行渠道，第二条命名 ·Key后4位 区分"""
    user = _zztest_user()
    k1, k2 = "sk-ant-rule2-1111abcd", "sk-ant-rule2-2222wxyz"
    monkeypatch.setattr(
        sync_mod,
        "scan_local_subscriptions",
        lambda: _report(_item("anthropic", k1), _item("anthropic", k2)),
    )
    result = sync_local_subscriptions(user)

    assert result["created"] == 2
    rows = _rows(sync_engine, user)
    labels = [r.label for r in rows]
    assert len(set(labels)) == 2  # 命名互不相同
    assert labels[0].endswith("-官方")
    assert labels[1] == f"{labels[0]}·wxyz"  # 渠道命名以 Key 后 4 位区分
    # 同步写入的行必须是渠道行（is_channel=TRUE），不参与卡片展示
    assert all(r.is_channel for r in rows)


# ---------------------------------------------------------------- 账号/渠道行分离


def test_list_accounts_excludes_channel_rows(tmp_path, monkeypatch):
    """卡片数据源只含账号行：list_accounts 默认排除 is_channel 行，include_channels 可见全部"""
    from sqlalchemy import create_engine as _ce

    import app.services.subscription_quota.accounts as accounts_mod

    engine = _ce(f"sqlite:///{tmp_path / 'acct_test.db'}")
    monkeypatch.setenv("QUOTA_STORAGE", "local")
    monkeypatch.setattr(accounts_mod, "_get_engine", lambda: engine)
    monkeypatch.setattr(accounts_mod, "_schema_ready_by_location", set())

    user = _zztest_user()
    accounts_mod.create_account(user, "kimi", label="账号行", api_key="sk-acct-0001")
    accounts_mod.create_account(
        user, "kimi", label="渠道行", api_key="sk-chan-0001", is_channel=True
    )

    visible = accounts_mod.list_accounts(user)
    assert len(visible) == 1
    assert visible[0].label == "账号行"
    assert visible[0].is_channel is False
    # include_channels=True 返回全部（云渠道列表场景）
    assert len(accounts_mod.list_accounts(user, include_channels=True)) == 2


def test_rule2_batch_disambig_same_last4(sync_engine, monkeypatch):
    """同批三条同渠道同尾 4 位的不同 Key → ·尾4位 再冲突时 -2 递增兜底"""
    user = _zztest_user()
    keys = ["sk-ant-x-0001abcd", "sk-ant-x-0002abcd", "sk-ant-x-0003abcd"]
    monkeypatch.setattr(
        sync_mod,
        "scan_local_subscriptions",
        lambda: _report(*[_item("anthropic", k) for k in keys]),
    )
    result = sync_local_subscriptions(user)

    assert result["created"] == 3
    labels = [r.label for r in _rows(sync_engine, user)]
    assert len(set(labels)) == 3
    assert sorted(labels)[0].endswith("-官方")
    assert any(l.endswith("·abcd") for l in labels)
    assert any(l.endswith("·abcd-2") for l in labels)


def test_rule1_same_key_different_provider_not_duplicated(sync_engine, monkeypatch):
    """同一把 Key 已在其他供应商名下（如救援通道的 custom 次优归类）→ 不重复罗列，
    明细注明既有归属 provider"""
    user = _zztest_user()
    key = "sk-shared-across-providers-777"
    monkeypatch.setattr(sync_mod, "scan_local_subscriptions", lambda: _report(_item("custom", key)))
    first = sync_local_subscriptions(user)
    assert first["created"] == 1

    monkeypatch.setattr(
        sync_mod,
        "scan_local_subscriptions",
        lambda: _report(_item("new-api", key, agent="cc-switch")),
    )
    second = sync_local_subscriptions(user)
    assert second["created"] == 0
    assert second["skipped"] == 1
    assert second["items"][0]["existingProviderId"] == "custom"
    assert len(_rows(sync_engine, user)) == 1  # 全局唯一，不重复入库


# ---------------------------------------------------------------- 安全与 dry_run


def test_response_contains_no_plaintext_key(sync_engine, monkeypatch):
    """响应序列化后不含明文 Key，只有掩码"""
    user = _zztest_user()
    secret = "sk-ant-supersecret-9999"
    monkeypatch.setattr(sync_mod, "scan_local_subscriptions", lambda: _report(_item("anthropic", secret)))
    result = sync_local_subscriptions(user)

    blob = json.dumps(result, ensure_ascii=False, default=str)
    assert secret not in blob
    assert secret[:4] in blob  # 掩码前 4 位可见


def test_dry_run_writes_nothing(sync_engine, monkeypatch):
    """dry_run：不 INSERT、不回填"""
    user = _zztest_user()
    monkeypatch.setattr(
        sync_mod, "scan_local_subscriptions", lambda: _report(_item("deepseek", "sk-ds-dryrun-0001"))
    )
    result = sync_local_subscriptions(user, dry_run=True)

    assert result["dryRun"] is True
    assert result["created"] == 0 and result["backfilled"] == 0
    assert len(_rows(sync_engine, user)) == 0


# ---------------------------------------------------------------- 官方域名后缀匹配（2026-11-20 审计修复）


def test_official_host_suffix_matching():
    """子域名后缀匹配：coding.dashscope.aliyuncs.com 必须命中 qwen（审计实锤的遗漏场景）"""
    from app.services.subscription_quota.agent_subscription_scan import (
        official_provider_of_host,
    )

    assert official_provider_of_host("coding.dashscope.aliyuncs.com") == "qwen"
    assert official_provider_of_host("api.deepseek.com") == "deepseek"  # 精确匹配仍生效
    assert official_provider_of_host("relay.example.com") is None


def test_classify_channel_with_subdomain_official():
    assert classify_channel("qwen", "https://coding.dashscope.aliyuncs.com/v1") == (
        "官方",
        "official",
    )


# ---------------------------------------------------------------- cc-switch 救援通道（2026-11-20 审计修复）


def _make_ccswitch_db(path) -> None:
    """构造覆盖救援场景的 cc-switch 数据库（qwen 救援 / 本地网关 / OAuth JWT / 无 Key）"""
    import sqlite3

    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE providers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, "
        "app_type TEXT, settings_config TEXT, meta TEXT, sort_index INTEGER DEFAULT 0)"
    )
    rows = [
        # 名字不匹配已知 provider + coding 子域 → 救援通道按 host 后缀识别为 qwen
        ("qwen3.6-plus", "openclaw",
         {"apiKey": "sk-qwen-rescue-000123", "baseUrl": "https://coding.dashscope.aliyuncs.com/v1"}),
        # 本地网关回路（127.0.0.1）→ 不入库
        ("default", "gemini",
         {"env": {"GEMINI_API_KEY": "sk-localgw-aaaaaaaaaaaa00"}, "baseUrl": "http://127.0.0.1:8045"}),
        # OAuth JWT（eyJ 开头）→ 不入库
        ("OpenAI Official", "codex",
         {"auth": {"OPENAI_API_KEY": "eyJhbGciOiJIUzI1NiJ9." + "x" * 600}}),
        # 配置字段值伪装（compat.maxTokensField 含 token 被误抓）→ 不入库
        ("PeanutTokenPlan", "pi",
         {"compat": {"maxTokensField": "max_completion_tokens"},
          "baseUrl": "https://tokenproxy.example.com/v1"}),
        # 无 Key → 不入库
        ("Kimi K2.5", "openclaw", {"baseUrl": "https://api.moonshot.cn/v1"}),
    ]
    for name, app, cfg in rows:
        conn.execute(
            "INSERT INTO providers (name, app_type, settings_config, meta) VALUES (?,?,?,?)",
            (name, app, json.dumps(cfg), "{}"),
        )
    conn.commit()
    conn.close()


def test_scan_cc_switch_rescue_pass(tmp_path, monkeypatch):
    """救援通道：被 load_candidates 名字匹配丢弃的真实订阅（qwen）必须被 host 后缀匹配捞回；
    本地网关 / OAuth JWT / 配置值伪装 / 无 Key 四类正确不入库（reportOnly）"""
    from app.services.subscription_quota import usage_import
    from app.services.subscription_quota.agent_subscription_scan import _scan_cc_switch

    db_file = tmp_path / "cc-switch.db"
    _make_ccswitch_db(db_file)
    monkeypatch.setattr(usage_import, "ccswitch_db_path", lambda: db_file)

    items = []
    result = _scan_cc_switch(items)

    assert result.error is None
    assert result.discovered == 1
    assert result.report_only == 4
    rescued = items[0]
    assert rescued.provider_id == "qwen"
    assert rescued.channel == "官方"  # coding.dashscope 子域 → 官方渠道
    assert rescued.api_key == "sk-qwen-rescue-000123"
    assert rescued.source_agents == ["cc-switch"]
    # 不入库的 Key/伪 Key 绝不能出现在条目里
    joined = " ".join(i.api_key for i in items)
    assert "sk-localgw" not in joined and "eyJhbGciOiJIUzI1NiJ9" not in joined
    assert "max_completion_tokens" not in joined


# ---------------------------------------------------------------- 扫描器解析（tmp_path 伪造，不读真实凭据）


def test_scan_claude(tmp_path, monkeypatch):
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps(
            {
                "env": {
                    "ANTHROPIC_AUTH_TOKEN": "sk-ant-claude-123456",
                    "ANTHROPIC_BASE_URL": "https://relay.example.com/v1",
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    items = []
    result = _scan_claude(items)
    assert result.discovered == 1 and result.error is None
    assert items[0].provider_id == "anthropic"
    assert items[0].channel == "relay.example.com"
    assert items[0].api_key == "sk-ant-claude-123456"


def test_scan_claude_official_when_no_base_url(tmp_path, monkeypatch):
    (tmp_path / "settings.json").write_text(
        json.dumps({"env": {"ANTHROPIC_API_KEY": "sk-ant-official-654321"}}), encoding="utf-8"
    )
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    items = []
    _scan_claude(items)
    assert items[0].channel == "官方"


def test_scan_codex(tmp_path, monkeypatch):
    (tmp_path / "auth.json").write_text(
        json.dumps({"OPENAI_API_KEY": "sk-codex-test-abcdef"}), encoding="utf-8"
    )
    (tmp_path / "config.toml").write_text(
        'model_provider = "myrelay"\n[model_providers.myrelay]\nbase_url = "https://my-relay.example.com/v1"\n',
        encoding="utf-8",
    )
    monkeypatch.setenv("CODEX_HOME", str(tmp_path))
    items = []
    result = _scan_codex(items)
    assert result.discovered == 1
    assert items[0].api_key == "sk-codex-test-abcdef"
    assert items[0].base_url == "https://my-relay.example.com/v1"
    assert items[0].channel == "my-relay.example.com"


def test_scan_opencode(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    config_dir = tmp_path / "config" / "opencode"
    data_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    (data_dir / "auth.json").write_text(
        json.dumps({"zhipu": {"type": "api", "key": "zp-opencode-zhipu-0001"}}), encoding="utf-8"
    )
    (config_dir / "opencode.json").write_text(
        json.dumps(
            {
                "provider": {
                    "myrelay": {
                        "options": {
                            "baseURL": "https://relay2.example.com/v1",
                            "apiKey": "sk-opencode-relay-0002",
                        }
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENCODE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    items = []
    result = _scan_opencode(items)
    assert result.discovered == 2
    by_channel = {i.channel: i for i in items}
    assert by_channel["官方"].api_key == "zp-opencode-zhipu-0001"
    assert by_channel["relay2.example.com"].api_key == "sk-opencode-relay-0002"

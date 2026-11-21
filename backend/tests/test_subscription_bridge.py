"""订阅中心 ↔ 本机应用（bridge）单测

覆盖设计 ``specs/agent-subscription-bridge-design.md`` 的：
* §4.3 base_url 归一化
* §5 去重规则（URL+Key；同 URL 同 Key 跳过 / 同 URL 异 Key 新增 / 异 URL 同 Key 新增）
* §5 并发兜底（唯一索引冲突 → skip，不抛 500）
* §4.6 + §6.2/6.3 深链生成（CC Switch / Magpie）
* §6.1 导出响应 no-store
* 重复项报告
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine, text

from app.services.subscription_quota import subscription_sync as sync_mod
from app.services.subscription_quota.agent_subscription_scan import (
    ScannedSubscription,
)
from app.services.subscription_quota.dedupe import (
    ExistingIndex,
    dedupe_mode,
    find_duplicate_groups,
    item_key,
    mask_key,
    sha256_hex,
)
from app.services.subscription_quota.link_builder import (
    build_ccswitch_link,
    build_magpie_link,
    resolve_endpoint,
)
from app.services.subscription_quota.url_norm import normalize_base_url

KEY_A = "sk-bridge-test-key-aaaa1111"
KEY_B = "sk-bridge-test-key-bbbb2222"


def _zztest_user() -> str:
    """zztest- 前缀 + UUID（项目规则：测试数据可识别且可清理）"""
    return f"zztest-{uuid.uuid4()}"


# ---------------------------------------------------------------- §4.3 归一化


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", "official"),
        (None, "official"),
        ("   ", "official"),
        ("https://API.Kimi.com/coding/v1/", "https://api.kimi.com/coding"),
        ("https://api.deepseek.com/v1", "https://api.deepseek.com"),
        ("https://api.anthropic.com", "https://api.anthropic.com"),
        ("https://x.example.com/v1beta", "https://x.example.com"),
        ("https://x.example.com:443/v1", "https://x.example.com"),
        ("https://x.example.com:8443/v1", "https://x.example.com:8443"),
        ("https://x.example.com/anthropic/v1", "https://x.example.com/anthropic"),
        ("https://x.example.com/a?k=1#f", "https://x.example.com/a"),
        ("官方直连", "官方直连"),
    ],
)
def test_normalize_base_url(raw, expected):
    assert normalize_base_url(raw) == expected


def test_normalize_is_idempotent():
    once = normalize_base_url("https://API.Kimi.com/coding/v1/")
    assert normalize_base_url(once) == once


# ---------------------------------------------------------------- §5 去重键


def test_item_key_url_and_key():
    k1 = item_key("kimi", "https://api.kimi.com/coding/v1", KEY_A)
    k2 = item_key("kimi-coding", "https://api.kimi.com/coding/", KEY_A)
    # provider_id 不参与唯一性；URL 归一后相同 → 同一订阅
    assert k1 == k2
    assert k1 == ("url_key", "https://api.kimi.com/coding", sha256_hex(KEY_A))


def test_item_key_legacy_mode(monkeypatch):
    monkeypatch.setenv("QUOTA_DEDUPE_MODE", "legacy")
    assert dedupe_mode() == "legacy"
    key = item_key("kimi", "https://a.example.com", KEY_A)
    assert key == ("legacy", "kimi", sha256_hex(KEY_A))


def _rows(*specs):
    """构造 ExistingIndex 用的行（dict 即可）"""
    out = []
    for row_id, provider_id, base_url_norm, key, label in specs:
        out.append(
            {
                "id": row_id,
                "provider_id": provider_id,
                "base_url_norm": base_url_norm,
                "api_key_hash": sha256_hex(key),
                "api_key_enc": None,
                "label": label,
            }
        )
    return out


def test_decide_same_url_same_key_skips():
    index = ExistingIndex.from_rows(
        _rows(("row-1", "kimi", "https://api.kimi.com/coding", KEY_A, "Kimi-官方"))
    )
    decision = index.decide(
        provider_id="kimi-coding",
        provider_name="Kimi Code",
        channel="官方",
        base_url="https://api.kimi.com/coding/v1",
        api_key=KEY_A,
    )
    assert decision.action == "skip"
    assert decision.reason == "duplicate"


def test_decide_same_url_different_key_creates():
    index = ExistingIndex.from_rows(
        _rows(("row-1", "kimi", "https://api.kimi.com/coding", KEY_A, "Kimi-官方"))
    )
    decision = index.decide(
        provider_id="kimi",
        provider_name="Kimi Code",
        channel="官方",
        base_url="https://api.kimi.com/coding",
        api_key=KEY_B,
    )
    assert decision.action == "create"
    assert decision.label  # 消歧后的 label


def test_decide_different_url_same_key_creates():
    index = ExistingIndex.from_rows(
        _rows(("row-1", "kimi", "https://api.kimi.com/coding", KEY_A, "Kimi-官方"))
    )
    decision = index.decide(
        provider_id="kimi",
        provider_name="Kimi Code",
        channel="relay.example.com",
        base_url="https://relay.example.com/v1",
        api_key=KEY_A,
    )
    assert decision.action == "create"


def test_mask_key_no_plaintext():
    assert mask_key(KEY_A).endswith("1111")
    assert KEY_A not in mask_key(KEY_A)
    assert mask_key("short") == "*****"


def test_find_duplicate_groups():
    rows = [
        {
            "id": "r1",
            "user_id": "u1",
            "provider_id": "kimi",
            "label": "Kimi-1",
            "base_url": "",
            "base_url_norm": "https://a.example.com",
            "api_key_hash": sha256_hex(KEY_A),
        },
        {
            "id": "r2",
            "user_id": "u1",
            "provider_id": "kimi-coding",
            "label": "Kimi-2",
            "base_url": "",
            "base_url_norm": "https://a.example.com",
            "api_key_hash": sha256_hex(KEY_A),
        },
        {
            "id": "r3",
            "user_id": "u1",
            "provider_id": "kimi",
            "label": "Kimi-3",
            "base_url": "",
            "base_url_norm": "https://b.example.com",
            "api_key_hash": sha256_hex(KEY_A),
        },
    ]
    groups = find_duplicate_groups(rows)
    assert len(groups) == 1
    assert groups[0]["count"] == 2


# ---------------------------------------------------------------- 入库（临时 SQLite）


@pytest.fixture
def sync_engine(tmp_path, monkeypatch):
    """临时 SQLite 作为远程库目标；重置 schema 标记与去重模式"""
    engine = create_engine(f"sqlite:///{tmp_path / 'bridge_test.db'}")
    monkeypatch.setattr(sync_mod, "_server_engine", lambda: engine)
    monkeypatch.setattr(sync_mod, "_schema_ready", False)
    monkeypatch.delenv("QUOTA_DEDUPE_MODE", raising=False)
    yield engine
    engine.dispose()


def _item(provider_id, key, *, base_url="", channel="官方", agent="cc-switch", name=None):
    return ScannedSubscription(
        provider_id=provider_id,
        provider_name=name or provider_id,
        channel=channel,
        base_url=base_url,
        api_key=key,
        source_agents=[agent],
    )


def _rows_of(engine, user_id):
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT id, provider_id, label, base_url, base_url_norm, api_key_hash "
                "FROM subscription_quota_accounts WHERE user_id = :uid ORDER BY sort_order"
            ),
            {"uid": user_id},
        ).fetchall()


def test_ingest_stores_base_url_and_norm(sync_engine):
    user = _zztest_user()
    result = sync_mod.ingest_items(
        user, [_item("deepseek", KEY_A, base_url="https://api.deepseek.com/v1")]
    )
    assert result["created"] == 1
    row = _rows_of(sync_engine, user)[0]
    assert row.base_url == "https://api.deepseek.com/v1"
    assert row.base_url_norm == "https://api.deepseek.com"
    assert row.api_key_hash == sha256_hex(KEY_A)


def test_ingest_second_time_skips(sync_engine):
    user = _zztest_user()
    item = _item("deepseek", KEY_A, base_url="https://api.deepseek.com/v1")
    assert sync_mod.ingest_items(user, [item])["created"] == 1
    second = sync_mod.ingest_items(user, [_item("deepseek", KEY_A, base_url="https://api.deepseek.com")])
    assert second["created"] == 0
    assert second["skipped"] == 1
    assert second["items"][0]["reason"] == "duplicate"
    assert len(_rows_of(sync_engine, user)) == 1


def test_ingest_same_url_different_key_creates_two(sync_engine):
    user = _zztest_user()
    result = sync_mod.ingest_items(
        user,
        [
            _item("kimi", KEY_A, base_url="https://api.kimi.com/coding/v1"),
            _item("kimi", KEY_B, base_url="https://api.kimi.com/coding/v1"),
        ],
    )
    assert result["created"] == 2
    labels = [r.label for r in _rows_of(sync_engine, user)]
    assert len(set(labels)) == 2


def test_ingest_different_url_same_key_creates_two(sync_engine):
    user = _zztest_user()
    result = sync_mod.ingest_items(
        user,
        [
            _item("kimi", KEY_A, base_url="https://api.kimi.com/coding/v1"),
            _item("kimi", KEY_A, base_url="https://relay.example.com/v1", channel="relay.example.com"),
        ],
    )
    assert result["created"] == 2


def test_ingest_dry_run_writes_nothing(sync_engine):
    user = _zztest_user()
    result = sync_mod.ingest_items(
        user, [_item("deepseek", KEY_A, base_url="https://api.deepseek.com/v1")], dry_run=True
    )
    assert result["created"] == 0
    assert result["items"][0]["action"] == "create"
    assert _rows_of(sync_engine, user) == []


def test_ingest_unique_conflict_degrades_to_skip(sync_engine, monkeypatch):
    """并发写同一 (url,key)：唯一索引冲突必须降级为 skip，不能抛异常"""
    from sqlalchemy.exc import IntegrityError

    user = _zztest_user()
    original_begin = sync_engine.begin

    class _Boom(IntegrityError):
        pass

    calls = {"n": 0}

    def fake_begin():
        calls["n"] += 1
        if calls["n"] >= 2:
            raise IntegrityError("INSERT", {}, Exception("UNIQUE constraint failed"))
        return original_begin()

    monkeypatch.setattr(sync_engine, "begin", fake_begin)
    result = sync_mod.ingest_items(user, [_item("deepseek", KEY_A, base_url="https://api.deepseek.com")])
    assert result["created"] == 0
    assert result["skipped"] == 1
    assert result["items"][0]["reason"] == "duplicate"


def test_list_duplicates_detects_existing(sync_engine):
    """改造前的历史重复行（同 URL+Key 两行）必须能被报告出来（不删除）"""
    user = _zztest_user()
    sync_mod._ensure_schema()
    with sync_engine.begin() as conn:
        # 模拟索引上线前的历史数据：先摘索引再插入两行同键记录
        conn.execute(text("DROP INDEX IF EXISTS uq_sq_accounts_url_key"))
        for row_id in ("dup-1", "dup-2"):
            conn.execute(
                text(
                    "INSERT INTO subscription_quota_accounts "
                    "(id, user_id, provider_id, label, api_key_enc, extra_json, api_key_hash, "
                    " base_url, base_url_norm, is_channel) "
                    "VALUES (:rid, :uid, 'deepseek', :rid, NULL, '{}', :hash, "
                    " 'https://api.deepseek.com', 'https://api.deepseek.com', TRUE)"
                ),
                {"rid": row_id, "uid": user, "hash": sha256_hex(KEY_A)},
            )
    report = sync_mod.list_duplicates(user)
    assert report["count"] == 1
    assert report["groups"][0]["count"] == 2


# ---------------------------------------------------------------- 深链生成


def test_ccswitch_link_shape():
    result = build_ccswitch_link(
        provider_id="deepseek",
        label="DeepSeek-官方",
        base_url="https://api.deepseek.com/v1",
        api_key=KEY_A,
        extra={},
    )
    assert result.url and result.url.startswith("ccswitch://v1/import?")
    assert "app=codex" in result.url
    assert "enabled=false" in result.url
    assert result.url.count("apiKey=") == 1


def test_ccswitch_link_anthropic_protocol_for_kimi():
    result = build_ccswitch_link(
        provider_id="kimi", label="Kimi", base_url="", api_key=KEY_A, extra={}
    )
    assert "app=opencode" in result.url
    assert "apiFormat=anthropic" in result.url
    assert "api.kimi.com" in result.url  # 空 base_url 用默认 endpoint


def test_ccswitch_link_missing_key_warns():
    result = build_ccswitch_link(
        provider_id="deepseek", label="x", base_url="", api_key="", extra={}
    )
    assert result.url is None
    assert result.warnings


def test_magpie_link_preset_and_region():
    cn = build_magpie_link(
        provider_id="zhipu", label="GLM", base_url="", api_key=KEY_A, extra={"region": "cn"}
    )
    intl = build_magpie_link(
        provider_id="zhipu", label="GLM", base_url="", api_key=KEY_A, extra={"region": "intl"}
    )
    assert "preset=zhipu" in cn.url
    assert "preset=zai" in intl.url


def test_magpie_link_custom_relay_uses_anthropic():
    result = build_magpie_link(
        provider_id="custom-relay",
        label="My Relay",
        base_url="https://relay.example.com/v1",
        api_key=KEY_A,
        extra={},
    )
    assert result.url and "chat=" in result.url


def test_resolve_endpoint_region_override():
    assert resolve_endpoint("zhipu", "", {"region": "intl"}) == "https://api.z.ai/api/anthropic"
    assert resolve_endpoint("zhipu", "", {"region": "cn"}) == "https://open.bigmodel.cn/api/anthropic"
    assert resolve_endpoint("unknown-provider", "", {}) is None


# ---------------------------------------------------------------- 导出接口（no-store）


def test_export_links_sets_no_store_and_masks(monkeypatch):
    from app.routes import subscription_quota as route_mod
    from app.services.subscription_quota.accounts import QuotaAccount

    account = QuotaAccount(
        id="acc-1",
        user_id="u1",
        provider_id="deepseek",
        label="DeepSeek",
        api_key=KEY_A,
        base_url="https://api.deepseek.com/v1",
    )
    monkeypatch.setattr(route_mod, "list_accounts", lambda _uid: [account])
    monkeypatch.setattr(route_mod, "_require_user", lambda authorization, scope=None: "u1")
    route_mod._export_calls.clear()

    from fastapi import Response

    response = Response()
    payload = route_mod.export_links(response, target="ccswitch", ids=None, authorization="Bearer x")

    assert response.headers["Cache-Control"] == "no-store"
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["maskedKey"].endswith("1111")
    assert KEY_A not in str(item["maskedKey"])
    assert item["url"].startswith("ccswitch://")


def test_export_links_rejects_unknown_target(monkeypatch):
    from app.routes import subscription_quota as route_mod
    from fastapi import HTTPException, Response

    monkeypatch.setattr(route_mod, "_require_user", lambda authorization, scope=None: "u1")
    with pytest.raises(HTTPException) as exc:
        route_mod.export_links(Response(), target="nope", ids=None, authorization="Bearer x")
    assert exc.value.status_code == 400
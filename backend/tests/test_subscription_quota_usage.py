"""usage_import 单测（用临时 sqlite 造数据，不碰真实库）"""

import sqlite3

import pytest

from app.services.subscription_quota import usage_import


def _make_db(tmp_path, rows, providers=None):
    db = tmp_path / "cc-switch.db"
    conn = sqlite3.connect(db)
    conn.execute(
        """
        CREATE TABLE usage_daily_rollups (
            date TEXT, app_type TEXT, provider_id TEXT, model TEXT,
            request_model TEXT, pricing_model TEXT, request_count INTEGER,
            success_count INTEGER, input_tokens INTEGER, output_tokens INTEGER,
            cache_read_tokens INTEGER, cache_creation_tokens INTEGER,
            total_cost_usd REAL, avg_latency_ms INTEGER, input_token_semantics TEXT
        )
        """
    )
    conn.execute("CREATE TABLE providers (id TEXT, name TEXT)")
    for pid, name in (providers or []):
        conn.execute("INSERT INTO providers VALUES (?,?)", (pid, name))
    for row in rows:
        conn.execute(
            "INSERT INTO usage_daily_rollups VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            row,
        )
    conn.commit()
    conn.close()
    return db


def _row(date, provider_id, model, requests, cost, itok, otok, cread=0, ccreate=0):
    return (
        date, "claude", provider_id, model, model, None,
        requests, requests, itok, otok, cread, ccreate, cost, 100, "inclusive",
    )


@pytest.fixture
def patched_db(tmp_path, monkeypatch):
    db = _make_db(
        tmp_path,
        [
            _row("2026-10-18", "p1", "model-a", 100, 5.0, 1000, 200, 50, 10),
            _row("2026-10-19", "p1", "model-a", 50, 2.5, 500, 100),
            _row("2026-10-19", "p2", "model-b", 30, 1.5, 300, 60),
            _row("2026-09-01", "p1", "model-a", 999, 99.0, 1, 1),  # 超出 30 天窗口
        ],
        providers=[("p1", "Provider One"), ("p2", "Provider Two")],
    )
    monkeypatch.setattr(usage_import, "ccswitch_db_path", lambda: db)
    return db


def test_read_usage_totals(patched_db):
    summary = usage_import.read_usage(days=30)
    assert summary.available is True
    assert summary.days == 2
    assert summary.date_from == "2026-10-18"
    assert summary.date_to == "2026-10-19"
    totals = summary.totals
    assert totals.requests == 180  # 100 + 50 + 30
    assert totals.input_tokens == 1800
    assert totals.output_tokens == 360
    assert totals.cache_read_tokens == 50
    assert totals.cache_creation_tokens == 10
    assert totals.cost_usd == pytest.approx(9.0)
    assert totals.total_tokens == 1800 + 360 + 50 + 10


def test_read_usage_groups_by_provider_and_model(patched_db):
    summary = usage_import.read_usage(days=30)
    providers = {b.key: b for b in summary.by_provider}
    assert providers["Provider One"].requests == 150
    assert providers["Provider One"].cost_usd == pytest.approx(7.5)
    assert providers["Provider Two"].requests == 30

    models = {b.key: b for b in summary.by_model}
    assert models["model-a"].cost_usd == pytest.approx(7.5)
    assert models["model-b"].cost_usd == pytest.approx(1.5)


def test_read_usage_sorted_by_cost_desc(patched_db):
    summary = usage_import.read_usage(days=30)
    costs = [b.cost_usd for b in summary.by_provider]
    assert costs == sorted(costs, reverse=True)


def test_read_usage_day_window_excludes_old_rows(patched_db):
    summary = usage_import.read_usage(days=30)
    # 9-01 那行被窗口排除（只有 2 天数据，按「最近 N 个不同日期」取）
    day_keys = [b.key for b in summary.by_day]
    assert "2026-09-01" not in day_keys


def test_read_usage_missing_db(tmp_path, monkeypatch):
    monkeypatch.setattr(usage_import, "ccswitch_db_path", lambda: tmp_path / "nope.db")
    summary = usage_import.read_usage()
    assert summary.available is False
    assert "cc-switch" in (summary.message or "")


def test_read_usage_missing_table(tmp_path, monkeypatch):
    db = tmp_path / "empty.db"
    sqlite3.connect(db).close()
    monkeypatch.setattr(usage_import, "ccswitch_db_path", lambda: db)
    summary = usage_import.read_usage()
    assert summary.available is False
    assert "usage_daily_rollups" in (summary.message or "")


def test_read_usage_empty_table(tmp_path, monkeypatch):
    db = _make_db(tmp_path, [])
    monkeypatch.setattr(usage_import, "ccswitch_db_path", lambda: db)
    summary = usage_import.read_usage()
    assert summary.available is False
    assert "还没有任何用量记录" in (summary.message or "")


def test_usage_summary_to_dict_shape(patched_db):
    data = usage_import.read_usage(days=30).to_dict()
    for key in ("available", "days", "dateFrom", "dateTo", "totals", "byDay", "byProvider", "byModel"):
        assert key in data
    assert set(data["totals"].keys()) == {
        "key", "requests", "inputTokens", "outputTokens", "cacheReadTokens",
        "cacheCreationTokens", "totalTokens", "costUsd",
    }


def test_ccswitch_db_path_uses_real_home_not_overridden_home(tmp_path, monkeypatch):
    """回归：必须基于 REAL_HOME 解析，不能用被 config.py 覆盖后的 HOME。

    真实缺陷（2026-11-19）：``app.config.config`` 在非桌面模式把 ``HOME``
    改写为 ``backend/data/cache``，原实现用 ``Path.home()`` 解析，于是
    ``~/.cc-switch/cc-switch.db`` 被解析到缓存目录，本机明明装了 cc-switch，
    页面却报「未找到 cc-switch 数据库」。
    """
    fake_real_home = tmp_path / "real-home"
    fake_cache_home = tmp_path / "cache"
    fake_real_home.mkdir()
    fake_cache_home.mkdir()

    # 模拟 config.py 覆盖 HOME：进程内 HOME 指向缓存目录
    monkeypatch.setenv("HOME", str(fake_cache_home))
    monkeypatch.delenv("CCSWITCH_DB", raising=False)

    # 让 REAL_HOME 指向真实家目录（真实实现是模块级常量）
    import app.services.subscription_quota.credentials as credentials

    monkeypatch.setattr(credentials, "real_home", lambda: fake_real_home)

    resolved = usage_import.ccswitch_db_path()

    assert resolved == fake_real_home / ".cc-switch" / "cc-switch.db"
    # 关键断言：绝不能落到被覆盖的 HOME（缓存目录）下
    assert str(fake_cache_home) not in str(resolved)


def test_ccswitch_db_path_env_override_wins(monkeypatch, tmp_path):
    """CCSWITCH_DB 显式指定时优先级最高（便于测试和自定义安装位置）。"""
    custom = tmp_path / "custom" / "cc-switch.db"
    monkeypatch.setenv("CCSWITCH_DB", str(custom))
    assert usage_import.ccswitch_db_path() == custom


# ---------------------------------------------------------------- 存储位置（本机 / 远程）


def test_storage_defaults_to_local(monkeypatch):
    """默认必须存本机：订阅额度数据是每台设备各不相同的本机状态"""
    monkeypatch.delenv("QUOTA_STORAGE", raising=False)
    assert usage_import is not None  # 保持 import 使用痕迹
    from app.services.subscription_quota import accounts

    assert accounts._storage_location() == "local"
    assert accounts._use_local() is True


def test_storage_can_be_switched_to_server(monkeypatch):
    """显式 QUOTA_STORAGE=server 时走远程主库（多端共享场景）"""
    monkeypatch.setenv("QUOTA_STORAGE", "server")
    from app.services.subscription_quota import accounts

    assert accounts._storage_location() == "server"
    assert accounts._use_local() is False


def test_local_storage_engine_is_local_sqlite(monkeypatch, tmp_path):
    """本地模式的 engine 必须指向 ~/.toolbox/toolbox.db，绝不能是远程主库"""
    monkeypatch.delenv("QUOTA_STORAGE", raising=False)
    from app.services.subscription_quota import accounts

    engine = accounts._get_engine()
    url = str(engine.url)
    assert url.startswith("sqlite:///"), f"本地模式应是 SQLite，实际 {url}"
    assert ".toolbox" in url


def test_local_storage_encrypts_with_local_key(monkeypatch):
    """本地模式的密文必须用本机文件密钥（不能依赖远程主库的主密钥）"""
    monkeypatch.delenv("QUOTA_STORAGE", raising=False)
    from app.services.subscription_quota import accounts
    from app.storage.crypto import LocalEncryption

    plain = "sk-local-secret-key-for-test"
    cipher = accounts._encrypt_key(plain)

    # 能被本机密钥解开
    assert LocalEncryption.decrypt(cipher) == plain
    # 且密文形态不是 AES-GCM 的 v1: 前缀（那是远程主密钥的格式）
    assert not cipher.startswith("v1:")
    # 往返一致
    assert accounts._decrypt_key(cipher) == plain

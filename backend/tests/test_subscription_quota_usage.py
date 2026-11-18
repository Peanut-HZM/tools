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

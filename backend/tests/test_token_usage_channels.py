"""调用渠道（Token Usage channel）测试

覆盖：
- 渠道归一化 / 展示名 / base_url host 映射 / 模型前缀拆分
- aggregate_records 按渠道分桶（同模型不同渠道不合并）
- 同步 upsert 唯一键含渠道，且清理历史 NULL 行（不双计）
- /summary 与 /details 返回渠道维度、渠道筛选、渠道展示名
"""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base
from app.models.token_usage_models import TokenUsageRecord
from app.services.token_usage_sync_service import _upsert_records
from app.services.token_usage_schema import ensure_token_usage_channel_schema
from app.utils.agent_readers.base import aggregate_records
from app.utils.token_usage_channels import (
    channel_display_name,
    channel_from_base_url,
    normalize_channel,
    split_model_provider_prefix,
)


# ---------------------------------------------------------------------------
# 归一化 / 展示名 / 映射
# ---------------------------------------------------------------------------


def test_normalize_channel_aliases_and_raw_fallback():
    assert normalize_channel("peanut") == "peanut"
    assert normalize_channel("Kimi-Code") == "kimi-code"
    assert normalize_channel("opencode-go") == "opencode"
    assert normalize_channel("account:bigmodel-individual-coding-plan").startswith(
        "account:bigmodel"
    )
    assert normalize_channel("some-custom-provider") == "some-custom-provider"
    assert normalize_channel(None, "claude") == "claude-official"
    assert normalize_channel(None) == "unknown"


def test_channel_display_name():
    assert channel_display_name("peanut") == "花生 TokenProxy"
    assert channel_display_name("aliyun-bailian") == "阿里云百炼"
    assert channel_display_name("kimi-code-cn") == "kimi-code-cn"  # 未知原样展示
    assert channel_display_name("account:bigmodel-start-plan").startswith("智谱 GLM")
    assert channel_display_name(None) == "未知渠道"


def test_channel_from_base_url():
    assert (
        channel_from_base_url("https://tokenproxy.peanuthzm.com.cn/v1") == "peanut"
    )
    assert (
        channel_from_base_url("https://api.kimi.com/coding/v1") == "kimi-code"
    )
    assert (
        channel_from_base_url("https://open.bigmodel.cn/api/paas/v4") == "zhipu"
    )
    assert channel_from_base_url("http://127.0.0.1:8080/v1") == "local-gateway"
    assert channel_from_base_url("https://unknown.example.com/v1") is None


def test_split_model_provider_prefix():
    assert split_model_provider_prefix("peanut/claude-opus-5.0", "kimi") == (
        "peanut",
        "claude-opus-5.0",
    )
    assert split_model_provider_prefix("kimi-code/k3.1-pro", "kimi") == (
        "kimi-code",
        "k3.1-pro",
    )
    assert split_model_provider_prefix("k3.1-pro", "kimi") == ("kimi-code", "k3.1-pro")


# ---------------------------------------------------------------------------
# 聚合按渠道分桶
# ---------------------------------------------------------------------------


def test_aggregate_records_splits_same_model_by_channel():
    day = date(2026, 1, 2)
    rows = [
        {
            "record_date": day,
            "model": "deepseek-v4.1-flash",
            "channel": "peanut",
            "input_tokens": 10,
            "output_tokens": 5,
        },
        {
            "record_date": day,
            "model": "deepseek-v4.1-flash",
            "channel": "aliyun-bailian",
            "input_tokens": 20,
            "output_tokens": 7,
        },
    ]

    records = aggregate_records(rows, source="opencode")

    assert len(records) == 2
    by_channel = {record["channel"]: record for record in records}
    assert by_channel["peanut"]["input_tokens"] == 10
    assert by_channel["aliyun-bailian"]["input_tokens"] == 20


# ---------------------------------------------------------------------------
# 同步 upsert：唯一键 + 历史 NULL 行清理
# ---------------------------------------------------------------------------


@pytest.fixture
def db_session(tmp_path):
    db_path = tmp_path / "channel.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _record(**kwargs):
    base = {
        "user_id": "user-1",
        "device_id": "device-1",
        "record_date": date(2026, 1, 2),
        "source": "opencode",
        "tool_id": "opencode",
        "tool_name": "OpenCode",
        "model": "deepseek-v4.1-flash",
        "model_display_name": "deepseek-v4.1-flash",
        "input_tokens": 1,
        "output_tokens": 1,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
        "total_tokens": 2,
        "total_cost": 0,
    }
    base.update(kwargs)
    return TokenUsageRecord(**base)


def test_upsert_keeps_channels_apart_and_removes_legacy_null(db_session):
    # 历史 legacy 行（改造前没有 channel）
    db_session.add(
        _record(channel=None, input_tokens=100, output_tokens=100, total_tokens=200)
    )
    db_session.commit()

    records = [
        {
            "record_date": date(2026, 1, 2),
            "model": "deepseek-v4.1-flash",
            "channel": "peanut",
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "total_tokens": 15,
            "total_cost": 0.0,
        },
        {
            "record_date": date(2026, 1, 2),
            "model": "deepseek-v4.1-flash",
            "channel": "aliyun-bailian",
            "input_tokens": 20,
            "output_tokens": 7,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "total_tokens": 27,
            "total_cost": 0.0,
        },
    ]

    count = _upsert_records(
        db_session, "user-1", "device-1", "opencode", records, "device-1"
    )
    db_session.commit()

    rows = (
        db_session.query(TokenUsageRecord)
        .filter(TokenUsageRecord.user_id == "user-1")
        .all()
    )
    assert count == 2
    assert len(rows) == 2
    assert {row.channel for row in rows} == {"peanut", "aliyun-bailian"}
    # legacy NULL 行被清理，总量不翻倍
    assert sum(row.input_tokens for row in rows) == 30


def test_upsert_is_idempotent(db_session):
    records = [
        {
            "record_date": date(2026, 1, 2),
            "model": "deepseek-v4.1-flash",
            "channel": "peanut",
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_creation_tokens": 0,
            "cache_read_tokens": 0,
            "total_tokens": 15,
            "total_cost": 0.0,
        }
    ]
    _upsert_records(db_session, "user-1", "device-1", "opencode", records, "device-1")
    db_session.commit()
    _upsert_records(db_session, "user-1", "device-1", "opencode", records, "device-1")
    db_session.commit()

    count = (
        db_session.query(TokenUsageRecord)
        .filter(TokenUsageRecord.user_id == "user-1")
        .count()
    )
    assert count == 1


def test_ensure_channel_schema_is_idempotent_on_sqlite(db_session):
    # 全量 ORM 建表后调用迁移：不应报错，可重复执行
    engine = db_session.get_bind()
    assert ensure_token_usage_channel_schema(engine) is True
    assert ensure_token_usage_channel_schema(engine) is True


# ---------------------------------------------------------------------------
# API：渠道维度 / 筛选 / 明细字段
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def no_side_effects(monkeypatch):
    monkeypatch.setattr(
        "app.routes.token_usage._maybe_trigger_stale_sync", lambda *a, **k: None
    )
    # 隔离 Redis 缓存，避免命中其他测试的数据
    monkeypatch.setattr(
        "app.services.token_usage_cache.get_query_cached_payload",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(
        "app.services.token_usage_cache.set_query_cached_data",
        lambda *a, **k: False,
    )


@pytest.fixture
def seeded_session(db_session):
    base = date.today()
    db_session.add_all(
        [
            _record(
                channel="peanut",
                record_date=base,
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
            ),
            _record(
                channel="aliyun-bailian",
                record_date=base,
                input_tokens=20,
                output_tokens=7,
                total_tokens=27,
            ),
        ]
    )
    db_session.commit()
    return db_session


def test_summary_returns_channel_dimension(client, seeded_session):
    with patch("app.routes.token_usage.SessionLocal", return_value=seeded_session):
        with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
            response = client.get(
                "/api/token-usage/summary",
                params={"type": "daily", "days": 30, "source": "all"},
                headers={"Authorization": "Bearer test-token"},
            )

    assert response.status_code == 200
    data = response.json()
    channels = data["dimension_summaries"]["channels"]
    assert {item["channel"] for item in channels} == {"peanut", "aliyun-bailian"}
    assert {item["channel_name"] for item in channels} == {
        "花生 TokenProxy",
        "阿里云百炼",
    }
    assert {item["channel"] for item in data["filter_options"]["channels"]} == {
        "peanut",
        "aliyun-bailian",
    }
    # 渠道拆分不改变总量
    assert data["summary"]["total_tokens"] == 42


def test_summary_filters_by_channel(client, seeded_session):
    with patch("app.routes.token_usage.SessionLocal", return_value=seeded_session):
        with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
            response = client.get(
                "/api/token-usage/summary",
                params={"type": "daily", "days": 30, "channel": "peanut"},
                headers={"Authorization": "Bearer test-token"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["total_tokens"] == 15
    assert len(data["dimension_summaries"]["channels"]) == 1


def test_details_returns_channel_fields(client, seeded_session):
    with patch("app.routes.token_usage.SessionLocal", return_value=seeded_session):
        with patch("app.routes.token_usage.get_current_user_id", return_value="user-1"):
            response = client.post(
                "/api/token-usage/details",
                json={"type": "daily", "days": 30, "limit": 10, "offset": 0},
                headers={"Authorization": "Bearer test-token"},
            )

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 2
    assert {item["channel"] for item in items} == {"peanut", "aliyun-bailian"}
    assert {item["channel_name"] for item in items} == {
        "花生 TokenProxy",
        "阿里云百炼",
    }
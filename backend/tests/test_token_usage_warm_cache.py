"""warm_query_cache 单元测试：同步完成后预热完整 summary 缓存。"""
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from app.services import token_usage_cache


def _make_full_payload():
    """返回一个含全部字段的完整 payload，模拟 _build_summary_payload 真实输出。"""
    return {
        "summary": {
            "total_input_tokens": 100,
            "total_output_tokens": 50,
            "total_cache_creation_tokens": 10,
            "total_cache_read_tokens": 20,
            "total_tokens": 180,
            "total_cost": 0.01,
            "days_count": 17,
            "avg_daily_cost": 0.0006,
        },
        "dimension_summaries": {},
        "model_summary": [],
        "filter_options": {},
        "sync_meta": {},
        "chart_series": [],
        "devices": [],
    }


def test_warm_returns_false_when_user_has_no_data():
    """用户无数据时不预热，返回 False。"""
    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.first.return_value = None

    with patch("app.models.base.SessionLocal", return_value=fake_db):
        with patch("app.services.token_usage_cache.set_query_cached_data") as mock_set:
            result = token_usage_cache.warm_query_cache("user-empty")

    assert result is False
    mock_set.assert_not_called()


def test_warm_writes_cache_when_user_has_data():
    """用户有数据时调 _build_summary_payload 并 set_query_cached_data 写入预热缓存。"""
    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.first.return_value = MagicMock()

    fake_payload = _make_full_payload()

    with patch("app.models.base.SessionLocal", return_value=fake_db):
        with patch(
            "app.routes.token_usage._build_summary_payload",
            return_value=fake_payload,
        ) as mock_build:
            with patch(
                "app.services.token_usage_cache.set_query_cached_data",
                return_value=True,
            ) as mock_set:
                result = token_usage_cache.warm_query_cache("user-1")

    assert result is True
    mock_build.assert_called_once()
    mock_set.assert_called_once()
    call_kwargs = mock_set.call_args.kwargs
    # 预热的是 daily/30天/all/none 这个最常用组合
    assert call_kwargs["report_type"] == "daily"
    assert call_kwargs["days"] == 30
    assert call_kwargs["source"] == "all"
    assert call_kwargs["group_by"] == "none"
    assert call_kwargs["user_id"] == "user-1"
    # 写的是完整 payload（含 dimension/chart 等全部字段）
    assert call_kwargs["data"] == fake_payload


def test_warm_returns_false_when_redis_unavailable():
    """Redis 不可用（set 返回 False）时整体返回 False，不抛异常。"""
    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.first.return_value = MagicMock()

    with patch("app.models.base.SessionLocal", return_value=fake_db):
        with patch(
            "app.routes.token_usage._build_summary_payload",
            return_value=_make_full_payload(),
        ):
            with patch(
                "app.services.token_usage_cache.set_query_cached_data",
                return_value=False,
            ):
                result = token_usage_cache.warm_query_cache("user-1")

    assert result is False


def test_warm_returns_false_when_build_payload_returns_none():
    """_build_summary_payload 返回 None（有数据但聚合为空）时不写缓存。"""
    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.first.return_value = MagicMock()

    with patch("app.models.base.SessionLocal", return_value=fake_db):
        with patch(
            "app.routes.token_usage._build_summary_payload",
            return_value=None,
        ):
            with patch("app.services.token_usage_cache.set_query_cached_data") as mock_set:
                result = token_usage_cache.warm_query_cache("user-1")

    assert result is False
    mock_set.assert_not_called()


def test_warm_returns_false_on_exception():
    """任意异常被吞掉，返回 False，不影响同步主流程。"""
    fake_db = MagicMock()
    fake_db.query.return_value.filter.return_value.first.side_effect = RuntimeError("db down")

    with patch("app.models.base.SessionLocal", return_value=fake_db):
        with patch("app.services.token_usage_cache.set_query_cached_data") as mock_set:
            result = token_usage_cache.warm_query_cache("user-1")

    assert result is False
    mock_set.assert_not_called()

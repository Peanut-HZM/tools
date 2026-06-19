"""测试 UsageFetcherV2 调用 ccusage CLI 的参数正确性。"""
from unittest.mock import patch, MagicMock

from app.utils.usage_fetcher_v2 import UsageFetcherV2


def test_fetch_ccusage_daily_uses_correct_flags():
    """验证 cmd 包含 ccusage daily --json --since X --until Y --offline"""
    fake_result = {
        "daily": [
            {
                "agent": "all",
                "period": "2026-06-05",
                "inputTokens": 100, "outputTokens": 10,
                "cacheCreationTokens": 0, "cacheReadTokens": 0,
                "totalTokens": 110, "totalCost": 0.001,
                "modelsUsed": ["claude-opus-4-8"],
                "modelBreakdowns": [
                    {"modelName": "claude-opus-4-8", "inputTokens": 100, "outputTokens": 10,
                     "cacheCreationTokens": 0, "cacheReadTokens": 0, "cost": 0.001},
                ],
                "metadata": {"agents": ["claude"]},
            }
        ],
        "totals": {"inputTokens": 100, "outputTokens": 10, "totalTokens": 110, "totalCost": 0.001}
    }

    with patch("app.utils.usage_fetcher_v2.run_ccusage", return_value={"ok": True, "data": fake_result}) as mock_run, \
         patch("app.utils.usage_fetcher_v2._get_from_cache", return_value=None), \
         patch("app.utils.usage_fetcher_v2._set_cache"), \
         patch("app.utils.usage_fetcher_v2.find_ccusage", return_value="/usr/bin/ccusage"):
        UsageFetcherV2.fetch_ccusage_daily(since="2026-06-05", until="2026-06-05")

    args = mock_run.call_args[0][0]
    assert args[0] == "daily"
    assert "--json" in args
    assert "--since=2026-06-05" in args
    assert "--until=2026-06-05" in args
    assert "--offline" in args


def test_fetch_ccusage_agent_daily_opencode():
    """验证 ccusage opencode daily 调用参数正确"""
    fake_result = {
        "daily": [
            {
                "date": "2026-06-05",
                "inputTokens": 100, "outputTokens": 10,
                "cacheCreationTokens": 0, "cacheReadTokens": 0,
                "totalTokens": 110, "totalCost": 0.0,
                "modelsUsed": ["minimax-m3-free"],
            }
        ],
        "totals": {"inputTokens": 100, "outputTokens": 10, "totalTokens": 110, "totalCost": 0.0}
    }

    with patch("app.utils.usage_fetcher_v2.run_ccusage", return_value={"ok": True, "data": fake_result}) as mock_run, \
         patch("app.utils.usage_fetcher_v2._get_from_cache", return_value=None), \
         patch("app.utils.usage_fetcher_v2._set_cache"), \
         patch("app.utils.usage_fetcher_v2.find_ccusage", return_value="/usr/bin/ccusage"):
        UsageFetcherV2.fetch_ccusage_agent_daily(
            agent="opencode", since="2026-06-05", until="2026-06-05"
        )

    args = mock_run.call_args[0][0]
    assert args[0] == "opencode"
    assert args[1] == "daily"
    assert "--json" in args
    assert "--since=2026-06-05" in args
    assert "--until=2026-06-05" in args

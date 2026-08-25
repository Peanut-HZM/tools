"""测试 _parse_agent_daily 解析 ccusage <agent> daily 的模型级明细。"""
import pytest

from app.services.token_usage_sync_service import _parse_agent_daily


# ---------- _parse_agent_daily ----------

def test_parse_agent_daily_with_model_breakdowns():
    """单 agent daily（含 modelBreakdowns）→ 全部归属该 agent，不做推断"""
    daily = [
        {
            "agent": "opencode",
            "date": "2026-08-22",
            "modelBreakdowns": [
                {"modelName": "deepseek-v4-pro", "inputTokens": 1213752, "outputTokens": 181448,
                 "cacheCreationTokens": 0, "cacheReadTokens": 51441792, "cost": 1.0188},
            ],
        }
    ]
    records = _parse_agent_daily("opencode", daily)
    assert len(records) == 1
    r = records[0]
    assert r["source"] == "opencode"
    assert r["tool_name"] == "OpenCode"
    assert r["model"] == "deepseek-v4-pro"
    assert r["record_date"].isoformat() == "2026-08-22"
    assert r["input_tokens"] == 1213752
    assert r["output_tokens"] == 181448
    assert r["cache_read_tokens"] == 51441792
    assert r["total_tokens"] == 1213752 + 181448 + 51441792
    assert r["total_cost"] == pytest.approx(1.0188)
    assert r["source_raw"] == "ccusage-agent-daily"


def test_parse_agent_daily_shared_model_keeps_both_agents():
    """claude 与 opencode 同日共用同一模型 → 各自明细独立保留，不互相吞并"""
    claude_daily = [
        {
            "agent": "claude",
            "date": "2026-08-22",
            "modelBreakdowns": [
                {"modelName": "deepseek-v4-pro", "inputTokens": 4935803, "outputTokens": 16083,
                 "cacheCreationTokens": 0, "cacheReadTokens": 851968, "cost": 0.0},
            ],
        }
    ]
    opencode_daily = [
        {
            "agent": "opencode",
            "date": "2026-08-22",
            "modelBreakdowns": [
                {"modelName": "deepseek-v4-pro", "inputTokens": 1213752, "outputTokens": 181448,
                 "cacheCreationTokens": 0, "cacheReadTokens": 51441792, "cost": 1.0188},
            ],
        }
    ]
    claude_records = _parse_agent_daily("claude", claude_daily)
    opencode_records = _parse_agent_daily("opencode", opencode_daily)

    assert len(claude_records) == 1 and claude_records[0]["source"] == "claude"
    assert len(opencode_records) == 1 and opencode_records[0]["source"] == "opencode"
    # opencode 的用量不被 claude 吞掉
    assert opencode_records[0]["cache_read_tokens"] == 51441792
    assert claude_records[0]["cache_read_tokens"] == 851968


def test_parse_agent_daily_period_field():
    """daily 条目使用 period 字段而非 date → 也能解析日期"""
    daily = [
        {
            "agent": "claude",
            "period": "2026-08-20",
            "modelBreakdowns": [
                {"modelName": "k3", "inputTokens": 100, "outputTokens": 10,
                 "cacheCreationTokens": 0, "cacheReadTokens": 5, "cost": 0.1},
            ],
        }
    ]
    records = _parse_agent_daily("claude", daily)
    assert len(records) == 1
    assert records[0]["record_date"].isoformat() == "2026-08-20"
    assert records[0]["total_tokens"] == 115


def test_parse_agent_daily_models_dict_format():
    """codex 等 agent 使用 models 字典（{model: {input, output, ...}}）→ 逐模型解析"""
    daily = [
        {
            "agent": "codex",
            "date": "2026-08-19",
            "models": {
                "anthropic--claude-4.7-opus": {
                    "input": 323940, "output": 22804,
                    "cache_read": 3184128, "cache_write": 0, "cost": 3.7819,
                },
            },
        }
    ]
    records = _parse_agent_daily("codex", daily)
    assert len(records) == 1
    r = records[0]
    assert r["source"] == "codex"
    assert r["model"] == "anthropic--claude-4.7-opus"
    assert r["input_tokens"] == 323940
    assert r["output_tokens"] == 22804
    assert r["cache_read_tokens"] == 3184128
    assert r["total_tokens"] == 323940 + 22804 + 3184128
    assert r["total_cost"] == pytest.approx(3.7819)


def test_parse_agent_daily_empty():
    """空 daily 数组 → 0 条"""
    assert _parse_agent_daily("opencode", []) == []


def test_parse_agent_daily_skips_invalid_date():
    """日期字段缺失/非法 → 跳过该天"""
    daily = [
        {"agent": "opencode", "modelBreakdowns": [
            {"modelName": "m1", "inputTokens": 1, "outputTokens": 1,
             "cacheCreationTokens": 0, "cacheReadTokens": 0}]},
        {"agent": "opencode", "date": "not-a-date", "modelBreakdowns": [
            {"modelName": "m2", "inputTokens": 1, "outputTokens": 1,
             "cacheCreationTokens": 0, "cacheReadTokens": 0}]},
    ]
    assert _parse_agent_daily("opencode", daily) == []

"""测试 _parse_ccusage_records 解析 ccusage daily + per-agent JSON。"""
import pytest

from app.services.token_usage_sync_service import _infer_agent, _parse_ccusage_records


# ---------- _infer_agent ----------

def test_infer_agent_basic_unique_model():
    """模型名只在 claude 的 modelsUsed 中 → 归属 claude"""
    agent_dict = {
        "2026-06-05": {
            "claude": {"claude-opus-4-8", "gpt-5.5"},
            "opencode": {"minimax-m3-free"},
        }
    }
    assert _infer_agent("claude-opus-4-8", "2026-06-05", agent_dict) == "claude"
    assert _infer_agent("minimax-m3-free", "2026-06-05", agent_dict) == "opencode"


def test_infer_agent_ambiguous_qwen_prefers_claude():
    """qwen3.6-plus 同时在 claude + opencode 列表 → 按优先级选 claude"""
    agent_dict = {
        "2026-06-05": {
            "claude": {"qwen3.6-plus", "claude-opus-4-8"},
            "opencode": {"qwen3.6-plus", "minimax-m3-free"},
        }
    }
    assert _infer_agent("qwen3.6-plus", "2026-06-05", agent_dict) == "claude"


def test_infer_agent_unknown_model_returns_other():
    """模型名不在任何 agent 列表 → 兜底 'other'"""
    agent_dict = {
        "2026-06-05": {
            "claude": {"claude-opus-4-8"},
        }
    }
    assert _infer_agent("unknown-model-xyz", "2026-06-05", agent_dict) == "other"


def test_infer_agent_empty_dict_returns_other():
    """agent 字典为空 → 'other'"""
    assert _infer_agent("any-model", "2026-06-05", {}) == "other"


# ---------- _parse_ccusage_records ----------

def test_parse_ccusage_daily_with_model_breakdowns():
    """1 日完整 JSON（含 modelBreakdowns + 2 agent 归属）→ 多条 (date, agent, model) 记录"""
    daily = [
        {
            "agent": "all",
            "period": "2026-06-05",
            "modelBreakdowns": [
                {"modelName": "claude-opus-4-8", "inputTokens": 215984263, "outputTokens": 213810,
                 "cacheCreationTokens": 0, "cacheReadTokens": 0, "cost": 1085.26},
                {"modelName": "gpt-5.5", "inputTokens": 1341214, "outputTokens": 13184,
                 "cacheCreationTokens": 0, "cacheReadTokens": 589824, "cost": 7.40},
                {"modelName": "minimax-m3-free", "inputTokens": 2504169, "outputTokens": 233288,
                 "cacheCreationTokens": 0, "cacheReadTokens": 51132786, "cost": 0.0},
            ],
            "metadata": {"agents": ["claude", "opencode"]},
        }
    ]
    agent_models = {
        "2026-06-05": {
            "claude": {"claude-opus-4-8", "gpt-5.5"},
            "opencode": {"minimax-m3-free", "qwen3.6-plus"},
        }
    }
    records = _parse_ccusage_records(daily, agent_models)
    assert len(records) == 3
    # claude-opus-4-8 → claude
    r = next(r for r in records if r["model"] == "claude-opus-4-8")
    assert r["source"] == "claude"
    assert r["record_date"].isoformat() == "2026-06-05"
    assert r["input_tokens"] == 215984263
    assert r["output_tokens"] == 213810
    assert r["cache_creation_tokens"] == 0
    assert r["cache_read_tokens"] == 0
    assert r["total_tokens"] == 216198073
    assert r["total_cost"] == 1085.26
    # minimax-m3-free → opencode
    r = next(r for r in records if r["model"] == "minimax-m3-free")
    assert r["source"] == "opencode"
    assert r["total_cost"] == 0.0


def test_parse_ccusage_daily_empty():
    """空 daily 数组 → 0 条"""
    records = _parse_ccusage_records([], {})
    assert records == []


def test_parse_ccusage_daily_with_no_agents_metadata():
    """agent 字典无该日期 → 模型全归 'other'"""
    daily = [
        {
            "agent": "all",
            "period": "2026-06-05",
            "modelBreakdowns": [
                {"modelName": "claude-opus-4-8", "inputTokens": 100, "outputTokens": 10,
                 "cacheCreationTokens": 0, "cacheReadTokens": 0, "cost": 1.0},
            ],
        }
    ]
    records = _parse_ccusage_records(daily, {})  # 空字典
    assert len(records) == 1
    assert records[0]["source"] == "other"
    assert records[0]["model"] == "claude-opus-4-8"
    assert records[0]["total_tokens"] == 110

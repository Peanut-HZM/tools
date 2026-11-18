"""cc-switch 导入脚本单测（不碰真实数据库）"""

import json
import sqlite3

import pytest

from scripts.import_ccswitch_providers import (
    PROVIDER_HINTS,
    _collect_secrets,
    _collect_urls,
    _match_provider,
    _pick_key,
    _region_of,
    load_candidates,
)


def test_match_provider_by_name():
    assert _match_provider("OpenDesign") == "opendesign"
    assert _match_provider("Zhipu GLM") == "zhipu"
    assert _match_provider("DeepSeek") == "deepseek"
    assert _match_provider("SiliconFlow") == "siliconflow"


def test_match_provider_does_not_match_transit_relay_as_opencode_go():
    """中转站配置（app_type=opencode）不能被误判成 OpenCode Go 订阅"""
    assert _match_provider("Peanut TokenProxy", "https://tokenproxy.example.com/v1") is None
    assert (
        _match_provider("OpenCode Go", "https://opencode.ai/zen/go/v1") == "opencode_go"
    )


def test_match_provider_opendesign_by_url():
    assert _match_provider("", "https://amr-link.open-design.ai/v1") == "opendesign"


def test_region_of():
    assert _region_of("https://api.minimaxi.com") == "cn"
    assert _region_of("https://api.minimax.io") == "intl"
    assert _region_of("https://api.kimi.ai/coding") == "intl"


def test_collect_secrets_and_urls():
    cfg = {
        "env": {"ANTHROPIC_AUTH_TOKEN": "sk-abc", "ANTHROPIC_BASE_URL": "https://x.ai"},
        "options": {"apiKey": "sk-def"},
        "models": {"m": {"limit": {"context": 100}}},
    }
    secrets = _collect_secrets(cfg)
    assert secrets["env.ANTHROPIC_AUTH_TOKEN"] == "sk-abc"
    assert secrets["options.apiKey"] == "sk-def"
    urls = _collect_urls(cfg)
    assert "https://x.ai" in urls


def test_pick_key_priority():
    secrets = {"env.ANTHROPIC_AUTH_TOKEN": "sk-primary-key-1234567890", "options.apiKey": "other"}
    assert _pick_key(secrets) == "sk-primary-key-1234567890"


def test_pick_key_ignores_short_values():
    assert _pick_key({"apiKey": "short"}) is None


def _make_db(tmp_path, providers):
    db = tmp_path / "cc-switch.db"
    conn = sqlite3.connect(db)
    conn.execute(
        """
        CREATE TABLE providers (
            id TEXT, app_type TEXT, name TEXT, settings_config TEXT,
            meta TEXT, sort_index INTEGER
        )
        """
    )
    for idx, item in enumerate(providers):
        conn.execute(
            "INSERT INTO providers VALUES (?,?,?,?,?,?)",
            (
                item.get("id", f"p{idx}"),
                item.get("app_type", "claude"),
                item.get("name", ""),
                json.dumps(item.get("settings_config", {})),
                json.dumps(item.get("meta", {})),
                idx,
            ),
        )
    conn.commit()
    conn.close()
    return db


def test_load_candidates_prefers_control_key(tmp_path):
    db = _make_db(
        tmp_path,
        [
            {
                "name": "OpenDesign",
                "settings_config": {
                    "env": {
                        "ANTHROPIC_AUTH_TOKEN": "sk-amr-runtime-key-abcdefghij",
                        "ANTHROPIC_BASE_URL": "https://amr-link.open-design.ai",
                    }
                },
                "meta": {
                    "usage_script": {"apiKey": "vela_ctrl_controlkey", "codingPlanProvider": "opendesign"}
                },
            }
        ],
    )
    candidates = load_candidates(db)
    assert len(candidates) == 1
    assert candidates[0]["provider_id"] == "opendesign"
    # 必须优先用控制面 Key（推理 Key 查不了账单）
    assert candidates[0]["api_key"] == "vela_ctrl_controlkey"
    assert candidates[0]["from_control_key"] is True
    assert candidates[0]["inference_key"] == "sk-amr-runtime-key-abcdefghij"


def test_load_candidates_falls_back_to_inference_key(tmp_path):
    db = _make_db(
        tmp_path,
        [
            {
                "name": "DeepSeek",
                "settings_config": {
                    "env": {"ANTHROPIC_AUTH_TOKEN": "sk-deepseek-key-1234567890"}
                },
            }
        ],
    )
    candidates = load_candidates(db)
    assert len(candidates) == 1
    assert candidates[0]["provider_id"] == "deepseek"
    assert candidates[0]["from_control_key"] is False


def test_load_candidates_skips_unknown_and_keyless(tmp_path):
    db = _make_db(
        tmp_path,
        [
            {"name": "Claude Desktop Official", "settings_config": {}},
            {"name": "Some Relay", "settings_config": {"options": {"apiKey": "sk-relay-key-1234567890"}}},
        ],
    )
    assert load_candidates(db) == []

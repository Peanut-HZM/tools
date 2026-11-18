"""ZCode provider_config 发现单测"""

import json

import pytest

from app.services.subscription_quota.zcode_provider_config import (
    _match_provider,
    _region_of,
    read_provider_keys,
)


def test_match_provider_by_id_and_name():
    assert _match_provider("kimi-code-cn", "Kimi Code（国内）") == "kimi"
    assert _match_provider("minimax-m-plan-cn", "") == "minimax"
    assert _match_provider("new-provider", "OpenDesign") == "opendesign"
    assert _match_provider("open.bigmodel.cn", "") == "zhipu"
    assert _match_provider("unknown-provider", "Unknown") is None


def test_region_of():
    assert _region_of("https://api.minimax.io/v1", "") == "intl"
    assert _region_of("https://api.kimi.com/coding", "") == "cn"
    assert _region_of("", "kimi-code-cn") == "cn"
    assert _region_of("", "siliconflow.com") == "intl"


def test_read_provider_keys(tmp_path, monkeypatch):
    config = {
        "config": {
            "providerConfigRules": {
                "providerRules": [
                    {
                        "providerId": "kimi-code-cn",
                        "providerName": "Kimi Code（国内）",
                        "config": {
                            "access": {"type": "api-key", "apiKey": "  sk-kimi-123  "},
                            "api": {"baseUrl": "https://api.kimi.com/coding"},
                        },
                    },
                    {
                        "providerId": "minimax-m-plan-cn",
                        "providerName": "MiniMax M Plan（中国）",
                        "config": {
                            "access": {"type": "api-key", "apiKey": "sk-minimax-456"},
                        },
                    },
                    {
                        "providerId": "new-provider",
                        "providerName": "OpenDesign",
                        "config": {
                            "access": {"type": "api-key", "apiKey": "sk-od-789"},
                            "api": {"baseUrl": "https://amr-link.open-design.ai/v1"},
                        },
                    },
                    {
                        "providerId": "oauth-only",
                        "providerName": "OAuth Only",
                        "config": {"access": {"type": "oauth"}},
                    },
                    {
                        "providerId": "kimi-code-dup",
                        "providerName": "Kimi Code（重复）",
                        "config": {"access": {"type": "api-key", "apiKey": "dup"}},
                    },
                ]
            }
        }
    }
    path = tmp_path / "provider_config.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr(
        "app.services.subscription_quota.zcode_provider_config._config_path", lambda: path
    )

    keys = read_provider_keys()
    by_provider = {k.provider_id: k for k in keys}

    assert set(by_provider) == {"kimi", "minimax", "opendesign"}
    # 去掉首尾空格
    assert by_provider["kimi"].api_key == "sk-kimi-123"
    assert by_provider["minimax"].api_key == "sk-minimax-456"
    assert by_provider["opendesign"].api_key == "sk-od-789"
    assert by_provider["opendesign"].base_url == "https://amr-link.open-design.ai/v1"
    # OAuth 类型被跳过；重复 provider 只保留第一条
    assert "oauth-only" not in [k.zcode_provider_id for k in keys]


def test_read_provider_keys_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.services.subscription_quota.zcode_provider_config._config_path",
        lambda: tmp_path / "nope.json",
    )
    assert read_provider_keys() == []


def test_read_provider_keys_broken_json(tmp_path, monkeypatch):
    path = tmp_path / "provider_config.json"
    path.write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(
        "app.services.subscription_quota.zcode_provider_config._config_path", lambda: path
    )
    assert read_provider_keys() == []

"""网关单测：上游解析 / 掩码 / 意图路由 / 插件 / 配置合并 / 转发构造

全部不联网：转发函数用 monkeypatch 打桩。
"""

import json

import pytest

from app.services.gateway import masking, plugins
from app.services.gateway.config_store import DEFAULT_CONFIG, GatewayConfig, _merge
from app.services.gateway.intent import DEFAULT_RULES, IntentRule, classify, group_target
from app.services.gateway.masking import MaskingSession, mask_request_body
from app.services.gateway.proxy import (
    RouteTarget,
    build_upstream_request,
    parse_model,
    prepare_masked_body,
    sse_unmask_bytes,
)
from app.services.gateway.upstreams import get_upstream, resolve_base
from app.services.subscription_quota.accounts import QuotaAccount


# ---------------------------------------------------------------- 上游


def test_resolve_base_from_spec():
    assert resolve_base("kimi", {}, "anthropic") == "https://api.kimi.com/coding"
    assert resolve_base("deepseek", {}, "openai") == "https://api.deepseek.com/v1"


def test_resolve_base_account_override_wins():
    extra = {"base_url": "https://relay.example.com/v1/"}
    # 未知供应商：通用 base_url 生效
    assert resolve_base("zenmux", extra, "openai") == "https://relay.example.com/v1"
    # 显式协议覆盖优先于内置
    assert resolve_base("kimi", {"anthropic_base": "https://x/y"}, "anthropic") == "https://x/y"


def test_resolve_base_generic_url_does_not_override_builtin_protocol():
    """cc-switch 导入的 base_url 是 Anthropic 地址，不能覆盖 OpenAI 协议入口"""
    extra = {"base_url": "https://api.kimi.com/coding"}
    assert resolve_base("kimi", extra, "openai") == "https://api.kimi.com/coding/v1"
    assert resolve_base("kimi", extra, "anthropic") == "https://api.kimi.com/coding"


def test_resolve_base_unknown_provider():
    assert resolve_base("nope", {}, "openai") is None


def test_anthropic_beta_for_official_claude():
    spec = get_upstream("claude")
    assert spec is not None
    assert spec.anthropic_beta == "oauth-2025-04-20"


# ---------------------------------------------------------------- 模型解析


def test_parse_model_with_and_without_prefix():
    assert parse_model("kimi/k3") == ("kimi", "k3")
    assert parse_model("glm-5.3") == (None, "glm-5.3")
    assert parse_model("group/coding") == ("group", "coding")


# ---------------------------------------------------------------- 请求构造


def _account(provider="kimi", key="sk-test-key-1234567890", extra=None, label="a"):
    return QuotaAccount(
        id="acc-1",
        user_id="u",
        provider_id=provider,
        label=label,
        api_key=key,
        extra=extra or {},
    )


def test_build_upstream_request_anthropic():
    target = RouteTarget(
        provider_id="kimi",
        model="k3",
        account=_account(),
        base_url="https://api.kimi.com/coding",
    )
    url, headers, body = build_upstream_request(
        target, "anthropic", {"model": "kimi/k3", "messages": []}
    )
    assert url == "https://api.kimi.com/coding/v1/messages"
    assert headers["Authorization"] == "Bearer sk-test-key-1234567890"
    # 模型名必须去掉 provider 前缀
    assert body["model"] == "k3"


def test_build_upstream_request_openai():
    target = RouteTarget(
        provider_id="deepseek",
        model="deepseek-v4-pro",
        account=_account("deepseek", "sk-ds-1234567890"),
        base_url="https://api.deepseek.com/v1",
    )
    url, headers, body = build_upstream_request(
        target, "openai", {"model": "deepseek/deepseek-v4-pro"}
    )
    assert url == "https://api.deepseek.com/v1/chat/completions"
    assert headers["Authorization"] == "Bearer sk-ds-1234567890"
    assert body["model"] == "deepseek-v4-pro"


def test_build_upstream_request_missing_key():
    target = RouteTarget(
        provider_id="kimi",
        model="k3",
        account=_account(key=None, extra={}),
        base_url="https://api.kimi.com/coding",
    )
    with pytest.raises(Exception) as exc:
        build_upstream_request(target, "anthropic", {"model": "k3"})
    assert "API Key" in str(exc.value)


# ---------------------------------------------------------------- 掩码


def test_mask_api_key():
    session = MaskingSession()
    text = "my key is sk-abcdefghijklmnopqrstuvwxyz and that's it"
    masked, hits = session.mask(text)
    assert hits == 1
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in masked
    assert "{{API_KEY_" in masked
    # 同一个值永远是同一个占位符
    masked2, _ = MaskingSession().mask(text)
    assert masked2 == masked


def test_mask_and_unmask_roundtrip():
    session = MaskingSession()
    original = "token sk-abcdefghijklmnopqrstuvwxyz leaked"
    masked, hits = session.mask(original)
    assert hits == 1
    assert session.unmask(masked) == original


def test_mask_disabled_is_noop():
    session = MaskingSession(enabled=False)
    text = "sk-abcdefghijklmnopqrstuvwxyz"
    masked, hits = session.mask(text)
    assert masked == text
    assert hits == 0


def test_mask_email_skips_example_domains():
    session = MaskingSession()
    masked, hits = session.mask("real: alice@corp.com")
    assert hits == 1
    assert "alice@corp.com" not in masked

    session2 = MaskingSession()
    masked2, hits2 = session2.mask("example: bob@example.com")
    assert hits2 == 0
    assert masked2 == "example: bob@example.com"


def test_mask_jwt():
    session = MaskingSession()
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
    masked, hits = session.mask(f"bearer {jwt}")
    assert hits == 1
    assert jwt not in masked


def test_mask_private_key_block():
    session = MaskingSession()
    block = "-----BEGIN RSA PRIVATE KEY-----\nMIIEow\n-----END RSA PRIVATE KEY-----"
    masked, hits = session.mask(block)
    assert hits == 1
    assert "MIIEow" not in masked


def test_mask_extra_words():
    session = MaskingSession(extra_words=("MySecretProject",))
    masked, hits = session.mask("we are building MySecretProject now")
    assert hits == 1
    assert "MySecretProject" not in masked


def test_mask_card_only_when_enabled_and_luhn():
    good = "4111111111111111"  # 合法 Luhn
    bad = "4111111111111112"

    off = MaskingSession()
    assert off.mask(good)[1] == 0

    on = MaskingSession(mask_cards=True)
    assert on.mask(good)[1] == 1
    assert on.mask(bad)[1] == 0


def test_mask_request_body_recursive():
    session = MaskingSession()
    body = {
        "model": "kimi/k3",
        "messages": [
            {"role": "user", "content": [{"type": "text", "text": "key sk-abcdefghijklmnopqrstuvwxyz"}]}
        ],
        "max_tokens": 10,
    }
    masked, hits = mask_request_body(body, session)
    assert hits == 1
    assert masked["model"] == "kimi/k3"
    assert masked["max_tokens"] == 10
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in json.dumps(masked)


def test_prepare_masked_body_handles_system_prompt():
    session = MaskingSession()
    body = {
        "model": "kimi/k3",
        "system": "secret sk-abcdefghijklmnopqrstuvwxyz",
        "messages": [{"role": "user", "content": "hi"}],
    }
    masked, hits = prepare_masked_body(body, session)
    assert hits == 1
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in masked["system"]


def test_sse_unmask_bytes_restores_placeholder():
    session = MaskingSession()
    _, _ = session.mask("sk-abcdefghijklmnopqrstuvwxyz")
    placeholder = next(iter(session.mapping))
    chunk = f'data: {{"text":"{placeholder}"}}\n\n'.encode()
    restored = sse_unmask_bytes(chunk, session)
    assert b"sk-abcdefghijklmnopqrstuvwxyz" in restored


def test_sse_unmask_passthrough_when_no_mapping():
    session = MaskingSession()
    chunk = b"data: hello\n\n"
    assert sse_unmask_bytes(chunk, session) == chunk


# ---------------------------------------------------------------- 意图路由


def test_classify_test_intent():
    result = classify([{"role": "user", "content": "帮我跑一下 pytest 测试"}])
    assert result is not None
    assert result.rule == "test"
    assert result.target == "group/coding"


def test_classify_code_intent_by_pattern():
    result = classify([{"role": "user", "content": "def hello():\n    pass"}])
    assert result is not None
    assert result.matched_by == "pattern"


def test_classify_chat_intent():
    result = classify([{"role": "user", "content": "你好，随便聊聊"}])
    assert result is not None
    assert result.rule == "chat"


def test_classify_anthropic_content_blocks():
    result = classify(
        [{"role": "user", "content": [{"type": "text", "text": "重构这段代码"}]}]
    )
    assert result is not None
    assert result.rule == "code"


def test_classify_no_match_returns_default():
    result = classify([{"role": "user", "content": "zzzz"}], default_target="group/fast")
    assert result is not None
    assert result.rule == "default"
    assert result.target == "group/fast"


def test_classify_no_match_no_default_returns_none():
    assert classify([{"role": "user", "content": "zzzz"}]) is None


def test_group_target():
    assert group_target("group/coding") == "coding"
    assert group_target("kimi/k3") is None


# ---------------------------------------------------------------- 插件


def test_plugins_discover_builtin_alias():
    found = plugins.discover_plugins()
    names = {p.name for p in found}
    assert "alias" in names
    alias = next(p for p in found if p.name == "alias")
    assert alias.enabled is True
    assert alias.error is None


def test_plugins_apply_alias():
    ctx = plugins.PluginContext(protocol="openai", provider_id=None, model="fast")
    body, applied = plugins.apply_plugins({"model": "fast"}, ctx)
    assert "alias" in applied
    assert body["model"] == "kimi/k3.1-pro"


def test_plugins_ignore_broken_plugin():
    broken = plugins.Plugin(name="broken", path=None, enabled=True)
    broken.handle = lambda body, ctx: (_ for _ in ()).throw(RuntimeError("boom"))
    body, applied = plugins.apply_plugins({"model": "kimi/k3"}, plugins.PluginContext("openai", None, "kimi/k3"), [broken])
    # 出错的插件不影响请求
    assert body == {"model": "kimi/k3"}
    assert "broken" not in applied


def test_plugins_ignore_non_dict_result():
    weird = plugins.Plugin(name="weird", path=None, enabled=True)
    weird.handle = lambda body, ctx: "not a dict"
    body, applied = plugins.apply_plugins({"model": "x"}, plugins.PluginContext("openai", None, "x"), [weird])
    assert body == {"model": "x"}
    assert "weird" not in applied


# ---------------------------------------------------------------- 配置


def test_merge_deep_one_level():
    base = {"a": 1, "masking": {"enabled": False, "maskCards": False}}
    merged = _merge(base, {"masking": {"enabled": True}})
    assert merged["a"] == 1
    assert merged["masking"]["enabled"] is True
    # 未覆盖的字段保留
    assert merged["masking"]["maskCards"] is False


def test_gateway_config_defaults():
    config = GatewayConfig()
    assert config.enabled is False
    assert config.port == 3425
    assert config.masking["enabled"] is False
    assert config.intent_routing is False
    assert config.failover["enabled"] is True


def test_default_config_has_groups():
    groups = DEFAULT_CONFIG["groups"]
    assert set(groups) == {"coding", "fast", "long-context"}
    assert all(isinstance(v, list) for v in groups.values())

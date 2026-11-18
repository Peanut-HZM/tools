"""ZCode 解密与额度适配器单测（不依赖真实凭据）"""

import base64
import hashlib
import json

import pytest

from app.services.subscription_quota.providers_zcode import (
    parse_bigmodel_limits,
    parse_zcode_balances,
)
from app.services.subscription_quota.zcode_credentials import (
    ZCodeSecret,
    _decrypt_value,
    _keyring_service_name,
)


def _seal(plaintext: str, key: bytes) -> str:
    """按 ZCode 的 seal 实现生成密文：iv.tag.ct（均 base64url）"""
    import os

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    iv = os.urandom(12)
    ct_and_tag = AESGCM(key).encrypt(iv, plaintext.encode(), None)
    ct, tag = ct_and_tag[:-16], ct_and_tag[-16:]
    b64 = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")  # noqa: E731
    return f"{b64(iv)}.{b64(tag)}.{b64(ct)}"


def test_keyring_service_name_uses_path_hash():
    from pathlib import Path

    path = Path(r"C:\Users\demo\.zcode\v2\credentials.json")
    name = _keyring_service_name(path)
    expected_digest = hashlib.sha256(str(path).encode()).hexdigest()
    assert name == f"{expected_digest}.ZCode Credential Encryption"


def test_decrypt_value_roundtrip():
    key = b"0123456789abcdef0123456789abcdef"
    payload = _seal("eyJhbGciOiJIUzI1NiJ9.test.sig", key)
    value = f"enc:v2:os:{hashlib.sha256(key).hexdigest()[:24]}:{payload}"
    assert _decrypt_value(value, key) == "eyJhbGciOiJIUzI1NiJ9.test.sig"


def test_decrypt_value_rejects_wrong_key():
    key = b"0123456789abcdef0123456789abcdef"
    other = b"ffffffffffffffffffffffffffffffff"
    payload = _seal("secret-token", key)
    value = f"enc:v2:os:{hashlib.sha256(key).hexdigest()[:24]}:{payload}"
    assert _decrypt_value(value, other) is None


def test_decrypt_value_rejects_bad_shape():
    key = b"0123456789abcdef0123456789abcdef"
    assert _decrypt_value("not-encrypted", key) is None
    assert _decrypt_value("enc:v2:os:abc:onlyonepart", key) is None


def test_parse_zcode_balances():
    data = {
        "balances": [
            {
                "show_name": "GLM-5.3-Flash",
                "total_units": 300_000_000,
                "used_units": 26_486_287,
                "remaining_units": 273_513_713,
                "expires_at": 1794877200,
            }
        ]
    }
    tiers = parse_zcode_balances(data)
    assert len(tiers) == 1
    assert tiers[0].name == "model:GLM-5.3-Flash"
    assert tiers[0].utilization == pytest.approx(8.83, abs=0.05)
    assert tiers[0].resets_at is not None
    assert tiers[0].balance_amount == 273_513_713


def test_parse_zcode_balances_skips_zero_total():
    data = {"balances": [{"show_name": "x", "total_units": 0, "used_units": 5}]}
    assert parse_zcode_balances(data) == []


def test_parse_zcode_balances_derives_used_from_remaining():
    data = {"balances": [{"show_name": "y", "total_units": 100, "remaining_units": 25}]}
    tiers = parse_zcode_balances(data)
    assert tiers[0].utilization == pytest.approx(75.0)


def test_parse_bigmodel_limits_real_shape():
    """真实响应：type=CREDIT_LIMIT，unit 3 → 5 小时，unit 6 → 每周"""
    data = {
        "limits": [
            {
                "type": "CREDIT_LIMIT",
                "unit": 3,
                "number": 5,
                "usage": 12000,
                "currentValue": 184,
                "remaining": 11815,
                "percentage": 1,
                "nextResetTime": 1795020491694,
            },
            {
                "type": "CREDIT_LIMIT",
                "unit": 6,
                "number": 1,
                "usage": 60000,
                "currentValue": 4608,
                "remaining": 55391,
                "percentage": 7,
                "nextResetTime": 1795351724983,
            },
        ],
        "level": "pro",
    }
    tiers = parse_bigmodel_limits(data)
    assert [t.name for t in tiers] == ["five_hour", "weekly_limit"]
    assert tiers[0].utilization == 1.0
    assert tiers[1].utilization == 7.0
    assert tiers[0].resets_at is not None


def test_parse_bigmodel_limits_computes_percentage_when_missing():
    data = {
        "limits": [
            {"type": "TOKENS_LIMIT", "unit": 3, "usage": 1000, "currentValue": 250}
        ]
    }
    tiers = parse_bigmodel_limits(data)
    assert tiers[0].utilization == pytest.approx(25.0)


def test_parse_bigmodel_limits_ignores_unknown_unit():
    data = {"limits": [{"type": "CREDIT_LIMIT", "unit": 99, "percentage": 5}]}
    assert parse_bigmodel_limits(data) == []


def test_parse_bigmodel_limits_ignores_unknown_type():
    data = {"limits": [{"type": "OTHER", "unit": 3, "percentage": 5}]}
    assert parse_bigmodel_limits(data) == []


def test_zcode_secret_dataclass_defaults():
    secret = ZCodeSecret()
    assert secret.token is None
    assert secret.status == "not_found"

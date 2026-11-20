# backend/tests/test_neo4j_crypto.py
import os
import pytest
from cryptography.fernet import Fernet


@pytest.fixture()
def configured_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("NEO4J_CRYPTO_KEY", key)
    # 重新导入以读取新环境变量
    import importlib
    from app.services import neo4j
    importlib.reload(neo4j.crypto)
    return key


def test_encrypt_decrypt_roundtrip(configured_key):
    from app.services.neo4j import crypto
    cipher = crypto.encrypt_password("p@ss+w/rd=%")
    assert cipher != "p@ss+w/rd=%"
    assert crypto.decrypt_password(cipher) == "p@ss+w/rd=%"


def test_encrypt_is_deterministic_in_shape_not_value(configured_key):
    from app.services.neo4j import crypto
    c1 = crypto.encrypt_password("abc")
    c2 = crypto.encrypt_password("abc")
    assert c1 != c2  # Fernet 随机 IV
    assert crypto.decrypt_password(c1) == "abc"
    assert crypto.decrypt_password(c2) == "abc"


def test_not_configured_when_key_missing(monkeypatch):
    monkeypatch.delenv("NEO4J_CRYPTO_KEY", raising=False)
    import importlib
    from app.services import neo4j
    importlib.reload(neo4j.crypto)
    from app.services.neo4j import crypto
    assert crypto.is_configured() is False
    with pytest.raises(RuntimeError):
        crypto.encrypt_password("x")


def test_model_response_excludes_password(configured_key):
    from app.models.neo4j_models import Neo4jConnectionResponse
    data = {
        "id": "u1", "user_id": "u1", "name": "local", "uri": "bolt://localhost:7687",
        "username": "neo4j", "database": "neo4j", "readonly": True,
        "created_at": "2026-11-20T00:00:00", "updated_at": "2026-11-20T00:00:00",
    }
    resp = Neo4jConnectionResponse(**data)
    assert not hasattr(resp, "password")
    assert not hasattr(resp, "encrypted_password")

"""
验证 llm_configs → llm_providers + llm_models 迁移逻辑

使用 SQLite 内存 DB 构造 3 条旧 llm_configs：
  - A, B 共用同一把 API Key（应去重为 1 个 provider）
  - C 使用不同的 API Key（独立的 provider）

断言：
  - llm_providers 数量 = 2
  - llm_models 数量 = 3
  - 每个 model 的 provider_id 正确指向对应 provider
"""
import os
import sys
import json
import pytest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import INET

# 确保 backend 在 sys.path 中
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))


# SQLite 无 INET 类型，注册降级编译器（与 conftest.py 一致）
@compiles(INET, "sqlite")
def _compile_inet_for_sqlite(element, compiler, **kw):
    return "VARCHAR(45)"


from app.models.base import Base
from app.models.llm_config import LLMConfig
from app.models.llm_provider import LLMProvider
from app.models.llm_model import LLMModel
from app.core.security import encrypt_api_key


# 复用迁移脚本的核心逻辑（不依赖其 DB session，直接调函数）
from scripts.migrate_llm_configs import (
    _group_key,
    _build_provider_name,
    _serialize_request_params,
)


@pytest.fixture
def db_session():
    """每个测试用例一个干净的 SQLite 内存 DB"""
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _seed(db_session):
    """构造 3 条旧 llm_configs：A、B 共用同一把明文 key（但密文不同），C 独立"""
    # 同一明文分两次加密 → 密文不同（AES-GCM 随机 IV），模拟真实 DB 中
    # 「同一把 API Key 多次录入」的场景
    same_key_encrypted_a = encrypt_api_key("sk-same-12345678")
    same_key_encrypted_b = encrypt_api_key("sk-same-12345678")
    assert same_key_encrypted_a != same_key_encrypted_b, (
        "测试前提：同一明文两次加密应得不同密文"
    )
    diff_key_encrypted = encrypt_api_key("sk-diff-99999999")

    configs = [
        LLMConfig(
            name="A",
            provider_type="openai",
            base_url="https://api.openai.com/v1",
            api_key_encrypted=same_key_encrypted_a,
            api_key_suffix="5678",
            model_name="gpt-4o",
            request_params={"temperature": 0.7, "max_tokens": 4096},
            category="chat",
            is_default=True,
            is_active=True,
        ),
        LLMConfig(
            name="B",
            provider_type="openai",
            base_url="https://api.openai.com/v1",
            api_key_encrypted=same_key_encrypted_b,  # 密文不同于 A，但明文相同
            api_key_suffix="5678",
            model_name="gpt-4o-mini",
            request_params={"temperature": 0.3},
            category="chat",
            is_default=False,
            is_active=True,
        ),
        LLMConfig(
            name="C",
            provider_type="anthropic",
            base_url="https://api.anthropic.com",
            api_key_encrypted=diff_key_encrypted,
            api_key_suffix="9999",
            model_name="claude-3-5-sonnet-20241022",
            request_params=None,
            category="chat",
            is_default=False,
            is_active=True,
        ),
    ]
    for c in configs:
        db_session.add(c)
    db_session.commit()
    return configs


def test_migration_dedupes_providers(db_session):
    """2 条共享 key 的 config 应去重为 1 个 provider，加上独立的 1 个，共 2 个"""
    configs = _seed(db_session)

    # 跑迁移逻辑（不依赖 SessionLocal，直接操作 session）
    _run_migration_logic(db_session)

    n_providers = db_session.query(LLMProvider).count()
    n_models = db_session.query(LLMModel).count()
    assert n_providers == 2, f"期望 2 个 provider，实际 {n_providers}"
    assert n_models == 3, f"期望 3 个 model，实际 {n_models}"


def test_models_point_to_correct_provider(db_session):
    """每个 model 的 provider_id 必须指向正确的 provider"""
    configs = _seed(db_session)
    _run_migration_logic(db_session)

    models = db_session.query(LLMModel).all()
    assert len(models) == 3

    # 按 model_name 索引
    by_name = {m.model_name: m for m in models}

    # A、B 应该指向同一个 provider
    provider_ab = by_name["gpt-4o"].provider_id
    assert provider_ab == by_name["gpt-4o-mini"].provider_id, (
        "gpt-4o 和 gpt-4o-mini 应共享同一 provider"
    )

    # C 应该指向另一个 provider
    provider_c = by_name["claude-3-5-sonnet-20241022"].provider_id
    assert provider_c != provider_ab, (
        "anthropic config 应指向独立的 provider"
    )

    # 验证 provider 的字段正确
    provider_obj = db_session.query(LLMProvider).filter_by(id=provider_ab).one()
    assert provider_obj.provider_type == "openai"
    assert provider_obj.base_url == "https://api.openai.com/v1"
    assert provider_obj.api_key_suffix == "5678"

    provider_c_obj = db_session.query(LLMProvider).filter_by(id=provider_c).one()
    assert provider_c_obj.provider_type == "anthropic"
    assert provider_c_obj.api_key_suffix == "9999"


def test_request_params_serialized_to_text(db_session):
    """旧 JSON 类型 request_params 应被序列化为 Text"""
    _seed(db_session)
    _run_migration_logic(db_session)

    gpt4o = db_session.query(LLMModel).filter_by(model_name="gpt-4o").one()
    assert isinstance(gpt4o.request_params, str)
    parsed = json.loads(gpt4o.request_params)
    assert parsed["temperature"] == 0.7
    assert parsed["max_tokens"] == 4096

    # C 的 request_params 为 None → 应保持 None
    claude = (
        db_session.query(LLMModel)
        .filter_by(model_name="claude-3-5-sonnet-20241022")
        .one()
    )
    assert claude.request_params is None


def test_group_key_decrypts_correctly():
    """_group_key 应能正确解密并按明文分组（即使密文因随机 IV 不同）"""
    key_b = encrypt_api_key("sk-test-bbb")

    # 同一明文分两次加密 → 密文不同（AES-GCM 使用随机 IV）
    cfg_a1 = LLMConfig(
        name="A1", provider_type="openai", base_url="https://x",
        api_key_encrypted=encrypt_api_key("sk-test-aaa"), model_name="m1",
    )
    cfg_a2 = LLMConfig(
        name="A2", provider_type="openai", base_url="https://x",
        api_key_encrypted=encrypt_api_key("sk-test-aaa"), model_name="m2",
    )
    cfg_b = LLMConfig(
        name="B", provider_type="openai", base_url="https://x",
        api_key_encrypted=key_b, model_name="m3",
    )

    # 两次加密同一明文得到的密文不同（AES-GCM 随机 IV）
    assert cfg_a1.api_key_encrypted != cfg_a2.api_key_encrypted, (
        "加密应使用随机 IV，同一明文两次加密结果应不同"
    )

    # 但 _group_key 解密后应相同（明文一致 → 分组键一致）
    assert _group_key(cfg_a1) == _group_key(cfg_a2)
    assert _group_key(cfg_a1) != _group_key(cfg_b)


# ========== 内部辅助：在给定 session 上跑迁移逻辑 ==========

def _run_migration_logic(db_session):
    """
    复刻 migrate_llm_configs.py 的核心写入逻辑，但接受外部传入的 session
    （方便测试注入 sqlite 内存 DB）。
    """
    old_configs = db_session.query(LLMConfig).all()
    groups: dict = {}
    for cfg in old_configs:
        key = _group_key(cfg)
        groups.setdefault(key, []).append(cfg)

    providers_to_create = []
    key_to_provider = {}
    models_to_create = []

    for key, cfgs in groups.items():
        first = cfgs[0]
        provider = LLMProvider(
            name=_build_provider_name(first.provider_type, first.api_key_suffix),
            provider_type=first.provider_type,
            base_url=first.base_url or "",
            api_key_encrypted=first.api_key_encrypted,
            api_key_suffix=first.api_key_suffix,
            notes=f"自动迁移自 llm_configs（包含 {len(cfgs)} 个模型）",
            is_active=first.is_active if first.is_active is not None else True,
        )
        providers_to_create.append(provider)
        key_to_provider[key] = provider

        for cfg in cfgs:
            model = LLMModel(
                name=cfg.name,
                model_name=cfg.model_name,
                provider=provider,
                request_params=_serialize_request_params(cfg.request_params),
                category=cfg.category or "chat",
                is_default=bool(cfg.is_default),
                is_default_for_category=False,
                notes=cfg.notes,
                is_active=cfg.is_active if cfg.is_active is not None else True,
            )
            models_to_create.append(model)

    for provider in providers_to_create:
        db_session.add(provider)
    db_session.flush()
    for model in models_to_create:
        db_session.add(model)
    db_session.commit()

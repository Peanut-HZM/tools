"""
llm_configs → llm_providers + llm_models 一次性数据迁移脚本

背景：
    v1 起把原本扁平的 llm_configs 拆分为「供应商 (LLMProvider)」+「模型 (LLMModel)」。
    本脚本负责把历史 llm_configs 数据回灌到两张新表。

去重规则：
    按 (provider_type, base_url, 明文 api_key) 分组 —— 同一把 API Key 在同一供应商
    下只创建一条 LLMProvider，原表每条 config 对应一条 LLMModel。
    注意：api_key_encrypted 因 AES-GCM 使用随机 IV，同一明文会生成不同密文，
    因此必须先 decrypt 再分组。

用法：
    cd backend
    # 1. 先跑 dry-run（默认），查看将要创建的内容
    python scripts/migrate_llm_configs.py
    # 2. 确认无问题后加 --apply 真实写入
    python scripts/migrate_llm_configs.py --apply
"""

import hashlib
import sys
import os
import json
import argparse
import logging

# 确保能导入项目模块（兼容直接 python scripts/xxx.py 执行）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.models.base import SessionLocal, engine, Base
# 触发新 model 注册到 Base.metadata（create_all 才能建到）
from app.models import LLMProvider, LLMModel  # noqa: F401
from app.models.llm_config import LLMConfig
from app.core.security import decrypt_api_key

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def _group_key(config) -> tuple:
    """
    返回分组键：(provider_type, base_url, 明文 api_key)。
    解密失败时降级用 api_key_encrypted，避免整批数据丢失。
    """
    try:
        plaintext_key = decrypt_api_key(config.api_key_encrypted)
    except Exception as e:  # noqa: BLE001
        logger.warning(
            f"  -> 解密失败 (config_id={config.id})，降级使用密文分组: {e}"
        )
        plaintext_key = config.api_key_encrypted
    return (config.provider_type, config.base_url or "", plaintext_key)


def _hash_api_key(plaintext: str) -> bytes:
    """计算明文 API Key 的 SHA-256 摘要（32 字节）"""
    return hashlib.sha256(plaintext.encode("utf-8")).digest()


def _build_provider_name(provider_type: str, api_key_suffix: str) -> str:
    suffix = api_key_suffix or "????"
    return f"Migrated: {provider_type}-{suffix}"


def _serialize_request_params(raw) -> str | None:
    """旧表 request_params 为 JSON（dict/list），新表为 Text，需要序列化。"""
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw
    return json.dumps(raw, ensure_ascii=False)


def run_migration(apply: bool = False) -> dict:
    """
    执行迁移。返回 {"providers": int, "models": int, "old_count": int}。
    apply=False 时只读不写（dry-run）。
    """
    db = SessionLocal()
    try:
        # ========== 1. 读取所有旧配置 ==========
        logger.info("步骤 1: 读取 llm_configs ...")
        old_configs = db.query(LLMConfig).all()
        old_count = len(old_configs)
        logger.info(f"  -> 共 {old_count} 条旧配置")
        if old_count == 0:
            logger.info("无需迁移")
            return {"providers": 0, "models": 0, "old_count": 0}

        # ========== 2. 按 (provider_type, base_url, 明文 api_key) 分组 ==========
        logger.info("步骤 2: 按 (provider_type, base_url, 明文 api_key) 分组...")
        groups: dict[tuple, list] = {}
        for cfg in old_configs:
            key = _group_key(cfg)
            groups.setdefault(key, []).append(cfg)
        logger.info(f"  -> 去重后得到 {len(groups)} 个供应商分组")

        # ========== 3. 计算将要创建的 providers / models ==========
        providers_to_create: list[LLMProvider] = []
        # key -> provider（尚未持久化，仅占位对象，用于给 model 赋 provider_id）
        key_to_provider: dict[tuple, LLMProvider] = {}
        models_to_create: list[LLMModel] = []

        for key, cfgs in groups.items():
            first = cfgs[0]
            # key = (provider_type, base_url, plaintext_api_key)
            _, _, plaintext_api_key = key
            provider = LLMProvider(
                name=_build_provider_name(first.provider_type, first.api_key_suffix),
                provider_type=first.provider_type,
                base_url=first.base_url or "",
                api_key_encrypted=first.api_key_encrypted,
                api_key_suffix=first.api_key_suffix,
                api_key_hash=_hash_api_key(plaintext_api_key),
                notes=f"自动迁移自 llm_configs（包含 {len(cfgs)} 个模型）",
                is_active=first.is_active if first.is_active is not None else True,
            )
            providers_to_create.append(provider)
            key_to_provider[key] = provider

            for cfg in cfgs:
                model = LLMModel(
                    name=cfg.name,
                    model_name=cfg.model_name,
                    # provider_id 在 apply 阶段由 ORM 自动填（provider 先 flush）
                    provider=provider,
                    request_params=_serialize_request_params(cfg.request_params),
                    category=cfg.category or "chat",
                    is_default=bool(cfg.is_default),
                    is_default_for_category=False,
                    notes=cfg.notes,
                    is_active=cfg.is_active if cfg.is_active is not None else True,
                )
                models_to_create.append(model)

        logger.info(
            f"  -> 将创建 {len(providers_to_create)} 个 provider，"
            f"{len(models_to_create)} 个 model"
        )

        # ========== 4. Dry-run 打印映射明细 ==========
        logger.info("步骤 3: 旧表 → 新表 ID 映射（dry-run 预览）...")
        for i, (key, cfgs) in enumerate(groups.items(), 1):
            provider = key_to_provider[key]
            provider_type, base_url, _ = key
            logger.info(
                f"  [{i}] provider_type={provider_type} base_url={base_url} "
                f"-> provider.name={provider.name} "
                f"(含 {len(cfgs)} 个 model: "
                f"{[c.model_name for c in cfgs]})"
            )

        if not apply:
            logger.info(
                "[DRY-RUN] 以上为预览，未写入任何数据。"
                "确认无问题后加 --apply 重新执行。"
            )
            db.rollback()
            return {
                "providers": len(providers_to_create),
                "models": len(models_to_create),
                "old_count": old_count,
            }

        # ========== 5. 真实写入 ==========
        logger.info("步骤 4: [--apply] 写入数据库...")
        for provider in providers_to_create:
            db.add(provider)
        # flush 让 provider 拿到 id，model 的外键才能正确赋值
        db.flush()
        for model in models_to_create:
            db.add(model)
        db.commit()
        logger.info("  -> 写入完成")

        # ========== 6. 验证 ==========
        logger.info("步骤 5: 验证...")
        n_providers = db.query(LLMProvider).count()
        n_models = db.query(LLMModel).count()
        logger.info(f"  -> llm_providers 总数: {n_providers}")
        logger.info(f"  -> llm_models 总数: {n_models}")
        # 每个 provider 关联的 models 数
        provider_model_counts = (
            db.query(LLMProvider.name, LLMModel.id)
            .join(LLMModel, LLMModel.provider_id == LLMProvider.id)
            .group_by(LLMProvider.name)
            .all()
        )
        # 上面 group_by 在某些 dialect 下不够直观，改用聚合查询
        from sqlalchemy import func as sa_func
        provider_model_counts = (
            db.query(LLMProvider.name, sa_func.count(LLMModel.id))
            .join(LLMModel, LLMModel.provider_id == LLMProvider.id)
            .group_by(LLMProvider.name)
            .all()
        )
        for name, cnt in provider_model_counts:
            logger.info(f"     - {name}: {cnt} 个 models")

        return {
            "providers": len(providers_to_create),
            "models": len(models_to_create),
            "old_count": old_count,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"迁移失败: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="llm_configs → providers + models 迁移")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="真实写入数据库（默认 dry-run）",
    )
    args = parser.parse_args()
    run_migration(apply=args.apply)


if __name__ == "__main__":
    main()

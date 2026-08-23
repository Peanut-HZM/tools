"""
一次性 patch 脚本：为已有 llm_providers 表添加 api_key_hash 列并回填

背景：
    Task 1.5.3 新增 api_key_hash 字段（SHA-256 摘要），用于幂等检索 / 去重。
    已有数据库通过 CREATE TABLE 不会自动加新列，需要本脚本手动 ALTER + 回填。

用法：
    cd backend
    # 1. 先跑 dry-run（默认），预览将变更的数量
    python scripts/patch_add_api_key_hash.py
    # 2. 确认无问题后加 --apply 真实执行
    python scripts/patch_add_api_key_hash.py --apply

幂等性：
    - 列已存在时，ALTER 会报 duplicate column，脚本忽略并继续
    - 已回填 hash 的记录不会重复计算（按 api_key_hash IS NULL 过滤）
"""

import sys
import os
import hashlib
import argparse
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.models.base import SessionLocal, engine
from app.models import LLMProvider  # noqa: F401 确保 model 注册
from app.core.security import decrypt_api_key

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def _hash_api_key(plaintext: str) -> bytes:
    return hashlib.sha256(plaintext.encode("utf-8")).digest()


def _dialect() -> str:
    """返回当前数据库方言（postgresql / sqlite 等）"""
    return engine.dialect.name


def run_patch(apply: bool = False) -> dict:
    """
    执行 patch。返回 {"added_column": bool, "backfilled": int, "skipped": int}。
    apply=False 时只读不写（dry-run）。
    """
    db = SessionLocal()
    dialect = _dialect()
    result = {"added_column": False, "backfilled": 0, "skipped": 0}

    try:
        # ========== 1. 添加列（如果不存在） ==========
        logger.info("步骤 1: 检查 / 添加 api_key_hash 列...")

        if dialect == "postgresql":
            alter_sql = "ALTER TABLE llm_providers ADD COLUMN api_key_hash BYTEA"
        elif dialect == "sqlite":
            alter_sql = "ALTER TABLE llm_providers ADD COLUMN api_key_hash BLOB"
        else:
            alter_sql = "ALTER TABLE llm_providers ADD COLUMN api_key_hash BLOB"
            logger.warning(f"未知方言 {dialect}，使用通用 BLOB 类型")

        if apply:
            try:
                db.execute(text(alter_sql))
                db.commit()
                result["added_column"] = True
                logger.info("  -> 列已添加")
            except Exception as e:
                # 列已存在时忽略（幂等）
                if "duplicate" in str(e).lower() or "already exists" in str(e).lower():
                    logger.info("  -> 列已存在，跳过 ALTER")
                else:
                    raise
        else:
            logger.info(f"  [DRY-RUN] 将执行: {alter_sql}")

        # ========== 2. 统计待回填记录 ==========
        logger.info("步骤 2: 统计待回填 hash 的记录...")
        count_stmt = text(
            "SELECT COUNT(*) FROM llm_providers WHERE api_key_hash IS NULL"
        )
        pending = db.execute(count_stmt).scalar() or 0
        logger.info(f"  -> 待回填: {pending} 条")

        if pending == 0:
            logger.info("无需回填")
            return result

        if not apply:
            logger.info(
                f"  [DRY-RUN] 将解密 {pending} 条记录并回填 api_key_hash"
            )
            return result

        # ========== 3. 逐条解密 + 计算 hash + 回填 ==========
        logger.info("步骤 3: 回填 api_key_hash...")
        providers = db.execute(
            text("SELECT id, api_key_encrypted FROM llm_providers WHERE api_key_hash IS NULL")
        ).fetchall()

        backfilled = 0
        skipped = 0
        for row in providers:
            pid, encrypted = row
            try:
                plaintext = decrypt_api_key(encrypted)
                h = _hash_api_key(plaintext)
                if dialect == "postgresql":
                    # PostgreSQL 需要 BYTEA 参数绑定
                    db.execute(
                        text("UPDATE llm_providers SET api_key_hash = :hash WHERE id = :id"),
                        {"hash": h, "id": pid},
                    )
                else:
                    db.execute(
                        text("UPDATE llm_providers SET api_key_hash = :hash WHERE id = :id"),
                        {"hash": h, "id": pid},
                    )
                backfilled += 1
            except Exception as e:
                logger.warning(f"  -> 跳过 provider {pid}: 解密失败 ({e})")
                skipped += 1

        db.commit()
        result["backfilled"] = backfilled
        result["skipped"] = skipped
        logger.info(f"  -> 回填完成: {backfilled} 条成功, {skipped} 条跳过")

        # ========== 4. 添加唯一索引（如果不存在） ==========
        logger.info("步骤 4: 创建唯一索引（如果不存在）...")
        if apply:
            try:
                if dialect == "postgresql":
                    idx_sql = "CREATE UNIQUE INDEX IF NOT EXISTS ix_llm_providers_api_key_hash ON llm_providers (api_key_hash)"
                else:
                    idx_sql = "CREATE UNIQUE INDEX IF NOT EXISTS ix_llm_providers_api_key_hash ON llm_providers (api_key_hash)"
                db.execute(text(idx_sql))
                db.commit()
                logger.info("  -> 索引已创建 / 已存在")
            except Exception as e:
                logger.warning(f"  -> 索引创建失败（可忽略）: {e}")
        else:
            logger.info("  [DRY-RUN] 将创建唯一索引 ix_llm_providers_api_key_hash")

        return result

    except Exception as e:
        db.rollback()
        logger.error(f"Patch 失败: {e}")
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="为 llm_providers 添加 api_key_hash 列并回填")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="真实执行 ALTER + 回填（默认 dry-run）",
    )
    args = parser.parse_args()
    run_patch(apply=args.apply)


if __name__ == "__main__":
    main()

"""
Token Usage 数据库迁移脚本

执行内容：
1. 添加 default_display_name 列到 device_registry
2. 将 system 用户的数据迁移到 peanut（包括 token_usage_records 和 device_registry）
3. 清理重复设备记录（保留有 default_display_name 的）

用法：
    cd /Users/huazhongmin/IdeaProjects/tools/backend
    python scripts/migrate_token_usage.py
"""

import sys
import os

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.base import SessionLocal, engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def run_migration():
    db = SessionLocal()
    try:
        # ========== 1. 添加 default_display_name 列 ==========
        logger.info("步骤 1: 添加 default_display_name 列...")
        try:
            db.execute(text("""
                ALTER TABLE device_registry
                ADD COLUMN IF NOT EXISTS default_display_name VARCHAR(128)
            """))
            db.commit()
            logger.info("  -> 列已添加")
        except Exception as e:
            db.rollback()
            logger.warning(f"  -> 列可能已存在: {e}")

        # ========== 2. 查找 system 用户的数据 ==========
        logger.info("步骤 2: 查找 system 用户的数据...")
        system_records = db.execute(text("""
            SELECT COUNT(*) FROM token_usage_records WHERE user_id = 'system'
        """)).scalar()
        logger.info(f"  -> token_usage_records 中 system 用户记录数: {system_records}")

        system_devices = db.execute(text("""
            SELECT device_id, COUNT(*) FROM device_registry
            WHERE user_id = 'system'
            GROUP BY device_id
        """)).fetchall()
        logger.info(f"  -> device_registry 中 system 用户设备数: {len(system_devices)}")
        for dev_id, cnt in system_devices:
            logger.info(f"     - 设备: {dev_id}")

        # ========== 3. 查找 peanut 用户的现有设备 ==========
        logger.info("步骤 3: 查找 peanut 用户的现有设备...")
        peanut_devices = db.execute(text("""
            SELECT device_id FROM device_registry WHERE user_id = 'peanut'
        """)).fetchall()
        peanut_device_ids = {row[0] for row in peanut_devices}
        logger.info(f"  -> peanut 现有设备: {peanut_device_ids}")

        # ========== 4. 迁移 token_usage_records ==========
        logger.info("步骤 4: 迁移 token_usage_records 数据...")
        # 先检查需要迁移的设备
        migrate_devices = []
        for dev_id, cnt in system_devices:
            if dev_id not in peanut_device_ids:
                # 设备不在 peanut 中，直接改 user_id
                migrate_devices.append(dev_id)
            else:
                # 设备已在 peanut 中，检查是否有数据冲突
                existing_count = db.execute(text("""
                    SELECT COUNT(*) FROM token_usage_records
                    WHERE user_id = 'peanut' AND device_id = :dev_id
                """), {"dev_id": dev_id}).scalar()
                if existing_count == 0:
                    migrate_devices.append(dev_id)
                else:
                    # 有冲突，检查数据是否相同
                    logger.info(f"     - 设备 {dev_id} 在 peanut 中已有 {existing_count} 条记录，跳过迁移")

        if migrate_devices:
            for dev_id in migrate_devices:
                result = db.execute(text("""
                    UPDATE token_usage_records
                    SET user_id = 'peanut'
                    WHERE user_id = 'system' AND device_id = :dev_id
                """), {"dev_id": dev_id})
                logger.info(f"     - 迁移设备 {dev_id}: {result.rowcount} 条记录")
            db.commit()
            logger.info("  -> 迁移完成")
        else:
            logger.info("  -> 无需迁移")

        # ========== 5. 迁移 device_registry ==========
        logger.info("步骤 5: 迁移 device_registry 数据...")
        for dev_id, cnt in system_devices:
            if dev_id not in peanut_device_ids:
                # 检查是否已有 peanut 用户的同名设备
                existing = db.execute(text("""
                    SELECT id FROM device_registry
                    WHERE user_id = 'peanut' AND device_id = :dev_id
                """), {"dev_id": dev_id}).fetchone()
                if not existing:
                    db.execute(text("""
                        UPDATE device_registry
                        SET user_id = 'peanut'
                        WHERE user_id = 'system' AND device_id = :dev_id
                    """), {"dev_id": dev_id})
                    logger.info(f"     - 迁移设备 {dev_id}")
                else:
                    # 已存在，删除 system 用户的重复记录
                    db.execute(text("""
                        DELETE FROM device_registry
                        WHERE user_id = 'system' AND device_id = :dev_id
                    """), {"dev_id": dev_id})
                    logger.info(f"     - 删除重复设备 {dev_id}")
        db.commit()

        # ========== 6. 清理 system 用户的残留数据 ==========
        logger.info("步骤 6: 清理 system 用户的残留数据...")
        remaining = db.execute(text("""
            SELECT COUNT(*) FROM token_usage_records WHERE user_id = 'system'
        """)).scalar()
        if remaining > 0:
            logger.info(f"  -> 删除 {remaining} 条残留记录")
            db.execute(text("DELETE FROM token_usage_records WHERE user_id = 'system'"))
            db.commit()

        remaining_devices = db.execute(text("""
            SELECT COUNT(*) FROM device_registry WHERE user_id = 'system'
        """)).scalar()
        if remaining_devices > 0:
            logger.info(f"  -> 删除 {remaining_devices} 条残留设备")
            db.execute(text("DELETE FROM device_registry WHERE user_id = 'system'"))
            db.commit()

        # ========== 7. 验证结果 ==========
        logger.info("步骤 7: 验证迁移结果...")
        peanut_record_count = db.execute(text("""
            SELECT COUNT(*) FROM token_usage_records WHERE user_id = 'peanut'
        """)).scalar()
        peanut_device_count = db.execute(text("""
            SELECT COUNT(*) FROM device_registry WHERE user_id = 'peanut'
        """)).scalar()
        system_record_count = db.execute(text("""
            SELECT COUNT(*) FROM token_usage_records WHERE user_id = 'system'
        """)).scalar()
        system_device_count = db.execute(text("""
            SELECT COUNT(*) FROM device_registry WHERE user_id = 'system'
        """)).scalar()

        logger.info(f"  -> peanut: {peanut_record_count} 条记录, {peanut_device_count} 个设备")
        logger.info(f"  -> system: {system_record_count} 条记录, {system_device_count} 个设备")
        logger.info("迁移完成！")

    except Exception as e:
        db.rollback()
        logger.error(f"迁移失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_migration()

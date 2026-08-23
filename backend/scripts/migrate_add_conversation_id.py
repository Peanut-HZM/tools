"""一次性迁移脚本：为 image_gen_history 表添加 conversation_id 字段

用途：
  支持多轮对话功能，将图片生成记录关联到对应的 conversation。

执行方式：
    cd backend
    python scripts/migrate_add_conversation_id.py

幂等性：
  - 使用 IF NOT EXISTS，重复执行不会报错
  - 索引也使用 IF NOT EXISTS 保证安全
"""

import os
import sys
import logging

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.models.base import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    with engine.begin() as conn:
        # 幂等：列已存在时不报错（PostgreSQL 支持 IF NOT EXISTS）
        conn.execute(text("""
            ALTER TABLE image_gen_history
            ADD COLUMN IF NOT EXISTS conversation_id VARCHAR(64) DEFAULT NULL
        """))
        logger.info("conversation_id 列已就绪")

        # 创建部分索引：只对非 NULL 的行建索引，节省空间
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_img_gen_history_conversation
            ON image_gen_history(conversation_id)
            WHERE conversation_id IS NOT NULL
        """))
        logger.info("idx_img_gen_history_conversation 索引已就绪")

    print("[OK] conversation_id 字段 + 索引已就绪")


if __name__ == "__main__":
    main()

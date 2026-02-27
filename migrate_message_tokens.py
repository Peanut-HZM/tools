#!/usr/bin/env python3
"""
数据库迁移脚本：添加消息token统计字段
"""

import sys

sys.path.insert(0, "/Users/huazhongmin/IdeaProjects/tools/backend")

from app.config.database import get_db_connection


def migrate():
    """执行迁移"""
    conn = get_db_connection()
    cur = conn.cursor()

    try:
        # 检查字段是否已存在
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'messages' 
            AND column_name = 'prompt_tokens';
        """)

        if cur.fetchone():
            print("✅ 字段已存在，跳过迁移")
            return

        # 添加新字段
        cur.execute("""
            ALTER TABLE messages 
            ADD COLUMN prompt_tokens INTEGER DEFAULT 0,
            ADD COLUMN completion_tokens INTEGER DEFAULT 0,
            ADD COLUMN total_tokens INTEGER DEFAULT 0,
            ADD COLUMN llm_config_id UUID REFERENCES llm_configs(id),
            ADD COLUMN llm_model_name VARCHAR(100);
        """)

        conn.commit()
        print("✅ 迁移完成：已添加token统计字段到messages表")

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()

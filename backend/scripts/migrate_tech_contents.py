#!/usr/bin/env python3
"""
技术分析内容平台 - 数据库迁移脚本

将现有 courses 表扩展，新增技术分析内容相关字段：
- content_type: 内容类型（analysis/sharing/case_study）
- author: 作者
- reading_time: 阅读时长（分钟）
- tags: 标签（JSON 数组）

用法:
    python backend/scripts/migrate_tech_contents.py
"""

import sys
from pathlib import Path

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text, inspect
from app.config.config import settings
from app.models.base import Base, engine
from app.models.course_platform import Course

def check_column_exists(table_name: str, column_name: str) -> bool:
    """检查列是否存在"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def migrate():
    """执行迁移"""
    print("=" * 60)
    print("技术分析内容平台 - 数据库迁移")
    print("=" * 60)
    print()

    # 创建连接
    print("正在连接数据库...")
    conn = engine.connect()

    try:
        # 检查并添加新列
        columns_to_add = [
            ("content_type", "VARCHAR(20) DEFAULT 'analysis'"),
            ("author", "VARCHAR(100)"),
            ("reading_time", "INT DEFAULT 0"),
            ("tags", "TEXT"),
        ]

        for column_name, column_def in columns_to_add:
            if check_column_exists("courses", column_name):
                print(f"⚠️  列 '{column_name}' 已存在，跳过")
            else:
                print(f"正在添加列 '{column_name}'...")
                conn.execute(text(f"ALTER TABLE courses ADD COLUMN {column_name} {column_def}"))
                conn.commit()
                print(f"✅ 列 '{column_name}' 添加成功")

        # 创建索引
        print()
        print("正在创建索引...")
        if check_index_exists("idx_courses_content_type"):
            print("⚠️  索引 'idx_courses_content_type' 已存在，跳过")
        else:
            conn.execute(text("CREATE INDEX idx_courses_content_type ON courses(content_type)"))
            conn.commit()
            print("✅ 索引 'idx_courses_content_type' 创建成功")

        # 更新现有数据
        print()
        print("正在更新现有数据...")
        result = conn.execute(text("SELECT COUNT(*) FROM courses")).scalar()
        print(f"数据库中共有 {result} 条课程记录")

        # 将所有现有记录的 content_type 设置为 'analysis'（如果为 NULL）
        conn.execute(text("""
            UPDATE courses
            SET content_type = 'analysis'
            WHERE content_type IS NULL
        """))
        conn.commit()
        print("✅ 现有数据更新完成")

        print()
        print("=" * 60)
        print("✅ 迁移完成！")
        print("=" * 60)
        print()
        print("新增字段:")
        print("  - content_type: 内容类型（默认：analysis）")
        print("  - author: 作者")
        print("  - reading_time: 阅读时长（分钟）")
        print("  - tags: 标签（JSON 数组）")
        print()
        print("新增索引:")
        print("  - idx_courses_content_type: content_type 字段索引")
        print()

    except Exception as e:
        conn.rollback()
        print(f"❌ 迁移失败：{e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        conn.close()


def check_index_exists(index_name: str) -> bool:
    """检查索引是否存在"""
    inspector = inspect(engine)
    # 检查所有表的索引
    for table_name in inspector.get_table_names():
        if table_name == 'alembic_version':
            continue
        indexes = inspector.get_indexes(table_name)
        for idx in indexes:
            if idx['name'] == index_name:
                return True
    return False


if __name__ == "__main__":
    migrate()

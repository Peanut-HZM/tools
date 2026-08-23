"""给 image_gen_history 表加 backend 列（幂等）

用途：
  ImageGenHistory 新增 backend 字段，用于区分生成后端（'dify' | 'selfdev'）。
  存量行回填默认值 'dify'。

注：任务简报中的 image_gen_records 表对应现有 image_gen_history 表
（自研/Dify 共用，见设计文档 2.2 节不变量 3）。

执行方式：
    cd backend
    python scripts/migrate_add_record_backend.py

幂等性：
  - 使用 ADD COLUMN IF NOT EXISTS，重复执行不会报错
"""

import os
import sys

# 确保能导入项目模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.models.base import engine


def migrate():
    sql = """
    ALTER TABLE image_gen_history
    ADD COLUMN IF NOT EXISTS backend VARCHAR(16) NOT NULL DEFAULT 'dify';
    """
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    print("[migrate_add_record_backend] OK")


if __name__ == "__main__":
    migrate()

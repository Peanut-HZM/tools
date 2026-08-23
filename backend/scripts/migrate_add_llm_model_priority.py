"""给 llm_models 表加 priority 列（幂等）

用途：
  LLMModel 新增 priority 字段，用于兜底链迭代顺序（越小越优先）。
  存量行回填默认值 100。

执行方式：
    cd backend
    python scripts/migrate_add_llm_model_priority.py

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
    ALTER TABLE llm_models
    ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 100;
    """
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    print("[migrate_add_llm_model_priority] OK")


if __name__ == "__main__":
    migrate()

#!/usr/bin/env python3
"""
初始化 SQLAlchemy 模型表
"""

import sys

sys.path.insert(0, "/Users/huazhongmin/IdeaProjects/tools/backend")

from sqlalchemy import create_engine
from app.models.base import Base
from app.config.config import settings


def init_sqlalchemy_tables():
    # 创建引擎
    engine = create_engine(settings.DATABASE_URL)

    # 创建所有表
    Base.metadata.create_all(bind=engine)

    print("✅ SQLAlchemy 表创建完成")

    # 列出创建的表
    from sqlalchemy import inspect

    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"📊 现有表: {tables}")


if __name__ == "__main__":
    init_sqlalchemy_tables()

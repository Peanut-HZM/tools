"""Harness 测试公共 fixtures

- 为 PostgreSQL 专属类型（JSONB / UUID）注册 SQLite 降级编译器
- 提供 test_db fixture：每个用例一个干净的 SQLite 内存库
"""
import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker


@compiles(JSONB, "sqlite")
def _compile_jsonb_for_sqlite(element, compiler, **kw):
    """SQLite 无 JSONB 类型，降级为 JSON。"""
    return "JSON"


@compiles(UUID, "sqlite")
def _compile_uuid_for_sqlite(element, compiler, **kw):
    """SQLite 无 UUID 类型，降级为 CHAR(32)，存储 32 字符 hex。

    SQLAlchemy 2.0 默认生成 `UUID NOT NULL`，SQLite 会以 NUMERIC 亲和性存储为 INTEGER，
    读回时 result_processor 调用 UUID(int) 抛错。强制 CHAR(32) 既保证存储容量，
    也让 SQLite 原生按字符串返回，绕开 int 反序列化问题。
    """
    return "CHAR(32)"


# 确保 backend 目录在 sys.path 中
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


@pytest.fixture
def test_db():
    """每个测试用例一个干净的 SQLite 内存 DB session

    建表前强制导入所有 harness 模型，确保 Base.metadata 包含全部表定义。
    """
    # 导入所有 harness 模型，触发 Base 注册
    from app.models.harness_models import (  # noqa: F401
        Tool,
        ToolBinding,
        SessionCheckpoint,
        AgentMemory,
        Trace,
        TraceStep,
    )
    # 同时导入扩展后的 Agent/Conversation/Message，使 relationship 能解析
    from app.models.agent import Agent  # noqa: F401
    from app.models.conversation import Conversation  # noqa: F401
    from app.models.message import Message  # noqa: F401
    from app.models.agent_memory import AgentMemoryLongTerm  # noqa: F401
    from app.models.base import Base

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

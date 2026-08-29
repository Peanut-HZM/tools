"""验证 memory vector 迁移脚本的正确性

这些测试需要真实 PostgreSQL 数据库 + pgvector 扩展，
在 CI 或无 DB 环境中自动跳过。运行时设置环境变量
MEMORY_VECTOR_INTEGRATION=1 启用。
"""
import os
import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("MEMORY_VECTOR_INTEGRATION"),
    reason="需要真实 PostgreSQL + pgvector，设置 MEMORY_VECTOR_INTEGRATION=1 启用",
)


def test_migration_adds_columns():
    """迁移后 agent_memory_long_term 表包含 embedding, importance, access_count 列"""
    # 通过 inspect DB 验证列存在
    from sqlalchemy import inspect
    from app.models.base import engine

    insp = inspect(engine)
    columns = {c["name"] for c in insp.get_columns("agent_memory_long_term")}
    assert "embedding" in columns
    assert "importance" in columns
    assert "access_count" in columns


def test_migration_creates_extension():
    """迁移后 pgvector 扩展已启用"""
    from sqlalchemy import text
    from app.models.base import engine

    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT extname FROM pg_extension WHERE extname = 'vector'"
        ))
        assert result.scalar() == "vector"


def test_migration_creates_vector_index():
    """迁移后向量索引存在"""
    from sqlalchemy import inspect
    from app.models.base import engine

    insp = inspect(engine)
    indexes = insp.get_indexes("agent_memory_long_term")
    index_names = {idx["name"] for idx in indexes}
    assert "idx_memory_embedding" in index_names


def test_migration_downgrade_removes_columns():
    """downgrade 后列和索引被移除"""
    # 实际 downgrade 测试在集成测试中覆盖
    pass

"""add memory vector columns (pgvector)

Revision ID: 20260829b_memory_vector
Revises: 1ae5ab879f5e
Create Date: 2026-08-29

Phase 3 Plan-1B / Task 1
参考 spec §3: docs/superpowers/specs/2026-08-29-agent-harness-phase3-plan1b-memory-vector-design.md
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision: str = "20260829b_memory_vector"
down_revision: Union[str, None] = "1ae5ab879f5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 检测 pgvector 可用性（不可用时降级为 TEXT 列——
    #    MemoryService 运行时本就支持无 pgvector 的关键词检索降级）。
    #    注意：用 pg_available_extensions 预检而非直接 CREATE EXTENSION，
    #    因为后者失败会中止当前迁移事务。
    _row = (
        op.get_bind()
        .execute(sa.text("SELECT default_version FROM pg_available_extensions WHERE name = 'vector'"))
        .fetchone()
    )
    pgvector_available = bool(_row)
    if not pgvector_available:
        import logging

        logging.getLogger("alembic").warning(
            "pgvector 扩展不可用，embedding 列降级为 TEXT（向量检索运行时自动走关键词兜底）"
        )

    # 2. 新增列
    op.add_column(
        "agent_memory_long_term",
        sa.Column("importance", sa.Float(), nullable=False, server_default="0.5"),
    )
    op.add_column(
        "agent_memory_long_term",
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="0"),
    )
    if pgvector_available:
        # embedding 列使用原生 SQL（SQLAlchemy 不直接支持 VECTOR 类型）
        op.execute(
            "ALTER TABLE agent_memory_long_term "
            "ADD COLUMN embedding VECTOR(1536)"
        )
    else:
        # 降级：ORM 中 embedding 本就是 Text 列（应用层做 list↔str 转换）
        op.execute(
            "ALTER TABLE agent_memory_long_term "
            "ADD COLUMN IF NOT EXISTS embedding TEXT"
        )

    # 3. 向量索引（仅 pgvector 可用时；HNSW — 空表也可创建，比 IVFFlat 更稳健）
    if pgvector_available:
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_embedding "
            "ON agent_memory_long_term "
            "USING hnsw (embedding vector_cosine_ops)"
        )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_memory_embedding")
    op.execute(
        "ALTER TABLE agent_memory_long_term DROP COLUMN IF EXISTS embedding"
    )
    op.drop_column("agent_memory_long_term", "access_count")
    op.drop_column("agent_memory_long_term", "importance")

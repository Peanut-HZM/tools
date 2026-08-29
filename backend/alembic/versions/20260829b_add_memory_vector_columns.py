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
    # 1. 启用 pgvector 扩展
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. 新增列
    op.add_column(
        "agent_memory_long_term",
        sa.Column("importance", sa.Float(), nullable=False, server_default="0.5"),
    )
    op.add_column(
        "agent_memory_long_term",
        sa.Column("access_count", sa.Integer(), nullable=False, server_default="0"),
    )
    # embedding 列使用原生 SQL（SQLAlchemy 不直接支持 VECTOR 类型）
    op.execute(
        "ALTER TABLE agent_memory_long_term "
        "ADD COLUMN embedding VECTOR(1536)"
    )

    # 3. 向量索引（HNSW — 空表也可创建，比 IVFFlat 更稳健）
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

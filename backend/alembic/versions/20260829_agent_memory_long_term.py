"""add agent_memory_long_term table

Revision ID: 20260829_agent_memory_long_term
Revises: e1b4d5e5e6b7
Create Date: 2026-08-29

Phase 2 Plan-2 / Task 1
参考 spec §6.2: docs/superpowers/specs/2026-08-29-agent-harness-phase2-design.md
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = "20260829_agent_memory_long_term"
down_revision: Union[str, None] = "e1b4d5e5e6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_memory_long_term",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "agent_id",
            sa.Uuid(),
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.UniqueConstraint(
            "agent_id", "user_id", "key", name="uq_agent_memory_long_term_key"
        ),
    )
    op.create_index(
        "ix_memory_agent_user", "agent_memory_long_term", ["agent_id", "user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_memory_agent_user", table_name="agent_memory_long_term")
    op.drop_table("agent_memory_long_term")
"""Checkpoint 时间旅行 — Phase 3-Plan-1D

扩展 conversations + session_checkpoints 表 + 新增 branches 表。
迁移幂等，可重复运行。
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "20260829c"
down_revision = "20260829b_memory_vector"  # 接 memory vector 迁移
branch_labels = None
depends_on = None


def upgrade():
    # ---- conversations 表扩展 ----
    op.execute(
        """
        ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS head_checkpoint_id UUID
            REFERENCES session_checkpoints(id) ON DELETE SET NULL
        """
    )
    op.execute(
        """
        ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS main_branch_id UUID
        """
    )

    # ---- session_checkpoints 表扩展 ----
    op.execute(
        """
        ALTER TABLE session_checkpoints
        ADD COLUMN IF NOT EXISTS branch_id UUID NOT NULL DEFAULT gen_random_uuid()
        """
    )
    op.execute(
        """
        ALTER TABLE session_checkpoints
        ADD COLUMN IF NOT EXISTS parent_checkpoint_id UUID
            REFERENCES session_checkpoints(id) ON DELETE SET NULL
        """
    )
    op.execute(
        """
        ALTER TABLE session_checkpoints
        ADD COLUMN IF NOT EXISTS messages_snapshot JSONB NOT NULL DEFAULT '[]'::jsonb
        """
    )
    op.execute(
        """
        ALTER TABLE session_checkpoints
        ADD COLUMN IF NOT EXISTS checkpoint_kind VARCHAR(20) NOT NULL DEFAULT 'auto'
        """
    )
    op.execute(
        """
        ALTER TABLE session_checkpoints
        ADD COLUMN IF NOT EXISTS label VARCHAR(100)
        """
    )
    op.execute(
        """
        ALTER TABLE session_checkpoints
        ADD COLUMN IF NOT EXISTS merge_parents JSONB
        """
    )
    op.execute(
        """
        ALTER TABLE session_checkpoints
        ADD COLUMN IF NOT EXISTS is_head BOOLEAN NOT NULL DEFAULT FALSE
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_checkpoints_branch
        ON session_checkpoints(branch_id)
        """
    )

    # ---- branches 表新建 ----
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS branches (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID NOT NULL
                REFERENCES conversations(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            parent_branch_id UUID REFERENCES branches(id),
            head_checkpoint_id UUID REFERENCES session_checkpoints(id),
            is_archived BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            closed_at TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_branches_conv
        ON branches(conversation_id)
        """
    )


def downgrade():
    # ---- branches 表删除 ----
    op.execute("DROP INDEX IF EXISTS ix_branches_conv")
    op.execute("DROP TABLE IF EXISTS branches")

    # ---- session_checkpoints 表回退 ----
    op.execute("DROP INDEX IF EXISTS ix_checkpoints_branch")
    op.execute("ALTER TABLE session_checkpoints DROP COLUMN IF EXISTS is_head")
    op.execute("ALTER TABLE session_checkpoints DROP COLUMN IF EXISTS merge_parents")
    op.execute("ALTER TABLE session_checkpoints DROP COLUMN IF EXISTS label")
    op.execute("ALTER TABLE session_checkpoints DROP COLUMN IF EXISTS checkpoint_kind")
    op.execute("ALTER TABLE session_checkpoints DROP COLUMN IF EXISTS messages_snapshot")
    op.execute("ALTER TABLE session_checkpoints DROP COLUMN IF EXISTS parent_checkpoint_id")
    op.execute("ALTER TABLE session_checkpoints DROP COLUMN IF EXISTS branch_id")

    # ---- conversations 表回退 ----
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS main_branch_id")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS head_checkpoint_id")
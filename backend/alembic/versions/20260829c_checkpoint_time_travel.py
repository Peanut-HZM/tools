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
    # main_branch_id FK 约束（幂等：仅当约束不存在时添加）
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.table_constraints
                WHERE constraint_name = 'fk_conversations_main_branch_id_branches'
                AND table_name = 'conversations'
            ) THEN
                ALTER TABLE conversations
                ADD CONSTRAINT fk_conversations_main_branch_id_branches
                FOREIGN KEY (main_branch_id) REFERENCES branches(id) ON DELETE SET NULL;
            END IF;
        END$$;
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

    # ---- 回填：每个 conversation 创建 '主线' branch（若尚无），然后把所有
    # 旧 checkpoint.branch_id 散落的"幽灵分支"指回主线，避免悬空 ----
    op.execute(
        """
        INSERT INTO branches (id, conversation_id, name, created_at)
        SELECT gen_random_uuid(), c.id, '主线', NOW()
        FROM conversations c
        WHERE NOT EXISTS (
            SELECT 1 FROM branches b WHERE b.conversation_id = c.id
        )
        """
    )
    op.execute(
        """
        UPDATE session_checkpoints sc
        SET branch_id = b.id
        FROM branches b
        WHERE b.conversation_id = sc.conversation_id
          AND b.name = '主线'
          AND sc.branch_id NOT IN (SELECT id FROM branches)
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
    op.execute(
        "ALTER TABLE conversations DROP CONSTRAINT IF EXISTS fk_conversations_main_branch_id_branches"
    )
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS main_branch_id")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS head_checkpoint_id")
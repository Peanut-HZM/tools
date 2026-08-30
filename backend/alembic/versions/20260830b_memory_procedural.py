"""P2-② Memory procedural — agent_procedural_memory 表 + agents 新列

迁移幂等，可重复运行。
"""
from alembic import op

revision = "20260830b"
down_revision = "20260830a"  # 接 P2-①c command_json 迁移
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_procedural_memory (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            name VARCHAR(100) NOT NULL,
            trigger TEXT NOT NULL,
            content TEXT NOT NULL,
            importance FLOAT NOT NULL DEFAULT 0.5,
            use_count INTEGER NOT NULL DEFAULT 0,
            is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_procedural_agent_user_name UNIQUE (agent_id, user_id, name)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_procedural_agent_user "
        "ON agent_procedural_memory (agent_id, user_id)"
    )
    op.execute(
        """
        ALTER TABLE agents
        ADD COLUMN IF NOT EXISTS memory_procedural_enabled BOOLEAN DEFAULT FALSE
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS agent_procedural_memory")
    op.execute("ALTER TABLE agents DROP COLUMN IF EXISTS memory_procedural_enabled")

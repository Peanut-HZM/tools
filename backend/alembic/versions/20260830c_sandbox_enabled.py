"""P2-③ 多模态沙箱 — agents 增加 sandbox_enabled 列

迁移幂等，可重复运行。
"""
from alembic import op

revision = "20260830c"
down_revision = "20260830b"  # 接 P2-② memory procedural 迁移
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE agents
        ADD COLUMN IF NOT EXISTS sandbox_enabled BOOLEAN DEFAULT FALSE
        """
    )


def downgrade():
    op.execute("ALTER TABLE agents DROP COLUMN IF EXISTS sandbox_enabled")

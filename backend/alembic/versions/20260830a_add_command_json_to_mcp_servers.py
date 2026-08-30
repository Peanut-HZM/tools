"""P2-①c 外部服务插件 — mcp_servers 增加 command_json 列

stdio transport 启动配置（JSON 字符串）。迁移幂等，可重复运行。
"""
from alembic import op

revision = "20260830a"
down_revision = "20260829c"  # 接 checkpoint 时间旅行迁移
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        ALTER TABLE mcp_servers
        ADD COLUMN IF NOT EXISTS command_json TEXT
        """
    )


def downgrade():
    op.execute(
        """
        ALTER TABLE mcp_servers
        DROP COLUMN IF EXISTS command_json
        """
    )

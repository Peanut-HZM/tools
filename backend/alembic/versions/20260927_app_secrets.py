"""应用级密钥表 app_secrets — 主密钥入库

背景：API Key 等敏感数据的主加密密钥此前放在各环境 .env（DB_ENCRYPTION_KEY），
密文却存在共享数据库，多设备/多部署各自持钥必然出现密文不可解（InvalidTag）。
主密钥入库后跟着数据库走，所有共享该库的环境天然一致。

迁移幂等，可重复运行。
"""
from alembic import op

revision = "20260927_app_secrets"
down_revision = "20260830d"  # 接 P3-⑨ agent_eval 迁移
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS app_secrets (
            key_id VARCHAR(64) PRIMARY KEY,
            secret_value TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ
        )
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS app_secrets")

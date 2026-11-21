"""add token usage channel

Revision ID: 20261121_token_usage_channel
Revises: 20261006_sanguo
Create Date: 2026-11-21

说明：生产部署链路（deploy.py）不自动执行 alembic，实际的幂等迁移在应用启动时
由 ``app.services.token_usage_schema.ensure_token_usage_channel_schema`` 完成。
本文件仅作可重放的留档。

幂等性：升级/降级均先查列/索引是否存在，重复执行不报错。
"""

from alembic import op
import sqlalchemy as sa


revision = "20261121_token_usage_channel"
down_revision = "20261006_sanguo"
branch_labels = None
depends_on = None


def _columns(conn) -> set[str]:
    inspector = sa.inspect(conn)
    return {col["name"] for col in inspector.get_columns("token_usage_records")}


def upgrade() -> None:
    conn = op.get_bind()
    if "channel" not in _columns(conn):
        op.add_column(
            "token_usage_records",
            sa.Column("channel", sa.String(length=64), nullable=True),
        )

    inspector = sa.inspect(conn)
    for constraint in inspector.get_unique_constraints("token_usage_records"):
        cols = set(constraint.get("column_names") or [])
        if cols == {"user_id", "device_id", "record_date", "source", "model"}:
            op.drop_constraint(
                constraint["name"], "token_usage_records", type_="unique"
            )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_token_usage_channel_key "
        "ON token_usage_records "
        "(user_id, device_id, record_date, source, channel, model)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_token_usage_channel "
        "ON token_usage_records (user_id, record_date, channel)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_token_usage_channel")
    op.execute("DROP INDEX IF EXISTS uq_token_usage_channel_key")
    conn = op.get_bind()
    if "channel" in _columns(conn):
        op.drop_column("token_usage_records", "channel")
"""token usage device fingerprint support

Revision ID: 20260607_token_usage_device_fingerprint
Revises: 20260516_token_usage_dimensions
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa


revision = "20260607_token_usage_device_fingerprint"
down_revision = "20260516_token_usage_dimensions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) 扩展 device_registry
    op.add_column(
        "device_registry",
        sa.Column("device_fingerprint", sa.String(length=256), nullable=True),
    )
    op.add_column(
        "device_registry",
        sa.Column("fingerprint_version", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "device_registry",
        sa.Column("id_type", sa.String(length=16), nullable=False, server_default="uuid"),
    )
    op.create_index(
        "idx_device_registry_fingerprint",
        "device_registry",
        ["user_id", "device_fingerprint"],
        unique=False,
    )

    # 2) 创建 device_id_alias 表
    op.create_table(
        "device_id_alias",
        sa.Column("alias_device_id", sa.String(length=128), nullable=False),
        sa.Column("canonical_device_id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("alias_device_id"),
    )
    op.create_index(
        "idx_device_alias_user",
        "device_id_alias",
        ["user_id", "canonical_device_id"],
        unique=False,
    )

    # 3) 创建 device_merge_log 表
    op.create_table(
        "device_merge_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("source_device_id", sa.String(length=128), nullable=False),
        sa.Column("target_device_id", sa.String(length=128), nullable=False),
        sa.Column("merged_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_device_merge_log_user",
        "device_merge_log",
        ["user_id", "merged_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("device_merge_log")
    op.drop_table("device_id_alias")
    op.drop_index("idx_device_registry_fingerprint", table_name="device_registry")
    op.drop_column("device_registry", "id_type")
    op.drop_column("device_registry", "fingerprint_version")
    op.drop_column("device_registry", "device_fingerprint")

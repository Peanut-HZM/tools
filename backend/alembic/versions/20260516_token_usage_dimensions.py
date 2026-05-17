"""add token usage dimension columns

Revision ID: 20260516_token_usage_dimensions
Revises: 6a4a752ab3ad
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260516_token_usage_dimensions"
down_revision = "6a4a752ab3ad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "token_usage_records",
        sa.Column("source_raw", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "token_usage_records",
        sa.Column("tool_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "token_usage_records",
        sa.Column("tool_name", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "token_usage_records",
        sa.Column("model_display_name", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "token_usage_records",
        sa.Column("device_name", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "idx_token_usage_dimensions",
        "token_usage_records",
        ["user_id", "record_date", "tool_id", "device_id", "model"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_token_usage_dimensions", table_name="token_usage_records")
    op.drop_column("token_usage_records", "device_name")
    op.drop_column("token_usage_records", "model_display_name")
    op.drop_column("token_usage_records", "tool_name")
    op.drop_column("token_usage_records", "tool_id")
    op.drop_column("token_usage_records", "source_raw")

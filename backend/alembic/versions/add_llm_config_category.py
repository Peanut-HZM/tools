"""add category and suffix to llm_configs

Revision ID: add_llm_config_category
Revises: 5472dbd39274
Create Date: 2026-03-03

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "add_llm_config_category"
down_revision = "5472dbd39274"  # 依赖于 Product Manager Agent 表的迁移
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 添加 category 字段
    op.add_column(
        "llm_configs",
        sa.Column("category", sa.String(20), server_default="chat", nullable=False),
    )
    # 添加 api_key_suffix 字段
    op.add_column(
        "llm_configs", sa.Column("api_key_suffix", sa.String(4), nullable=True)
    )
    # 添加 notes 字段
    op.add_column("llm_configs", sa.Column("notes", sa.String(500), nullable=True))
    # 添加 updated_at 字段
    op.add_column(
        "llm_configs",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("llm_configs", "updated_at")
    op.drop_column("llm_configs", "notes")
    op.drop_column("llm_configs", "api_key_suffix")
    op.drop_column("llm_configs", "category")

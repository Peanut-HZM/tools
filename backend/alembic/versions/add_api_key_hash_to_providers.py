"""add api_key_hash to llm_providers

Revision ID: add_api_key_hash_to_providers
Revises: add_llm_config_category
Create Date: 2026-08-24

llm_provider 模型添加了 api_key_hash 字段（用于幂等去重），
但表创建时未经过 alembic 迁移，需补加此列。
"""

from alembic import op
import sqlalchemy as sa


revision = "add_api_key_hash_to_providers"
down_revision = None  # 独立迁移，不依赖现有链（多 head 场景）
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "llm_providers",
        sa.Column(
            "api_key_hash",
            sa.LargeBinary(32),
            nullable=True,
            comment="SHA256 of plaintext api_key, for idempotent lookup",
        ),
    )
    op.create_index(
        op.f("ix_llm_providers_api_key_hash"),
        "llm_providers",
        ["api_key_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_llm_providers_api_key_hash"), table_name="llm_providers")
    op.drop_column("llm_providers", "api_key_hash")

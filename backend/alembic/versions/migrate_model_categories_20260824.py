"""migrate llm_models category: chat/code/image_polish→text, multimodal→vision

Revision ID: migrate_model_categories_20260824
Revises: add_api_key_hash_to_providers
Create Date: 2026-08-24

分类重整：
  - chat → text
  - code → text
  - image_polish → text
  - multimodal → vision
  - vision → vision (unchanged)
  - image_gen → image_gen (unchanged)
  - voice → voice (unchanged)
  - embedding → embedding (unchanged)
"""

from alembic import op
import sqlalchemy as sa


revision = "migrate_model_categories_20260824"
down_revision = "add_api_key_hash_to_providers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 批量更新 category 字段
    conn = op.get_bind()

    # chat → text
    conn.execute(
        sa.text("UPDATE llm_models SET category = 'text' WHERE category = 'chat'")
    )
    # code → text
    conn.execute(
        sa.text("UPDATE llm_models SET category = 'text' WHERE category = 'code'")
    )
    # image_polish → text
    conn.execute(
        sa.text("UPDATE llm_models SET category = 'text' WHERE category = 'image_polish'")
    )
    # multimodal → vision
    conn.execute(
        sa.text("UPDATE llm_models SET category = 'vision' WHERE category = 'multimodal'")
    )


def downgrade() -> None:
    """注意：降级无法精确还原原始分类（chat/code/image_polish 都映射到 text），
    统一回退为 chat（最常见的默认值）"""
    conn = op.get_bind()
    conn.execute(
        sa.text("UPDATE llm_models SET category = 'chat' WHERE category = 'text'")
    )
    conn.execute(
        sa.text("UPDATE llm_models SET category = 'multimodal' WHERE category = 'vision'")
    )

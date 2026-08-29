"""Revision ID: a848084f5062
Revises: 20260829_agent_memory_long_term
Create Date: 2026-08-29 14:17:13.877366

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'a848084f5062'
down_revision: Union[str, None] = '20260829_agent_memory_long_term'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # drop 两张 Dify image_gen 相关表，使用 if_exists 容错
    # 先 drop image_gen_history（可能存在指向 image_gen_conversations 的外键）
    op.drop_table('image_gen_history', if_exists=True)
    op.drop_table('image_gen_conversations', if_exists=True)


def downgrade() -> None:
    # 不实现 downgrade（不可逆操作）
    # 如需回滚，从 git 历史恢复代码即可
    pass

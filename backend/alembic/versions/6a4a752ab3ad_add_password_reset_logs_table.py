"""add password reset logs table

Revision ID: 6a4a752ab3ad
Revises: 5472dbd39274
Create Date: 2026-04-03 21:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = '6a4a752ab3ad'
down_revision: Union[str, None] = '5472dbd39274'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建密码重置日志表
    op.create_table(
        'password_reset_logs',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('reset_by_user_id', sa.String(length=36), nullable=False),
        sa.Column('reset_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('ip_address', sa.String(length=45), nullable=True),  # IPv6 最大长度
        sa.PrimaryKeyConstraint('id')
    )

    # 创建索引
    op.create_index('idx_password_reset_logs_user_id', 'password_reset_logs', ['user_id'], unique=False)
    op.create_index('idx_password_reset_logs_reset_at', 'password_reset_logs', ['reset_at'], unique=False)


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_password_reset_logs_reset_at', table_name='password_reset_logs')
    op.drop_index('idx_password_reset_logs_user_id', table_name='password_reset_logs')

    # 删除表
    op.drop_table('password_reset_logs')

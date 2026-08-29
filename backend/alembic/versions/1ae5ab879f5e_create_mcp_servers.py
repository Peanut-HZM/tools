"""Revision ID: 1ae5ab879f5e
Revises: a848084f5062
Create Date: 2026-08-29 15:41:46.681824

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers
revision: str = '1ae5ab879f5e'
down_revision: Union[str, None] = 'a848084f5062'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'mcp_servers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('server_url', sa.String(500), nullable=False),
        sa.Column('transport', sa.String(20), nullable=False, server_default='sse'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('headers_json', sa.Text(), nullable=True),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('last_connected_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('tools_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_mcp_servers_name', 'mcp_servers', ['name'])
    op.create_index('ix_mcp_servers_is_active', 'mcp_servers', ['is_active'])


def downgrade() -> None:
    op.drop_index('ix_mcp_servers_is_active', table_name='mcp_servers')
    op.drop_index('ix_mcp_servers_name', table_name='mcp_servers')
    op.drop_table('mcp_servers')

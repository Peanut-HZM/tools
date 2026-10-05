"""sanguo game records

Revision ID: 20261006_sanguo
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '20261006_sanguo'
down_revision: str | None = '20261005b_wftl'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    if "sanguo_game_records" not in existing:
        op.create_table(
            "sanguo_game_records",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("room_id", sa.String(16), nullable=False, index=True),
            sa.Column("board_name", sa.String(64), nullable=False,
                      server_default="4人身份局"),
            sa.Column("player_count", sa.Integer(), nullable=False),
            sa.Column("winner", sa.String(16), nullable=False),
            sa.Column("turn_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("duration_seconds", sa.Integer(), nullable=False,
                      server_default="0"),
            sa.Column("config", sa.JSON(), nullable=False),
            sa.Column("timeline", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("sanguo_game_records")

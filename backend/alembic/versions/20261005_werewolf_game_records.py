"""werewolf game records

Revision ID: 20261005_werewolf
Create Date: 2026-10-05

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '20261005_werewolf'
down_revision: str | None = '20260830d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 幂等守卫：开发库可能由 Base.metadata.create_all 初始化，表已存在时跳过
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    if "werewolf_game_records" not in existing:
        op.create_table(
            "werewolf_game_records",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("room_id", sa.String(16), nullable=False, index=True),
            sa.Column("board_name", sa.String(64), nullable=False),
            sa.Column("player_count", sa.Integer(), nullable=False),
            sa.Column("winner", sa.String(16), nullable=False),
            sa.Column("day_count", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("duration_seconds", sa.Integer(), nullable=False,
                      server_default="0"),
            sa.Column("config", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )
    if "werewolf_game_record_players" not in existing:
        op.create_table(
            "werewolf_game_record_players",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("record_id", sa.Integer(),
                      sa.ForeignKey("werewolf_game_records.id"),
                      nullable=False, index=True),
            sa.Column("user_id", sa.String(64), nullable=False, index=True),
            sa.Column("nickname", sa.String(64), nullable=False),
            sa.Column("role", sa.String(16), nullable=False),
            sa.Column("alive_at_end", sa.Boolean(), nullable=False,
                      server_default=sa.false()),
            sa.Column("is_winner", sa.Boolean(), nullable=False,
                      server_default=sa.false()),
        )


def downgrade() -> None:
    op.drop_table("werewolf_game_record_players")
    op.drop_table("werewolf_game_records")

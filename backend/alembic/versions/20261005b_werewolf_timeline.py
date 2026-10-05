"""werewolf game record timeline

Revision ID: 20261005b_wftl
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '20261005b_wftl'
down_revision: str | None = '20261005_werewolf'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_cols = {c["name"] for c in sa.inspect(bind).get_columns("werewolf_game_records")}
    if "timeline" not in existing_cols:
        op.add_column("werewolf_game_records",
                      sa.Column("timeline", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("werewolf_game_records") as batch_op:
        batch_op.drop_column("timeline")

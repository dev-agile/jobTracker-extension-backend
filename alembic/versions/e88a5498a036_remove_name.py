"""remove name

Revision ID: e88a5498a036
Revises: 0748b02f4b2d
Create Date: 2026-07-16 16:10:06.586926

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e88a5498a036'
down_revision: Union[str, Sequence[str], None] = '0748b02f4b2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("user_invites")}
    if "name" in cols:
        op.drop_column("user_invites", "name")


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("user_invites")}
    if "name" not in cols:
        op.add_column(
            "user_invites",
            sa.Column("name", sa.VARCHAR(), autoincrement=False, nullable=True),
        )

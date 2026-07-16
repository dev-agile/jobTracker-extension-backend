"""added name in user invite

Revision ID: 0748b02f4b2d
Revises: 615c60ad3e29
Create Date: 2026-07-16 16:08:08.281177

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0748b02f4b2d'
down_revision: Union[str, Sequence[str], None] = '615c60ad3e29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("user_invites")}
    if "name" not in cols:
        op.add_column("user_invites", sa.Column("name", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    cols = {c["name"] for c in sa.inspect(bind).get_columns("user_invites")}
    if "name" in cols:
        op.drop_column("user_invites", "name")

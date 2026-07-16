"""create initial schema

Revision ID: c0ffee000001
Revises:
Create Date: 2026-07-16 16:30:00.000000

Creates all tables for a fresh database. On existing DBs this is skipped
by Alembic (already stamped past this revision via descendants).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c0ffee000001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "users" in inspector.get_table_names():
        return

    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_invite_id", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="user"),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("user_invite_id"),
    )

    op.create_table(
        "user_invites",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("invited_by_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_user_invites_invited_by_id", "user_invites", ["invited_by_id"])

    op.create_table(
        "jobbs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=True),
        sa.Column("posted", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("skills", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("experience_level", sa.String(), nullable=True),
        sa.Column("hourly_range", sa.String(), nullable=True),
        sa.Column("hourly", sa.String(), nullable=True),
        sa.Column("project_length", sa.String(), nullable=True),
        sa.Column("fixed_price", sa.String(), nullable=True),
        sa.Column("cover_letter", sa.String(), nullable=True),
        sa.Column("connects", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=True),
        sa.Column("applied_date", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=True),
        sa.Column("updated_at", sa.String(), nullable=True),
    )
    op.create_index("ix_jobbs_user_id", "jobbs", ["user_id"])

    op.create_table(
        "activity",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("actor_display_name", sa.String(), nullable=True),
        sa.Column("actor_user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobbs.id"), nullable=True),
        sa.Column("user_invite_id", sa.String(), sa.ForeignKey("user_invites.id"), nullable=True),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_activity_actor_user_id", "activity", ["actor_user_id"])
    op.create_index("ix_activity_user_invite_id", "activity", ["user_invite_id"])


def downgrade() -> None:
    op.drop_table("activity")
    op.drop_table("jobbs")
    op.drop_table("user_invites")
    op.drop_table("users")

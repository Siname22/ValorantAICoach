"""Bind new coaching reports to their generating user."""

import sqlalchemy as sa
from alembic import op

revision = "20261126_01"
down_revision = "20261013_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "coaching_reports", sa.Column("owner_user_id", sa.String(36), nullable=True)
    )
    op.create_index(
        "ix_coaching_reports_owner_user_id", "coaching_reports", ["owner_user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_coaching_reports_owner_user_id", table_name="coaching_reports")
    op.drop_column("coaching_reports", "owner_user_id")

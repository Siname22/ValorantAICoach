"""Add last_synced_at column to linked_player_accounts table."""

import sqlalchemy as sa
from alembic import op

revision = "20261008_01"
down_revision = "20261007_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "linked_player_accounts",
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("linked_player_accounts", "last_synced_at")

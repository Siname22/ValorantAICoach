"""Add is_admin flag to users table."""

import sqlalchemy as sa
from alembic import op

revision = "20261013_01"
down_revision = "20261008_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")

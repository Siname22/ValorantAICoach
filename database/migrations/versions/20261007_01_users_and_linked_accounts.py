"""Create users and linked player accounts tables."""

import sqlalchemy as sa
from alembic import op

revision = "20261007_01"
down_revision = "20261006_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "linked_player_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("game_name", sa.String(64), nullable=False),
        sa.Column("tag_line", sa.String(16), nullable=False),
        sa.Column("puuid", sa.Text(), nullable=True),
        sa.Column("region", sa.String(16), nullable=True),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_linked_player_accounts_user_id",
        "linked_player_accounts",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_linked_player_accounts_user_id",
        table_name="linked_player_accounts",
    )
    op.drop_table("linked_player_accounts")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

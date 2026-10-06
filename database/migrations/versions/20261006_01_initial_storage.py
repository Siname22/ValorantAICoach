"""Create provider-backed storage without automatic application migrations."""

import sqlalchemy as sa
from alembic import op

revision = "20261006_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "players",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("game_name", sa.Text(), nullable=False),
        sa.Column("tag_line", sa.Text(), nullable=False),
        sa.Column("puuid", sa.Text()),
        sa.Column("region", sa.String(16)),
        sa.Column("source", sa.String(16)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "player_snapshots",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("operation", sa.String(32), nullable=False),
        sa.Column(
            "player_id", sa.String(64), sa.ForeignKey("players.id", ondelete="CASCADE")
        ),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("providers", sa.JSON(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_player_snapshots_expires_at", "player_snapshots", ["expires_at"]
    )
    op.create_table(
        "matches",
        sa.Column("provider", sa.String(16), primary_key=True),
        sa.Column("match_id", sa.Text(), primary_key=True),
        sa.Column("map_name", sa.Text()),
        sa.Column("mode", sa.Text()),
        sa.Column("provider_timestamp", sa.JSON()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("detail", sa.JSON()),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "player_match_history",
        sa.Column(
            "player_id",
            sa.String(64),
            sa.ForeignKey("players.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("provider", sa.String(16), primary_key=True),
        sa.Column("match_id", sa.Text(), primary_key=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider", "match_id"],
            ["matches.provider", "matches.match_id"],
            ondelete="CASCADE",
        ),
    )
    op.create_table(
        "coaching_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "player_id",
            sa.String(64),
            sa.ForeignKey("players.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("coaching_reports")
    op.drop_table("player_match_history")
    op.drop_table("matches")
    op.drop_index("ix_player_snapshots_expires_at", table_name="player_snapshots")
    op.drop_table("player_snapshots")
    op.drop_table("players")

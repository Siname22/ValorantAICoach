from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


class UTCDateTime(TypeDecorator):
    """Preserve UTC semantics when SQLite returns naive stored timestamps."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("An observation timestamp must include a timezone")
        return value.astimezone(UTC)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return (
            value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        )


class Base(DeclarativeBase):
    pass


class PlayerRecord(Base):
    __tablename__ = "players"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    game_name: Mapped[str] = mapped_column(Text)
    tag_line: Mapped[str] = mapped_column(Text)
    puuid: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(String(16))
    source: Mapped[str | None] = mapped_column(String(16))
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime())


class PlayerSnapshot(Base):
    __tablename__ = "player_snapshots"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    operation: Mapped[str] = mapped_column(String(32))
    player_id: Mapped[str | None] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE")
    )
    payload: Mapped[Any] = mapped_column(JSON, nullable=False)
    providers: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime())
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime(), index=True)


class MatchRecord(Base):
    __tablename__ = "matches"

    provider: Mapped[str] = mapped_column(String(16), primary_key=True)
    match_id: Mapped[str] = mapped_column(Text, primary_key=True)
    map_name: Mapped[str | None] = mapped_column(Text)
    mode: Mapped[str | None] = mapped_column(Text)
    provider_timestamp: Mapped[Any | None] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime())


class PlayerMatchHistory(Base):
    __tablename__ = "player_match_history"
    __table_args__ = (
        ForeignKeyConstraint(
            ["provider", "match_id"],
            ["matches.provider", "matches.match_id"],
            ondelete="CASCADE",
        ),
    )

    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.id", ondelete="CASCADE"), primary_key=True
    )
    provider: Mapped[str] = mapped_column(String(16), primary_key=True)
    match_id: Mapped[str] = mapped_column(Text, primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(UTCDateTime())


class CoachingReportRecord(Base):
    """Storage schema only; grounded report generation/ownership is not exposed yet."""

    __tablename__ = "coaching_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    player_id: Mapped[str] = mapped_column(ForeignKey("players.id", ondelete="CASCADE"))
    schema_version: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())


class UserRecord(Base):
    """Registered application user."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())


class LinkedAccountRecord(Base):
    """Player Riot account linked to a registered user."""

    __tablename__ = "linked_player_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    game_name: Mapped[str] = mapped_column(String(64), nullable=False)
    tag_line: Mapped[str] = mapped_column(String(16), nullable=False)
    puuid: Mapped[str | None] = mapped_column(Text, nullable=True)
    region: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    linked_at: Mapped[datetime] = mapped_column(UTCDateTime())
    last_synced_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True, default=None
    )

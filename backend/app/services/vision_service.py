"""Scoreboard screenshot extraction.

Only data actually read from the image is returned. When no vision model is
configured, or the model output is incomplete or invalid, extraction fails
explicitly; the service never substitutes synthetic statistics.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from backend.app.content.catalog import resolve_agent_name, resolve_map_name
from backend.app.schemas.vision_schemas import (
    ScoreboardAnalysisResponse,
    ScoreboardPlayerRow,
)
from backend.app.services.player_service import PlayerMatch
from pydantic import BaseModel, Field, NonNegativeInt, ValidationError

logger = logging.getLogger(__name__)

MAX_IMAGE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
MAX_SCOREBOARD_ROWS = 10


class VisionError(Exception):
    """Base exception for vision processing errors."""


class InvalidImageError(VisionError):
    """Raised when an uploaded image is invalid, corrupt, or of unsupported type."""


class VisionUnavailableError(VisionError):
    """Raised when no vision model is configured or reachable."""


class VisionExtractionError(VisionError):
    """Raised when the model output cannot be trusted as a scoreboard reading."""


def decode_and_validate_image(image_input: str | bytes) -> tuple[bytes, str]:
    """Decode base64 or accept raw bytes, validating image format and size."""
    if isinstance(image_input, str):
        # Strip potential data URL prefix, e.g. "data:image/png;base64,..."
        clean_base64 = image_input.strip()
        if "," in clean_base64 and clean_base64.startswith("data:"):
            clean_base64 = clean_base64.split(",", 1)[1]
        try:
            raw_bytes = base64.b64decode(clean_base64, validate=True)
        except Exception as exc:
            raise InvalidImageError("Invalid base64 encoding") from exc
    elif isinstance(image_input, bytes):
        raw_bytes = image_input
    else:
        raise InvalidImageError("Image input must be bytes or a base64 string")

    if not raw_bytes:
        raise InvalidImageError("Image data is empty")

    if len(raw_bytes) > MAX_IMAGE_SIZE_BYTES:
        raise InvalidImageError(
            f"Image exceeds maximum supported size of "
            f"{MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB"
        )

    # Magic byte inspection for PNG, JPEG, WebP
    if raw_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        mime_type = "image/png"
    elif raw_bytes.startswith(b"\xff\xd8\xff"):
        mime_type = "image/jpeg"
    elif (
        raw_bytes.startswith(b"RIFF")
        and len(raw_bytes) >= 12
        and raw_bytes[8:12] == b"WEBP"
    ):
        mime_type = "image/webp"
    else:
        raise InvalidImageError(
            "Unsupported image format. Allowed formats: PNG, JPEG, WebP"
        )

    return raw_bytes, mime_type


class _ModelRow(BaseModel):
    """Strict shape required from the model for one scoreboard row."""

    player_name: str = Field(min_length=1)
    tag_line: str | None = None
    agent: str = Field(min_length=1)
    team: Literal["friendly", "enemy", "blue", "red", "unknown"] = "unknown"
    score: NonNegativeInt | None = None
    kills: NonNegativeInt
    deaths: NonNegativeInt
    assists: NonNegativeInt
    damage_per_round: float | None = Field(default=None, ge=0)
    first_bloods: NonNegativeInt | None = None
    plants: NonNegativeInt | None = None
    defuses: NonNegativeInt | None = None


class _ModelScoreboard(BaseModel):
    """Strict shape required from the model for a whole scoreboard."""

    map_name: str = Field(min_length=1)
    game_mode: str | None = None
    result: Literal["Victory", "Defeat", "Draw"]
    rounds_won: NonNegativeInt
    rounds_lost: NonNegativeInt
    scoreboard_rows: list[_ModelRow] = Field(
        min_length=1, max_length=MAX_SCOREBOARD_ROWS
    )
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    tactical_takeaways: list[str] = Field(default_factory=list, max_length=5)


_PROMPT = (
    "You are reading a VALORANT end-of-match scoreboard screenshot.\n"
    "Return JSON only with: map_name, game_mode, result (Victory, Defeat or "
    "Draw, from the friendly team's perspective), rounds_won, rounds_lost, "
    "scoreboard_rows and confidence_score (0-1).\n"
    "Each scoreboard row: player_name, tag_line, agent, team ('friendly' or "
    "'enemy'), score (ACS), kills, deaths, assists, damage_per_round, "
    "first_bloods, plants, defuses.\n"
    "Only report values that are visible in the image. Use null for any value "
    "you cannot read. Never estimate or invent numbers. If the image is not a "
    'VALORANT scoreboard, return {"error": "not_a_scoreboard"}.\n'
    "Optionally add up to 3 tactical_takeaways that cite the visible numbers."
)


def _row_to_schema(row: _ModelRow) -> ScoreboardPlayerRow:
    return ScoreboardPlayerRow(
        player_name=row.player_name.strip(),
        tag_line=row.tag_line.strip() if row.tag_line else None,
        agent=resolve_agent_name(row.agent),
        team=row.team,
        score=row.score,
        kills=row.kills,
        deaths=row.deaths,
        assists=row.assists,
        damage_per_round=row.damage_per_round,
        first_bloods=row.first_bloods,
        plants=row.plants,
        defuses=row.defuses,
    )


def find_target_row(
    rows: list[ScoreboardPlayerRow],
    game_name: str | None,
    tag_line: str | None,
) -> ScoreboardPlayerRow | None:
    """Return the row matching the requested player, never a guessed substitute."""
    if not game_name:
        return None
    wanted = game_name.strip().casefold()
    candidates = [r for r in rows if r.player_name.strip().casefold() == wanted]
    if tag_line and len(candidates) > 1:
        wanted_tag = tag_line.strip().casefold()
        candidates = [
            r for r in candidates if (r.tag_line or "").strip().casefold() == wanted_tag
        ]
    return candidates[0] if len(candidates) == 1 else None


class ScoreboardVisionService:
    """Service to extract structured match data from scoreboard screenshots."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-2.5-flash",
    ) -> None:
        self.api_key = (
            api_key if api_key is not None else os.environ.get("GEMINI_API_KEY")
        )
        self.model_name = model_name

    def _get_genai_client(self) -> Any:
        if not self.api_key or not self.api_key.strip():
            return None
        try:
            from google import genai

            return genai.Client(api_key=self.api_key.strip())
        except ImportError:
            logger.warning("google-genai package not installed for vision service")
            return None
        except Exception as exc:
            logger.warning("Failed to initialize genai client: %s", type(exc).__name__)
            return None

    async def extract_scoreboard(
        self,
        image_data: str | bytes,
        *,
        target_game_name: str | None = None,
        target_tag_line: str | None = None,
    ) -> ScoreboardAnalysisResponse:
        """Read a scoreboard screenshot; fail explicitly instead of guessing."""
        raw_bytes, mime_type = decode_and_validate_image(image_data)

        client = self._get_genai_client()
        if client is None:
            raise VisionUnavailableError(
                "Scoreboard vision is not configured (GEMINI_API_KEY missing). "
                "No data was extracted."
            )

        try:
            text = await asyncio.to_thread(self._generate, client, raw_bytes, mime_type)
        except Exception as exc:
            logger.warning("Gemini vision request failed: %s", type(exc).__name__)
            raise VisionUnavailableError(
                "The vision model could not be reached. No data was extracted."
            ) from None

        return self._parse_model_output(
            text,
            target_game_name=target_game_name,
            target_tag_line=target_tag_line,
        )

    def _generate(self, client: Any, raw_bytes: bytes, mime_type: str) -> str:
        from google.genai import types

        image_part = types.Part.from_bytes(data=raw_bytes, mime_type=mime_type)
        response = client.models.generate_content(
            model=self.model_name,
            contents=[_PROMPT, image_part],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        return response.text or ""

    def _parse_model_output(
        self,
        text: str,
        *,
        target_game_name: str | None,
        target_tag_line: str | None,
    ) -> ScoreboardAnalysisResponse:
        try:
            data = json.loads(text)
        except (TypeError, json.JSONDecodeError):
            raise VisionExtractionError(
                "The vision model did not return valid JSON."
            ) from None
        if not isinstance(data, dict):
            raise VisionExtractionError("The vision model returned an invalid shape.")
        if data.get("error"):
            raise VisionExtractionError("The image was not recognised as a scoreboard.")
        try:
            board = _ModelScoreboard.model_validate(data)
        except ValidationError:
            raise VisionExtractionError(
                "The scoreboard could not be read completely; required values "
                "were missing or invalid."
            ) from None

        rows = [_row_to_schema(r) for r in board.scoreboard_rows]
        takeaways = [t.strip() for t in board.tactical_takeaways if t.strip()]
        return ScoreboardAnalysisResponse(
            match_id=f"vision-{uuid4().hex[:12]}",
            map_name=resolve_map_name(board.map_name),
            game_mode=board.game_mode or "Unknown",
            result=board.result,
            rounds_won=board.rounds_won,
            rounds_lost=board.rounds_lost,
            target_player_stats=find_target_row(
                rows, target_game_name, target_tag_line
            ),
            scoreboard_rows=rows,
            confidence_score=board.confidence_score,
            extractor_engine="gemini-multimodal",
            tactical_takeaways=takeaways,
            persisted_as_match=False,
        )

    def convert_to_player_match(
        self,
        analysis: ScoreboardAnalysisResponse,
        target_game_name: str,
        target_tag_line: str,
    ) -> PlayerMatch:
        """Convert the requested player's extracted row into a domain match.

        Raises VisionExtractionError when that player was not found on the
        scoreboard, so another player's stats are never stored as theirs.
        """
        stats = analysis.target_player_stats
        if (
            stats is None
            or stats.player_name.strip().casefold()
            != target_game_name.strip().casefold()
        ):
            stats = find_target_row(
                analysis.scoreboard_rows, target_game_name, target_tag_line
            )
        if stats is None:
            raise VisionExtractionError(
                f"Player '{target_game_name}#{target_tag_line}' was not found "
                "on the scoreboard."
            )
        return PlayerMatch(
            match_id=analysis.match_id,
            map_name=analysis.map_name,
            mode=analysis.game_mode,
            # The screenshot does not carry the match time; this is ingestion time.
            timestamp=datetime.now(UTC).isoformat(),
            result=analysis.result,
            kills=stats.kills,
            deaths=stats.deaths,
            assists=stats.assists,
            # Scoreboards show ACS, not total score.
            score=None,
            provider_score=stats.score,
            agent_name=resolve_agent_name(stats.agent),
            provider="vision",
        )

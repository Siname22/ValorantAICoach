from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from alembic import command
from alembic.config import Config
from backend.app.api.vision_router import get_vision_service
from backend.app.core.config import get_settings
from backend.app.dependencies.provider_deps import get_player_service
from backend.app.schemas.vision_schemas import (
    ScoreboardAnalysisResponse,
    ScoreboardPlayerRow,
)
from backend.app.services.vision_service import (
    InvalidImageError,
    ScoreboardVisionService,
    VisionExtractionError,
    VisionUnavailableError,
    decode_and_validate_image,
)
from backend.app.storage.models import MatchRecord, PlayerMatchHistory
from backend.app.storage.player_service import PersistentPlayerService
from backend.app.storage.repository import SQLPlayerStore
from backend.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

# 1x1 transparent PNG sample bytes
VALID_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06"
    b"\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf"
    b"\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
)
VALID_PNG_BASE64 = base64.b64encode(VALID_PNG_BYTES).decode("utf-8")

VALID_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb"
)
VALID_WEBP_BYTES = b"RIFF\x18\x00\x00\x00WEBPVP8 \x0c\x00\x00\x00/\x00\x00\x00\x00"


@pytest.fixture
def storage_database(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.chdir(tmp_path)
    url = f"sqlite+pysqlite:///{(tmp_path / 'coach.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("DATABASE_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "database/migrations"))
    engine = create_engine(url)
    try:
        yield config, engine, url
    finally:
        engine.dispose()
        get_settings.cache_clear()


@pytest.fixture(autouse=True)
def override_vision_auth():
    from backend.app.dependencies.auth_deps import get_current_user

    app.dependency_overrides[get_current_user] = lambda: {
        "id": "mock-vision-user",
        "email": "vision@test.com",
        "is_active": True,
        "is_admin": False,
    }
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_vision_endpoints_require_authentication():
    from backend.app.dependencies.auth_deps import get_current_user

    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as client:
        res = client.post(
            "/vision/scoreboard/analyze",
            json={"image_base64": VALID_PNG_BASE64},
        )
        assert res.status_code == 401


def test_decode_and_validate_image_valid_formats():
    raw, mime = decode_and_validate_image(VALID_PNG_BYTES)
    assert raw == VALID_PNG_BYTES
    assert mime == "image/png"

    raw_b64, mime_b64 = decode_and_validate_image(VALID_PNG_BASE64)
    assert raw_b64 == VALID_PNG_BYTES
    assert mime_b64 == "image/png"

    data_url = f"data:image/png;base64,{VALID_PNG_BASE64}"
    raw_url, mime_url = decode_and_validate_image(data_url)
    assert raw_url == VALID_PNG_BYTES
    assert mime_url == "image/png"

    _, mime_jpg = decode_and_validate_image(VALID_JPEG_BYTES)
    assert mime_jpg == "image/jpeg"

    _, mime_webp = decode_and_validate_image(VALID_WEBP_BYTES)
    assert mime_webp == "image/webp"


def test_decode_and_validate_image_invalid_cases():
    with pytest.raises(InvalidImageError, match="empty"):
        decode_and_validate_image(b"")

    with pytest.raises(InvalidImageError, match="Invalid base64"):
        decode_and_validate_image("not-a-valid-base-64-string!@#$")

    with pytest.raises(InvalidImageError, match="Unsupported image format"):
        decode_and_validate_image(b"GIF89a\x01\x00\x01\x00")

    with pytest.raises(InvalidImageError, match="exceeds maximum supported size"):
        oversized = b"\x89PNG\r\n\x1a\n" + (b"\x00" * (16 * 1024 * 1024))
        decode_and_validate_image(oversized)


@pytest.mark.asyncio
async def test_extract_scoreboard_no_api_key_raises_unavailable():
    service = ScoreboardVisionService(api_key="")
    with pytest.raises(VisionUnavailableError, match="GEMINI_API_KEY missing"):
        await service.extract_scoreboard(
            VALID_PNG_BYTES,
            target_game_name="TenZ",
            target_tag_line="SEN",
        )


@pytest.mark.asyncio
async def test_extract_scoreboard_unparseable_output_raises_extraction_error(
    monkeypatch,
):
    service = ScoreboardVisionService(api_key="synthetic-test-key")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Sorry, I cannot read this scoreboard."
    mock_client.models.generate_content.return_value = mock_response
    monkeypatch.setattr(service, "_get_genai_client", lambda: mock_client)

    with pytest.raises(
        VisionExtractionError, match="The vision model did not return valid JSON"
    ):
        await service.extract_scoreboard(
            VALID_PNG_BASE64,
            target_game_name="Derke",
            target_tag_line="FNC",
        )


@pytest.mark.asyncio
async def test_extract_scoreboard_gemini_multimodal_mocked(monkeypatch):
    service = ScoreboardVisionService(api_key="synthetic-test-key")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        '{"map_name": "/Game/Maps/Ascent/Ascent", "game_mode": "Competitive", '
        '"result": "Victory", "rounds_won": 13, "rounds_lost": 11, '
        '"target_player_stats": {"player_name": "Derke", "tag_line": "FNC", '
        '"agent": "Jett", "team": "friendly", "score": 280, "kills": 24, '
        '"deaths": 14, "assists": 5, "damage_per_round": 175.5}, '
        '"scoreboard_rows": [{"player_name": "Derke", "tag_line": "FNC", '
        '"agent": "Jett", "team": "friendly", "score": 280, "kills": 24, '
        '"deaths": 14, "assists": 5, "damage_per_round": 175.5}], '
        '"confidence_score": 0.98, "tactical_takeaways": ["High duel conversion."]}'
    )
    mock_client.models.generate_content.return_value = mock_response

    monkeypatch.setattr(service, "_get_genai_client", lambda: mock_client)

    analysis = await service.extract_scoreboard(
        VALID_PNG_BASE64,
        target_game_name="Derke",
        target_tag_line="FNC",
    )

    assert analysis.extractor_engine == "gemini-multimodal"
    assert analysis.map_name == "Ascent"  # Resolved by catalog
    assert analysis.rounds_won == 13
    assert analysis.rounds_lost == 11
    assert analysis.target_player_stats is not None
    assert analysis.target_player_stats.player_name == "Derke"
    assert analysis.target_player_stats.agent == "Jett"
    assert analysis.target_player_stats.kills == 24
    assert analysis.target_player_stats.score == 280


def test_convert_to_player_match():
    service = ScoreboardVisionService()
    analysis = ScoreboardAnalysisResponse(
        match_id="vision-test-123",
        map_name="Ascent",
        game_mode="Competitive",
        result="Victory",
        rounds_won=13,
        rounds_lost=7,
        confidence_score=0.92,
        extractor_engine="gemini-multimodal",
        tactical_takeaways=["Great play."],
        persisted_as_match=False,
        target_player_stats=ScoreboardPlayerRow(
            player_name="TenZ",
            tag_line="SEN",
            agent="Jett",
            team="friendly",
            score=310,
            kills=25,
            deaths=10,
            assists=4,
            damage_per_round=180.0,
        ),
    )

    match = service.convert_to_player_match(analysis, "TenZ", "SEN")
    assert match.match_id == "vision-test-123"
    assert match.map_name == "Ascent"
    assert match.result == "Victory"
    assert match.provider == "vision"
    assert match.score is None
    assert match.provider_score == 310
    assert match.agent_name == "Jett"
    assert match.kills == 25
    assert match.deaths == 10
    assert match.assists == 4


def test_convert_to_player_match_mismatched_target_raises():
    service = ScoreboardVisionService()
    analysis = ScoreboardAnalysisResponse(
        match_id="vision-test-123",
        map_name="Ascent",
        game_mode="Competitive",
        result="Victory",
        rounds_won=13,
        rounds_lost=7,
        extractor_engine="gemini-multimodal",
        target_player_stats=ScoreboardPlayerRow(
            player_name="Chronicle",
            tag_line="FNC",
            agent="Breach",
            kills=10,
            deaths=12,
            assists=15,
        ),
    )

    with pytest.raises(VisionExtractionError, match="was not found on the scoreboard"):
        service.convert_to_player_match(analysis, "TenZ", "SEN")


def test_api_analyze_scoreboard_endpoint():
    mock_svc = MagicMock(spec=ScoreboardVisionService)
    mock_svc.extract_scoreboard = AsyncMock(
        return_value=ScoreboardAnalysisResponse(
            match_id="vision-mock-123",
            map_name="Ascent",
            game_mode="Competitive",
            result="Victory",
            rounds_won=13,
            rounds_lost=7,
            extractor_engine="gemini-multimodal",
            target_player_stats=ScoreboardPlayerRow(
                player_name="TenZ",
                tag_line="SEN",
                agent="Jett",
                team="friendly",
                score=300,
                kills=20,
                deaths=10,
                assists=5,
            ),
        )
    )
    app.dependency_overrides[get_vision_service] = lambda: mock_svc
    try:
        with TestClient(app) as client:
            res = client.post(
                "/vision/scoreboard/analyze",
                json={
                    "image_base64": VALID_PNG_BASE64,
                    "game_name": "TenZ",
                    "tag_line": "SEN",
                    "save_to_history": False,
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert data["match_id"] == "vision-mock-123"
            assert data["extractor_engine"] == "gemini-multimodal"
            assert data["target_player_stats"]["player_name"] == "TenZ"
    finally:
        app.dependency_overrides.clear()


def test_api_analyze_scoreboard_unavailable_status():
    mock_svc = MagicMock(spec=ScoreboardVisionService)
    mock_svc.extract_scoreboard = AsyncMock(
        side_effect=VisionUnavailableError(
            "Scoreboard vision is not configured (GEMINI_API_KEY missing)."
        )
    )
    app.dependency_overrides[get_vision_service] = lambda: mock_svc
    try:
        with TestClient(app) as client:
            res = client.post(
                "/vision/scoreboard/analyze",
                json={
                    "image_base64": VALID_PNG_BASE64,
                    "game_name": "TenZ",
                    "tag_line": "SEN",
                },
            )
            assert res.status_code == 503
            assert "GEMINI_API_KEY missing" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_api_analyze_scoreboard_extraction_error_status():
    mock_svc = MagicMock(spec=ScoreboardVisionService)
    mock_svc.extract_scoreboard = AsyncMock(
        side_effect=VisionExtractionError("Image was unreadable")
    )
    app.dependency_overrides[get_vision_service] = lambda: mock_svc
    try:
        with TestClient(app) as client:
            res = client.post(
                "/vision/scoreboard/analyze",
                json={
                    "image_base64": VALID_PNG_BASE64,
                    "game_name": "TenZ",
                    "tag_line": "SEN",
                },
            )
            assert res.status_code == 422
            assert "Image was unreadable" in res.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_api_analyze_scoreboard_invalid_image_fails():
    with TestClient(app) as client:
        res = client.post(
            "/vision/scoreboard/analyze",
            json={
                "image_base64": "invalid-base64",
                "game_name": "TenZ",
                "tag_line": "SEN",
            },
        )
        assert res.status_code == 400
        assert "Invalid base64" in res.json()["detail"]


def test_api_upload_scoreboard_file():
    mock_svc = MagicMock(spec=ScoreboardVisionService)
    mock_svc.extract_scoreboard = AsyncMock(
        return_value=ScoreboardAnalysisResponse(
            match_id="vision-mock-456",
            map_name="Lotus",
            game_mode="Competitive",
            result="Victory",
            rounds_won=13,
            rounds_lost=9,
            extractor_engine="gemini-multimodal",
            target_player_stats=ScoreboardPlayerRow(
                player_name="Boaster",
                tag_line="FNC",
                agent="Omen",
                score=195,
                kills=14,
                deaths=13,
                assists=12,
            ),
        )
    )
    app.dependency_overrides[get_vision_service] = lambda: mock_svc
    try:
        with TestClient(app) as client:
            res = client.post(
                "/vision/scoreboard/upload",
                files={"file": ("scoreboard.png", VALID_PNG_BYTES, "image/png")},
                data={
                    "game_name": "Boaster",
                    "tag_line": "FNC",
                    "save_to_history": "false",
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert data["target_player_stats"]["player_name"] == "Boaster"
    finally:
        app.dependency_overrides.clear()


def test_api_player_scoreboard_convenience_endpoint():
    mock_svc = MagicMock(spec=ScoreboardVisionService)
    mock_svc.extract_scoreboard = AsyncMock(
        return_value=ScoreboardAnalysisResponse(
            match_id="vision-mock-789",
            map_name="Bind",
            game_mode="Competitive",
            result="Victory",
            rounds_won=13,
            rounds_lost=11,
            extractor_engine="gemini-multimodal",
            target_player_stats=ScoreboardPlayerRow(
                player_name="Chronicle",
                tag_line="FNC",
                agent="Breach",
                score=230,
                kills=18,
                deaths=14,
                assists=9,
            ),
        )
    )
    app.dependency_overrides[get_vision_service] = lambda: mock_svc
    try:
        with TestClient(app) as client:
            res = client.post(
                "/players/Chronicle/FNC/scoreboard",
                json={
                    "image_base64": VALID_PNG_BASE64,
                    "save_to_history": False,
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert data["target_player_stats"]["player_name"] == "Chronicle"
            assert data["target_player_stats"]["tag_line"] == "FNC"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_vision_match_persisted_to_storage(storage_database):
    config, engine, url = storage_database
    command.upgrade(config, "head")

    store = SQLPlayerStore(url, ttl_seconds=300, test_mode=True)
    try:
        service = PersistentPlayerService(
            store=store,
            riot_provider=AsyncMock(),
            henrik_provider=AsyncMock(),
            tracker_provider=AsyncMock(),
        )

        app.dependency_overrides[get_player_service] = lambda: service
        vision_svc = ScoreboardVisionService()
        mock_analysis = ScoreboardAnalysisResponse(
            match_id="vision-aspas-101",
            map_name="Ascent",
            game_mode="Competitive",
            result="Victory",
            rounds_won=13,
            rounds_lost=8,
            extractor_engine="gemini-multimodal",
            target_player_stats=ScoreboardPlayerRow(
                player_name="Aspas",
                tag_line="LEV",
                agent="Jett",
                team="friendly",
                score=340,
                kills=26,
                deaths=11,
                assists=3,
                damage_per_round=192.0,
            ),
        )
        vision_svc.extract_scoreboard = AsyncMock(return_value=mock_analysis)
        app.dependency_overrides[get_vision_service] = lambda: vision_svc

        with TestClient(app) as client:
            res = client.post(
                "/players/Aspas/LEV/scoreboard",
                json={
                    "image_base64": VALID_PNG_BASE64,
                    "save_to_history": True,
                },
            )
            assert res.status_code == 200
            data = res.json()
            assert data["persisted_as_match"] is True

        # Verify DB directly has the MatchRecord
        with Session(engine) as session:
            match_row = session.scalar(
                select(MatchRecord).where(MatchRecord.match_id == "vision-aspas-101")
            )
            assert match_row is not None
            assert match_row.map_name == "Ascent"
            assert match_row.provider == "vision"

            history_row = session.scalar(
                select(PlayerMatchHistory).where(
                    PlayerMatchHistory.match_id == "vision-aspas-101"
                )
            )
            assert history_row is not None
            assert history_row.payload["provider"] == "vision"
            assert history_row.payload["score"] is None
            assert history_row.payload["provider_score"] == 340
            assert history_row.payload["kills"] == 26
            assert history_row.payload["deaths"] == 11
            assert history_row.payload["assists"] == 3

    finally:
        app.dependency_overrides.clear()
        store.close()

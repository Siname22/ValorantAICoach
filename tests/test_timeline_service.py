"""Tests for round-by-round replay timeline analysis and tactical metrics."""

from typing import Any
from unittest.mock import AsyncMock

import pytest
from backend.app.dependencies.provider_deps import get_player_service
from backend.app.schemas.timeline_schemas import (
    MatchTimelineResponse,
    PlayerTimelineAnalyticsResponse,
)
from backend.app.services.player_service import PlayerNotFoundError
from backend.app.services.timeline_service import TimelineService
from backend.main import app
from fastapi.testclient import TestClient


@pytest.fixture
def mock_player_service():
    service = AsyncMock()
    app.dependency_overrides[get_player_service] = lambda: service
    yield service
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    return TestClient(app)


def create_sample_match_detail() -> dict[str, Any]:
    """Create a realistic sample Riot-style match detail fixture."""
    return {
        "matchInfo": {
            "matchId": "test-match-101",
            "mapId": "/Game/Maps/Ascent/Ascent",
            "gameMode": "Competitive",
            "gameStartMillis": 1728000000000,
        },
        "players": [
            {
                "puuid": "p-tenz",
                "gameName": "TenZ",
                "tagLine": "SEN",
                "teamId": "Blue",
                "characterId": "add6443a-41bd-e414-f6ad-e58d267f4e95",
            },
            {
                "puuid": "p-sacy",
                "gameName": "Sacy",
                "tagLine": "SEN",
                "teamId": "Blue",
                "characterId": "dade69b4-4f5a-8528-247b-219e5a1facd6",
            },
            {
                "puuid": "p-derke",
                "gameName": "Derke",
                "tagLine": "FNC",
                "teamId": "Red",
                "characterId": "eb93336a-449b-9c1b-0a54-a891f7921d69",
            },
            {
                "puuid": "p-chronicle",
                "gameName": "Chronicle",
                "tagLine": "FNC",
                "teamId": "Red",
                "characterId": "cc8b64c8-4b25-4ff9-6e7f-37b4da43d235",
            },
        ],
        "teams": [
            {"teamId": "Blue", "won": True, "roundsWon": 13},
            {"teamId": "Red", "won": False, "roundsWon": 7},
        ],
        "roundResults": [
            # Round 1: Pistol Round, Trade Kill sequence
            {
                "roundNum": 0,
                "roundResult": "Eliminated",
                "roundCeremony": "CeremonyDefault",
                "winningTeam": "Blue",
                "plantRoundTime": 0,
                "defuseRoundTime": 0,
                "playerStats": [
                    {
                        "puuid": "p-derke",
                        "economy": {
                            "loadoutValue": 800,
                            "weapon": "Ghost",
                            "remaining": 200,
                        },
                        "kills": [
                            {
                                "roundTime": 15000,
                                "gameTime": 15000,
                                "killer": "p-derke",
                                "victim": "p-sacy",
                                "assistants": [],
                                "finishingDamage": {
                                    "damageType": "Weapon",
                                    "damageItem": "Ghost",
                                },
                                "damage": [{"headshots": 1}],
                            }
                        ],
                    },
                    {
                        "puuid": "p-tenz",
                        "economy": {
                            "loadoutValue": 800,
                            "weapon": "Classic",
                            "remaining": 400,
                        },
                        "kills": [
                            # Trade kill within 1.5s (15000 -> 16500)
                            {
                                "roundTime": 16500,
                                "gameTime": 16500,
                                "killer": "p-tenz",
                                "victim": "p-derke",
                                "assistants": [],
                                "finishingDamage": {
                                    "damageType": "Weapon",
                                    "damageItem": "Classic",
                                },
                                "damage": [{"headshots": 1}],
                            },
                            # Non-trade kill later in the round (16500 -> 35000)
                            {
                                "roundTime": 35000,
                                "gameTime": 35000,
                                "killer": "p-tenz",
                                "victim": "p-chronicle",
                                "assistants": [],
                                "finishingDamage": {
                                    "damageType": "Weapon",
                                    "damageItem": "Classic",
                                },
                                "damage": [{"headshots": 0}],
                            },
                        ],
                    },
                ],
            },
            # Round 2: Spike Plant & Defuse (Retake scenario)
            {
                "roundNum": 1,
                "roundResult": "Bomb defused",
                "roundCeremony": "CeremonyClutch",
                "winningTeam": "Blue",
                "bombPlanter": "p-chronicle",
                "plantRoundTime": 45000,
                "plantSite": "A",
                "bombDefuser": "p-tenz",
                "defuseRoundTime": 72000,
                "playerStats": [
                    {
                        "puuid": "p-tenz",
                        "economy": {
                            "loadoutValue": 3500,
                            "weapon": "Spectre",
                            "remaining": 1200,
                        },
                        "kills": [
                            {
                                "roundTime": 65000,
                                "gameTime": 65000,
                                "killer": "p-tenz",
                                "victim": "p-chronicle",
                                "assistants": [],
                                "finishingDamage": {
                                    "damageType": "Weapon",
                                    "damageItem": "Spectre",
                                },
                                "damage": [{"headshots": 1}],
                            }
                        ],
                    },
                    {
                        "puuid": "p-chronicle",
                        "economy": {
                            "loadoutValue": 1500,
                            "weapon": "Ghost",
                            "remaining": 200,
                        },
                        "kills": [],
                    },
                ],
            },
            # Round 3: Anti-Eco Loss (Blue has full buy, Red has eco, Red wins)
            {
                "roundNum": 2,
                "roundResult": "Eliminated",
                "roundCeremony": "CeremonyThrifty",
                "winningTeam": "Red",
                "plantRoundTime": 0,
                "defuseRoundTime": 0,
                "playerStats": [
                    {
                        "puuid": "p-tenz",
                        "economy": {
                            "loadoutValue": 10500,  # Full buy
                            "weapon": "Vandal",
                            "remaining": 800,
                        },
                        "kills": [],
                    },
                    {
                        "puuid": "p-sacy",
                        "economy": {
                            "loadoutValue": 10000,  # Full buy
                            "weapon": "Phantom",
                            "remaining": 500,
                        },
                        "kills": [],
                    },
                    {
                        "puuid": "p-derke",
                        "economy": {
                            "loadoutValue": 4500,  # Eco
                            "weapon": "Sheriff",
                            "remaining": 3000,
                        },
                        "kills": [
                            {
                                "roundTime": 22000,
                                "gameTime": 22000,
                                "killer": "p-derke",
                                "victim": "p-tenz",
                                "assistants": [],
                                "finishingDamage": {
                                    "damageType": "Weapon",
                                    "damageItem": "Sheriff",
                                },
                                "damage": [{"headshots": 1}],
                            },
                            {
                                "roundTime": 28000,
                                "gameTime": 28000,
                                "killer": "p-derke",
                                "victim": "p-sacy",
                                "assistants": [],
                                "finishingDamage": {
                                    "damageType": "Weapon",
                                    "damageItem": "Sheriff",
                                },
                                "damage": [{"headshots": 1}],
                            },
                        ],
                    },
                ],
            },
        ],
    }


def test_classify_economy():
    """Verify tiering of loadouts into eco, semi-eco, semi-buy, and full-buy."""
    assert TimelineService.classify_economy(1500) == "eco"
    assert TimelineService.classify_economy(2500) == "semi-eco"
    assert TimelineService.classify_economy(3600) == "semi-buy"
    assert TimelineService.classify_economy(4500) == "full-buy"


def test_resolve_weapon_name():
    """Verify mapping of known weapon UUIDs and cleanup of raw tokens."""
    # Vandal UUID
    assert (
        TimelineService.resolve_weapon_name("9c82e19d-4575-0200-1a81-3eacf00cd872")
        == "Vandal"
    )
    # Phantom UUID
    assert (
        TimelineService.resolve_weapon_name("ee8e8d15-496b-07ac-e5f6-8fae5d4c7b1a")
        == "Phantom"
    )
    # Raw token with namespace
    assert TimelineService.resolve_weapon_name("EWeaponType::Sheriff") == "Sheriff"
    assert TimelineService.resolve_weapon_name(None) == "Unknown"


def test_parse_match_timeline_trade_kills():
    """Verify timeline parser accurately identifies trade kills within 3.0s window."""
    detail = create_sample_match_detail()
    timeline = TimelineService.parse_match_timeline(
        detail, player_identifier="TenZ#SEN"
    )

    assert timeline.match_id == "test-match-101"
    assert timeline.map_name == "Ascent"
    assert timeline.friendly_team == "Blue"
    assert len(timeline.rounds) == 3

    r1 = timeline.rounds[0]
    assert r1.round_num == 1
    assert r1.friendly_won is True
    assert len(r1.kills) == 3

    # Kill 0: Derke kills Sacy (First Blood)
    assert r1.first_blood is not None
    assert r1.first_blood.killer_name == "Derke#FNC"
    assert r1.first_blood.is_trade_kill is False

    # Kill 1: TenZ trades Derke 1.5s after Sacy dies
    k1 = r1.kills[1]
    assert k1.killer_name == "TenZ#SEN"
    assert k1.victim_name == "Derke#FNC"
    assert k1.is_trade_kill is True
    assert k1.traded_killer_name == "Sacy#SEN"
    assert k1.trade_window_millis == 1500

    # Kill 2: TenZ kills Chronicle 18.5s later (not a trade)
    k2 = r1.kills[2]
    assert k2.is_trade_kill is False


def test_parse_match_timeline_spike_and_retake():
    """Verify detection of plant, defuse, and retake situations."""
    detail = create_sample_match_detail()
    timeline = TimelineService.parse_match_timeline(detail, player_identifier="p-tenz")

    r2 = timeline.rounds[1]
    assert r2.round_num == 2
    assert r2.win_type == "Bomb defused"
    assert r2.spike_plant is not None
    assert r2.spike_plant.site == "A"
    assert r2.spike_plant.player_name == "Chronicle#FNC"
    assert r2.spike_defuse is not None
    assert r2.spike_defuse.player_name == "TenZ#SEN"
    assert r2.spike_defuse.success is True
    assert r2.retake_situation is True
    assert r2.retake_successful is True
    assert r2.is_clutch is True
    assert r2.clutch_won is True
    assert r2.clutch_player == "TenZ#SEN"


def test_parse_match_timeline_anti_eco_loss():
    """Verify anti-eco loss detection when full-buy team loses to an eco."""
    detail = create_sample_match_detail()
    timeline = TimelineService.parse_match_timeline(
        detail, player_identifier="TenZ#SEN"
    )

    r3 = timeline.rounds[2]
    assert r3.round_num == 3
    assert r3.friendly_won is False
    assert r3.is_anti_eco_loss is True
    assert r3.is_thrifty is True

    # Summary checks
    summary = timeline.summary
    assert summary.total_rounds == 3
    assert summary.anti_eco_losses == 1
    assert summary.thrifty_wins == 0
    assert summary.clutch_wins == 1
    assert any("anti-eco" in t.lower() for t in summary.tactical_takeaways)


def test_parse_match_timeline_empty():
    """Verify graceful fallback with missing or empty round payloads."""
    empty_detail = {"matchInfo": {"matchId": "empty-1"}, "players": []}
    timeline = TimelineService.parse_match_timeline(empty_detail)
    assert timeline.match_id == "empty-1"
    assert len(timeline.rounds) == 0
    assert timeline.summary.total_rounds == 0


def test_aggregate_player_timeline_analytics():
    """Verify cross-match timeline metrics aggregation and tactical leak alerts."""
    m1 = create_sample_match_detail()
    m2 = create_sample_match_detail()

    analytics = TimelineService.aggregate_player_timeline_analytics(
        [m1, m2],
        player_identifier="TenZ#SEN",
        game_name="TenZ",
        tag_line="SEN",
    )

    assert analytics.game_name == "TenZ"
    assert analytics.tag_line == "SEN"
    assert analytics.matches_analyzed == 2
    assert analytics.total_rounds_analyzed == 6
    assert analytics.anti_eco_losses_total == 2
    assert "1v1" in analytics.clutches_won_breakdown
    assert any(
        "fugas frente a compras" in lk.lower()
        for lk in analytics.identified_tactical_leaks
    )


def test_get_match_timeline_endpoint(client, mock_player_service):
    """Verify GET /matches/{match_id}/timeline endpoint integration."""
    expected = MatchTimelineResponse(
        match_id="m-test-1",
        map_name="Ascent",
        game_mode="Standard",
        friendly_team="Blue",
        rounds=[],
        summary=TimelineService.compute_tactical_summary([], "Blue"),
    )
    mock_player_service.get_match_timeline = AsyncMock(return_value=expected)

    response = client.get("/matches/m-test-1/timeline?player=TenZ%23SEN")
    assert response.status_code == 200
    data = response.json()
    assert data["match_id"] == "m-test-1"
    assert data["map_name"] == "Ascent"
    mock_player_service.get_match_timeline.assert_awaited_once_with(
        "m-test-1", player_identifier="TenZ#SEN"
    )


def test_get_match_timeline_not_found(client, mock_player_service):
    """Verify GET /matches/{match_id}/timeline returns 404 when match not found."""
    mock_player_service.get_match_timeline = AsyncMock(
        side_effect=PlayerNotFoundError("Match not found")
    )
    response = client.get("/matches/unknown-match/timeline")
    assert response.status_code == 404


def test_get_player_timeline_analytics_endpoint(client, mock_player_service):
    """Verify GET /players/{game_name}/{tag_line}/timeline-analytics endpoint."""
    expected = PlayerTimelineAnalyticsResponse(
        game_name="TenZ",
        tag_line="SEN",
        matches_analyzed=3,
        total_rounds_analyzed=65,
        overall_attack_win_rate=54.5,
        overall_defense_win_rate=48.0,
        overall_trade_efficiency=33.3,
        overall_clutch_win_rate=50.0,
        clutches_won_breakdown={"1v1": 2},
        anti_eco_losses_total=1,
        retake_success_rate=40.0,
        identified_tactical_leaks=["Perfil equilibrado."],
    )
    mock_player_service.get_player_timeline_analytics = AsyncMock(return_value=expected)

    response = client.get("/players/TenZ/SEN/timeline-analytics?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert data["game_name"] == "TenZ"
    assert data["matches_analyzed"] == 3
    assert data["overall_attack_win_rate"] == 54.5
    mock_player_service.get_player_timeline_analytics.assert_awaited_once_with(
        "TenZ", "SEN", region=None, limit=3
    )


def test_get_player_timeline_analytics_invalid_limit(client, mock_player_service):
    """Verify validation error when limit is outside allowed range (1-10)."""
    response = client.get("/players/TenZ/SEN/timeline-analytics?limit=0")
    assert response.status_code == 422
    response = client.get("/players/TenZ/SEN/timeline-analytics?limit=25")
    assert response.status_code == 422

from __future__ import annotations

from unittest.mock import AsyncMock

from backend.app.dependencies.provider_deps import get_player_service
from backend.app.schemas.synergy_schemas import (
    CompositionSynergyRequest,
    CounterPickRequest,
)
from backend.app.services.player_service import PlayerMatch, PlayerService
from backend.app.services.synergy_service import SynergyService
from backend.main import app
from fastapi.testclient import TestClient


def test_evaluate_composition_synergy_balanced_meta():
    service = SynergyService()
    res = service.evaluate_composition_synergy(
        map_name="Ascent",
        allied_agents=["Sova", "Killjoy", "Omen", "Jett", "KAY/O"],
        enemy_agents=["Cypher", "Jett", "Reyna"],
    )

    assert res.map_name == "Ascent"
    assert res.synergy_score >= 85.0
    assert res.tier in ["S", "A"]
    assert res.role_distribution == {
        "Duelist": 1,
        "Initiator": 2,
        "Controller": 1,
        "Sentinel": 1,
    }
    assert res.utility_coverage.smokes is True
    assert res.utility_coverage.recon_info is True
    assert res.utility_coverage.flashes is True
    assert res.utility_coverage.sentinel_anchor is True
    assert res.utility_coverage.entry_duelist is True
    assert any("meta" in s.lower() for s in res.strengths)
    assert len(res.weaknesses) == 0


def test_evaluate_composition_synergy_missing_controller():
    service = SynergyService()
    res = service.evaluate_composition_synergy(
        map_name="Ascent",
        allied_agents=["Sova", "Killjoy", "Jett", "Reyna", "Raze"],
    )

    assert res.utility_coverage.smokes is False
    assert res.role_distribution["Controller"] == 0
    assert res.synergy_score < 75.0
    assert any("Missing Controller" in w for w in res.weaknesses)
    assert any("Controller" in a for a in res.tactical_advice)


def test_evaluate_composition_synergy_excess_duelists():
    service = SynergyService()
    res = service.evaluate_composition_synergy(
        map_name="Bind",
        allied_agents=["Jett", "Reyna", "Raze", "Phoenix"],
    )

    assert res.role_distribution["Duelist"] == 4
    assert res.synergy_score <= 50.0
    assert res.tier in ["C", "D"]
    assert any("Excess Duelists" in w for w in res.weaknesses)


def test_recommend_counter_picks_against_sentinels():
    service = SynergyService()
    res = service.recommend_counter_picks(
        map_name="Ascent",
        enemy_agents=["Cypher", "Killjoy"],
        allied_agents=["Jett", "Omen"],
        top_k=4,
    )

    assert res.map_name == "Ascent"
    assert len(res.recommendations) <= 4
    top_names = [r.agent_name for r in res.recommendations]
    # KAY/O and Sova are prime counters against Cypher and Killjoy
    assert "KAY/O" in top_names or "Sova" in top_names
    for r in res.recommendations:
        if r.agent_name in ["KAY/O", "Sova"]:
            assert len(r.counter_targets) > 0
            assert len(r.counter_rationale) > 0


def test_recommend_counter_picks_with_player_mastery():
    service = SynergyService()
    mock_history = [
        {
            "agent_name": "Sova",
            "result": "Victory",
            "kills": 20,
            "deaths": 10,
            "assists": 8,
        },
        {
            "agent_name": "Sova",
            "result": "Victory",
            "kills": 18,
            "deaths": 9,
            "assists": 11,
        },
        {
            "agent_name": "Sova",
            "result": "Victory",
            "kills": 22,
            "deaths": 12,
            "assists": 6,
        },
    ]

    res = service.recommend_counter_picks(
        map_name="Ascent",
        enemy_agents=["Cypher"],
        allied_agents=["Jett"],
        player_history_matches=mock_history,
    )

    sova_rec = next(r for r in res.recommendations if r.agent_name == "Sova")
    assert sova_rec.mastery_context is not None
    assert "3 match(es)" in sova_rec.mastery_context
    assert "100%" in sova_rec.mastery_context


def test_api_composition_synergy_endpoint():
    with TestClient(app) as client:
        req = CompositionSynergyRequest(
            map_name="Ascent",
            allied_agents=["Sova", "Killjoy", "Omen", "Jett", "KAY/O"],
            enemy_agents=["Cypher"],
        )
        res = client.post(
            "/recommendations/composition/synergy",
            json=req.model_dump(),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["map_name"] == "Ascent"
        assert data["synergy_score"] >= 80.0
        assert data["tier"] in ["S", "A"]


def test_api_counter_picks_endpoint():
    with TestClient(app) as client:
        req = CounterPickRequest(
            map_name="Bind",
            enemy_agents=["Killjoy", "Raze"],
            allied_agents=["Brimstone"],
        )
        res = client.post(
            "/recommendations/counter-picks",
            json=req.model_dump(),
        )
        assert res.status_code == 200
        data = res.json()
        assert data["map_name"] == "Bind"
        assert len(data["recommendations"]) > 0


def test_api_player_counter_picks_endpoint():
    mock_player_service = AsyncMock(spec=PlayerService)
    mock_player_service.get_recent_matches.return_value = [
        PlayerMatch(
            match_id="m1",
            map_name="Ascent",
            mode="Competitive",
            timestamp="2026-10-10T12:00:00Z",
            result="Victory",
            kills=21,
            deaths=10,
            assists=7,
            agent_name="KAY/O",
            provider="riot",
        ),
        PlayerMatch(
            match_id="m2",
            map_name="Ascent",
            mode="Competitive",
            timestamp="2026-10-10T14:00:00Z",
            result="Victory",
            kills=19,
            deaths=12,
            assists=11,
            agent_name="KAY/O",
            provider="riot",
        ),
    ]

    app.dependency_overrides[get_player_service] = lambda: mock_player_service
    try:
        with TestClient(app) as client:
            url = (
                "/players/Derke/FNC/counter-picks"
                "?map_name=Ascent&enemy_agents=Cypher&allied_agents=Jett"
            )
            res = client.get(url)
            assert res.status_code == 200
            data = res.json()
            assert data["map_name"] == "Ascent"
            kayo_rec = next(
                (r for r in data["recommendations"] if r["agent_name"] == "KAY/O"),
                None,
            )
            assert kayo_rec is not None
            assert kayo_rec["mastery_context"] is not None
            assert "2 match(es)" in kayo_rec["mastery_context"]
    finally:
        app.dependency_overrides.clear()

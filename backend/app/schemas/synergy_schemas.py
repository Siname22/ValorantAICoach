from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class UtilityCoverage(BaseModel):
    """Evaluation of essential tactical utility coverage in a team composition."""

    smokes: bool = Field(
        ...,
        description=(
            "Team has reliable smoke utility for executing and blocking vision"
        ),
    )
    flashes: bool = Field(
        ...,
        description=(
            "Team has blinding utility to clear tight angles or contest duels"
        ),
    )
    recon_info: bool = Field(
        ...,
        description=(
            "Team has information gathering utility to reveal enemy positions"
        ),
    )
    sentinel_anchor: bool = Field(
        ...,
        description=(
            "Team has defensive stall/anchor utility to hold sites and watch flanks"
        ),
    )
    entry_duelist: bool = Field(
        ...,
        description="Team has aggressive space-taking or movement entry utility",
    )


class CompositionSynergyRequest(BaseModel):
    """Request payload to analyze team composition synergy on a map."""

    map_name: str = Field(..., description="Map name (e.g. Ascent, Bind, Haven, Lotus)")
    allied_agents: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="List of allied agents selected (1 to 5 agents)",
    )
    enemy_agents: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Optional list of known enemy agents (up to 5 agents)",
    )


class CompositionSynergyResponse(BaseModel):
    """Detailed synergy rating and utility analysis for a composition."""

    map_name: str = Field(..., description="Canonical map display name")
    synergy_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Overall team synergy score between 0 and 100",
    )
    tier: Literal["S", "A", "B", "C", "D"] = Field(
        ..., description="Composition tier grade on the given map"
    )
    role_distribution: dict[str, int] = Field(
        ...,
        description=(
            "Count of agents per role (Duelist, Initiator, Controller, Sentinel)"
        ),
    )
    utility_coverage: UtilityCoverage = Field(
        ..., description="Status of essential tactical utilities"
    )
    strengths: list[str] = Field(
        default_factory=list, description="Tactical strengths of the lineup"
    )
    weaknesses: list[str] = Field(
        default_factory=list,
        description="Tactical vulnerabilities or missing utility",
    )
    tactical_advice: list[str] = Field(
        default_factory=list,
        description="Strategic recommendations for playing this comp",
    )


class CounterPickRequest(BaseModel):
    """Request payload to find best counter-pick agents."""

    map_name: str = Field(..., description="Map name (e.g. Ascent, Bind, Haven)")
    allied_agents: list[str] = Field(
        default_factory=list,
        max_length=4,
        description="Allied agents already locked in (0 to 4 agents)",
    )
    enemy_agents: list[str] = Field(
        ...,
        min_length=1,
        max_length=5,
        description="Known enemy agents to counter (1 to 5 agents)",
    )


class AgentCounterRecommendation(BaseModel):
    """Individual agent recommendation with counter rationales and synergy fit."""

    agent_name: str = Field(..., description="Canonical agent display name")
    role: str = Field(
        ..., description="Agent role (Duelist, Initiator, Controller, Sentinel)"
    )
    recommendation_score: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description=(
            "Overall fitness score combining counter capability and map affinity"
        ),
    )
    counter_targets: list[str] = Field(
        default_factory=list,
        description="Enemy agents this pick effectively counters",
    )
    counter_rationale: list[str] = Field(
        default_factory=list,
        description="Detailed tactical explanations for why this pick counters enemies",
    )
    map_synergy_rationale: str = Field(
        ...,
        description="Why this agent fits the specific map and allied composition",
    )
    mastery_context: str | None = Field(
        None,
        description="Player-specific historical performance context if available",
    )


class CounterPickResponse(BaseModel):
    """Ranked recommendations of counter-pick agents against the opposing lineup."""

    map_name: str = Field(..., description="Canonical map display name")
    recommendations: list[AgentCounterRecommendation] = Field(
        ..., description="Ranked list of top recommended agents to pick"
    )
    enemy_threat_assessment: list[str] = Field(
        default_factory=list,
        description="Key tactical threats posed by the enemy composition",
    )

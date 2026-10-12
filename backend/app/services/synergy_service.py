from __future__ import annotations

from typing import Any

from backend.app.content.catalog import (
    get_agent_info,
    get_all_agents,
    resolve_agent_name,
    resolve_map_name,
)
from backend.app.schemas.synergy_schemas import (
    AgentCounterRecommendation,
    CompositionSynergyResponse,
    CounterPickResponse,
    UtilityCoverage,
)

# Utility categories
SMOKE_AGENTS = {"Astra", "Brimstone", "Clove", "Harbor", "Omen", "Viper"}
FLASH_AGENTS = {"Breach", "KAY/O", "Skye", "Phoenix", "Reyna", "Yoru"}
RECON_AGENTS = {"Sova", "Fade", "Cypher", "Skye", "Gekko", "Tejo"}
SENTINEL_ANCHOR_AGENTS = {"Killjoy", "Cypher", "Deadlock", "Sage", "Vyse"}
ENTRY_DUELIST_AGENTS = {"Jett", "Raze", "Neon", "Yoru", "Iso", "Phoenix"}

# Top meta picks per map (competitive consensus)
MAP_META_PICKS: dict[str, set[str]] = {
    "Ascent": {"Sova", "Killjoy", "Omen", "Jett", "KAY/O"},
    "Bind": {"Brimstone", "Viper", "Raze", "Skye", "Cypher"},
    "Haven": {"Sova", "Breach", "Omen", "Killjoy", "Jett"},
    "Lotus": {"Fade", "Omen", "Killjoy", "Raze", "Breach", "Viper"},
    "Split": {"Raze", "Omen", "Cypher", "Breach", "Skye", "Jett"},
    "Breeze": {"Viper", "Sova", "Cypher", "Jett", "KAY/O"},
    "Icebox": {"Viper", "Sova", "Killjoy", "Sage", "Jett"},
    "Sunset": {"Cypher", "Omen", "Fade", "Raze", "Breach"},
    "Abyss": {"Omen", "Sova", "Cypher", "Jett", "Astra", "Vyse"},
    "Fracture": {"Breach", "Brimstone", "Raze", "Cypher", "Fade"},
    "Pearl": {"Astra", "Fade", "Killjoy", "Jett", "Viper"},
}

# Direct tactical counter mappings:
# COUNTER_MATRIX[counter_agent] = { target_agent: explanation }
COUNTER_MATRIX: dict[str, dict[str, str]] = {
    "KAY/O": {
        "Cypher": ("ZERO/POINT knife suppresses and disables Trapwires and Spycam."),
        "Killjoy": ("Suppression disables Turret, Alarmbot, and cancels Lockdown."),
        "Jett": ("Suppression denies Tailwind dash, neutralizing Operator angles."),
        "Raze": ("Disables Blast Pack mobility and cancels Showstopper rocket."),
        "Neon": ("Suppresses High Gear sprint/slide, eliminating fast rotate threats."),
        "Chamber": ("Disables Rendezvous teleport anchor and Headhunter utility."),
        "Viper": ("Suppresses Toxic Screen and Poison Cloud, clearing vision blocks."),
    },
    "Sova": {
        "Cypher": "Shock Darts break Tripwires safely from distance.",
        "Killjoy": "Hunter's Fury reliably destroys Lockdown through geometry.",
        "Jett": "Recon Bolt reveals snipers and forces Operators off angles.",
        "Viper": "Recon Bolt and Owl Drone tag enemies inside Viper's Pit.",
    },
    "Breach": {
        "Killjoy": "Aftershock destroys Lockdown ultimates and clears nests.",
        "Jett": "Fault Line concuss forces snipers off long angles.",
        "Chamber": "Heavy concuss and flashes force early teleports.",
        "Cypher": "Rolling Thunder and Aftershock detonate wire traps in chokes.",
    },
    "Raze": {
        "Cypher": (
            "Paint Shells and Boom Bot detonate Trapwires without line-of-sight."
        ),
        "Killjoy": (
            "Grenade cluster damage clears Alarmbot, Nanoswarms, and Lockdown."
        ),
        "Sage": (
            "Blast Packs allow easy traversal over Barrier Orb; nades break segments."
        ),
    },
    "Brimstone": {
        "Killjoy": (
            "Orbital Strike instantly eliminates Killjoy Lockdown from anywhere."
        ),
        "Cypher": (
            "Incendiary molly burns out narrow choke points and triggers wires."
        ),
        "Sage": "Orbital Strike wipes out Sage slow and barrier chokes on retakes.",
    },
    "Fade": {
        "Cypher": "Prowlers track player trails and trigger Trapwires safely.",
        "Viper": "Haunt and Nightfall reveal and deafen enemies inside Viper's Pit.",
        "Jett": "Seize tethers Jett and prevents Tailwind dash escapes.",
    },
    "Cypher": {
        "Jett": "Trapwires stop aggressive Tailwind dash entries in their tracks.",
        "Neon": "Trapwires abruptly halt High Gear slide-ins and reveal flankers.",
        "Raze": "High and low wire setups catch Blast Pack entries mid-flight.",
        "Yoru": "Tripwires and Spycam tag Dimensional Drift paths and fake decoys.",
    },
    "Killjoy": {
        "Neon": "Turret and Alarmbot slow momentum entries and warn of rotates.",
        "Raze": "Alarmbot vulnerability punishes aggressive site jumps in chokes.",
        "Jett": "Turret tagging breaks Jett dash accuracy and movement momentum.",
    },
    "Vyse": {
        "Jett": "Shear wall isolates Jett from her team upon dashing into site.",
        "Neon": "Shear wall blocks fast slides and divides executing attackers.",
        "Raze": "Shear barrier traps explosive entrants inside lethal crossfires.",
    },
    "Omen": {
        "Jett": ("Paranoia nearsight negates long-range Operator sightlines."),
        "Chamber": ("Paranoia forces Chamber to teleport away without taking duels."),
        "Sova": ("Dark Cover hollow smokes block sightlines without triggering recon."),
    },
}


class SynergyService:
    """Service to evaluate team composition synergy and recommend counter-picks."""

    def evaluate_composition_synergy(
        self,
        map_name: str,
        allied_agents: list[str],
        enemy_agents: list[str] | None = None,
    ) -> CompositionSynergyResponse:
        """Evaluate role balance, utility coverage, and map affinity."""
        canonical_map = resolve_map_name(map_name)
        resolved_allies = [resolve_agent_name(a) for a in allied_agents if a]
        resolved_enemies = [resolve_agent_name(e) for e in (enemy_agents or []) if e]

        # 1. Role distribution
        role_counts: dict[str, int] = {
            "Duelist": 0,
            "Initiator": 0,
            "Controller": 0,
            "Sentinel": 0,
        }
        for agent in resolved_allies:
            info = get_agent_info(agent)
            if info and info.role in role_counts:
                role_counts[info.role] += 1

        # 2. Utility coverage
        coverage = UtilityCoverage(
            smokes=any(a in SMOKE_AGENTS for a in resolved_allies),
            flashes=any(a in FLASH_AGENTS for a in resolved_allies),
            recon_info=any(a in RECON_AGENTS for a in resolved_allies),
            sentinel_anchor=any(a in SENTINEL_ANCHOR_AGENTS for a in resolved_allies),
            entry_duelist=any(a in ENTRY_DUELIST_AGENTS for a in resolved_allies),
        )

        # 3. Calculate synergy score
        score = 75.0
        strengths: list[str] = []
        weaknesses: list[str] = []
        advice: list[str] = []

        # Role checks
        if role_counts["Controller"] == 0:
            score -= 25.0
            weaknesses.append(
                "Missing Controller: No vision denial or smoke execution utility."
            )
            advice.append(
                "Prioritize locking at least one Controller (e.g. Omen, Viper)."
            )
        elif role_counts["Controller"] >= 1:
            score += 6.0
            strengths.append("Reliable vision denial via Controller smokes.")

        if role_counts["Initiator"] == 0:
            score -= 15.0
            weaknesses.append("Missing Initiator: No recon info or initiation utility.")
            advice.append(
                "Add an Initiator (e.g. Sova, Fade, Breach) to safely check angles."
            )
        elif role_counts["Initiator"] >= 1:
            score += 5.0
            strengths.append(
                "Structured initiation and space-clearing utility present."
            )

        if role_counts["Sentinel"] == 0:
            score -= 8.0
            weaknesses.append(
                "Missing Sentinel: Vulnerable to aggressive flanks and quick retakes."
            )
            advice.append(
                "Assign a player to watch flanks or maintain defensive stall."
            )
        else:
            score += 4.0
            strengths.append("Defensive site anchor and flank protection secured.")

        if role_counts["Duelist"] == 0:
            score -= 5.0
            weaknesses.append(
                "No dedicated Duelist: May struggle to crack open contested chokes."
            )
        elif role_counts["Duelist"] > 2:
            score -= 14.0
            weaknesses.append(
                f"Excess Duelists ({role_counts['Duelist']}): Utility-starved lineup."
            )
            advice.append(
                "Trade one duelist for supporting utility to improve round consistency."
            )
        else:
            score += 4.0
            strengths.append("Balanced duelist presence for entry fragging.")

        # Specific utility checks
        if not coverage.smokes and "Missing Controller" not in weaknesses[0]:
            score -= 10.0
            weaknesses.append("No reliable smoke coverage.")
        if not coverage.recon_info and not coverage.flashes:
            score -= 10.0
            weaknesses.append(
                "No recon or flash utility: Peeking corners blindly is high-risk."
            )

        # Map affinity bonuses
        meta_picks = MAP_META_PICKS.get(canonical_map, set())
        matched_meta = [a for a in resolved_allies if a in meta_picks]
        if matched_meta:
            score += min(len(matched_meta) * 3.0, 12.0)
            meta_str = ", ".join(matched_meta)
            strengths.append(
                f"High map synergy on {canonical_map}: Meta picks ({meta_str})."
            )

        # Enemy matchup check if enemy agents are provided
        if resolved_enemies:
            counters_ready = 0
            for enemy in resolved_enemies:
                for ally in resolved_allies:
                    if ally in COUNTER_MATRIX and enemy in COUNTER_MATRIX[ally]:
                        counters_ready += 1
                        break
            if counters_ready >= 2:
                score += 5.0
                strengths.append(
                    f"Solid counter-utility against {counters_ready} enemy threats."
                )

        # Normalize score
        final_score = max(10.0, min(100.0, round(score, 1)))

        # Tier calculation
        if final_score >= 88.0:
            tier = "S"
        elif final_score >= 75.0:
            tier = "A"
        elif final_score >= 60.0:
            tier = "B"
        elif final_score >= 45.0:
            tier = "C"
        else:
            tier = "D"

        if not advice:
            advice.append(
                "Coordinate initiator utility before duelist entries on sites."
            )

        return CompositionSynergyResponse(
            map_name=canonical_map,
            synergy_score=final_score,
            tier=tier,
            role_distribution=role_counts,
            utility_coverage=coverage,
            strengths=strengths,
            weaknesses=weaknesses,
            tactical_advice=advice,
        )

    def recommend_counter_picks(
        self,
        map_name: str,
        enemy_agents: list[str],
        allied_agents: list[str] | None = None,
        player_history_matches: list[dict[str, Any]] | None = None,
        top_k: int = 5,
    ) -> CounterPickResponse:
        """Recommend agent picks that counter the enemy composition on this map."""
        canonical_map = resolve_map_name(map_name)
        resolved_allies = {resolve_agent_name(a) for a in (allied_agents or []) if a}
        resolved_enemies = [resolve_agent_name(e) for e in enemy_agents if e]

        all_agents = get_all_agents()
        meta_picks = MAP_META_PICKS.get(canonical_map, set())

        # Determine missing roles in allied composition
        allied_roles = {
            get_agent_info(a).role for a in resolved_allies if get_agent_info(a)
        }

        # Calculate player historical performance per agent if history is provided
        mastery_stats: dict[str, dict[str, Any]] = {}
        if player_history_matches:
            for m in player_history_matches:
                agent = m.get("agent_name") or m.get("agent")
                if not agent:
                    continue
                c_agent = resolve_agent_name(agent)
                if c_agent not in mastery_stats:
                    mastery_stats[c_agent] = {"matches": 0, "wins": 0}
                mastery_stats[c_agent]["matches"] += 1
                res = str(m.get("result", "")).lower()
                if "win" in res or "vic" in res:
                    mastery_stats[c_agent]["wins"] += 1

        recommendations: list[AgentCounterRecommendation] = []
        threats: list[str] = []

        # Identify major enemy threats
        for enemy in resolved_enemies:
            if enemy in {"Cypher", "Killjoy"}:
                threats.append(f"{enemy}: Strong site lockdowns and flank detection.")
            elif enemy in {"Jett", "Chamber"}:
                threats.append(
                    f"{enemy}: High-impact Operator sniping and escape mobility."
                )
            elif enemy in {"Viper"}:
                threats.append(
                    f"{enemy}: Long-lasting line-of-sight denial and decay damage."
                )

        for agent_info in all_agents:
            agent_name = agent_info.name
            if agent_name in resolved_allies:
                continue  # Already locked by teammate

            score = 50.0
            countered_targets: list[str] = []
            counter_rationales: list[str] = []

            # 1. Counter power against enemy picks
            matrix_entry = COUNTER_MATRIX.get(agent_name, {})
            for enemy in resolved_enemies:
                if enemy in matrix_entry:
                    countered_targets.append(enemy)
                    counter_rationales.append(matrix_entry[enemy])
                    score += 16.0

            # 2. Map affinity
            if agent_name in meta_picks:
                score += 15.0
                map_rationale = f"Tier-1 competitive meta choice on {canonical_map}."
            else:
                map_rationale = f"Viable tactical pick on {canonical_map}."

            # 3. Allied role synergy bonus
            if agent_info.role not in allied_roles:
                score += 12.0
                map_rationale += f" Fills your team's missing {agent_info.role} role."

            # 4. Player mastery bonus
            mastery_note: str | None = None
            if agent_name in mastery_stats:
                stats = mastery_stats[agent_name]
                matches = stats["matches"]
                wins = stats["wins"]
                win_rate = (wins / matches) * 100 if matches > 0 else 0
                if matches >= 2:
                    score += min(matches * 2.0, 10.0)
                    if win_rate >= 50.0:
                        score += 5.0
                    mastery_note = (
                        f"Personal mastery: {matches} match(es) recorded with "
                        f"{win_rate:.0f}% win rate."
                    )

            final_score = max(10.0, min(100.0, round(score, 1)))

            recommendations.append(
                AgentCounterRecommendation(
                    agent_name=agent_name,
                    role=agent_info.role,
                    recommendation_score=final_score,
                    counter_targets=countered_targets,
                    counter_rationale=counter_rationales,
                    map_synergy_rationale=map_rationale,
                    mastery_context=mastery_note,
                )
            )

        # Sort recommendations descending by score
        recommendations.sort(key=lambda r: r.recommendation_score, reverse=True)
        top_recommendations = recommendations[:top_k]

        return CounterPickResponse(
            map_name=canonical_map,
            recommendations=top_recommendations,
            enemy_threat_assessment=list(dict.fromkeys(threats)),
        )

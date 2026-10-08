"""Timeline analysis service for Valorant round-by-round replay replays.

Parses official and normalized match payloads into granular chronological
round timelines, tracking kills, trades, Spike plants/defuses, economies,
clutches, anti-eco conversions, and tactical takeaways.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.app.content.catalog import resolve_map_name
from backend.app.schemas.timeline_schemas import (
    EconomyCategory,
    KillEvent,
    MatchTimelineResponse,
    PlayerRoundEconomy,
    PlayerTimelineAnalyticsResponse,
    RoundTimeline,
    Side,
    SpikeEvent,
    TimelineTacticalSummary,
    WinType,
)

logger = logging.getLogger(__name__)

# Common weapon UUIDs and display names in Valorant.
KNOWN_WEAPONS: dict[str, str] = {
    # Pistols
    "29a0cfab-485b-f5d5-779a-b59f85e204a8": "Classic",
    "42da8cee-42fc-274e-4992-9694a4e00423": "Shorty",
    "44d4e95c-4f52-294a-4a70-3fe0a455dfda": "Frenzy",
    "1baa85b4-4c70-1284-64bb-6481dfc3bb4e": "Ghost",
    "e3367f01-4f53-49e7-747b-36a59435b0f7": "Sheriff",
    # SMGs
    "f7e1b454-4ad4-1609-3838-5e95180e8b29": "Stinger",
    "462080d1-4035-2281-17cc-ad92c26ca6ec": "Spectre",
    # Shotguns
    "910be178-4f55-7076-9f89-20f11432aab2": "Bucky",
    "ec84293c-47ac-ba4a-01ec-dd953ba24cc2": "Judge",
    # Rifles
    "ae3de142-4d85-253a-bf64-2d8aba169571": "Bulldog",
    "4ade7faa-4cf1-8376-7ab2-86ba5de43228": "Guardian",
    "ee8e8d15-496b-07ac-e5f6-8fae5d4c7b1a": "Phantom",
    "9c82e19d-4575-0200-1a81-3eacf00cd872": "Vandal",
    # Snipers
    "c4883e50-4494-202c-4ec3-6b8a9284f80b": "Marshal",
    "5f0aaf3a-4b34-205a-5104-59b36347d83e": "Outlaw",
    "a03c24d1-470c-056e-6028-89517125916b": "Operator",
    # Heavies
    "55d8d0e7-4674-ad63-760c-4cace47bb5ee": "Ares",
    "63e6c2b6-4a88-4f11-5c81-739270dcedec": "Odin",
    # Melee
    "2f5f1409-424d-97e6-4c72-6c9f9b9f65db": "Tactical Knife",
}

# Max delta in milliseconds between consecutive kills for a trade kill.
TRADE_KILL_WINDOW_MILLIS: int = 3000


class TimelineService:
    """Core service for parsing, analyzing, and synthesizing replay timelines."""

    @staticmethod
    def classify_economy(loadout_value: int) -> EconomyCategory:
        """Classify round buy tier by loadout valuation."""
        if loadout_value < 2000:
            return "eco"
        if loadout_value < 3300:
            return "semi-eco"
        if loadout_value < 3900:
            return "semi-buy"
        return "full-buy"

    @staticmethod
    def resolve_weapon_name(item_id_or_name: str | None) -> str:
        """Resolve a weapon UUID or raw token into a display name."""
        if not item_id_or_name:
            return "Unknown"
        token = str(item_id_or_name).strip()
        lowered = token.lower()
        if lowered in KNOWN_WEAPONS:
            return KNOWN_WEAPONS[lowered]
        if "::" in token:
            token = token.split("::")[-1]
        return token

    @classmethod
    def parse_match_timeline(
        cls,
        match_detail: dict[str, Any],
        player_identifier: str | None = None,
    ) -> MatchTimelineResponse:
        """Parse raw match detail into a structured round-by-round timeline."""
        info = match_detail.get("matchInfo", {})
        match_id = str(info.get("matchId") or match_detail.get("match_id", "unknown"))
        raw_map = info.get("mapId") or match_detail.get("map_name", "Unknown")
        map_name = resolve_map_name(raw_map)
        game_mode = str(info.get("gameMode") or match_detail.get("mode", "Standard"))

        # Build player metadata lookup (puuid -> name, team, agent)
        players = match_detail.get("players", [])
        player_lookup: dict[str, dict[str, str]] = {}
        friendly_team: str | None = None

        norm_ident = player_identifier.lower().strip() if player_identifier else None

        for p in players:
            puuid = str(p.get("puuid", ""))
            gname = str(p.get("gameName", ""))
            tag = str(p.get("tagLine", ""))
            team_id = str(p.get("teamId", ""))
            display_name = f"{gname}#{tag}" if gname and tag else gname or puuid

            player_lookup[puuid] = {
                "name": display_name,
                "team": team_id,
                "puuid": puuid,
            }

            if norm_ident and (
                norm_ident == puuid.lower()
                or norm_ident == display_name.lower()
                or norm_ident == gname.lower()
            ):
                friendly_team = team_id

        if not friendly_team and players:
            friendly_team = str(players[0].get("teamId", "Blue"))

        raw_rounds = match_detail.get("roundResults", [])
        parsed_rounds: list[RoundTimeline] = []

        friendly_score = 0
        enemy_score = 0

        for r_idx, r in enumerate(raw_rounds):
            round_num = int(r.get("roundNum", r_idx)) + 1
            winning_team = str(r.get("winningTeam", "Unknown"))
            ceremony = r.get("roundCeremony")

            # Determine side for winning team:
            # Standard Valorant: Red attacks first half (1-12), Blue defends.
            # In second half (13-24), Red defends, Blue attacks.
            is_first_half = round_num <= 12
            red_side: Side = "attack" if is_first_half else "defense"
            blue_side: Side = "defense" if is_first_half else "attack"

            if winning_team == "Red":
                winning_side = red_side
            elif winning_team == "Blue":
                winning_side = blue_side
            else:
                winning_side = "unknown"

            friendly_won = (winning_team == friendly_team) if friendly_team else None
            if friendly_won:
                friendly_score += 1
            elif friendly_team and winning_team in ("Red", "Blue"):
                enemy_score += 1

            # Parse round win type
            raw_result = str(r.get("roundResult", ""))
            win_type: WinType = "Unknown"
            if "eliminated" in raw_result.lower():
                win_type = "Eliminated"
            elif "defused" in raw_result.lower():
                win_type = "Bomb defused"
            elif "detonated" in raw_result.lower() or "bomb" in raw_result.lower():
                win_type = "Bomb detonated"
            elif "time" in raw_result.lower() or "expired" in raw_result.lower():
                win_type = "Time out"
            elif "surrender" in raw_result.lower():
                win_type = "Surrender"

            # Parse player economies
            player_economies: dict[str, PlayerRoundEconomy] = {}
            team_loadouts: dict[str, int] = {"Red": 0, "Blue": 0}

            for pstats in r.get("playerStats", []):
                p_id = str(pstats.get("puuid", ""))
                econ_data = pstats.get("economy", {})
                loadout = int(econ_data.get("loadoutValue", 0))
                rem_creds = int(econ_data.get("remaining", 0))
                wep = cls.resolve_weapon_name(econ_data.get("weapon"))
                armor = econ_data.get("armor")
                cat = cls.classify_economy(loadout)

                p_name = player_lookup.get(p_id, {}).get("name", p_id)
                p_team = player_lookup.get(p_id, {}).get("team")
                if p_team in team_loadouts:
                    team_loadouts[p_team] += loadout

                player_economies[p_id] = PlayerRoundEconomy(
                    puuid=p_id,
                    player_name=p_name,
                    loadout_value=loadout,
                    weapon=wep,
                    armor=armor,
                    remaining_credits=rem_creds,
                    category=cat,
                )

            # Parse kills
            kills: list[KillEvent] = []
            kill_idx = 0
            for pstats in r.get("playerStats", []):
                for k in pstats.get("kills", []):
                    k_puuid = str(k.get("killer", ""))
                    v_puuid = str(k.get("victim", ""))
                    k_meta = player_lookup.get(k_puuid, {})
                    v_meta = player_lookup.get(v_puuid, {})

                    k_name = k_meta.get("name") or k_puuid or "Unknown"
                    v_name = v_meta.get("name") or v_puuid or "Unknown"
                    k_team = k_meta.get("team") or "Unknown"
                    v_team = v_meta.get("team") or "Unknown"

                    finishing = k.get("finishingDamage", {})
                    weapon_item = finishing.get("damageItem")
                    wep_name = cls.resolve_weapon_name(weapon_item)
                    is_hs = finishing.get("damageType") == "Weapon" and any(
                        d.get("headshots", 0) > 0 for d in k.get("damage", [])
                    )

                    assist_names = [
                        player_lookup.get(str(a), {}).get("name", str(a))
                        for a in k.get("assistants", [])
                    ]

                    round_time = int(k.get("roundTime", 0))
                    game_time = k.get("gameTime")

                    kills.append(
                        KillEvent(
                            kill_index=kill_idx,
                            round_time_millis=round_time,
                            game_time_millis=game_time,
                            killer_puuid=k_puuid,
                            killer_name=k_name,
                            killer_team=k_team,
                            victim_puuid=v_puuid,
                            victim_name=v_name,
                            victim_team=v_team,
                            assistants=assist_names,
                            weapon=wep_name,
                            is_headshot=is_hs,
                        )
                    )
                    kill_idx += 1

            # Sort kills chronologically
            kills.sort(key=lambda item: item.round_time_millis)
            for i, item in enumerate(kills):
                item.kill_index = i

            # Detect Trade Kills:
            # If player A (Team 1) kills B (Team 2) at T1, and at T2 (T2 - T1 <= 3000ms)
            # player C (Team 2) kills A, then that kill is a trade kill.
            for i in range(len(kills)):
                curr_kill = kills[i]
                for prev_idx in range(i - 1, -1, -1):
                    prev_kill = kills[prev_idx]
                    time_diff = (
                        curr_kill.round_time_millis - prev_kill.round_time_millis
                    )
                    if time_diff > TRADE_KILL_WINDOW_MILLIS:
                        break
                    # If current killer traded prev victim by killing prev killer
                    if (
                        curr_kill.victim_puuid == prev_kill.killer_puuid
                        and curr_kill.killer_team == prev_kill.victim_team
                    ):
                        curr_kill.is_trade_kill = True
                        curr_kill.traded_killer_name = prev_kill.victim_name
                        curr_kill.trade_window_millis = time_diff
                        break

            first_blood = kills[0] if kills else None
            first_death = kills[0] if kills else None

            # Parse Spike events
            plant_event: SpikeEvent | None = None
            defuse_event: SpikeEvent | None = None

            planter = r.get("bombPlanter")
            plant_time = int(r.get("plantRoundTime", 0))
            plant_site = r.get("plantSite")
            if planter or plant_time > 0 or plant_site:
                p_meta = player_lookup.get(str(planter), {})
                plant_event = SpikeEvent(
                    event_type="plant",
                    round_time_millis=plant_time,
                    site=str(plant_site) if plant_site else None,
                    player_puuid=str(planter) if planter else None,
                    player_name=p_meta.get("name"),
                    player_team=p_meta.get("team"),
                    success=True,
                )

            defuser = r.get("bombDefuser")
            defuse_time = int(r.get("defuseRoundTime", 0))
            if defuser or defuse_time > 0:
                d_meta = player_lookup.get(str(defuser), {})
                defuse_event = SpikeEvent(
                    event_type="defuse",
                    round_time_millis=defuse_time,
                    site=plant_event.site if plant_event else None,
                    player_puuid=str(defuser) if defuser else None,
                    player_name=d_meta.get("name"),
                    player_team=d_meta.get("team"),
                    success=(win_type == "Bomb defused"),
                )

            retake_situation = plant_event is not None
            retake_successful = defuse_event is not None and win_type == "Bomb defused"

            # Tactical flags: Clutch, Thrifty, Anti-eco loss
            is_clutch = ceremony == "CeremonyClutch"
            clutch_player: str | None = None
            clutch_opponents = 0
            clutch_won = False

            if is_clutch:
                clutch_won = True
                if kills:
                    last_kill = kills[-1]
                    clutch_player = last_kill.killer_name
                    # Estimate opponents faced
                    enemies_in_round = [
                        k.victim_puuid for k in kills if k.killer_team == winning_team
                    ]
                    clutch_opponents = max(len(enemies_in_round) or 1, 1)

            # Thrifty detection
            winner_loadout = team_loadouts.get(winning_team, 0)
            loser_team = "Blue" if winning_team == "Red" else "Red"
            loser_loadout = team_loadouts.get(loser_team, 0)

            is_thrifty = ceremony == "CeremonyThrifty" or (
                winner_loadout > 0 and winner_loadout < 12500 and loser_loadout >= 20000
            )

            # Anti-eco loss detection:
            # Friendly team had full loadout (>= 19000 total or >= 3800 avg),
            # while enemy had eco (< 12500 total), but friendly team lost.
            is_anti_eco_loss = False
            if friendly_team:
                friendly_loadout = team_loadouts.get(friendly_team, 0)
                other_team = loser_team if friendly_won else winning_team
                enemy_loadout = team_loadouts.get(other_team, 0)
                if (
                    not friendly_won
                    and friendly_loadout >= 18000
                    and enemy_loadout < 12500
                ):
                    is_anti_eco_loss = True

            parsed_rounds.append(
                RoundTimeline(
                    round_num=round_num,
                    winning_team=winning_team,
                    winning_side=winning_side,
                    win_type=win_type,
                    friendly_won=friendly_won,
                    ceremony=ceremony,
                    is_clutch=is_clutch,
                    clutch_player=clutch_player,
                    clutch_opponents=clutch_opponents,
                    clutch_won=clutch_won,
                    is_thrifty=is_thrifty,
                    is_anti_eco_loss=is_anti_eco_loss,
                    first_blood=first_blood,
                    first_death=first_death,
                    spike_plant=plant_event,
                    spike_defuse=defuse_event,
                    retake_situation=retake_situation,
                    retake_successful=retake_successful,
                    kills=kills,
                    player_economies=player_economies,
                    team_loadouts=team_loadouts,
                    friendly_score_after=friendly_score,
                    enemy_score_after=enemy_score,
                )
            )

        summary = cls.compute_tactical_summary(parsed_rounds, friendly_team)

        return MatchTimelineResponse(
            match_id=match_id,
            map_name=map_name,
            game_mode=game_mode,
            friendly_team=friendly_team,
            rounds=parsed_rounds,
            summary=summary,
        )

    @classmethod
    def compute_tactical_summary(
        cls,
        rounds: list[RoundTimeline],
        friendly_team: str | None,
    ) -> TimelineTacticalSummary:
        """Compute aggregate tactical metrics and diagnostic takeaways."""
        total_rounds = len(rounds)
        if total_rounds == 0:
            return TimelineTacticalSummary(total_rounds=0)

        atk_won = 0
        atk_total = 0
        def_won = 0
        def_total = 0

        first_bloods = 0
        first_deaths = 0
        fb_round_wins = 0

        trade_kills = 0
        friendly_deaths = 0

        clutch_attempts = 0
        clutch_wins = 0

        anti_eco_losses = 0
        thrifty_wins = 0

        retake_attempts = 0
        retake_successes = 0

        for r in rounds:
            is_friendly_winner = r.friendly_won is True
            # Determine if friendly team was attacking or defending
            is_friendly_atk = (r.winning_side == "attack" and is_friendly_winner) or (
                r.winning_side == "defense" and not is_friendly_winner
            )

            if is_friendly_atk:
                atk_total += 1
                if is_friendly_winner:
                    atk_won += 1
            else:
                def_total += 1
                if is_friendly_winner:
                    def_won += 1

            # First blood conversion
            if r.first_blood:
                fb = r.first_blood
                is_fb_friendly = fb.killer_team == friendly_team
                if is_fb_friendly:
                    first_bloods += 1
                    if is_friendly_winner:
                        fb_round_wins += 1
                else:
                    first_deaths += 1

            # Trade kills & friendly deaths
            for k in r.kills:
                if k.killer_team == friendly_team and k.is_trade_kill:
                    trade_kills += 1
                if k.victim_team == friendly_team:
                    friendly_deaths += 1

            # Clutches
            if r.is_clutch:
                clutch_attempts += 1
                if is_friendly_winner:
                    clutch_wins += 1

            # Anti-eco losses & thrifties
            if r.is_anti_eco_loss:
                anti_eco_losses += 1
            if r.is_thrifty and is_friendly_winner:
                thrifty_wins += 1

            # Retakes
            if r.retake_situation:
                # If friendly team was defending during plant
                friendly_defending = not is_friendly_atk
                if friendly_defending:
                    retake_attempts += 1
                    if r.retake_successful and is_friendly_winner:
                        retake_successes += 1

        atk_wr = round((atk_won / atk_total * 100), 1) if atk_total > 0 else 0.0
        def_wr = round((def_won / def_total * 100), 1) if def_total > 0 else 0.0
        fb_conv = (
            round((fb_round_wins / first_bloods * 100), 1) if first_bloods > 0 else 0.0
        )
        trade_eff = (
            round((trade_kills / friendly_deaths * 100), 1)
            if friendly_deaths > 0
            else 0.0
        )
        clutch_wr = (
            round((clutch_wins / clutch_attempts * 100), 1)
            if clutch_attempts > 0
            else 0.0
        )
        retake_sr = (
            round((retake_successes / retake_attempts * 100), 1)
            if retake_attempts > 0
            else 0.0
        )

        # Grounded tactical takeaways
        takeaways: list[str] = []

        if anti_eco_losses > 0:
            takeaways.append(
                f"Vulnerabilidad anti-eco: Se perdieron {anti_eco_losses} ronda(s) "
                f"con ventaja económica completa frente a compras económicas. "
                "Mantén mayor distancia angular y evita asomarte en solitario."
            )

        if trade_eff < 25.0 and friendly_deaths >= 5:
            takeaways.append(
                f"Baja eficiencia de tradeo ({trade_eff}%): Muy pocas bajas "
                "de compañeros fueron re-fragueadas en menos de 3s. "
                "Prioriza avanzar en parejas y posicionar fuego cruzado."
            )
        elif trade_eff >= 40.0:
            takeaways.append(
                f"Excelente disciplina de tradeo ({trade_eff}%): La mayoría de "
                "bajas aliadas fueron inmediatamente intercambiadas."
            )

        if first_bloods >= 3 and fb_conv >= 70.0:
            takeaways.append(
                f"Alta conversión tras Primera Sangre ({fb_conv}% de victoria): "
                "El equipo aprovecha con eficacia la ventaja numérica temprana."
            )
        elif first_bloods >= 3 and fb_conv < 45.0:
            takeaways.append(
                f"Pérdida de ventaja de Primera Sangre ({fb_conv}% de conversión): "
                "Se obtienen aperturas pero se dilapida la ventaja con "
                "sobre-extensiones."
            )

        if retake_attempts >= 3 and retake_sr < 30.0:
            takeaways.append(
                f"Dificultad en retoma de sitios post-plant ({retake_sr}% de éxito): "
                "Coordinar utilidades simultáneas y sincronizar accesos múltiples."
            )

        if atk_total >= 6 and def_total >= 6:
            if atk_wr - def_wr >= 25.0:
                takeaways.append(
                    f"Desbalance de bando: Marcado sesgo atacante ({atk_wr}% ataque vs "
                    f"{def_wr}% defensa). Reforzar anclajes en sitios de defensa."
                )
            elif def_wr - atk_wr >= 25.0:
                takeaways.append(
                    f"Desbalance de bando: Solidez defensiva ({def_wr}%) pero "
                    f"dificultad ofensiva ({atk_wr}%). Mejorar ejecución de entradas."
                )

        if not takeaways:
            takeaways.append(
                "Rendimiento táctico equilibrado en gestión económica y tradeos."
            )

        return TimelineTacticalSummary(
            total_rounds=total_rounds,
            attack_rounds_won=atk_won,
            attack_rounds_total=atk_total,
            attack_win_rate=atk_wr,
            defense_rounds_won=def_won,
            defense_rounds_total=def_total,
            defense_win_rate=def_wr,
            first_bloods_count=first_bloods,
            first_deaths_count=first_deaths,
            first_blood_conversion_rate=fb_conv,
            trade_kills_count=trade_kills,
            trade_efficiency_rate=trade_eff,
            clutch_attempts=clutch_attempts,
            clutch_wins=clutch_wins,
            clutch_win_rate=clutch_wr,
            anti_eco_losses=anti_eco_losses,
            thrifty_wins=thrifty_wins,
            retake_attempts=retake_attempts,
            retake_successes=retake_successes,
            retake_success_rate=retake_sr,
            tactical_takeaways=takeaways,
        )

    @classmethod
    def aggregate_player_timeline_analytics(
        cls,
        matches: list[dict[str, Any]],
        player_identifier: str,
        game_name: str,
        tag_line: str,
    ) -> PlayerTimelineAnalyticsResponse:
        """Aggregate tactical timeline metrics across a set of matches for a player."""
        total_rounds = 0
        atk_won_sum = 0
        atk_total_sum = 0
        def_won_sum = 0
        def_total_sum = 0
        trade_kills_sum = 0
        friendly_deaths_sum = 0
        clutch_attempts_sum = 0
        clutch_wins_sum = 0
        clutches_breakdown: dict[str, int] = {}
        anti_eco_losses_sum = 0
        retake_attempts_sum = 0
        retake_successes_sum = 0

        valid_matches_count = 0

        for m in matches:
            timeline = cls.parse_match_timeline(m, player_identifier)
            s = timeline.summary
            if s.total_rounds == 0:
                continue

            valid_matches_count += 1
            total_rounds += s.total_rounds
            atk_won_sum += s.attack_rounds_won
            atk_total_sum += s.attack_rounds_total
            def_won_sum += s.defense_rounds_won
            def_total_sum += s.defense_rounds_total
            trade_kills_sum += s.trade_kills_count
            anti_eco_losses_sum += s.anti_eco_losses
            retake_attempts_sum += s.retake_attempts
            retake_successes_sum += s.retake_successes
            clutch_attempts_sum += s.clutch_attempts
            clutch_wins_sum += s.clutch_wins

            for r in timeline.rounds:
                if r.is_clutch and r.clutch_won:
                    key = f"1v{r.clutch_opponents}"
                    clutches_breakdown[key] = clutches_breakdown.get(key, 0) + 1

                for k in r.kills:
                    if (
                        timeline.friendly_team
                        and k.victim_team == timeline.friendly_team
                    ):
                        friendly_deaths_sum += 1

        overall_atk_wr = (
            round((atk_won_sum / atk_total_sum * 100), 1) if atk_total_sum > 0 else 0.0
        )
        overall_def_wr = (
            round((def_won_sum / def_total_sum * 100), 1) if def_total_sum > 0 else 0.0
        )
        overall_trade_eff = (
            round((trade_kills_sum / friendly_deaths_sum * 100), 1)
            if friendly_deaths_sum > 0
            else 0.0
        )
        overall_clutch_wr = (
            round((clutch_wins_sum / clutch_attempts_sum * 100), 1)
            if clutch_attempts_sum > 0
            else 0.0
        )
        overall_retake_sr = (
            round((retake_successes_sum / retake_attempts_sum * 100), 1)
            if retake_attempts_sum > 0
            else 0.0
        )

        leaks: list[str] = []
        if anti_eco_losses_sum >= 2:
            leaks.append(
                f"Fugas frente a compras económicas ({anti_eco_losses_sum} rondas): "
                "Pérdidas recurrentes contra pistolas y armas de bajo coste. "
                "Mantener disciplina de distancias medias/largas."
            )
        if overall_trade_eff < 25.0 and total_rounds >= 15:
            leaks.append(
                f"Aislamiento táctico (Trade efficiency {overall_trade_eff}%): "
                "Se toman enfrentamientos sin posibilidad de re-frag por el equipo."
            )
        if overall_def_wr < 40.0 and def_total_sum >= 10:
            leaks.append(
                f"Debilidad defensiva ({overall_def_wr}% en defensa): "
                "Dificultades notorias para sostener o retomar puntos en defensa."
            )
        if overall_retake_sr < 25.0 and retake_attempts_sum >= 4:
            leaks.append(
                f"Baja conversión de retoma ({overall_retake_sr}%): "
                "Coordinar entrada conjunta con utilidades en lugar de "
                "retomas staggered."
            )
        if not leaks:
            leaks.append("Perfil táctico consistente sin fugas críticas recurrentes.")

        return PlayerTimelineAnalyticsResponse(
            game_name=game_name,
            tag_line=tag_line,
            matches_analyzed=valid_matches_count,
            total_rounds_analyzed=total_rounds,
            overall_attack_win_rate=overall_atk_wr,
            overall_defense_win_rate=overall_def_wr,
            overall_trade_efficiency=overall_trade_eff,
            overall_clutch_win_rate=overall_clutch_wr,
            clutches_won_breakdown=clutches_breakdown,
            anti_eco_losses_total=anti_eco_losses_sum,
            retake_success_rate=overall_retake_sr,
            identified_tactical_leaks=leaks,
        )

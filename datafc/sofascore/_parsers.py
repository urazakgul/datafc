"""
Pure data-transformation functions shared by sync fetch modules and aio.py.

Each function takes raw API response data and returns either a list of records
(dicts) or a DataFrame. No HTTP calls, no side effects.

Keeping parsing logic here means a schema change only needs to be made in one
place instead of twice (once in the sync file, once in aio.py).
"""

from typing import Optional
import pandas as pd
from datafc.utils._validate import safe_get
from datafc.exceptions import DataNotAvailableError


# ---------------------------------------------------------------------------
# Match-level parsers
# ---------------------------------------------------------------------------

def parse_match_events(events: list) -> pd.DataFrame:
    """
    Build the standard match DataFrame from a list of Sofascore event objects.

    Raises:
        DataNotAvailableError: If a critical identity field (game_id, team name/id)
            is missing, indicating a Sofascore schema change.
    """
    records = []
    for idx, ev in enumerate(events):
        game_id = ev.get("id")
        if not game_id:
            raise DataNotAvailableError(
                f"Event at index {idx} is missing required field 'id'. "
                "Sofascore schema may have changed."
            )
        home_team = ev.get("homeTeam", {})
        away_team = ev.get("awayTeam", {})
        home_name = home_team.get("name", "")
        home_id = home_team.get("id", "")
        away_name = away_team.get("name", "")
        away_id = away_team.get("id", "")
        if not home_name:
            raise DataNotAvailableError(
                f"Event {game_id}: missing 'homeTeam.name'. Sofascore schema may have changed."
            )
        if not home_id:
            raise DataNotAvailableError(
                f"Event {game_id}: missing 'homeTeam.id'. Sofascore schema may have changed."
            )
        if not away_name:
            raise DataNotAvailableError(
                f"Event {game_id}: missing 'awayTeam.name'. Sofascore schema may have changed."
            )
        if not away_id:
            raise DataNotAvailableError(
                f"Event {game_id}: missing 'awayTeam.id'. Sofascore schema may have changed."
            )
        records.append({
            "country":               ev.get("tournament", {}).get("category", {}).get("name", ""),
            "tournament":            ev.get("tournament", {}).get("name", ""),
            "season":                ev.get("season", {}).get("year", ""),
            "week":                  ev.get("roundInfo", {}).get("round", ""),
            "game_id":               game_id,
            "home_team":             home_name,
            "home_team_id":          home_id,
            "away_team":             away_name,
            "away_team_id":          away_id,
            "injury_time_1":         ev.get("time", {}).get("injuryTime1"),
            "injury_time_2":         ev.get("time", {}).get("injuryTime2"),
            "start_timestamp":       ev.get("startTimestamp"),
            "status":                ev.get("status", {}).get("description", ""),
            "home_score_current":    ev.get("homeScore", {}).get("current"),
            "home_score_display":    ev.get("homeScore", {}).get("display"),
            "home_score_period1":    ev.get("homeScore", {}).get("period1"),
            "home_score_period2":    ev.get("homeScore", {}).get("period2"),
            "home_score_normaltime": ev.get("homeScore", {}).get("normaltime"),
            "away_score_current":    ev.get("awayScore", {}).get("current"),
            "away_score_display":    ev.get("awayScore", {}).get("display"),
            "away_score_period1":    ev.get("awayScore", {}).get("period1"),
            "away_score_period2":    ev.get("awayScore", {}).get("period2"),
            "away_score_normaltime": ev.get("awayScore", {}).get("normaltime"),
        })
    return pd.DataFrame(records)


def parse_match_stats_records(
    data: dict, country: str, tournament: str, season, week, game_id
) -> list:
    """Extract match statistics records from a single event's statistics response."""
    records = []
    for period_data in data.get("statistics", []):
        for group in period_data.get("groups", []):
            for item in group.get("statisticsItems", []):
                records.append({
                    "country": country, "tournament": tournament,
                    "season": season, "week": week, "game_id": game_id,
                    "period": period_data.get("period"),
                    "group_name": group.get("groupName"),
                    "stat_name": item.get("name"),
                    "home_team_stat": item.get("home"),
                    "away_team_stat": item.get("away"),
                })
    return records


def parse_shots_records(
    data: dict, country: str, tournament: str, season, week, game_id
) -> list:
    """Extract shot map records from a single event's shotmap response."""
    records = []
    for shot in data.get("shotmap", []):
        records.append({
            "country": country, "tournament": tournament,
            "season": season, "week": week, "game_id": game_id,
            "player_name": safe_get(shot, "player", "name"),
            "player_id": safe_get(shot, "player", "id"),
            "player_position": safe_get(shot, "player", "position"),
            "is_home": shot.get("isHome"),
            "incident_type": shot.get("incidentType"),
            "shot_type": shot.get("shotType"),
            "body_part": shot.get("bodyPart"),
            "goal_type": shot.get("goalType"),
            "situation": shot.get("situation"),
            "goal_mouth_location": shot.get("goalMouthLocation"),
            "xg": shot.get("xg"),
            "xgot": shot.get("xgot"),
            "player_coordinates_x": safe_get(shot, "playerCoordinates", "x"),
            "player_coordinates_y": safe_get(shot, "playerCoordinates", "y"),
            "player_coordinates_z": safe_get(shot, "playerCoordinates", "z"),
            "goal_mouth_coordinates_x": safe_get(shot, "goalMouthCoordinates", "x"),
            "goal_mouth_coordinates_y": safe_get(shot, "goalMouthCoordinates", "y"),
            "goal_mouth_coordinates_z": safe_get(shot, "goalMouthCoordinates", "z"),
            "draw_start_x": safe_get(shot, "draw", "start", "x"),
            "draw_start_y": safe_get(shot, "draw", "start", "y"),
            "draw_end_x": safe_get(shot, "draw", "end", "x"),
            "draw_end_y": safe_get(shot, "draw", "end", "y"),
            "draw_goal_x": safe_get(shot, "draw", "goal", "x"),
            "draw_goal_y": safe_get(shot, "draw", "goal", "y"),
            "block_coordinates_x": safe_get(shot, "blockCoordinates", "x"),
            "block_coordinates_y": safe_get(shot, "blockCoordinates", "y"),
            "block_coordinates_z": safe_get(shot, "blockCoordinates", "z"),
            "time": shot.get("time"),
            "time_seconds": shot.get("timeSeconds"),
            "added_time": shot.get("addedTime"),
        })
    return records


def parse_momentum_records(
    data: dict, country: str, tournament: str, season, week, game_id
) -> list:
    """Extract momentum graph records from a single event's graph response."""
    return [
        {
            "country": country, "tournament": tournament,
            "season": season, "week": week, "game_id": game_id,
            "minute": point.get("minute"),
            "value": point.get("value"),
        }
        for point in data.get("graphPoints", [])
    ]


def parse_lineups_records(
    data: dict, country: str, tournament: str, season, week, game_id
) -> list:
    """Extract per-player lineup statistics records from a single event's lineups response."""
    records = []
    for team_key in ("home", "away"):
        for player in data.get(team_key, {}).get("players", []):
            player_info = player.get("player", {})
            for stat_name, stat_value in player.get("statistics", {}).items():
                if stat_name == "ratingVersions" and isinstance(stat_value, dict):
                    stat_value = stat_value.get("original", stat_value)
                records.append({
                    "country": country, "tournament": tournament,
                    "season": season, "week": week, "game_id": game_id,
                    "team": team_key,
                    "player_name": player_info.get("name"),
                    "player_id": player_info.get("id"),
                    "stat_name": stat_name,
                    "stat_value": stat_value,
                })
    return records


def parse_substitutions_records(
    data: dict, country: str, tournament: str, season, week, game_id
) -> list:
    """Extract substitution event records from a single event's incidents response."""
    records = []
    for incident in data.get("incidents", []):
        if incident.get("incidentType") != "substitution":
            continue
        records.append({
            "country": country, "tournament": tournament,
            "season": season, "week": week, "game_id": game_id,
            "time": incident.get("time"),
            "player_in": incident.get("playerIn", {}).get("name"),
            "player_in_id": incident.get("playerIn", {}).get("id"),
            "player_out": incident.get("playerOut", {}).get("name"),
            "player_out_id": incident.get("playerOut", {}).get("id"),
        })
    return records


def parse_match_details_records(
    data: dict, country: str, tournament: str, season, week, game_id
) -> dict:
    """Extract referee and venue details from a single event response."""
    ev = data.get("event", {})
    referee = ev.get("referee") or {}
    venue = ev.get("venue") or {}
    return {
        "country":              country,
        "tournament":           tournament,
        "season":               season,
        "week":                 week,
        "game_id":              game_id,
        "referee_id":           referee.get("id"),
        "referee_name":         referee.get("name"),
        "referee_country":      (referee.get("country") or {}).get("name"),
        "referee_yellow_cards": referee.get("yellowCards"),
        "referee_red_cards":    referee.get("redCards"),
        "referee_games":        referee.get("games"),
        "venue_id":             venue.get("id"),
        "venue_name":           venue.get("name"),
        "venue_city":           (venue.get("city") or {}).get("name"),
        "venue_country":        (venue.get("country") or {}).get("name"),
        "venue_capacity":       venue.get("capacity"),
    }


def parse_upcoming_matches_records(data: dict, seen_game_ids: set) -> list:
    """Extract upcoming fixture records, skipping already-seen game IDs."""
    records = []
    for ev in data.get("events", []):
        game_id = ev.get("id")
        if not game_id or game_id in seen_game_ids:
            continue
        seen_game_ids.add(game_id)
        records.append({
            "country":         (ev.get("tournament") or {}).get("category", {}).get("name"),
            "tournament":      (ev.get("tournament") or {}).get("name"),
            "season":          (ev.get("season") or {}).get("year"),
            "week":            (ev.get("roundInfo") or {}).get("round"),
            "game_id":         game_id,
            "home_team":       (ev.get("homeTeam") or {}).get("name"),
            "home_team_id":    (ev.get("homeTeam") or {}).get("id"),
            "away_team":       (ev.get("awayTeam") or {}).get("name"),
            "away_team_id":    (ev.get("awayTeam") or {}).get("id"),
            "start_timestamp": ev.get("startTimestamp"),
            "status":          (ev.get("status") or {}).get("description"),
        })
    return records


def parse_team_match_history_records(data: dict, seen_game_ids: set) -> list:
    """Extract past match records for a team, skipping already-seen game IDs."""
    records = []
    for ev in data.get("events", []):
        game_id = ev.get("id")
        if not game_id or game_id in seen_game_ids:
            continue
        seen_game_ids.add(game_id)
        home_score = ev.get("homeScore") or {}
        away_score = ev.get("awayScore") or {}
        records.append({
            "country":                (ev.get("tournament") or {}).get("category", {}).get("name"),
            "tournament":             (ev.get("tournament") or {}).get("name"),
            "season":                 (ev.get("season") or {}).get("year"),
            "week":                   (ev.get("roundInfo") or {}).get("round"),
            "game_id":                game_id,
            "home_team":              (ev.get("homeTeam") or {}).get("name"),
            "home_team_id":           (ev.get("homeTeam") or {}).get("id"),
            "away_team":              (ev.get("awayTeam") or {}).get("name"),
            "away_team_id":           (ev.get("awayTeam") or {}).get("id"),
            "home_score_period1":     home_score.get("period1"),
            "home_score_period2":     home_score.get("period2"),
            "home_score_normaltime":  home_score.get("normaltime"),
            "home_score_display":     home_score.get("display"),
            "home_score_current":     home_score.get("current"),
            "away_score_period1":     away_score.get("period1"),
            "away_score_period2":     away_score.get("period2"),
            "away_score_normaltime":  away_score.get("normaltime"),
            "away_score_display":     away_score.get("display"),
            "away_score_current":     away_score.get("current"),
            "start_timestamp":        ev.get("startTimestamp"),
            "status":                 (ev.get("status") or {}).get("description"),
        })
    return records


def parse_incidents_records(
    data: dict, country: str, tournament: str, season, week, game_id
) -> list:
    """Extract goal, card and VAR decision records from a single event's incidents response."""
    _SUPPORTED = {"goal", "card", "varDecision"}
    records = []
    for incident in data.get("incidents", []):
        incident_type = incident.get("incidentType")
        if incident_type not in _SUPPORTED:
            continue
        player = incident.get("player", {}) or {}
        records.append({
            "country":        country,
            "tournament":     tournament,
            "season":         season,
            "week":           week,
            "game_id":        game_id,
            "incident_type":  incident_type,
            "incident_class": incident.get("incidentClass"),
            "time":           incident.get("time"),
            "added_time":     incident.get("addedTime"),
            "is_home":        incident.get("isHome"),
            "player_id":      player.get("id"),
            "player_name":    player.get("name"),
            # goal-specific
            "home_score":     incident.get("homeScore"),
            "away_score":     incident.get("awayScore"),
            "goal_from":      incident.get("from"),
            # card-specific
            "card_reason":    incident.get("reason"),
            "rescinded":      incident.get("rescinded"),
            # varDecision-specific
            "var_confirmed":  incident.get("confirmed"),
        })
    return records


def parse_match_odds_records(
    data: dict, country: str, tournament: str, season, week, game_id
) -> list:
    """Extract betting odds records from a single event's odds response."""
    records = []
    for market in data.get("markets", []):
        for choice in market.get("choices", []):
            records.append({
                "country": country, "tournament": tournament,
                "season": season, "week": week, "game_id": game_id,
                "market_name": market.get("marketName", "Unknown"),
                "market_id": market.get("marketId"),
                "is_live": market.get("isLive", False),
                "choice_name": choice.get("name", ""),
                "initial_fractional_value": choice.get("initialFractionalValue", ""),
                "current_fractional_value": choice.get("fractionalValue", ""),
                "winning": choice.get("winning", False),
                "change": choice.get("change", 0),
            })
    return records


def parse_best_players_records(
    data: dict, country: str, tournament: str, season, week, game_id
) -> list:
    """Extract best-player records from a single event's best-players response."""
    records = []
    for side in ("home", "away"):
        entry = data.get(f"best{side.capitalize()}TeamPlayer")
        if not isinstance(entry, dict):
            continue
        player = entry.get("player", {})
        records.append({
            "country": country, "tournament": tournament,
            "season": season, "week": week, "game_id": game_id,
            "team": side,
            "player_name": player.get("name"),
            "player_id": player.get("id"),
            "position": player.get("position"),
            "label": entry.get("label"),
            "value": entry.get("value"),
        })
    return records


def parse_match_h2h_record(
    data: dict,
    country: str, tournament: str, season, week, game_id,
    home_team: str, away_team: str,
) -> Optional[dict]:
    """Extract H2H win/draw/loss record from a single event's h2h response.

    Returns None if the teamDuel key is missing.
    """
    duel = data.get("teamDuel")
    if not isinstance(duel, dict):
        return None
    return {
        "country": country, "tournament": tournament,
        "season": season, "week": week, "game_id": game_id,
        "home_team": home_team, "away_team": away_team,
        "home_wins": duel.get("homeWins", 0),
        "away_wins": duel.get("awayWins", 0),
        "draws": duel.get("draws", 0),
    }


# ---------------------------------------------------------------------------
# League / season-level parsers
# ---------------------------------------------------------------------------

def parse_standings_rows(
    data: dict,
    category: str,
    tournament_id: int = 0,
    season_id: int = 0,
) -> list:
    """
    Extract standings rows from a single category (total/home/away) response.

    Raises:
        DataNotAvailableError: If required tournament metadata or row fields are
            missing, indicating a Sofascore schema change.
    """
    rows = []
    for standing in data.get("standings", []):
        try:
            country = standing["tournament"]["category"]["name"]
            tournament = standing["tournament"]["name"]
        except (KeyError, TypeError) as exc:
            raise DataNotAvailableError(
                f"Standings response missing tournament metadata: {exc}. "
                "Sofascore schema may have changed."
            ) from exc
        for row in standing.get("rows", []):
            try:
                rows.append({
                    "country":        country,
                    "tournament":     tournament,
                    "tournament_id":  tournament_id,
                    "season_id":      season_id,
                    "team_name":      row["team"]["name"],
                    "team_id":        row["team"]["id"],
                    "position":       row["position"],
                    "matches":        row["matches"],
                    "wins":           row["wins"],
                    "draws":          row["draws"],
                    "losses":         row["losses"],
                    "scores_for":     row["scoresFor"],
                    "scores_against": row["scoresAgainst"],
                    "points":         row["points"],
                    "category":       category.capitalize(),
                })
            except (KeyError, TypeError) as exc:
                raise DataNotAvailableError(
                    f"Standings row missing required field: {exc}. "
                    "Sofascore schema may have changed."
                ) from exc
    return rows


def parse_seasons_records(data: dict, tournament_id: int) -> list:
    """Extract season records from a tournament's seasons response."""
    return [
        {
            "tournament_id": tournament_id,
            "season_id": s.get("id"),
            "season_name": s.get("name"),
            "season_year": s.get("year"),
        }
        for s in data.get("seasons", [])
    ]


def parse_average_positions_records(
    data: dict,
    country: str, tournament: str, season, week, game_id,
    home_team: str, away_team: str,
) -> list:
    """Extract average positional records from a single event's average-positions response."""
    records = []
    for side in ("home", "away"):
        for entry in data.get(side, []):
            player = entry.get("player", {})
            records.append({
                "country": country, "tournament": tournament,
                "season": season, "week": week, "game_id": game_id,
                "home_team": home_team, "away_team": away_team,
                "side": side,
                "player_name": player.get("name"),
                "player_id": player.get("id"),
                "position": player.get("position"),
                "jersey_number": player.get("jerseyNumber"),
                "average_x": entry.get("averageX"),
                "average_y": entry.get("averageY"),
                "points_count": entry.get("pointsCount"),
            })
    return records


def parse_league_player_stats_records(
    data: dict, tournament_id: int, season_id: int, selected_fields: list
) -> list:
    """Extract player statistics records from a single statistics page response."""
    records = []
    for entry in data.get("results", []):
        player = entry.get("player", {})
        team = entry.get("team", {})
        row = {
            "tournament_id": tournament_id,
            "season_id": season_id,
            "player_name": player.get("name"),
            "player_id": player.get("id"),
            "team_name": team.get("name"),
            "team_id": team.get("id"),
        }
        for field in selected_fields:
            row[field] = entry.get(field)
        records.append(row)
    return records


def parse_pass_network_records(
    data: dict, country: str, tournament: str, season, week, game_id
) -> list:
    """Extract pass network pair records from a single event's pass-network response."""
    records = []
    for side, team_key in (("home", "homeTeam"), ("away", "awayTeam")):
        team_data = data.get(team_key) or data.get(side, {})
        for pair in team_data.get("pairPasses", []):
            p1 = pair.get("player1") or {}
            p2 = pair.get("player2") or {}
            records.append({
                "country": country, "tournament": tournament,
                "season": season, "week": week, "game_id": game_id,
                "side": side,
                "player1_id": p1.get("id"),
                "player1_name": p1.get("name"),
                "player2_id": p2.get("id"),
                "player2_name": p2.get("name"),
                "passes": pair.get("passes"),
                "passes_back": pair.get("passesBack"),
            })
    return records


_SEARCH_TYPE_MAP = {"tournament": "uniqueTournament"}
_SEARCH_TYPE_REVERSE = {v: k for k, v in _SEARCH_TYPE_MAP.items()}


def parse_search_records(results: list, entity_type: Optional[str]) -> list:
    """Extract search result records, optionally filtered by entity_type."""
    api_type = _SEARCH_TYPE_MAP.get(entity_type, entity_type) if entity_type is not None else None
    records = []
    for item in results:
        item_type = item.get("type")
        if api_type is not None and item_type != api_type:
            continue
        entity = item.get("entity", {})
        country = entity.get("country", {})
        records.append({
            "entity_id": entity.get("id"),
            "entity_name": entity.get("name"),
            "entity_type": _SEARCH_TYPE_REVERSE.get(item_type, item_type),
            "score": item.get("score"),
            "country": country.get("name") if isinstance(country, dict) else None,
            "position": entity.get("position"),
        })
    return records

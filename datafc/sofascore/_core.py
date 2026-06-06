"""
Shared control-flow helpers for sync fetch modules and the async mirror (aio.py).

Every helper here is internal (underscore-prefixed package) and is consumed by the
thin sync wrappers in ``datafc/sofascore/fetch_*_data.py`` and by ``aio.py``.

The helpers fall into three groups:

* ``_export_df`` — DataFrame -> JSON/Excel export block shared by every fetch.
* ``iter_per_match_sync`` / ``iter_per_match_async`` — generic per-match iterators
  parameterised by URL builder, response parser, error policy and record shape.
* ``resolve_world_cup_week_sync`` / ``_async`` — World Cup knockout round lookup.

Pure record-builder functions for endpoints that are not in ``_parsers.py``
(squad rosters, player profiles, transfers, etc.) are also kept here so that the
sync and async versions share the same row schema.

No exception class or behaviour is changed by this module; helpers preserve
exactly the error policy used in the original duplicated code (per-function
divergence around ``APIError`` is encoded in the ``catch_api_error`` flags).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Union

import pandas as pd

from datafc.exceptions import APIError, DataNotAvailableError
from datafc.utils._config import API_URLS, WORLD_CUP_KNOCKOUT_SLUGS
from datafc.utils._helpers import _ts_to_age
from datafc.utils._save_files import save_excel, save_json

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Export helper
# ---------------------------------------------------------------------------

# Keys we look up for export filename — many parsers only emit a subset.
_EXPORT_FIELDS = ("country", "tournament", "season", "week")


def _resolve_field(first_row, key, default=""):
    """Read ``key`` from a pandas.Series, dict, or None — without raising."""
    if first_row is None:
        return default
    if isinstance(first_row, dict):
        return first_row.get(key, default)
    # pandas Series / Mapping protocol
    try:
        return first_row[key] if key in first_row else default
    except Exception:
        try:
            return getattr(first_row, key)
        except Exception:
            return default


class _Sentinel:
    pass


_SENTINEL = _Sentinel()


def export_df(
    df: pd.DataFrame,
    *,
    fn_name: str,
    data_source: str,
    output_dir: str,
    enable_json_export: bool,
    enable_excel_export: bool,
    first_row=None,
    country: Any = _SENTINEL,
    tournament: Any = _SENTINEL,
    season: Any = _SENTINEL,
    week_number: Any = _SENTINEL,
    include_week: bool = True,
) -> None:
    """Public wrapper that uses sentinel objects to distinguish 'unset' from None.

    Any explicitly-passed argument (including ``None``) is forwarded as-is to
    save_json / save_excel; arguments left as the sentinel fall back to
    ``first_row`` (or ``df.iloc[0]``).
    """
    if not (enable_json_export or enable_excel_export):
        return

    if first_row is None and not df.empty:
        first_row = df.iloc[0]

    kwargs: dict = dict(fn_name=fn_name, data_source=data_source)

    if country is _SENTINEL:
        kwargs["country"] = _resolve_field(first_row, "country", "")
    else:
        kwargs["country"] = country

    if tournament is _SENTINEL:
        kwargs["tournament"] = _resolve_field(first_row, "tournament", "")
    else:
        kwargs["tournament"] = tournament

    if season is _SENTINEL:
        kwargs["season"] = _resolve_field(first_row, "season", None)
    else:
        kwargs["season"] = season

    if include_week:
        if week_number is _SENTINEL:
            kwargs["week_number"] = _resolve_field(first_row, "week", None)
        else:
            kwargs["week_number"] = week_number

    if enable_json_export:
        save_json(data=df, **kwargs, output_dir=output_dir)
    if enable_excel_export:
        save_excel(data=df, **kwargs, output_dir=output_dir)


# ---------------------------------------------------------------------------
# Per-match generic iterators
# ---------------------------------------------------------------------------

# Endpoint may be a format string with {base} and {game_id}, or a callable
# (row, data_source_base) -> url.
EndpointSpec = Union[str, Callable[[pd.Series, str], str]]
RecordsParser = Callable[..., Union[list, dict, None]]


def _build_url(endpoint: EndpointSpec, row: pd.Series, base: str) -> str:
    if isinstance(endpoint, str):
        return endpoint.format(base=base, game_id=row["game_id"])
    return endpoint(row, base)


def iter_per_match_sync(
    match_df: pd.DataFrame,
    client,
    *,
    data_source: str,
    endpoint: EndpointSpec,
    parser: RecordsParser,
    extra_args_fn: Optional[Callable[[pd.Series], tuple]] = None,
    single_record: bool = False,
    catch_api_error: bool = True,
    log_label: str = "data",
) -> list:
    """Iterate ``match_df`` sequentially, fetching ``endpoint`` per row.

    Args:
        match_df: DataFrame with country/tournament/season/week/game_id columns.
        client: A SofascoreClient with ``.get(url)`` returning a dict.
        data_source: Used to look up ``API_URLS[data_source]``.
        endpoint: Format string with ``{base}`` and ``{game_id}``, or a callable
            ``(row, base) -> url`` for endpoints that need other row fields.
        parser: Either ``(data, country, tournament, season, week, game_id, *extra)
            -> list`` (default) or ``-> dict | None`` when ``single_record=True``.
        extra_args_fn: Optional callable ``(row) -> tuple`` of extra parser args.
        single_record: If True, parser returns one record (or None to skip).
        catch_api_error: When True, log + continue on APIError. When False,
            propagate the exception (matches behaviour of e.g. match_h2h_data,
            match_odds_data).
        log_label: Human-readable label inserted into the warning message.
    """
    base = API_URLS[data_source]
    records: list = []
    for _, row in match_df.iterrows():
        country, tournament, season, week, game_id = row[
            ["country", "tournament", "season", "week", "game_id"]
        ]
        url = _build_url(endpoint, row, base)
        try:
            data = client.get(url)
        except APIError as exc:
            if not catch_api_error:
                raise
            logger.warning("Failed to fetch %s for game_id=%s: %s", log_label, game_id, exc)
            continue
        extra = extra_args_fn(row) if extra_args_fn else ()
        result = parser(data, country, tournament, season, week, game_id, *extra)
        if single_record:
            if result is not None:
                records.append(result)
        else:
            records.extend(result or [])
    return records


async def iter_per_match_async(
    match_df: pd.DataFrame,
    client,
    *,
    data_source: str,
    endpoint: EndpointSpec,
    parser: RecordsParser,
    extra_args_fn: Optional[Callable[[pd.Series], tuple]] = None,
    single_record: bool = False,
    catch_api_error: bool = True,
    log_label: str = "data",
) -> list:
    """Async mirror of ``iter_per_match_sync`` — all rows fetched in parallel.

    Behaviour is identical to the sync version, except requests are dispatched
    concurrently via ``asyncio.gather``.
    """
    base = API_URLS[data_source]

    async def _one(row: pd.Series):
        country, tournament, season, week, game_id = row[
            ["country", "tournament", "season", "week", "game_id"]
        ]
        url = _build_url(endpoint, row, base)
        try:
            data = await client.get(url)
        except APIError as exc:
            if not catch_api_error:
                raise
            logger.warning("Failed to fetch %s for game_id=%s: %s", log_label, game_id, exc)
            return None if single_record else []
        extra = extra_args_fn(row) if extra_args_fn else ()
        return parser(data, country, tournament, season, week, game_id, *extra)

    raw = await asyncio.gather(*[_one(row) for _, row in match_df.iterrows()])

    records: list = []
    for item in raw:
        if single_record:
            if item is not None:
                records.append(item)
        else:
            records.extend(item or [])
    return records


# ---------------------------------------------------------------------------
# World Cup knockout-round resolution
# ---------------------------------------------------------------------------


def _wc_rounds_url(base: str, tournament_id: int, season_id: int) -> str:
    return f"{base}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/rounds"


def _pick_wc_round(rounds_data: dict, target_slug: str, tournament_id: int, season_id: int) -> int:
    rounds = rounds_data.get("rounds") or rounds_data.get("currentRounds") or []
    matched = next((r for r in rounds if r.get("slug") == target_slug), None)
    if matched is None:
        raise DataNotAvailableError(
            f"Could not find round with slug '{target_slug}' for "
            f"tournament_id={tournament_id}, season_id={season_id}."
        )
    return matched["round"]


def needs_world_cup_resolution(
    tournament_type: Optional[str],
    tournament_stage: Optional[str],
    week_number: Optional[int],
) -> bool:
    return (
        tournament_type == "world_cup"
        and tournament_stage in WORLD_CUP_KNOCKOUT_SLUGS
        and week_number is None
    )


def resolve_world_cup_week_sync(
    client,
    tournament_id: int,
    season_id: int,
    tournament_stage: str,
    data_source: str,
) -> int:
    target_slug = WORLD_CUP_KNOCKOUT_SLUGS[tournament_stage]
    rounds_data = client.get(_wc_rounds_url(API_URLS[data_source], tournament_id, season_id))
    return _pick_wc_round(rounds_data, target_slug, tournament_id, season_id)


async def resolve_world_cup_week_async(
    client,
    tournament_id: int,
    season_id: int,
    tournament_stage: str,
    data_source: str,
) -> int:
    target_slug = WORLD_CUP_KNOCKOUT_SLUGS[tournament_stage]
    rounds_data = await client.get(_wc_rounds_url(API_URLS[data_source], tournament_id, season_id))
    return _pick_wc_round(rounds_data, target_slug, tournament_id, season_id)


# ---------------------------------------------------------------------------
# Pure record-builders for non-_parsers endpoints
# ---------------------------------------------------------------------------

_TRANSFER_TYPES = {1: "loan", 2: "permanent", 3: "free", 4: "end_of_contract"}


def _format_transfer_date(ts):
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def _transfer_dict(transfer: dict) -> dict:
    fee_raw = transfer.get("transferFee")
    return {
        "transfer_date": _format_transfer_date(transfer.get("transferDate")),
        "from_team_id": (transfer.get("transferFrom") or {}).get("id"),
        "from_team_name": (transfer.get("transferFrom") or {}).get("name"),
        "to_team_id": (transfer.get("transferTo") or {}).get("id"),
        "to_team_name": (transfer.get("transferTo") or {}).get("name"),
        "transfer_type": _TRANSFER_TYPES.get(transfer.get("type"), "unknown"),
        "fee": fee_raw.get("value") if isinstance(fee_raw, dict) else None,
        "fee_currency": fee_raw.get("currency") if isinstance(fee_raw, dict) else None,
    }


def squad_records_from_response(data: dict, row: pd.Series) -> list:
    """Build squad rows for one team from /team/{id}/players response."""
    country = row["country"]
    tournament = row["tournament"]
    team_name = row["team_name"]
    team_id = row["team_id"]
    tournament_id = row.get("tournament_id", 0)
    season_id = row.get("season_id", 0)
    out = []
    for p in data.get("players", []):
        player = p.get("player")
        if not player:
            continue
        out.append({
            "country": country,
            "tournament": tournament,
            "tournament_id": tournament_id,
            "season_id": season_id,
            "team_name": team_name,
            "team_id": team_id,
            "player_name": player.get("name"),
            "player_id": player.get("id"),
            "age": _ts_to_age(player.get("dateOfBirthTimestamp")),
            "height": player.get("height"),
            "player_country": player.get("country", {}).get("name"),
            "position": player.get("position"),
            "preferred_foot": player.get("preferredFoot"),
            "contract_until": player.get("contractUntilTimestamp"),
            "market_value": player.get("proposedMarketValueRaw", {}).get("value"),
            "market_currency": player.get("proposedMarketValueRaw", {}).get("currency"),
        })
    return out


def player_stats_records_from_response(data: dict, row: pd.Series) -> list:
    country, tournament = row["country"], row["tournament"]
    team_name, team_id = row["team_name"], row["team_id"]
    out = []
    for players in data.get("topPlayers", {}).values():
        for player_data in players:
            player = player_data.get("player", {})
            player_id = player.get("id")
            for stat, value in player_data.get("statistics", {}).items():
                if stat in ("id", "type") or isinstance(value, (dict, list)):
                    continue
                out.append({
                    "country": country,
                    "tournament": tournament,
                    "team_name": team_name,
                    "team_id": team_id,
                    "player_name": player.get("name"),
                    "player_id": player_id,
                    "position": player.get("position"),
                    "stat_name": stat,
                    "stat_value": value,
                })
    return out


def team_stats_records_from_response(data: dict, row: pd.Series) -> list:
    country, tournament = row["country"], row["tournament"]
    team_name, team_id = row["team_name"], row["team_id"]
    out = []
    for stat, value in data.get("statistics", {}).items():
        if stat in {"country", "tournament", "team_name", "team_id"}:
            continue
        if isinstance(value, (dict, list)):
            continue
        out.append({
            "country": country,
            "tournament": tournament,
            "team_name": team_name,
            "team_id": team_id,
            "stat": stat,
            "value": value,
        })
    return out


def team_transfers_records_from_response(data: dict, row: pd.Series) -> list:
    country, tournament = row["country"], row["tournament"]
    team_name, team_id = row["team_name"], row["team_id"]
    out = []
    for direction in ("transfersIn", "transfersOut"):
        dir_label = "in" if direction == "transfersIn" else "out"
        for transfer in data.get(direction, []):
            player = transfer.get("player", {})
            rec = {
                "country": country,
                "tournament": tournament,
                "team_name": team_name,
                "team_id": team_id,
                "direction": dir_label,
                "player_id": player.get("id"),
                "player_name": player.get("name"),
            }
            rec.update(_transfer_dict(transfer))
            out.append(rec)
    return out


def player_transfers_records_from_response(data: dict, player_id, player_name) -> list:
    out = []
    for transfer in data.get("transferHistory", []):
        rec = {"player_id": player_id, "player_name": player_name}
        rec.update(_transfer_dict(transfer))
        out.append(rec)
    return out


def player_national_team_records_from_response(data: dict, player_id, player_name) -> list:
    out = []
    for entry in data.get("statistics", []):
        team = entry.get("team", {})
        out.append({
            "player_id": player_id,
            "player_name": player_name,
            "team_id": team.get("id"),
            "team_name": team.get("name"),
            "team_code": team.get("nameCode"),
            "appearances": entry.get("appearances"),
            "goals": entry.get("goals"),
            "debut_timestamp": entry.get("debutTimestamp"),
        })
    return out


def player_attribute_overviews_records_from_response(data: dict, player_id, player_name) -> list:
    """Build attribute-overview rows (player series + average series) for one player."""
    out = []
    for series, key in (("player", "playerAttributeOverviews"), ("average", "averageAttributeOverviews")):
        for entry in data.get(key, []):
            out.append({
                "player_id": player_id,
                "player_name": player_name,
                "series": series,
                "position": entry.get("position"),
                "year_shift": entry.get("yearShift"),
                "attacking": entry.get("attacking"),
                "technical": entry.get("technical"),
                "tactical": entry.get("tactical"),
                "defending": entry.get("defending"),
                "creativity": entry.get("creativity"),
            })
    return out


def player_profile_record_from_response(data: dict, player_id, player_name) -> Optional[dict]:
    """Build the single profile row; return None if the response is empty."""
    p = data.get("player") or {}
    if not p:
        return None
    country = p.get("country") or {}
    team = p.get("team") or {}
    dob_ts = p.get("dateOfBirthTimestamp")
    mv_raw = p.get("proposedMarketValueRaw") or {}
    return {
        "player_id": player_id,
        "player_name": p.get("name") or player_name,
        "date_of_birth": (
            datetime.fromtimestamp(dob_ts, tz=timezone.utc).strftime("%Y-%m-%d")
            if dob_ts else None
        ),
        "age": p.get("age") if p.get("age") is not None else _ts_to_age(dob_ts),
        "nationality": country.get("name"),
        "nationality_id": country.get("id"),
        "height": p.get("height"),
        "weight": p.get("weight"),
        "preferred_foot": p.get("preferredFoot"),
        "jersey_number": p.get("jerseyNumber") or p.get("shirtNumber"),
        "position": p.get("position"),
        "market_value": mv_raw.get("value"),
        "market_currency": mv_raw.get("currency"),
        "team_id": team.get("id"),
        "team_name": team.get("name"),
    }


def team_profile_record_from_response(data: dict, row: pd.Series) -> Optional[dict]:
    t = data.get("team") or {}
    if not t:
        return None
    country = t.get("country") or {}
    venue = t.get("venue") or {}
    stadium = venue.get("stadium") or {}
    manager = t.get("manager") or {}
    colors = t.get("teamColors") or {}
    return {
        "country": row["country"],
        "tournament": row["tournament"],
        "team_id": row["team_id"],
        "team_name": t.get("name") or row["team_name"],
        "short_name": t.get("shortName") or t.get("nameCode"),
        "slug": t.get("slug"),
        "national": t.get("national"),
        "country_name": country.get("name"),
        "country_id": country.get("id"),
        "primary_color": colors.get("primary"),
        "secondary_color": colors.get("secondary"),
        "text_color": colors.get("text"),
        "venue_id": venue.get("id"),
        "venue_name": stadium.get("name") or venue.get("name"),
        "venue_capacity": stadium.get("capacity"),
        "venue_city": (venue.get("city") or {}).get("name"),
        "manager_id": manager.get("id"),
        "manager_name": manager.get("name"),
        "manager_country": (manager.get("country") or {}).get("name"),
    }


def player_career_stats_records_from_responses(
    seasons_data: dict, fetch_stats: Callable[[Any, Any], Optional[dict]],
    player_id, player_name,
) -> list:
    """Helper used by sync career-stats only — async needs interleaved awaits.

    ``fetch_stats(tid, sid)`` should return the stats dict or None on APIError.
    """
    out = []
    for entry in seasons_data.get("uniqueTournamentSeasons", []):
        tournament = entry.get("uniqueTournament", {})
        tid = tournament.get("id")
        for season in entry.get("seasons", []):
            sid = season.get("id")
            stats_data = fetch_stats(tid, sid)
            if stats_data is None:
                continue
            team = stats_data.get("team", {})
            for stat_name, stat_value in stats_data.get("statistics", {}).items():
                if isinstance(stat_value, (dict, list)):
                    continue
                out.append({
                    "player_id": player_id,
                    "player_name": player_name,
                    "tournament_id": tid,
                    "tournament_name": tournament.get("name"),
                    "season_id": sid,
                    "season_name": season.get("year"),
                    "team_id": team.get("id"),
                    "team_name": team.get("name"),
                    "stat": stat_name,
                    "value": stat_value,
                })
    return out


def career_stats_records_for_pair(
    tournament_entry: dict,
    season: dict,
    stats_data: dict,
    player_id,
    player_name,
) -> list:
    """Build career-stats rows from one (tournament, season, stats) triple."""
    tid = tournament_entry.get("id")
    sid = season.get("id")
    team = stats_data.get("team", {})
    out = []
    for stat_name, stat_value in stats_data.get("statistics", {}).items():
        if isinstance(stat_value, (dict, list)):
            continue
        out.append({
            "player_id": player_id,
            "player_name": player_name,
            "tournament_id": tid,
            "tournament_name": tournament_entry.get("name"),
            "season_id": sid,
            "season_name": season.get("year"),
            "team_id": team.get("id"),
            "team_name": team.get("name"),
            "stat": stat_name,
            "value": stat_value,
        })
    return out


def match_log_records_from_response(data: dict, player_id, player_name) -> list:
    out = []
    for ev in data.get("events", []):
        stats = ev.get("playerStatistics") or {}
        home_team = ev.get("homeTeam") or {}
        away_team = ev.get("awayTeam") or {}
        row = {
            "player_id": player_id,
            "player_name": player_name,
            "game_id": ev.get("id"),
            "start_timestamp": ev.get("startTimestamp"),
            "tournament": (ev.get("tournament") or {}).get("name"),
            "season": (ev.get("season") or {}).get("year"),
            "home_team": home_team.get("name"),
            "home_team_id": home_team.get("id"),
            "away_team": away_team.get("name"),
            "away_team_id": away_team.get("id"),
            "home_score": (ev.get("homeScore") or {}).get("current"),
            "away_score": (ev.get("awayScore") or {}).get("current"),
            "status": (ev.get("status") or {}).get("description"),
        }
        for stat_name, stat_value in stats.items():
            if not isinstance(stat_value, (dict, list)):
                row[stat_name] = stat_value
        out.append(row)
    return out


# ---------------------------------------------------------------------------
# pregame-form / referee / season-rounds / past-matches helpers
# ---------------------------------------------------------------------------


def pregame_form_records(
    data: dict, country, tournament, season, week, game_id,
) -> list:
    out = []
    for side in ("homeTeam", "awayTeam"):
        team_form = data.get(side)
        if not isinstance(team_form, dict):
            continue
        form_row = {
            "country": country,
            "tournament": tournament,
            "season": season,
            "week": week,
            "game_id": game_id,
            "team": "home" if side == "homeTeam" else "away",
            "avg_rating": team_form.get("avgRating"),
            "position": team_form.get("position"),
            "value": team_form.get("value"),
        }
        for i, result in enumerate(team_form.get("form", []), start=1):
            form_row[f"form_{i}"] = result
        out.append(form_row)
    return out


def pregame_form_coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for col in ("avg_rating", "value", "position"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def referee_stats_records(statistics: list, referee_id, referee_name) -> list:
    out = []
    for entry in statistics:
        tournament = entry.get("uniqueTournament", {})
        for stat_name, stat_value in entry.items():
            if stat_name == "uniqueTournament" or isinstance(stat_value, (dict, list)):
                continue
            out.append({
                "referee_id": referee_id,
                "referee_name": referee_name,
                "tournament_id": tournament.get("id"),
                "tournament_name": tournament.get("name"),
                "stat": stat_name,
                "value": stat_value,
            })
    return out


def season_rounds_records(rounds: list, tournament_id, season_id) -> list:
    return [
        {
            "tournament_id": tournament_id,
            "season_id": season_id,
            "round_number": r.get("round"),
            "slug": r.get("slug"),
            "name": r.get("name"),
            "prefix": r.get("prefix"),
            "is_latest": r.get("isLatest", False),
        }
        for r in rounds
    ]


def past_match_record_from_event(event: dict) -> dict:
    return {
        "country": event.get("tournament", {}).get("category", {}).get("name", ""),
        "tournament": event.get("tournament", {}).get("name", ""),
        "season": event.get("season", {}).get("year", ""),
        "week": event.get("roundInfo", {}).get("round", ""),
        "game_id": event.get("id", ""),
        "home_team": event.get("homeTeam", {}).get("name", ""),
        "home_team_id": event.get("homeTeam", {}).get("id", ""),
        "away_team": event.get("awayTeam", {}).get("name", ""),
        "away_team_id": event.get("awayTeam", {}).get("id", ""),
        "injury_time_1": event.get("time", {}).get("injuryTime1", ""),
        "injury_time_2": event.get("time", {}).get("injuryTime2", ""),
        "start_timestamp": event.get("startTimestamp", ""),
        "status": event.get("status", {}).get("description", ""),
        "home_score_current": event.get("homeScore", {}).get("current", ""),
        "home_score_display": event.get("homeScore", {}).get("display", ""),
        "home_score_period1": event.get("homeScore", {}).get("period1", ""),
        "home_score_period2": event.get("homeScore", {}).get("period2", ""),
        "home_score_normaltime": event.get("homeScore", {}).get("normaltime", ""),
        "away_score_current": event.get("awayScore", {}).get("current", ""),
        "away_score_display": event.get("awayScore", {}).get("display", ""),
        "away_score_period1": event.get("awayScore", {}).get("period1", ""),
        "away_score_period2": event.get("awayScore", {}).get("period2", ""),
        "away_score_normaltime": event.get("awayScore", {}).get("normaltime", ""),
    }


# ---------------------------------------------------------------------------
# goal_networks post-processor
# ---------------------------------------------------------------------------


def _coord(coords, key):
    return coords.get(key) if isinstance(coords, dict) else None


def goal_networks_post_process(incidents_df: pd.DataFrame) -> pd.DataFrame:
    """Pivot the incidents -> footballPassingNetworkAction long-format frame."""
    from datafc.utils._helpers import _safe_apply

    if "footballPassingNetworkAction" not in incidents_df.columns:
        raise DataNotAvailableError("No passing network actions found in incident data.")

    actions_list = []
    for _, row in incidents_df[
        ["id", "footballPassingNetworkAction", "country", "tournament", "season", "week", "game_id"]
    ].iterrows():
        if not isinstance(row["footballPassingNetworkAction"], list):
            continue
        for event in row["footballPassingNetworkAction"]:
            event = dict(event)
            event["id"] = row["id"]
            event.update({
                "country": row["country"],
                "tournament": row["tournament"],
                "season": row["season"],
                "week": row["week"],
                "game_id": row["game_id"],
            })
            actions_list.append(event)

    if not actions_list:
        raise DataNotAvailableError("No passing network actions found.")

    raw_df = pd.DataFrame(actions_list)
    result_df = raw_df.assign(
        player_name=raw_df["player"].apply(lambda p: p.get("name") if isinstance(p, dict) else None),
        player_id=raw_df["player"].apply(lambda p: p.get("id") if isinstance(p, dict) else None),
        event_type=raw_df["eventType"],
        player_x=raw_df["playerCoordinates"].apply(lambda c: _coord(c, "x")),
        player_y=raw_df["playerCoordinates"].apply(lambda c: _coord(c, "y")),
        pass_end_x=_safe_apply(raw_df, "passEndCoordinates", lambda c: _coord(c, "x")),
        pass_end_y=_safe_apply(raw_df, "passEndCoordinates", lambda c: _coord(c, "y")),
        is_assist=_safe_apply(raw_df, "isAssist"),
        goalkeeper_x=_safe_apply(raw_df, "gkCoordinates", lambda c: _coord(c, "x")),
        goalkeeper_y=_safe_apply(raw_df, "gkCoordinates", lambda c: _coord(c, "y")),
        goal_shot_x=_safe_apply(raw_df, "goalShotCoordinates", lambda c: _coord(c, "x")),
        goal_shot_y=_safe_apply(raw_df, "goalShotCoordinates", lambda c: _coord(c, "y")),
        goal_mouth_x=_safe_apply(raw_df, "goalMouthCoordinates", lambda c: _coord(c, "x")),
        goal_mouth_y=_safe_apply(raw_df, "goalMouthCoordinates", lambda c: _coord(c, "y")),
        goalkeeper_name=_safe_apply(
            raw_df, "goalkeeper", lambda gk: gk.get("name") if isinstance(gk, dict) else None
        ),
        goalkeeper_id=_safe_apply(
            raw_df, "goalkeeper", lambda gk: gk.get("id") if isinstance(gk, dict) else None
        ),
    )[[
        "country", "tournament", "season", "week", "game_id",
        "player_name", "player_id", "event_type",
        "player_x", "player_y", "pass_end_x", "pass_end_y",
        "is_assist", "id",
        "goalkeeper_x", "goalkeeper_y",
        "goal_shot_x", "goal_shot_y",
        "goal_mouth_x", "goal_mouth_y",
        "goalkeeper_name", "goalkeeper_id",
    ]]
    return result_df


def heatmap_records(data: dict, row: pd.Series) -> list:
    """coordinates_data per-player heatmap parser."""
    return [
        {
            "country": row["country"],
            "tournament": row["tournament"],
            "season": row["season"],
            "week": row["week"],
            "game_id": row["game_id"],
            "team": row["team"],
            "player_id": row["player_id"],
            "player_name": row["player_name"],
            "x": point["x"],
            "y": point["y"],
        }
        for point in data.get("heatmap", [])
        if isinstance(point, dict) and "x" in point and "y" in point
    ]

"""
Async versions of all datafc fetch functions.

Each function mirrors its sync counterpart in ``datafc.sofascore``; the only
behavioural difference is that per-row / per-team / per-player work runs
concurrently via ``asyncio.gather``. Public signatures, return types, and the
exceptions raised are identical to the sync versions.

Rate limiting is shared globally — all concurrent coroutines respect the same
per-second budget (default 2 req/s).

Example::

    import asyncio
    from datafc.sofascore import aio

    async def main():
        df = await aio.match_data(52, 63814, week_number=21)
        # Fan-out: fetch all 38 weeks of a season in parallel
        tasks = [aio.match_data(52, 63814, week_number=w) for w in range(1, 39)]
        frames = await asyncio.gather(*tasks)

    asyncio.run(main())
"""

import asyncio
import logging
from typing import Optional
from urllib.parse import quote

import pandas as pd

from datafc.exceptions import APIError, DataNotAvailableError, InvalidParameterError
from datafc.sofascore._core import (
    career_stats_records_for_pair,
    export_df,
    goal_networks_post_process,
    heatmap_records,
    iter_per_match_async,
    match_log_records_from_response,
    needs_world_cup_resolution,
    past_match_record_from_event,
    player_attribute_overviews_records_from_response,
    player_national_team_records_from_response,
    player_profile_record_from_response,
    player_stats_records_from_response,
    player_transfers_records_from_response,
    pregame_form_coerce_numeric,
    pregame_form_records,
    referee_stats_records,
    resolve_world_cup_week_async,
    season_rounds_records,
    squad_records_from_response,
    team_profile_record_from_response,
    team_stats_records_from_response,
    team_transfers_records_from_response,
)
from datafc.sofascore._parsers import (
    parse_average_positions_records,
    parse_formations_records,
    parse_incidents_records,
    parse_league_player_stats_records,
    parse_lineups_records,
    parse_match_details_records,
    parse_match_events,
    parse_match_h2h_record,
    parse_match_odds_records,
    parse_match_stats_records,
    parse_momentum_records,
    parse_search_records,
    parse_seasons_records,
    parse_shots_records,
    parse_standings_rows,
    parse_substitutions_records,
    parse_team_match_history_records,
    parse_upcoming_matches_records,
)
from datafc.sofascore.fetch_league_player_stats_data import (
    AVAILABLE_ACCUMULATIONS,
    AVAILABLE_FIELDS,
    DEFAULT_FIELDS,
)
from datafc.sofascore.fetch_search_data import AVAILABLE_ENTITY_TYPES
from datafc.utils._async_client import AsyncSofascoreClient
from datafc.utils._cache import DiskCache
from datafc.utils._config import API_URLS, WWW_URLS
from datafc.utils._helpers import _cast_int_cols
from datafc.utils._tournament_info import resolve_tournament_season
from datafc.utils._validate import build_tournament_url, validate_df, validate_source

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Match-level (per-match iterator pattern)
# ---------------------------------------------------------------------------

async def match_data(
    tournament_id: int,
    season_id: int,
    week_number: Optional[int] = None,
    tournament_type: Optional[str] = None,
    tournament_stage: Optional[str] = None,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of match_data(). See the sync docstring for parameters."""
    validate_source(data_source)

    if needs_world_cup_resolution(tournament_type, tournament_stage, week_number):
        async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
            week_number = await resolve_world_cup_week_async(
                client, tournament_id, season_id, tournament_stage, data_source,
            )

    url = build_tournament_url(
        API_URLS[data_source], tournament_id, season_id, week_number,
        tournament_type, tournament_stage,
    )

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        data = await client.get(url)

    events = data.get("events")
    if not isinstance(events, list) or not events:
        raise DataNotAvailableError(
            f"No match data found for tournament_id={tournament_id}, "
            f"season_id={season_id}, week_number={week_number}."
        )

    result_df = parse_match_events(events)
    export_df(
        result_df, fn_name="match_data", data_source=data_source,
        output_dir=output_dir,
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
    )
    return result_df


async def _per_match_simple(
    match_df, data_source, rate_limit, cache, *,
    endpoint, parser, log_label, fn_name, error_msg,
    enable_json_export, enable_excel_export, output_dir,
    extra_args_fn=None, single_record=False, catch_api_error=True,
):
    """Internal: per-match concurrent fetch + standard export tail."""
    validate_source(data_source)
    validate_df(match_df, "match_df")

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        records = await iter_per_match_async(
            match_df, client,
            data_source=data_source,
            endpoint=endpoint, parser=parser,
            extra_args_fn=extra_args_fn, single_record=single_record,
            catch_api_error=catch_api_error, log_label=log_label,
        )

    df = pd.DataFrame(records)
    if df.empty:
        raise DataNotAvailableError(error_msg)
    export_df(
        df, fn_name=fn_name, data_source=data_source,
        output_dir=output_dir,
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
    )
    return df


async def match_stats_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of match_stats_data()."""
    return await _per_match_simple(
        match_df, data_source, rate_limit, cache,
        endpoint="{base}/api/v1/event/{game_id}/statistics",
        parser=parse_match_stats_records,
        log_label="match stats",
        fn_name="match_stats_data",
        error_msg="No match statistics data found.",
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        output_dir=output_dir,
    )


async def shots_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of shots_data()."""
    return await _per_match_simple(
        match_df, data_source, rate_limit, cache,
        endpoint="{base}/api/v1/event/{game_id}/shotmap",
        parser=parse_shots_records,
        log_label="shots",
        fn_name="shots_data",
        error_msg="No shot data found.",
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        output_dir=output_dir,
    )


async def momentum_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of momentum_data()."""
    return await _per_match_simple(
        match_df, data_source, rate_limit, cache,
        endpoint="{base}/api/v1/event/{game_id}/graph",
        parser=parse_momentum_records,
        log_label="momentum",
        fn_name="momentum_data",
        error_msg="No momentum data found.",
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        output_dir=output_dir,
    )


async def formations_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of formations_data()."""
    return await _per_match_simple(
        match_df, data_source, rate_limit, cache,
        endpoint="{base}/api/v1/event/{game_id}/lineups",
        parser=parse_formations_records,
        log_label="formations",
        fn_name="formations_data",
        error_msg="No formation data found.",
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        output_dir=output_dir,
    )


async def lineups_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of lineups_data()."""
    return await _per_match_simple(
        match_df, data_source, rate_limit, cache,
        endpoint="{base}/api/v1/event/{game_id}/lineups",
        parser=parse_lineups_records,
        log_label="lineups",
        fn_name="lineups_data",
        error_msg="No lineup data found.",
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        output_dir=output_dir,
    )


async def substitutions_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of substitutions_data()."""
    return await _per_match_simple(
        match_df, data_source, rate_limit, cache,
        endpoint="{base}/api/v1/event/{game_id}/incidents",
        parser=parse_substitutions_records,
        log_label="substitutions",
        fn_name="substitutions_data",
        error_msg="No substitution data found.",
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        output_dir=output_dir,
    )


async def incidents_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of incidents_data()."""
    return await _per_match_simple(
        match_df, data_source, rate_limit, cache,
        endpoint="{base}/api/v1/event/{game_id}/incidents",
        parser=parse_incidents_records,
        log_label="incidents",
        fn_name="incidents_data",
        error_msg="No incident data found.",
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        output_dir=output_dir,
    )


async def match_details_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of match_details_data()."""
    df = await _per_match_simple(
        match_df, data_source, rate_limit, cache,
        endpoint="{base}/api/v1/event/{game_id}",
        parser=parse_match_details_records,
        log_label="details",
        fn_name="match_details_data",
        error_msg="No match detail data found.",
        single_record=True,
        enable_json_export=False, enable_excel_export=False,
        output_dir=output_dir,
    )
    _cast_int_cols(df, "referee_id")
    # Export after int casting.
    export_df(
        df, fn_name="match_details_data", data_source=data_source,
        output_dir=output_dir,
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
    )
    return df


async def match_odds_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of match_odds_data()."""
    return await _per_match_simple(
        match_df, data_source, rate_limit, cache,
        endpoint="{base}/api/v1/event/{game_id}/odds/1/all",
        parser=parse_match_odds_records,
        log_label="odds",
        fn_name="match_odds_data",
        error_msg="No odds data found.",
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        output_dir=output_dir,
    )


async def match_h2h_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of match_h2h_data()."""
    return await _per_match_simple(
        match_df, data_source, rate_limit, cache,
        endpoint="{base}/api/v1/event/{game_id}/h2h",
        parser=parse_match_h2h_record,
        log_label="h2h",
        fn_name="match_h2h_data",
        error_msg="No H2H data found.",
        extra_args_fn=lambda row: (row["home_team"], row["away_team"]),
        single_record=True,
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        output_dir=output_dir,
    )


async def average_positions_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of average_positions_data()."""
    return await _per_match_simple(
        match_df, data_source, rate_limit, cache,
        endpoint="{base}/api/v1/event/{game_id}/average-positions",
        parser=parse_average_positions_records,
        log_label="average positions",
        fn_name="average_positions_data",
        error_msg="No average position data found.",
        extra_args_fn=lambda row: (row["home_team"], row["away_team"]),
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        output_dir=output_dir,
    )


async def pregame_form_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of pregame_form_data()."""
    validate_source(data_source)
    validate_df(match_df, "match_df")

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        records = await iter_per_match_async(
            match_df, client,
            data_source=data_source,
            endpoint="{base}/api/v1/event/{game_id}/pregame-form",
            parser=pregame_form_records,
            log_label="pregame form",
        )

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No pre-game form data found for the specified matches.")
    result_df = pregame_form_coerce_numeric(result_df)
    export_df(
        result_df, fn_name="pregame_form_data", data_source=data_source,
        output_dir=output_dir,
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
    )
    return result_df


# ---------------------------------------------------------------------------
# Coordinates / Goal networks
# ---------------------------------------------------------------------------

async def coordinates_data(
    lineups_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of coordinates_data(). Players with no heatmap data are silently skipped."""
    validate_source(data_source)
    validate_df(lineups_df, "lineups_df")

    unique_players = lineups_df[[
        "country", "tournament", "season", "week", "game_id", "team", "player_id", "player_name"
    ]].drop_duplicates()
    if unique_players.empty:
        raise InvalidParameterError("No unique players found in lineups_df.")

    sem = asyncio.Semaphore(1)
    base = API_URLS[data_source]

    async def _fetch(client, row):
        url = f"{base}/api/v1/event/{row['game_id']}/player/{row['player_id']}/heatmap"
        async with sem:
            try:
                data = await client.get(url)
            except APIError as exc:
                if exc.status_code in (404, 403):
                    return []
                raise
        return heatmap_records(data, row)

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        batches = await asyncio.gather(*[_fetch(client, row) for _, row in unique_players.iterrows()])

    heatmap_data = [rec for batch in batches for rec in batch]
    result_df = pd.DataFrame(heatmap_data)
    if result_df.empty:
        raise DataNotAvailableError("No heatmap data found for the specified players.")

    export_df(
        result_df, fn_name="coordinates_data", data_source=data_source,
        output_dir=output_dir,
        first_row=lineups_df.iloc[0],
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
    )
    return result_df


async def goal_networks_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of goal_networks_data()."""
    validate_source(data_source)
    validate_df(match_df, "match_df")
    base = API_URLS[data_source]

    async def _fetch(client, row):
        country, tournament, season, week, game_id = row[
            ["country", "tournament", "season", "week", "game_id"]
        ]
        data = await client.get(f"{base}/api/v1/event/{game_id}/incidents")
        incidents = data.get("incidents", [])
        if not isinstance(incidents, list) or not incidents:
            return None
        frame = pd.DataFrame(incidents)
        frame["country"] = country
        frame["tournament"] = tournament
        frame["season"] = season
        frame["week"] = week
        frame["game_id"] = game_id
        return frame

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        frames = await asyncio.gather(*[_fetch(client, row) for _, row in match_df.iterrows()])

    incidents_frames = [f for f in frames if f is not None]
    if not incidents_frames:
        raise DataNotAvailableError("No goal network data found for the specified parameters.")
    incidents_df = pd.concat(incidents_frames, ignore_index=True)
    result_df = goal_networks_post_process(incidents_df)

    export_df(
        result_df, fn_name="goal_networks_data", data_source=data_source,
        output_dir=output_dir,
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
    )
    return result_df


# ---------------------------------------------------------------------------
# past_matches: two-stage (round events + parallel h2h)
# ---------------------------------------------------------------------------

async def past_matches_data(
    tournament_id: int,
    season_id: int,
    week_number: Optional[int] = None,
    tournament_type: Optional[str] = None,
    tournament_stage: Optional[str] = None,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of past_matches_data(). H2H requests for each match run in parallel."""
    validate_source(data_source)
    round_url = build_tournament_url(
        base_url=API_URLS[data_source],
        tournament_id=tournament_id,
        season_id=season_id,
        week_number=week_number,
        tournament_type=tournament_type,
        tournament_stage=tournament_stage,
    )

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        round_data = await client.get(round_url)
        events = round_data.get("events")
        if not isinstance(events, list) or not events:
            raise DataNotAvailableError(
                f"No match data found for tournament_id={tournament_id}, "
                f"season_id={season_id}, week_number={week_number}."
            )

        first_event = events[0]
        fn_country = first_event.get("tournament", {}).get("category", {}).get("name", "")
        fn_tournament = first_event.get("tournament", {}).get("name", "")
        fn_season = first_event.get("season", {}).get("year", "")

        events_df = pd.DataFrame(events)
        if "customId" not in events_df.columns:
            raise DataNotAvailableError(
                f"customId field missing in API response for tournament_id={tournament_id}, "
                f"season_id={season_id}, week_number={week_number}."
            )
        custom_ids = events_df["customId"].dropna().tolist()

        async def _fetch_h2h(custom_id):
            url = f"{WWW_URLS[data_source]}/api/v1/event/{custom_id}/h2h/events"
            h2h_data = await client.get(url)
            h2h_events = h2h_data.get("events")
            if not isinstance(h2h_events, list):
                return []
            return [past_match_record_from_event(ev) for ev in h2h_events]

        batches = await asyncio.gather(*[_fetch_h2h(cid) for cid in custom_ids])

    all_matches = [m for batch in batches for m in batch]
    if not all_matches:
        raise DataNotAvailableError(
            f"No H2H match data found for tournament_id={tournament_id}, "
            f"season_id={season_id}, week_number={week_number}."
        )
    result_df = pd.DataFrame(all_matches)
    export_df(
        result_df, fn_name="past_matches_data", data_source=data_source,
        output_dir=output_dir,
        country=fn_country, tournament=fn_tournament, season=fn_season,
        week_number=week_number,
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
    )
    return result_df


# ---------------------------------------------------------------------------
# Standings, seasons, search, season_rounds, league_player_stats
# ---------------------------------------------------------------------------

async def standings_data(
    tournament_id: int,
    season_id: int,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of standings_data()."""
    validate_source(data_source)
    base = API_URLS[data_source]

    async def _fetch(client, category):
        url = (
            f"{base}/api/v1/unique-tournament/{tournament_id}"
            f"/season/{season_id}/standings/{category}"
        )
        try:
            data = await client.get(url)
            return parse_standings_rows(data, category, tournament_id, season_id)
        except APIError:
            return []

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        batches = await asyncio.gather(*[_fetch(client, c) for c in ("total", "home", "away")])

    rows = [r for batch in batches for r in batch]
    df = pd.DataFrame(rows)
    if df.empty:
        raise DataNotAvailableError("No standings data found.")

    if enable_json_export or enable_excel_export:
        country, tournament_name, season_year = resolve_tournament_season(
            tournament_id, season_id, data_source=data_source, rate_limit=rate_limit
        )
        first = df.iloc[0]
        export_df(
            df, fn_name="standings_data", data_source=data_source,
            output_dir=output_dir,
            country=country or first["country"],
            tournament=tournament_name or first["tournament"],
            season=season_year, include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return df


async def seasons_data(
    tournament_id: int,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of seasons_data()."""
    validate_source(data_source)
    base = API_URLS[data_source]
    country = ""
    tournament_name = str(tournament_id)

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        data = await client.get(f"{base}/api/v1/unique-tournament/{tournament_id}/seasons")
        if enable_json_export or enable_excel_export:
            try:
                t_data = await client.get(f"{base}/api/v1/unique-tournament/{tournament_id}")
                ut = t_data.get("uniqueTournament", {})
                country = ut.get("category", {}).get("name", "") or ""
                tournament_name = ut.get("name", str(tournament_id)) or str(tournament_id)
            except Exception:
                pass

    seasons = data.get("seasons", [])
    if not seasons:
        raise DataNotAvailableError(f"No seasons found for tournament_id={tournament_id}.")
    result_df = pd.DataFrame(parse_seasons_records(data, tournament_id))

    export_df(
        result_df, fn_name="seasons_data", data_source=data_source,
        output_dir=output_dir,
        country=country, tournament=tournament_name,
        season=None, include_week=False,
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
    )
    return result_df


async def search_data(
    query: str,
    entity_type: Optional[str] = None,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of search_data()."""
    validate_source(data_source)
    if not query or not query.strip():
        raise InvalidParameterError("query must be a non-empty string.")
    if entity_type is not None and entity_type not in AVAILABLE_ENTITY_TYPES:
        raise InvalidParameterError(
            f"Invalid entity_type: '{entity_type}'. "
            f"Must be one of {AVAILABLE_ENTITY_TYPES} or None."
        )

    url = f"{API_URLS[data_source]}/api/v1/search/{quote(query.strip(), safe='')}"
    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        data = await client.get(url)

    results = data.get("results", [])
    if not results:
        raise DataNotAvailableError(f"No results found for query='{query}'.")
    records = parse_search_records(results, entity_type)
    df = pd.DataFrame(records)
    if df.empty:
        raise DataNotAvailableError(
            f"No results found for query='{query}'"
            + (f" with entity_type='{entity_type}'" if entity_type else "") + "."
        )
    result_df = df.sort_values("score", ascending=False).reset_index(drop=True)

    if enable_json_export or enable_excel_export:
        from datafc.utils._save_files import save_excel, save_json
        kwargs = dict(fn_name="search_data", data_source=data_source,
                      country="", tournament=query.strip())
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)
    return result_df


async def season_rounds_data(
    tournament_id: int,
    season_id: int,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of season_rounds_data()."""
    validate_source(data_source)
    url = (
        f"{API_URLS[data_source]}/api/v1/unique-tournament/{tournament_id}"
        f"/season/{season_id}/rounds"
    )
    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        data = await client.get(url)
    rounds = data.get("rounds") or data.get("currentRounds") or []
    if not rounds:
        raise DataNotAvailableError(
            f"No round data found for tournament_id={tournament_id}, season_id={season_id}."
        )
    result_df = pd.DataFrame(season_rounds_records(rounds, tournament_id, season_id))

    if enable_json_export or enable_excel_export:
        country, tournament_name, season_year = resolve_tournament_season(
            tournament_id, season_id, data_source=data_source, rate_limit=rate_limit
        )
        export_df(
            result_df, fn_name="season_rounds_data", data_source=data_source,
            output_dir=output_dir,
            country=country, tournament=tournament_name, season=season_year,
            include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df


async def league_player_stats_data(
    tournament_id: int,
    season_id: int,
    order: str = "-rating",
    accumulation: str = "total",
    fields: Optional[list] = None,
    position: Optional[str] = None,
    max_players: int = 100,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of league_player_stats_data()."""
    validate_source(data_source)
    if accumulation not in AVAILABLE_ACCUMULATIONS:
        raise InvalidParameterError(
            f"Invalid accumulation: '{accumulation}'. Must be one of {AVAILABLE_ACCUMULATIONS}."
        )
    if position is not None and position not in ("G", "D", "M", "F"):
        raise InvalidParameterError(
            f"Invalid position: '{position}'. Must be one of 'G', 'D', 'M', 'F' or None."
        )
    if fields is not None:
        invalid = set(fields) - AVAILABLE_FIELDS
        if invalid:
            raise InvalidParameterError(
                f"Unknown fields: {invalid}. Available: {sorted(AVAILABLE_FIELDS)}."
            )

    selected_fields = fields if fields is not None else DEFAULT_FIELDS
    fields_param = ",".join(selected_fields)
    order_field = order.lstrip("-")
    if order_field not in AVAILABLE_FIELDS:
        raise InvalidParameterError(
            f"Invalid order field: '{order_field}'. Must be one of {sorted(AVAILABLE_FIELDS)}."
        )
    if order_field not in selected_fields:
        fields_param = f"{fields_param},{order_field}"

    page_size = min(max_players, 100)
    records = []
    page = 1
    base = API_URLS[data_source]

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        while len(records) < max_players:
            url = (
                f"{base}/api/v1/unique-tournament/{tournament_id}"
                f"/season/{season_id}/statistics"
                f"?limit={page_size}&order={order}&accumulation={accumulation}"
                f"&fields={fields_param}&page={page}"
            )
            if position is not None:
                url += f"&filters=position.in.{position}"
            data = await client.get(url)
            results = data.get("results", [])
            if not results:
                break
            records.extend(parse_league_player_stats_records(
                data, tournament_id, season_id, selected_fields,
            ))
            total_pages = data.get("pages", page)
            if page >= total_pages or len(records) >= max_players:
                break
            page += 1

    if not records:
        raise DataNotAvailableError(
            f"No player stats found for tournament_id={tournament_id}, season_id={season_id}."
        )
    result_df = pd.DataFrame(records).head(max_players)

    if enable_json_export or enable_excel_export:
        country, tournament, season = resolve_tournament_season(
            tournament_id, season_id, data_source=data_source, rate_limit=rate_limit
        )
        export_df(
            result_df, fn_name="league_player_stats_data", data_source=data_source,
            output_dir=output_dir,
            country=country, tournament=tournament, season=season,
            include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df


# ---------------------------------------------------------------------------
# Per-team (standings_df-driven) concurrent iterators
# ---------------------------------------------------------------------------

async def _per_team_concurrent(
    standings_df, data_source, rate_limit, cache, *,
    url_for_team, parser, log_label,
):
    """Run a per-team parser concurrently across the 'Total' standings rows.

    ``url_for_team(row, base) -> str``;
    ``parser(data, row) -> list of records``.

    Returns ``(records, failed_team_ids)``.
    """
    base = API_URLS[data_source]
    teams = standings_df[standings_df["category"] == "Total"]

    async def _fetch(client, row):
        team_id = row["team_id"]
        team_name = row["team_name"]
        try:
            data = await client.get(url_for_team(row, base))
            return parser(data, row), None
        except APIError as exc:
            logger.warning(
                "Failed to fetch %s for team_id=%s (%s): %s",
                log_label, team_id, team_name, exc,
            )
            return [], team_id

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        results = await asyncio.gather(*[_fetch(client, row) for _, row in teams.iterrows()])

    records, failed = [], []
    for recs, failed_id in results:
        records.extend(recs)
        if failed_id is not None:
            failed.append(failed_id)
    return records, failed


async def squad_data(
    standings_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of squad_data(). All team requests run in parallel."""
    validate_source(data_source)
    validate_df(standings_df, "standings_df")

    records, failed_teams = await _per_team_concurrent(
        standings_df, data_source, rate_limit, cache,
        url_for_team=lambda row, base: f"{base}/api/v1/team/{row['team_id']}/players",
        parser=squad_records_from_response,
        log_label="squad data",
    )
    if failed_teams:
        logger.warning("Could not retrieve squad for %d team(s): %s",
                       len(failed_teams), failed_teams)
    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No squad data found for the specified teams.")

    if enable_json_export or enable_excel_export:
        first = standings_df.iloc[0]
        t_id = int(first.get("tournament_id") or 0)
        s_id = int(first.get("season_id") or 0)
        _, _, season_year = resolve_tournament_season(
            t_id, s_id, data_source=data_source, rate_limit=rate_limit
        ) if t_id and s_id else ("", "", None)
        export_df(
            result_df, fn_name="squad_data", data_source=data_source,
            output_dir=output_dir,
            country=first["country"], tournament=first["tournament"],
            season=season_year, include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df


async def player_stats_data(
    standings_df: pd.DataFrame,
    tournament_id: int,
    season_id: int,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of player_stats_data(). All team requests run in parallel."""
    validate_source(data_source)
    validate_df(standings_df, "standings_df")

    def _url(row, base):
        # Note: the player-stats endpoint lives under www.* (WWW_URLS), not api.*.
        www = WWW_URLS[data_source]
        return (
            f"{www}/api/v1/team/{row['team_id']}"
            f"/unique-tournament/{tournament_id}/season/{season_id}/top-players/overall"
        )

    records, failed_teams = await _per_team_concurrent(
        standings_df, data_source, rate_limit, cache,
        url_for_team=_url,
        parser=player_stats_records_from_response,
        log_label="player stats",
    )
    if failed_teams:
        logger.warning("Could not retrieve player stats for %d team(s): %s",
                       len(failed_teams), failed_teams)
    result_df = pd.DataFrame(records).drop_duplicates(
        subset=["team_id", "player_id", "stat_name"]
    )
    if result_df.empty:
        raise DataNotAvailableError("No player statistics data found for the specified teams.")

    if enable_json_export or enable_excel_export:
        country, tournament_name, season_year = resolve_tournament_season(
            tournament_id, season_id, data_source=data_source, rate_limit=rate_limit
        )
        first = result_df.iloc[0]
        export_df(
            result_df, fn_name="player_stats_data", data_source=data_source,
            output_dir=output_dir,
            country=country or first["country"],
            tournament=tournament_name or first["tournament"],
            season=season_year, include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df


async def team_stats_data(
    standings_df: pd.DataFrame,
    tournament_id: int,
    season_id: int,
    season: Optional[str] = None,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of team_stats_data(). All team requests run in parallel.

    Args:
        season: Optional season label used in the export filename. If None,
            it is resolved from tournament_id / season_id.
    """
    validate_source(data_source)
    validate_df(standings_df, "standings_df")

    def _url(row, base):
        www = WWW_URLS[data_source]
        return (
            f"{www}/api/v1/team/{row['team_id']}"
            f"/unique-tournament/{tournament_id}/season/{season_id}/statistics/overall"
        )

    records, failed_teams = await _per_team_concurrent(
        standings_df, data_source, rate_limit, cache,
        url_for_team=_url,
        parser=team_stats_records_from_response,
        log_label="team stats",
    )
    if failed_teams:
        logger.warning("Could not retrieve stats for %d team(s): %s",
                       len(failed_teams), failed_teams)
    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No team statistics data found for the specified teams.")

    if enable_json_export or enable_excel_export:
        if season is None:
            country, tournament_name, season_label = resolve_tournament_season(
                tournament_id, season_id, data_source=data_source, rate_limit=rate_limit
            )
        else:
            country, tournament_name, season_label = "", "", season
        first = result_df.iloc[0]
        export_df(
            result_df, fn_name="team_stats_data", data_source=data_source,
            output_dir=output_dir,
            country=country or first["country"],
            tournament=tournament_name or first["tournament"],
            season=season_label, include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df


async def team_transfers_data(
    standings_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of team_transfers_data(). All team requests run in parallel."""
    validate_source(data_source)
    validate_df(standings_df, "standings_df")

    records, failed = await _per_team_concurrent(
        standings_df, data_source, rate_limit, cache,
        url_for_team=lambda row, base: f"{base}/api/v1/team/{row['team_id']}/transfers",
        parser=team_transfers_records_from_response,
        log_label="transfers",
    )
    if failed:
        logger.warning("Could not retrieve transfers for %d team(s): %s", len(failed), failed)

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No transfer data found for the specified teams.")
    _cast_int_cols(result_df, "from_team_id", "to_team_id")

    if enable_json_export or enable_excel_export:
        first = standings_df.iloc[0]
        export_df(
            result_df, fn_name="team_transfers_data", data_source=data_source,
            output_dir=output_dir,
            country=first["country"], tournament=first["tournament"],
            season=None, include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df


async def team_data(
    standings_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of team_data(). All team requests run in parallel."""
    validate_source(data_source)
    validate_df(standings_df, "standings_df")

    base = API_URLS[data_source]
    teams = standings_df[standings_df["category"] == "Total"]

    async def _fetch(client, row):
        team_id, team_name = row["team_id"], row["team_name"]
        try:
            data = await client.get(f"{base}/api/v1/team/{team_id}")
            rec = team_profile_record_from_response(data, row)
            if rec is None:
                logger.warning("Empty team response for team_id=%s", team_id)
                return None, team_id
            return rec, None
        except APIError as exc:
            logger.warning(
                "Failed to fetch profile for team_id=%s (%s): %s",
                team_id, team_name, exc,
            )
            return None, team_id

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        results = await asyncio.gather(*[_fetch(client, row) for _, row in teams.iterrows()])

    records, failed = [], []
    for record, failed_id in results:
        if record is not None:
            records.append(record)
        if failed_id is not None:
            failed.append(failed_id)
    if failed:
        logger.warning("Could not retrieve profile for %d team(s): %s", len(failed), failed)

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No team profile data found for the specified teams.")

    if enable_json_export or enable_excel_export:
        first = standings_df.iloc[0]
        t_id = int(first.get("tournament_id") or 0)
        s_id = int(first.get("season_id") or 0)
        _, _, season_year = resolve_tournament_season(
            t_id, s_id, data_source=data_source, rate_limit=rate_limit
        ) if t_id and s_id else ("", "", None)
        export_df(
            result_df, fn_name="team_data", data_source=data_source,
            output_dir=output_dir,
            country=first.get("country", "unknown"),
            tournament=first.get("tournament", "unknown"),
            season=season_year, include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df


# ---------------------------------------------------------------------------
# Per-player (squad_df-driven) concurrent iterators
# ---------------------------------------------------------------------------

async def _per_player_concurrent(
    squad_df, data_source, rate_limit, cache, *,
    url_for_player, parser, log_label,
):
    """Run a per-player parser concurrently across unique squad players.

    ``url_for_player(player_id, base) -> str``;
    ``parser(data, player_id, player_name) -> list``.

    Returns ``(records, failed_player_ids)``.
    """
    base = API_URLS[data_source]
    unique_players = squad_df[["player_id", "player_name"]].drop_duplicates()

    async def _fetch(client, player_id, player_name):
        try:
            data = await client.get(url_for_player(player_id, base))
            return parser(data, player_id, player_name), None
        except APIError as exc:
            logger.warning(
                "Failed to fetch %s for player_id=%s (%s): %s",
                log_label, player_id, player_name, exc,
            )
            return [], player_id

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        results = await asyncio.gather(*[
            _fetch(client, row["player_id"], row["player_name"])
            for _, row in unique_players.iterrows()
        ])

    records, failed = [], []
    for recs, failed_id in results:
        records.extend(recs)
        if failed_id is not None:
            failed.append(failed_id)
    return records, failed


async def player_transfers_data(
    squad_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of player_transfers_data(). All player requests run in parallel."""
    validate_source(data_source)
    validate_df(squad_df, "squad_df")

    records, failed = await _per_player_concurrent(
        squad_df, data_source, rate_limit, cache,
        url_for_player=lambda pid, base: f"{base}/api/v1/player/{pid}/transfer-history",
        parser=player_transfers_records_from_response,
        log_label="transfers",
    )
    if failed:
        logger.warning("Could not retrieve transfers for %d player(s): %s", len(failed), failed)

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No transfer data found for the specified players.")
    _cast_int_cols(result_df, "from_team_id", "to_team_id")

    if enable_json_export or enable_excel_export:
        first = squad_df.iloc[0]
        t_id = int(first.get("tournament_id") or 0)
        s_id = int(first.get("season_id") or 0)
        _, _, season_year = resolve_tournament_season(
            t_id, s_id, data_source=data_source, rate_limit=rate_limit
        ) if t_id and s_id else ("", "", None)
        export_df(
            result_df, fn_name="player_transfers_data", data_source=data_source,
            output_dir=output_dir,
            country=first.get("country", "unknown"),
            tournament=first.get("tournament", "unknown"),
            season=season_year, include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df


async def player_national_team_data(
    squad_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of player_national_team_data()."""
    validate_source(data_source)
    validate_df(squad_df, "squad_df")

    records, _ = await _per_player_concurrent(
        squad_df, data_source, rate_limit, cache,
        url_for_player=lambda pid, base: f"{base}/api/v1/player/{pid}/national-team-statistics",
        parser=player_national_team_records_from_response,
        log_label="national team stats",
    )

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No national team data found for the specified players.")

    if enable_json_export or enable_excel_export:
        first = squad_df.iloc[0]
        export_df(
            result_df, fn_name="player_national_team_data", data_source=data_source,
            output_dir=output_dir,
            country=first.get("country", "unknown"),
            tournament=first.get("tournament", "unknown"),
            season=None, include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df


async def player_attribute_overviews_data(
    squad_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of player_attribute_overviews_data(). All players fetched in parallel."""
    validate_source(data_source)
    validate_df(squad_df, "squad_df")

    records, _ = await _per_player_concurrent(
        squad_df, data_source, rate_limit, cache,
        url_for_player=lambda pid, base: f"{base}/api/v1/player/{pid}/attribute-overviews",
        parser=player_attribute_overviews_records_from_response,
        log_label="attribute overviews",
    )

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError(
            "No attribute overview data found for the specified players."
        )

    if enable_json_export or enable_excel_export:
        first = squad_df.iloc[0]
        export_df(
            result_df, fn_name="player_attribute_overviews_data", data_source=data_source,
            output_dir=output_dir,
            country=first.get("country", "unknown"),
            tournament=first.get("tournament", "unknown"),
            season=None, include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df


async def player_data(
    squad_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of player_data()."""
    validate_source(data_source)
    validate_df(squad_df, "squad_df")

    def _parser(data, player_id, player_name):
        rec = player_profile_record_from_response(data, player_id, player_name)
        return [rec] if rec is not None else []

    records, _ = await _per_player_concurrent(
        squad_df, data_source, rate_limit, cache,
        url_for_player=lambda pid, base: f"{base}/api/v1/player/{pid}",
        parser=_parser,
        log_label="profile",
    )

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No player profile data found for the specified players.")

    if enable_json_export or enable_excel_export:
        first = squad_df.iloc[0]
        t_id = int(first.get("tournament_id") or 0)
        s_id = int(first.get("season_id") or 0)
        _, _, season_year = resolve_tournament_season(
            t_id, s_id, data_source=data_source, rate_limit=rate_limit
        ) if t_id and s_id else ("", "", None)
        export_df(
            result_df, fn_name="player_data", data_source=data_source,
            output_dir=output_dir,
            country=first.get("country", "unknown"),
            tournament=first.get("tournament", "unknown"),
            season=season_year, include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df


async def player_match_log_data(
    squad_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of player_match_log_data(). All players fetched in parallel."""
    validate_source(data_source)
    validate_df(squad_df, "squad_df")
    base = API_URLS[data_source]

    async def _fetch(client, player_id, player_name):
        page = 0
        out = []
        while True:
            url = f"{base}/api/v1/player/{player_id}/events/last/{page}"
            try:
                data = await client.get(url)
            except APIError as exc:
                logger.warning(
                    "Failed to fetch match log for player_id=%s (%s): %s",
                    player_id, player_name, exc,
                )
                break
            out.extend(match_log_records_from_response(data, player_id, player_name))
            if not data.get("hasNextPage", False):
                break
            page += 1
        return out

    unique_players = squad_df[["player_id", "player_name"]].drop_duplicates()
    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        batches = await asyncio.gather(*[
            _fetch(client, row["player_id"], row["player_name"])
            for _, row in unique_players.iterrows()
        ])

    records = [rec for batch in batches for rec in batch]
    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No match log data found for the specified players.")

    if enable_json_export or enable_excel_export:
        first = squad_df.iloc[0]
        export_df(
            result_df, fn_name="player_match_log_data", data_source=data_source,
            output_dir=output_dir,
            country=first.get("country", ""),
            tournament=first.get("tournament", ""),
            season=result_df.iloc[0].get("season"),
            include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df


async def player_career_stats_data(
    squad_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of player_career_stats_data(). All player requests run in parallel."""
    validate_source(data_source)
    validate_df(squad_df, "squad_df")
    base = API_URLS[data_source]

    async def _fetch(client, player_id, player_name):
        try:
            seasons_data = await client.get(
                f"{base}/api/v1/player/{player_id}/statistics/seasons"
            )
        except APIError as exc:
            logger.warning(
                "Failed to fetch career stats for player_id=%s (%s): %s",
                player_id, player_name, exc,
            )
            return [], player_id

        out = []
        for entry in seasons_data.get("uniqueTournamentSeasons", []):
            tournament = entry.get("uniqueTournament", {})
            tid = tournament.get("id")
            for season in entry.get("seasons", []):
                sid = season.get("id")
                try:
                    stats_data = await client.get(
                        f"{base}/api/v1/player/{player_id}"
                        f"/unique-tournament/{tid}/season/{sid}/statistics/overall"
                    )
                except APIError:
                    continue
                out.extend(career_stats_records_for_pair(
                    tournament, season, stats_data, player_id, player_name,
                ))
        return out, None

    unique_players = squad_df[["player_id", "player_name"]].drop_duplicates()
    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        results = await asyncio.gather(*[
            _fetch(client, row["player_id"], row["player_name"])
            for _, row in unique_players.iterrows()
        ])

    records, failed = [], []
    for recs, failed_id in results:
        records.extend(recs)
        if failed_id is not None:
            failed.append(failed_id)
    if failed:
        logger.warning("Could not retrieve career stats for %d player(s): %s", len(failed), failed)

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No career stats data found for the specified players.")
    _cast_int_cols(result_df, "team_id")

    if enable_json_export or enable_excel_export:
        first = squad_df.iloc[0]
        export_df(
            result_df, fn_name="player_career_stats_data", data_source=data_source,
            output_dir=output_dir,
            country=first.get("country", "unknown"),
            tournament=first.get("tournament", "unknown"),
            season=None, include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df


# ---------------------------------------------------------------------------
# Upcoming matches / team match history / referee
# ---------------------------------------------------------------------------

async def upcoming_matches_data(
    standings_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of upcoming_matches_data()."""
    validate_source(data_source)
    validate_df(standings_df, "standings_df")
    base = API_URLS[data_source]
    teams = standings_df[standings_df["category"] == "Total"]
    seen_game_ids: set = set()

    async def _fetch_team(client, team_id):
        team_pages = []
        page = 0
        while True:
            url = f"{base}/api/v1/team/{team_id}/events/next/{page}"
            try:
                data = await client.get(url)
            except APIError:
                break
            team_pages.append(data)
            if not data.get("hasNextPage", False):
                break
            page += 1
        return team_pages

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        all_pages = await asyncio.gather(*[
            _fetch_team(client, row["team_id"]) for _, row in teams.iterrows()
        ])

    records = []
    for team_pages in all_pages:
        for data in team_pages:
            records.extend(parse_upcoming_matches_records(data, seen_game_ids))

    df = pd.DataFrame(records)
    if df.empty:
        raise DataNotAvailableError("No upcoming match data found for the specified teams.")
    result_df = df.sort_values("start_timestamp").reset_index(drop=True)

    if enable_json_export or enable_excel_export:
        first = standings_df.iloc[0]
        t_id = int(first.get("tournament_id") or 0)
        s_id = int(first.get("season_id") or 0)
        _, _, season_year = resolve_tournament_season(
            t_id, s_id, data_source=data_source, rate_limit=rate_limit
        ) if t_id and s_id else ("", "", None)
        export_df(
            result_df, fn_name="upcoming_matches_data", data_source=data_source,
            output_dir=output_dir,
            country=first.get("country", ""),
            tournament=first.get("tournament", ""),
            season=season_year, include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df


async def team_match_history_data(
    team_id: int,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of team_match_history_data()."""
    validate_source(data_source)
    seen_game_ids: set = set()
    records = []
    base = API_URLS[data_source]

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        page = 0
        while True:
            url = f"{base}/api/v1/team/{team_id}/events/last/{page}"
            try:
                data = await client.get(url)
            except APIError as exc:
                logger.warning(
                    "Failed to fetch match history for team_id=%s page=%s: %s",
                    team_id, page, exc,
                )
                break
            records.extend(parse_team_match_history_records(data, seen_game_ids))
            if not data.get("hasNextPage", False):
                break
            page += 1

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError(
            f"No historical match data found for team_id={team_id}."
        )
    result_df = result_df.sort_values("start_timestamp").reset_index(drop=True)
    result_df = _cast_int_cols(
        result_df,
        "week",
        "home_team_id", "away_team_id",
        "home_score_period1", "home_score_period2", "home_score_normaltime",
        "home_score_display", "home_score_current",
        "away_score_period1", "away_score_period2", "away_score_normaltime",
        "away_score_display", "away_score_current",
        "start_timestamp",
    )

    if enable_json_export or enable_excel_export:
        first = result_df.iloc[0]
        export_df(
            result_df, fn_name="team_match_history_data", data_source=data_source,
            output_dir=output_dir,
            country=first.get("country", ""),
            tournament=first.get("tournament", ""),
            season=first.get("season"), include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df


async def referee_stats_data(
    referee_id: int,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of referee_stats_data()."""
    validate_source(data_source)
    referee_name = str(referee_id)
    base = API_URLS[data_source]

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        data = await client.get(f"{base}/api/v1/referee/{referee_id}/statistics")
        if enable_json_export or enable_excel_export:
            try:
                r_data = await client.get(f"{base}/api/v1/referee/{referee_id}")
                referee_name = (r_data.get("referee") or {}).get("name", str(referee_id)) or str(referee_id)
            except Exception:
                pass

    statistics = data.get("statistics", [])
    if not statistics:
        raise DataNotAvailableError(f"No statistics found for referee_id={referee_id}.")

    result_df = pd.DataFrame(referee_stats_records(statistics, referee_id, referee_name))
    if result_df.empty:
        raise DataNotAvailableError(f"No statistics found for referee_id={referee_id}.")

    export_df(
        result_df, fn_name="referee_stats_data", data_source=data_source,
        output_dir=output_dir,
        country="", tournament=referee_name, season=None, include_week=False,
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
    )
    return result_df

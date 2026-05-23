"""
Async versions of all datafc fetch functions.

Every function here is an async coroutine that mirrors its sync counterpart
in datafc.sofascore. The primary use case is fetching many rounds / players /
teams in parallel using asyncio.gather(), which is dramatically faster than
sequential sync calls for large datasets.

Example — fetch an entire season concurrently:

    import asyncio
    import pandas as pd
    from datafc.sofascore import aio

    async def fetch_season(tournament_id, season_id, total_weeks):
        tasks = [
            aio.match_data(tournament_id, season_id, week_number=w)
            for w in range(1, total_weeks + 1)
        ]
        frames = await asyncio.gather(*tasks)
        return pd.concat(frames, ignore_index=True)

    df = asyncio.run(fetch_season(52, 63814, total_weeks=38))

Rate limiting applies globally across all concurrent coroutines (default 2 req/s).
Adjust with the rate_limit parameter on each function.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote
import pandas as pd

from datafc.utils._async_client import AsyncSofascoreClient
from datafc.utils._cache import DiskCache
from datafc.utils._config import API_URLS, WWW_URLS
from datafc.utils._validate import validate_source, validate_df, build_tournament_url
from datafc.utils._save_files import save_json, save_excel
from datafc.utils._tournament_info import resolve_tournament_season
from datafc.utils._helpers import _ts_to_age, _safe_apply, _cast_int_cols
from datafc.exceptions import APIError, InvalidParameterError, DataNotAvailableError
from datafc.sofascore._parsers import (
    parse_match_events,
    parse_match_stats_records,
    parse_shots_records,
    parse_momentum_records,
    parse_lineups_records,
    parse_substitutions_records,
    parse_incidents_records,
    parse_match_details_records,
    parse_upcoming_matches_records,
    parse_team_match_history_records,
    parse_match_odds_records,
    parse_match_h2h_record,
    parse_standings_rows,
    parse_seasons_records,
    parse_average_positions_records,
    parse_league_player_stats_records,
    parse_search_records,
)
from datafc.sofascore.fetch_league_player_stats_data import (
    AVAILABLE_FIELDS,
    AVAILABLE_ACCUMULATIONS,
    DEFAULT_FIELDS,
)
from datafc.sofascore.fetch_search_data import AVAILABLE_ENTITY_TYPES

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Match-level functions
# ---------------------------------------------------------------------------

async def match_data(
    tournament_id: int,
    season_id: int,
    week_number: int,
    tournament_type: Optional[str] = None,
    tournament_stage: Optional[str] = None,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of match_data(). See sync docstring for full parameter docs."""
    validate_source(data_source)
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

    if enable_json_export or enable_excel_export:
        first = result_df.iloc[0]
        kwargs = dict(
            fn_name="match_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=first["season"],
            week_number=first["week"],
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


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
    validate_source(data_source)
    validate_df(match_df, "match_df")

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series) -> list:
        country, tournament, season, week, game_id = row[
            ["country", "tournament", "season", "week", "game_id"]
        ]
        data = await client.get(f"{API_URLS[data_source]}/api/v1/event/{game_id}/statistics")
        return parse_match_stats_records(data, country, tournament, season, week, game_id)

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        batches = await asyncio.gather(*[_fetch(client, row) for _, row in match_df.iterrows()])

    records = [rec for batch in batches for rec in batch]
    df = pd.DataFrame(records)
    if df.empty:
        raise DataNotAvailableError("No match statistics data found.")

    if enable_json_export or enable_excel_export:
        first = match_df.iloc[0]
        kwargs = dict(
            fn_name="match_stats_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=first["season"],
            week_number=first["week"],
        )
        if enable_json_export:
            save_json(data=df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=df, **kwargs, output_dir=output_dir)

    return df


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
    validate_source(data_source)
    validate_df(match_df, "match_df")

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series) -> list:
        country, tournament, season, week, game_id = row[
            ["country", "tournament", "season", "week", "game_id"]
        ]
        data = await client.get(f"{API_URLS[data_source]}/api/v1/event/{game_id}/shotmap")
        return parse_shots_records(data, country, tournament, season, week, game_id)

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        batches = await asyncio.gather(*[_fetch(client, row) for _, row in match_df.iterrows()])

    records = [rec for batch in batches for rec in batch]
    df = pd.DataFrame(records)
    if df.empty:
        raise DataNotAvailableError("No shot data found.")

    if enable_json_export or enable_excel_export:
        first = match_df.iloc[0]
        kwargs = dict(
            fn_name="shots_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=first["season"],
            week_number=first["week"],
        )
        if enable_json_export:
            save_json(data=df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=df, **kwargs, output_dir=output_dir)

    return df


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
    validate_source(data_source)
    validate_df(match_df, "match_df")

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series) -> list:
        country, tournament, season, week, game_id = row[
            ["country", "tournament", "season", "week", "game_id"]
        ]
        data = await client.get(f"{API_URLS[data_source]}/api/v1/event/{game_id}/graph")
        return parse_momentum_records(data, country, tournament, season, week, game_id)

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        batches = await asyncio.gather(*[_fetch(client, row) for _, row in match_df.iterrows()])

    records = [rec for batch in batches for rec in batch]
    df = pd.DataFrame(records)
    if df.empty:
        raise DataNotAvailableError("No momentum data found.")

    if enable_json_export or enable_excel_export:
        first = match_df.iloc[0]
        kwargs = dict(
            fn_name="momentum_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=first["season"],
            week_number=first["week"],
        )
        if enable_json_export:
            save_json(data=df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=df, **kwargs, output_dir=output_dir)

    return df


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
    validate_source(data_source)
    validate_df(match_df, "match_df")

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series) -> list:
        country, tournament, season, week, game_id = row[
            ["country", "tournament", "season", "week", "game_id"]
        ]
        data = await client.get(f"{API_URLS[data_source]}/api/v1/event/{game_id}/lineups")
        return parse_lineups_records(data, country, tournament, season, week, game_id)

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        batches = await asyncio.gather(*[_fetch(client, row) for _, row in match_df.iterrows()])

    records = [rec for batch in batches for rec in batch]
    df = pd.DataFrame(records)
    if df.empty:
        raise DataNotAvailableError("No lineup data found.")

    if enable_json_export or enable_excel_export:
        first = match_df.iloc[0]
        kwargs = dict(
            fn_name="lineups_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=first["season"],
            week_number=first["week"],
        )
        if enable_json_export:
            save_json(data=df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=df, **kwargs, output_dir=output_dir)

    return df


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
    validate_source(data_source)
    validate_df(match_df, "match_df")

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series) -> list:
        country, tournament, season, week, game_id = row[
            ["country", "tournament", "season", "week", "game_id"]
        ]
        data = await client.get(f"{API_URLS[data_source]}/api/v1/event/{game_id}/incidents")
        return parse_substitutions_records(data, country, tournament, season, week, game_id)

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        batches = await asyncio.gather(*[_fetch(client, row) for _, row in match_df.iterrows()])

    records = [rec for batch in batches for rec in batch]
    df = pd.DataFrame(records)
    if df.empty:
        raise DataNotAvailableError("No substitution data found.")

    if enable_json_export or enable_excel_export:
        first = match_df.iloc[0]
        kwargs = dict(
            fn_name="substitutions_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=first["season"],
            week_number=first["week"],
        )
        if enable_json_export:
            save_json(data=df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=df, **kwargs, output_dir=output_dir)

    return df


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
    validate_source(data_source)
    validate_df(match_df, "match_df")

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series) -> list:
        country, tournament, season, week, game_id = row[
            ["country", "tournament", "season", "week", "game_id"]
        ]
        data = await client.get(f"{API_URLS[data_source]}/api/v1/event/{game_id}/incidents")
        return parse_incidents_records(data, country, tournament, season, week, game_id)

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        batches = await asyncio.gather(*[_fetch(client, row) for _, row in match_df.iterrows()])

    records = [rec for batch in batches for rec in batch]
    df = pd.DataFrame(records)
    if df.empty:
        raise DataNotAvailableError("No incident data found.")

    if enable_json_export or enable_excel_export:
        first = match_df.iloc[0]
        kwargs = dict(
            fn_name="incidents_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=first["season"],
            week_number=first["week"],
        )
        if enable_json_export:
            save_json(data=df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=df, **kwargs, output_dir=output_dir)

    return df


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
    validate_source(data_source)
    validate_df(match_df, "match_df")

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series):
        country, tournament, season, week, game_id = row[
            ["country", "tournament", "season", "week", "game_id"]
        ]
        try:
            data = await client.get(f"{API_URLS[data_source]}/api/v1/event/{game_id}")
            return parse_match_details_records(data, country, tournament, season, week, game_id)
        except APIError as exc:
            logger.warning("Failed to fetch details for game_id=%s: %s", game_id, exc)
            return None

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        results = await asyncio.gather(*[_fetch(client, row) for _, row in match_df.iterrows()])

    records = [r for r in results if r is not None]
    df = pd.DataFrame(records)
    if df.empty:
        raise DataNotAvailableError("No match detail data found.")
    _cast_int_cols(df, "referee_id")

    if enable_json_export or enable_excel_export:
        first = match_df.iloc[0]
        kwargs = dict(
            fn_name="match_details_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=first["season"],
            week_number=first["week"],
        )
        if enable_json_export:
            save_json(data=df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=df, **kwargs, output_dir=output_dir)

    return df


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

    teams = standings_df[standings_df["category"] == "Total"]
    seen_game_ids: set = set()
    records = []

    async def _fetch_team(client: AsyncSofascoreClient, team_id) -> list:
        team_records = []
        page = 0
        while True:
            url = f"{API_URLS[data_source]}/api/v1/team/{team_id}/events/next/{page}"
            try:
                data = await client.get(url)
            except APIError:
                break
            team_records.append((data, page))
            if not data.get("hasNextPage", False):
                break
            page += 1
        return team_records

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        all_pages = await asyncio.gather(
            *[_fetch_team(client, row["team_id"]) for _, row in teams.iterrows()]
        )

    for team_pages in all_pages:
        for data, _ in team_pages:
            records.extend(parse_upcoming_matches_records(data, seen_game_ids))

    df = pd.DataFrame(records)
    if df.empty:
        raise DataNotAvailableError("No upcoming match data found.")
    result_df = df.sort_values("start_timestamp").reset_index(drop=True)

    if enable_json_export or enable_excel_export:
        first = standings_df.iloc[0]
        t_id = int(first.get("tournament_id") or 0)
        s_id = int(first.get("season_id") or 0)
        _, _, season_year = resolve_tournament_season(
            t_id, s_id, data_source=data_source, rate_limit=rate_limit
        ) if t_id and s_id else ("", "", None)
        kwargs = dict(
            fn_name="upcoming_matches_data",
            data_source=data_source,
            country=first.get("country", ""),
            tournament=first.get("tournament", ""),
            season=season_year,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

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

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        page = 0
        while True:
            url = f"{API_URLS[data_source]}/api/v1/team/{team_id}/events/last/{page}"
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
        kwargs = dict(
            fn_name="team_match_history_data",
            data_source=data_source,
            country=first.get("country", ""),
            tournament=first.get("tournament", ""),
            season=first.get("season"),
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


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
    validate_source(data_source)
    validate_df(match_df, "match_df")

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series) -> list:
        country, tournament, season, week, game_id = row[
            ["country", "tournament", "season", "week", "game_id"]
        ]
        data = await client.get(f"{API_URLS[data_source]}/api/v1/event/{game_id}/odds/1/all")
        return parse_match_odds_records(data, country, tournament, season, week, game_id)

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        batches = await asyncio.gather(*[_fetch(client, row) for _, row in match_df.iterrows()])

    records = [rec for batch in batches for rec in batch]
    df = pd.DataFrame(records)
    if df.empty:
        raise DataNotAvailableError("No odds data found.")

    if enable_json_export or enable_excel_export:
        first = match_df.iloc[0]
        kwargs = dict(
            fn_name="match_odds_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=first["season"],
            week_number=first["week"],
        )
        if enable_json_export:
            save_json(data=df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=df, **kwargs, output_dir=output_dir)

    return df


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

    async def _fetch(client: AsyncSofascoreClient, category: str) -> list:
        url = (
            f"{API_URLS[data_source]}/api/v1/unique-tournament/{tournament_id}"
            f"/season/{season_id}/standings/{category}"
        )
        data = await client.get(url)
        return parse_standings_rows(data, category, tournament_id, season_id)

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        batches = await asyncio.gather(*[_fetch(client, cat) for cat in ("total", "home", "away")])

    rows = [row for batch in batches for row in batch]
    df = pd.DataFrame(rows)
    if df.empty:
        raise DataNotAvailableError("No standings data found.")

    if enable_json_export or enable_excel_export:
        country, tournament_name, season_year = resolve_tournament_season(
            tournament_id, season_id, data_source=data_source, rate_limit=rate_limit
        )
        first = df.iloc[0]
        kwargs = dict(
            fn_name="standings_data",
            data_source=data_source,
            country=country or first["country"],
            tournament=tournament_name or first["tournament"],
            season=season_year,
        )
        if enable_json_export:
            save_json(data=df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=df, **kwargs, output_dir=output_dir)

    return df


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
    validate_source(data_source)
    validate_df(match_df, "match_df")

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series):
        country, tournament, season, week, game_id = row[
            ["country", "tournament", "season", "week", "game_id"]
        ]
        data = await client.get(f"{API_URLS[data_source]}/api/v1/event/{game_id}/h2h")
        return parse_match_h2h_record(
            data, country, tournament, season, week, game_id,
            row["home_team"], row["away_team"],
        )

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        results = await asyncio.gather(*[_fetch(client, row) for _, row in match_df.iterrows()])

    records = [r for r in results if r is not None]
    df = pd.DataFrame(records)
    if df.empty:
        raise DataNotAvailableError("No H2H data found.")

    if enable_json_export or enable_excel_export:
        first = match_df.iloc[0]
        kwargs = dict(
            fn_name="match_h2h_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=first["season"],
            week_number=first["week"],
        )
        if enable_json_export:
            save_json(data=df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=df, **kwargs, output_dir=output_dir)

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

    country = ""
    tournament_name = str(tournament_id)

    url = f"{API_URLS[data_source]}/api/v1/unique-tournament/{tournament_id}/seasons"
    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        data = await client.get(url)
        if enable_json_export or enable_excel_export:
            try:
                t_data = await client.get(
                    f"{API_URLS[data_source]}/api/v1/unique-tournament/{tournament_id}"
                )
                ut = t_data.get("uniqueTournament", {})
                country = ut.get("category", {}).get("name", "") or ""
                tournament_name = ut.get("name", str(tournament_id)) or str(tournament_id)
            except Exception:
                pass

    seasons = data.get("seasons", [])
    if not seasons:
        raise DataNotAvailableError(f"No seasons found for tournament_id={tournament_id}.")

    result_df = pd.DataFrame(parse_seasons_records(data, tournament_id))

    if enable_json_export or enable_excel_export:
        kwargs = dict(
            fn_name="seasons_data",
            data_source=data_source,
            country=country,
            tournament=tournament_name,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


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
    validate_source(data_source)
    validate_df(match_df, "match_df")

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series) -> list:
        country, tournament, season, week, game_id = row[
            ["country", "tournament", "season", "week", "game_id"]
        ]
        data = await client.get(
            f"{API_URLS[data_source]}/api/v1/event/{game_id}/average-positions"
        )
        return parse_average_positions_records(
            data, country, tournament, season, week, game_id,
            row["home_team"], row["away_team"],
        )

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        batches = await asyncio.gather(*[_fetch(client, row) for _, row in match_df.iterrows()])

    records = [rec for batch in batches for rec in batch]
    df = pd.DataFrame(records)
    if df.empty:
        raise DataNotAvailableError("No average position data found.")

    if enable_json_export or enable_excel_export:
        first = match_df.iloc[0]
        kwargs = dict(
            fn_name="average_positions_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=first["season"],
            week_number=first["week"],
        )
        if enable_json_export:
            save_json(data=df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=df, **kwargs, output_dir=output_dir)

    return df


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

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        while len(records) < max_players:
            url = (
                f"{API_URLS[data_source]}/api/v1/unique-tournament/{tournament_id}"
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

            records.extend(parse_league_player_stats_records(data, tournament_id, season_id, selected_fields))

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
        kwargs = dict(
            fn_name="league_player_stats_data",
            data_source=data_source,
            country=country,
            tournament=tournament,
            season=season,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

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
        kwargs = dict(
            fn_name="search_data",
            data_source=data_source,
            country="",
            tournament=query.strip(),
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


# ---------------------------------------------------------------------------
# Match-level functions (continued)
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

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series) -> list:
        url = (
            f"{API_URLS[data_source]}/api/v1/event/{row['game_id']}"
            f"/player/{row['player_id']}/heatmap"
        )
        async with sem:
            try:
                data = await client.get(url)
            except APIError as exc:
                if exc.status_code in (404, 403):
                    return []
                raise
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

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        batches = await asyncio.gather(*[_fetch(client, row) for _, row in unique_players.iterrows()])

    heatmap_data = [rec for batch in batches for rec in batch]
    result_df = pd.DataFrame(heatmap_data)
    if result_df.empty:
        raise DataNotAvailableError("No heatmap data found for the specified players.")

    if enable_json_export or enable_excel_export:
        first = lineups_df.iloc[0]
        kwargs = dict(
            fn_name="coordinates_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=first["season"],
            week_number=first["week"],
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

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

    def _coord(coords, key):
        return coords.get(key) if isinstance(coords, dict) else None

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series):
        country, tournament, season, week, game_id = row[
            ["country", "tournament", "season", "week", "game_id"]
        ]
        data = await client.get(f"{API_URLS[data_source]}/api/v1/event/{game_id}/incidents")
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
        goalkeeper_name=_safe_apply(raw_df, "goalkeeper", lambda gk: gk.get("name") if isinstance(gk, dict) else None),
        goalkeeper_id=_safe_apply(raw_df, "goalkeeper", lambda gk: gk.get("id") if isinstance(gk, dict) else None),
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

    if enable_json_export or enable_excel_export:
        first = match_df.iloc[0]
        kwargs = dict(
            fn_name="goal_networks_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=first["season"],
            week_number=first["week"],
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


async def past_matches_data(
    tournament_id: int,
    season_id: int,
    week_number: int,
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

        async def _fetch_h2h(custom_id) -> list:
            url = f"{WWW_URLS[data_source]}/api/v1/event/{custom_id}/h2h/events"
            h2h_data = await client.get(url)
            h2h_events = h2h_data.get("events")
            if not isinstance(h2h_events, list):
                return []
            return [
                {
                    "country": ev.get("tournament", {}).get("category", {}).get("name", ""),
                    "tournament": ev.get("tournament", {}).get("name", ""),
                    "season": ev.get("season", {}).get("year", ""),
                    "week": ev.get("roundInfo", {}).get("round", ""),
                    "game_id": ev.get("id", ""),
                    "home_team": ev.get("homeTeam", {}).get("name", ""),
                    "home_team_id": ev.get("homeTeam", {}).get("id", ""),
                    "away_team": ev.get("awayTeam", {}).get("name", ""),
                    "away_team_id": ev.get("awayTeam", {}).get("id", ""),
                    "injury_time_1": ev.get("time", {}).get("injuryTime1"),
                    "injury_time_2": ev.get("time", {}).get("injuryTime2"),
                    "start_timestamp": ev.get("startTimestamp", ""),
                    "status": ev.get("status", {}).get("description", ""),
                    "home_score_current": ev.get("homeScore", {}).get("current", ""),
                    "home_score_display": ev.get("homeScore", {}).get("display", ""),
                    "home_score_period1": ev.get("homeScore", {}).get("period1", ""),
                    "home_score_period2": ev.get("homeScore", {}).get("period2", ""),
                    "home_score_normaltime": ev.get("homeScore", {}).get("normaltime", ""),
                    "away_score_current": ev.get("awayScore", {}).get("current", ""),
                    "away_score_display": ev.get("awayScore", {}).get("display", ""),
                    "away_score_period1": ev.get("awayScore", {}).get("period1", ""),
                    "away_score_period2": ev.get("awayScore", {}).get("period2", ""),
                    "away_score_normaltime": ev.get("awayScore", {}).get("normaltime", ""),
                }
                for ev in h2h_events
            ]

        batches = await asyncio.gather(*[_fetch_h2h(cid) for cid in custom_ids])

    all_matches = [match for batch in batches for match in batch]
    if not all_matches:
        raise DataNotAvailableError(
            f"No H2H match data found for tournament_id={tournament_id}, "
            f"season_id={season_id}, week_number={week_number}."
        )
    result_df = pd.DataFrame(all_matches)

    if enable_json_export or enable_excel_export:
        kwargs = dict(
            fn_name="past_matches_data",
            data_source=data_source,
            country=fn_country,
            tournament=fn_tournament,
            season=fn_season,
            week_number=week_number,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


# ---------------------------------------------------------------------------
# Season / roster functions
# ---------------------------------------------------------------------------


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

    teams = standings_df[standings_df["category"] == "Total"]

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series):
        team_id = row["team_id"]
        team_name = row["team_name"]
        url = f"{API_URLS[data_source]}/api/v1/team/{team_id}/players"
        try:
            data = await client.get(url)
            players = []
            for p in data.get("players", []):
                player = p.get("player")
                if not player:
                    continue
                players.append({
                    "country": row["country"],
                    "tournament": row["tournament"],
                    "tournament_id": row.get("tournament_id", 0),
                    "season_id": row.get("season_id", 0),
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
            return players, None
        except APIError as exc:
            logger.warning(
                "Failed to fetch squad data for team_id=%s (%s): %s",
                team_id, team_name, exc,
            )
            return [], team_id

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        results = await asyncio.gather(*[_fetch(client, row) for _, row in teams.iterrows()])

    squad_list, failed_teams = [], []
    for players, failed_id in results:
        squad_list.extend(players)
        if failed_id is not None:
            failed_teams.append(failed_id)

    if failed_teams:
        logger.warning("Could not retrieve squad for %d team(s): %s", len(failed_teams), failed_teams)

    result_df = pd.DataFrame(squad_list)
    if result_df.empty:
        raise DataNotAvailableError("No squad data found for the specified teams.")

    if enable_json_export or enable_excel_export:
        first = standings_df.iloc[0]
        t_id = int(first.get("tournament_id") or 0)
        s_id = int(first.get("season_id") or 0)
        _, _, season_year = resolve_tournament_season(
            t_id, s_id, data_source=data_source, rate_limit=rate_limit
        ) if t_id and s_id else ("", "", None)
        kwargs = dict(
            fn_name="squad_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=season_year,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

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

    teams = standings_df[standings_df["category"] == "Total"]

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series):
        team_id = row["team_id"]
        team_name = row["team_name"]
        url = (
            f"{WWW_URLS[data_source]}/api/v1/team/{team_id}"
            f"/unique-tournament/{tournament_id}/season/{season_id}/top-players/overall"
        )
        try:
            data = await client.get(url)
            stats = [
                {
                    "country": row["country"],
                    "tournament": row["tournament"],
                    "team_name": team_name,
                    "team_id": team_id,
                    "player_name": player_data.get("player", {}).get("name"),
                    "player_id": player_data.get("player", {}).get("id"),
                    "position": player_data.get("player", {}).get("position"),
                    "stat_name": stat,
                    "stat_value": value,
                }
                for players in data.get("topPlayers", {}).values()
                for player_data in players
                for stat, value in player_data.get("statistics", {}).items()
                if stat not in ("id", "type") and not isinstance(value, (dict, list))
            ]
            return stats, None
        except APIError as exc:
            logger.warning(
                "Failed to fetch player stats for team_id=%s (%s): %s",
                team_id, team_name, exc,
            )
            return [], team_id

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        results = await asyncio.gather(*[_fetch(client, row) for _, row in teams.iterrows()])

    stats_list, failed_teams = [], []
    for stats, failed_id in results:
        stats_list.extend(stats)
        if failed_id is not None:
            failed_teams.append(failed_id)

    if failed_teams:
        logger.warning(
            "Could not retrieve player stats for %d team(s): %s", len(failed_teams), failed_teams
        )

    result_df = pd.DataFrame(stats_list).drop_duplicates(
        subset=["team_id", "player_id", "stat_name"]
    )
    if result_df.empty:
        raise DataNotAvailableError("No player statistics data found for the specified teams.")

    if enable_json_export or enable_excel_export:
        country, tournament_name, season_year = resolve_tournament_season(
            tournament_id, season_id, data_source=data_source, rate_limit=rate_limit
        )
        first = result_df.iloc[0]
        kwargs = dict(
            fn_name="player_stats_data",
            data_source=data_source,
            country=country or first["country"],
            tournament=tournament_name or first["tournament"],
            season=season_year,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


async def team_stats_data(
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
    """Async version of team_stats_data(). All team requests run in parallel."""
    validate_source(data_source)
    validate_df(standings_df, "standings_df")

    teams = standings_df[standings_df["category"] == "Total"]

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series):
        team_id = row["team_id"]
        team_name = row["team_name"]
        url = (
            f"{WWW_URLS[data_source]}/api/v1/team/{team_id}"
            f"/unique-tournament/{tournament_id}/season/{season_id}/statistics/overall"
        )
        try:
            data = await client.get(url)
            stats = [
                {
                    "country": row["country"],
                    "tournament": row["tournament"],
                    "team_name": team_name,
                    "team_id": team_id,
                    "stat": stat,
                    "value": value,
                }
                for stat, value in data.get("statistics", {}).items()
                if stat not in {"country", "tournament", "team_name", "team_id"}
                and not isinstance(value, (dict, list))
            ]
            return stats, None
        except APIError as exc:
            logger.warning(
                "Failed to fetch team stats for team_id=%s (%s): %s",
                team_id, team_name, exc,
            )
            return [], team_id

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        results = await asyncio.gather(*[_fetch(client, row) for _, row in teams.iterrows()])

    stats_list, failed_teams = [], []
    for stats, failed_id in results:
        stats_list.extend(stats)
        if failed_id is not None:
            failed_teams.append(failed_id)

    if failed_teams:
        logger.warning(
            "Could not retrieve stats for %d team(s): %s", len(failed_teams), failed_teams
        )

    result_df = pd.DataFrame(stats_list)
    if result_df.empty:
        raise DataNotAvailableError("No team statistics data found for the specified teams.")

    if enable_json_export or enable_excel_export:
        country, tournament_name, season_year = resolve_tournament_season(
            tournament_id, season_id, data_source=data_source, rate_limit=rate_limit
        )
        first = result_df.iloc[0]
        kwargs = dict(
            fn_name="team_stats_data",
            data_source=data_source,
            country=country or first["country"],
            tournament=tournament_name or first["tournament"],
            season=season_year,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


# ---------------------------------------------------------------------------
# New player-level functions
# ---------------------------------------------------------------------------

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

    unique_players = squad_df[["player_id", "player_name"]].drop_duplicates()

    async def _fetch(client: AsyncSofascoreClient, player_id, player_name):
        try:
            seasons_data = await client.get(
                f"{API_URLS[data_source]}/api/v1/player/{player_id}/statistics/seasons"
            )
            records = []
            for entry in seasons_data.get("uniqueTournamentSeasons", []):
                tournament = entry.get("uniqueTournament", {})
                tid = tournament.get("id")
                for season in entry.get("seasons", []):
                    sid = season.get("id")
                    try:
                        stats_data = await client.get(
                            f"{API_URLS[data_source]}/api/v1/player/{player_id}"
                            f"/unique-tournament/{tid}/season/{sid}/statistics/overall"
                        )
                    except APIError:
                        continue
                    team = stats_data.get("team", {})
                    for stat_name, stat_value in stats_data.get("statistics", {}).items():
                        if isinstance(stat_value, (dict, list)):
                            continue
                        records.append({
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
            return records, None
        except APIError as exc:
            logger.warning(
                "Failed to fetch career stats for player_id=%s (%s): %s",
                player_id, player_name, exc,
            )
            return [], player_id

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        results = await asyncio.gather(*[
            _fetch(client, row["player_id"], row["player_name"])
            for _, row in unique_players.iterrows()
        ])

    all_records, failed = [], []
    for records, failed_id in results:
        all_records.extend(records)
        if failed_id is not None:
            failed.append(failed_id)

    if failed:
        logger.warning("Could not retrieve career stats for %d player(s): %s", len(failed), failed)

    result_df = pd.DataFrame(all_records)
    if result_df.empty:
        raise DataNotAvailableError("No career stats data found for the specified players.")
    _cast_int_cols(result_df, "team_id")

    if enable_json_export or enable_excel_export:
        first = squad_df.iloc[0]
        kwargs = dict(
            fn_name="player_career_stats_data",
            data_source=data_source,
            country=first.get("country", "unknown"),
            tournament=first.get("tournament", "unknown"),
            season=None,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


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
    _TRANSFER_TYPES = {1: "loan", 2: "permanent", 3: "free", 4: "end_of_contract"}

    validate_source(data_source)
    validate_df(squad_df, "squad_df")

    unique_players = squad_df[["player_id", "player_name"]].drop_duplicates()

    async def _fetch(client: AsyncSofascoreClient, player_id, player_name):
        url = f"{API_URLS[data_source]}/api/v1/player/{player_id}/transfer-history"
        try:
            data = await client.get(url)
            records = []
            for transfer in data.get("transferHistory", []):
                date_ts = transfer.get("transferDate")
                fee_raw = transfer.get("transferFee")
                records.append({
                    "player_id": player_id,
                    "player_name": player_name,
                    "transfer_date": (
                        datetime.fromtimestamp(date_ts, tz=timezone.utc).strftime("%Y-%m-%d")
                        if date_ts else None
                    ),
                    "from_team_id": (transfer.get("transferFrom") or {}).get("id"),
                    "from_team_name": (transfer.get("transferFrom") or {}).get("name"),
                    "to_team_id": (transfer.get("transferTo") or {}).get("id"),
                    "to_team_name": (transfer.get("transferTo") or {}).get("name"),
                    "transfer_type": _TRANSFER_TYPES.get(transfer.get("type"), "unknown"),
                    "fee": fee_raw.get("value") if isinstance(fee_raw, dict) else None,
                    "fee_currency": fee_raw.get("currency") if isinstance(fee_raw, dict) else None,
                })
            return records, None
        except APIError as exc:
            logger.warning(
                "Failed to fetch transfers for player_id=%s (%s): %s",
                player_id, player_name, exc,
            )
            return [], player_id

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        results = await asyncio.gather(*[
            _fetch(client, row["player_id"], row["player_name"])
            for _, row in unique_players.iterrows()
        ])

    all_records, failed = [], []
    for records, failed_id in results:
        all_records.extend(records)
        if failed_id is not None:
            failed.append(failed_id)

    if failed:
        logger.warning("Could not retrieve transfers for %d player(s): %s", len(failed), failed)

    result_df = pd.DataFrame(all_records)
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
        kwargs = dict(
            fn_name="player_transfers_data",
            data_source=data_source,
            country=first.get("country", "unknown"),
            tournament=first.get("tournament", "unknown"),
            season=season_year,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


# ---------------------------------------------------------------------------
# New league / season functions
# ---------------------------------------------------------------------------


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
    _TRANSFER_TYPES = {1: "loan", 2: "permanent", 3: "free", 4: "end_of_contract"}

    validate_source(data_source)
    validate_df(standings_df, "standings_df")

    teams = standings_df[standings_df["category"] == "Total"]

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series):
        team_id = row["team_id"]
        team_name = row["team_name"]
        url = f"{API_URLS[data_source]}/api/v1/team/{team_id}/transfers"
        try:
            data = await client.get(url)
            records = []
            for direction in ("transfersIn", "transfersOut"):
                dir_label = "in" if direction == "transfersIn" else "out"
                for transfer in data.get(direction, []):
                    player = transfer.get("player", {})
                    date_ts = transfer.get("transferDate")
                    fee_raw = transfer.get("transferFee")
                    records.append({
                        "country": row["country"],
                        "tournament": row["tournament"],
                        "team_name": team_name,
                        "team_id": team_id,
                        "direction": dir_label,
                        "player_id": player.get("id"),
                        "player_name": player.get("name"),
                        "transfer_date": (
                            datetime.fromtimestamp(date_ts, tz=timezone.utc).strftime("%Y-%m-%d")
                            if date_ts else None
                        ),
                        "from_team_id": (transfer.get("transferFrom") or {}).get("id"),
                        "from_team_name": (transfer.get("transferFrom") or {}).get("name"),
                        "to_team_id": (transfer.get("transferTo") or {}).get("id"),
                        "to_team_name": (transfer.get("transferTo") or {}).get("name"),
                        "transfer_type": _TRANSFER_TYPES.get(transfer.get("type"), "unknown"),
                        "fee": fee_raw.get("value") if isinstance(fee_raw, dict) else None,
                        "fee_currency": fee_raw.get("currency") if isinstance(fee_raw, dict) else None,
                    })
            return records, None
        except APIError as exc:
            logger.warning(
                "Failed to fetch transfers for team_id=%s (%s): %s",
                team_id, team_name, exc,
            )
            return [], team_id

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        results = await asyncio.gather(*[_fetch(client, row) for _, row in teams.iterrows()])

    all_records, failed = [], []
    for records, failed_id in results:
        all_records.extend(records)
        if failed_id is not None:
            failed.append(failed_id)

    if failed:
        logger.warning("Could not retrieve transfers for %d team(s): %s", len(failed), failed)

    result_df = pd.DataFrame(all_records)
    if result_df.empty:
        raise DataNotAvailableError("No transfer data found for the specified teams.")
    _cast_int_cols(result_df, "from_team_id", "to_team_id")

    if enable_json_export or enable_excel_export:
        first = standings_df.iloc[0]
        kwargs = dict(
            fn_name="team_transfers_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=None,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


# ---------------------------------------------------------------------------
# New match-level function
# ---------------------------------------------------------------------------

async def pregame_form_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of pregame_form_data(). All match requests run in parallel."""
    validate_source(data_source)
    validate_df(match_df, "match_df")

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series) -> list:
        country, tournament, season, week, game_id = row[
            ["country", "tournament", "season", "week", "game_id"]
        ]
        try:
            data = await client.get(f"{API_URLS[data_source]}/api/v1/event/{game_id}/pregame-form")
        except APIError as exc:
            logger.warning("Failed to fetch pregame form for game_id=%s: %s", game_id, exc)
            return []
        records = []
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
            records.append(form_row)
        return records

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        batches = await asyncio.gather(*[_fetch(client, row) for _, row in match_df.iterrows()])

    records = [rec for batch in batches for rec in batch]
    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No pre-game form data found for the specified matches.")

    for col in ("avg_rating", "value", "position"):
        if col in result_df.columns:
            result_df[col] = pd.to_numeric(result_df[col], errors="coerce")

    if enable_json_export or enable_excel_export:
        first = match_df.iloc[0]
        kwargs = dict(
            fn_name="pregame_form_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=first["season"],
            week_number=first["week"],
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


# ---------------------------------------------------------------------------
# Player match log
# ---------------------------------------------------------------------------

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

    async def _fetch(client: AsyncSofascoreClient, player_id, player_name) -> list:
        page = 0
        records = []
        while True:
            url = (
                f"{API_URLS[data_source]}/api/v1/player/{player_id}"
                f"/events/last/{page}"
            )
            try:
                data = await client.get(url)
            except APIError as exc:
                logger.warning(
                    "Failed to fetch match log for player_id=%s (%s): %s",
                    player_id, player_name, exc,
                )
                break
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
                records.append(row)
            if not data.get("hasNextPage", False):
                break
            page += 1
        return records

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
        kwargs = dict(
            fn_name="player_match_log_data",
            data_source=data_source,
            country=first.get("country", ""),
            tournament=first.get("tournament", ""),
            season=result_df.iloc[0].get("season"),
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


# ---------------------------------------------------------------------------
# Referee stats
# ---------------------------------------------------------------------------

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

    url = f"{API_URLS[data_source]}/api/v1/referee/{referee_id}/statistics"

    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        data = await client.get(url)
        if enable_json_export or enable_excel_export:
            try:
                r_data = await client.get(f"{API_URLS[data_source]}/api/v1/referee/{referee_id}")
                referee_name = (r_data.get("referee") or {}).get("name", str(referee_id)) or str(referee_id)
            except Exception:
                pass
    statistics = data.get("statistics", [])

    if not statistics:
        raise DataNotAvailableError(f"No statistics found for referee_id={referee_id}.")

    records = []
    for entry in statistics:
        tournament = entry.get("uniqueTournament", {})
        for stat_name, stat_value in entry.items():
            if stat_name == "uniqueTournament" or isinstance(stat_value, (dict, list)):
                continue
            records.append({
                "referee_id": referee_id,
                "referee_name": referee_name,
                "tournament_id": tournament.get("id"),
                "tournament_name": tournament.get("name"),
                "stat": stat_name,
                "value": stat_value,
            })

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError(f"No statistics found for referee_id={referee_id}.")

    if enable_json_export or enable_excel_export:
        kwargs = dict(
            fn_name="referee_stats_data",
            data_source=data_source,
            country="",
            tournament=referee_name,
            season=None,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


# ---------------------------------------------------------------------------
# Player national team stats
# ---------------------------------------------------------------------------

async def player_national_team_data(
    squad_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of player_national_team_data(). All players fetched in parallel."""
    validate_source(data_source)
    validate_df(squad_df, "squad_df")

    async def _fetch(client: AsyncSofascoreClient, player_id, player_name) -> list:
        url = f"{API_URLS[data_source]}/api/v1/player/{player_id}/national-team-statistics"
        try:
            data = await client.get(url)
            records = []
            for entry in data.get("statistics", []):
                team = entry.get("team", {})
                records.append({
                    "player_id": player_id,
                    "player_name": player_name,
                    "team_id": team.get("id"),
                    "team_name": team.get("name"),
                    "team_code": team.get("nameCode"),
                    "appearances": entry.get("appearances"),
                    "goals": entry.get("goals"),
                    "debut_timestamp": entry.get("debutTimestamp"),
                })
            return records
        except APIError as exc:
            logger.warning(
                "Failed to fetch national team stats for player_id=%s (%s): %s",
                player_id, player_name, exc,
            )
            return []

    unique_players = squad_df[["player_id", "player_name"]].drop_duplicates()
    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        batches = await asyncio.gather(*[
            _fetch(client, row["player_id"], row["player_name"])
            for _, row in unique_players.iterrows()
        ])

    records = [rec for batch in batches for rec in batch]
    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No national team data found for the specified players.")

    if enable_json_export or enable_excel_export:
        first = squad_df.iloc[0]
        kwargs = dict(
            fn_name="player_national_team_data",
            data_source=data_source,
            country=first.get("country", "unknown"),
            tournament=first.get("tournament", "unknown"),
            season=None,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


# ---------------------------------------------------------------------------
# Player profile
# ---------------------------------------------------------------------------

async def player_data(
    squad_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional[DiskCache] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Async version of player_data(). All players fetched in parallel."""
    validate_source(data_source)
    validate_df(squad_df, "squad_df")

    async def _fetch(client: AsyncSofascoreClient, player_id, player_name) -> list:
        url = f"{API_URLS[data_source]}/api/v1/player/{player_id}"
        try:
            data = await client.get(url)
            p = data.get("player") or {}
            if not p:
                return []
            country = p.get("country") or {}
            team = p.get("team") or {}
            dob_ts = p.get("dateOfBirthTimestamp")
            mv_raw = p.get("proposedMarketValueRaw") or {}
            return [{
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
            }]
        except APIError as exc:
            logger.warning(
                "Failed to fetch profile for player_id=%s (%s): %s",
                player_id, player_name, exc,
            )
            return []

    unique_players = squad_df[["player_id", "player_name"]].drop_duplicates()
    async with AsyncSofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        batches = await asyncio.gather(*[
            _fetch(client, row["player_id"], row["player_name"])
            for _, row in unique_players.iterrows()
        ])

    records = [rec for batch in batches for rec in batch]
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
        kwargs = dict(
            fn_name="player_data",
            data_source=data_source,
            country=first.get("country", "unknown"),
            tournament=first.get("tournament", "unknown"),
            season=season_year,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


# ---------------------------------------------------------------------------
# Team profile
# ---------------------------------------------------------------------------

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

    teams = standings_df[standings_df["category"] == "Total"]

    async def _fetch(client: AsyncSofascoreClient, row: pd.Series):
        team_id = row["team_id"]
        team_name = row["team_name"]
        url = f"{API_URLS[data_source]}/api/v1/team/{team_id}"
        try:
            data = await client.get(url)
            t = data.get("team") or {}
            if not t:
                return None, team_id
            country = t.get("country") or {}
            venue = t.get("venue") or {}
            stadium = venue.get("stadium") or {}
            manager = t.get("manager") or {}
            colors = t.get("teamColors") or {}
            return {
                "country": row["country"],
                "tournament": row["tournament"],
                "team_id": team_id,
                "team_name": t.get("name") or team_name,
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
            }, None
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
        kwargs = dict(
            fn_name="team_data",
            data_source=data_source,
            country=first.get("country", "unknown"),
            tournament=first.get("tournament", "unknown"),
            season=season_year,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df


# ---------------------------------------------------------------------------
# Season rounds
# ---------------------------------------------------------------------------

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
    """Async version of season_rounds_data(). Single request."""
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

    records = [
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

    result_df = pd.DataFrame(records)

    if enable_json_export or enable_excel_export:
        country, tournament_name, season_year = resolve_tournament_season(
            tournament_id, season_id, data_source=data_source, rate_limit=rate_limit
        )
        kwargs = dict(
            fn_name="season_rounds_data",
            data_source=data_source,
            country=country,
            tournament=tournament_name,
            season=season_year,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df

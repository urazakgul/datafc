from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._save_files import save_json, save_excel
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source
from datafc.utils._tournament_info import resolve_tournament_season
from datafc.sofascore._parsers import parse_league_player_stats_records
from datafc.exceptions import InvalidParameterError, DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache

AVAILABLE_FIELDS = {
    "goals", "assists", "rating", "expectedGoals", "expectedAssists",
    "goalsAssistsSum", "penaltyGoals", "freeKickGoal", "scoringFrequency",
    "totalShots", "shotsOnTarget", "bigChancesCreated", "bigChancesMissed",
    "accuratePasses", "accuratePassesPercentage", "keyPasses",
    "accurateLongBalls", "accurateLongBallsPercentage",
    "successfulDribbles", "successfulDribblesPercentage",
    "tackles", "interceptions", "clearances", "possessionLost",
    "yellowCards", "redCards", "saves", "goalsPrevented",
    "minutesPlayed", "appearances",
}

AVAILABLE_ACCUMULATIONS = {"total", "per90", "perMatch"}

DEFAULT_FIELDS = [
    "goals", "assists", "rating", "expectedGoals", "expectedAssists",
    "totalShots", "shotsOnTarget", "keyPasses", "successfulDribbles",
    "tackles", "yellowCards", "redCards", "minutesPlayed", "appearances",
]


def league_player_stats_data(
    tournament_id: int,
    season_id: int,
    order: str = "-rating",
    accumulation: str = "total",
    fields: Optional[list] = None,
    position: Optional[str] = None,
    max_players: int = 100,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """
    Fetches league-wide player statistics ranked by a chosen metric.

    Unlike season_top_players_data (which returns top 50 per category in long
    format), this function returns a wide-format table where each row is a
    player and each column is a requested stat field. Supports pagination to
    retrieve more than the default API page size.

    Args:
        tournament_id: The unique identifier for the tournament.
        season_id: The unique identifier for the season.
        order: Field to sort by, prefix with '-' for descending (e.g. '-goals',
               '-rating', 'assists'). Defaults to '-rating'.
        accumulation: How stats are aggregated: 'total', 'per90', or 'perMatch'.
                      Defaults to 'total'.
        fields: List of stat fields to include. If None, uses a default set of
                14 common fields. See AVAILABLE_FIELDS for all options.
        position: Filter by position: 'G' (goalkeeper), 'D' (defender),
                  'M' (midfielder), 'F' (forward). If None, all positions.
        max_players: Maximum number of players to return. Fetches multiple API
                     pages if needed. Defaults to 100.
        data_source: The data source ('sofavpn' or 'sofascore'). Defaults to 'sofascore'.
        rate_limit: Maximum requests per second. Defaults to 2.0.
        cache: Optional DiskCache instance. Cached responses skip the API call.
        enable_json_export: If True, saves output as JSON. Defaults to False.
        enable_excel_export: If True, saves output as Excel. Defaults to False.

    Returns:
        Wide-format DataFrame with columns: tournament_id, season_id,
        player_name, player_id, team_name, team_id,
        + one column per requested stat field.

    Raises:
        InvalidParameterError: If invalid parameters are given.
        DataNotAvailableError: If no player stats are found.
        APIError: On HTTP errors from the Sofascore API.
    """
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

    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        while len(records) < max_players:
            url = (
                f"{API_URLS[data_source]}/api/v1/unique-tournament/{tournament_id}"
                f"/season/{season_id}/statistics"
                f"?limit={page_size}&order={order}&accumulation={accumulation}"
                f"&fields={fields_param}&page={page}"
            )
            if position is not None:
                url += f"&filters=position.in.{position}"

            data = client.get(url)
            page_records = parse_league_player_stats_records(
                data, tournament_id, season_id, selected_fields
            )
            if not page_records:
                break
            records.extend(page_records)

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

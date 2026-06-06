from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source
from datafc.utils._tournament_info import resolve_tournament_season
from datafc.sofascore._parsers import parse_league_player_stats_records
from datafc.sofascore._core import export_df
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


def _validate_lps_params(accumulation, position, fields, order):
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
    return selected_fields, fields_param


def _build_lps_url(base, tournament_id, season_id, page_size, order, accumulation,
                   fields_param, page, position):
    url = (
        f"{base}/api/v1/unique-tournament/{tournament_id}"
        f"/season/{season_id}/statistics"
        f"?limit={page_size}&order={order}&accumulation={accumulation}"
        f"&fields={fields_param}&page={page}"
    )
    if position is not None:
        url += f"&filters=position.in.{position}"
    return url


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
    """Fetches league-wide player statistics ranked by a chosen metric."""
    validate_source(data_source)
    selected_fields, fields_param = _validate_lps_params(accumulation, position, fields, order)

    page_size = min(max_players, 100)
    records = []
    page = 1
    base = API_URLS[data_source]

    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        while len(records) < max_players:
            url = _build_lps_url(
                base, tournament_id, season_id, page_size, order, accumulation,
                fields_param, page, position,
            )
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
        export_df(
            result_df, fn_name="league_player_stats_data", data_source=data_source,
            output_dir=output_dir,
            country=country, tournament=tournament, season=season,
            include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df

from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source, build_tournament_url
from datafc.sofascore._parsers import parse_match_events
from datafc.sofascore._core import (
    needs_world_cup_resolution,
    resolve_world_cup_week_sync,
    export_df,
)
from datafc.exceptions import DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def match_data(
    tournament_id: int,
    season_id: int,
    week_number: Optional[int] = None,
    tournament_type: Optional[str] = None,
    tournament_stage: Optional[str] = None,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """
    Fetches match data for a specified tournament, season, and matchweek.

    Args:
        tournament_id: The unique identifier for the tournament.
        season_id: The unique identifier for the season.
        week_number: The matchweek number within the season.
        tournament_type: The tournament type ('uefa', 'world_cup'). If None, assumes league format.
        tournament_stage: The specific stage of the tournament (e.g., 'group_stage_week', 'round_of_16').
        data_source: 'sofavpn' or 'sofascore'. Defaults to 'sofascore'.
        rate_limit: Maximum requests per second.
        cache: Optional DiskCache. Cached responses skip the API call.
        enable_json_export / enable_excel_export: Export switches.
        output_dir: Directory where exported files are written.

    Returns:
        Match data with columns for teams, scores, status, and timestamps.

    Raises:
        InvalidParameterError, DataNotAvailableError, APIError.
    """
    validate_source(data_source)

    if needs_world_cup_resolution(tournament_type, tournament_stage, week_number):
        with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
            week_number = resolve_world_cup_week_sync(
                client, tournament_id, season_id, tournament_stage, data_source,
            )

    url = build_tournament_url(
        API_URLS[data_source], tournament_id, season_id, week_number,
        tournament_type, tournament_stage,
    )

    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        data = client.get(url)

    events = data.get("events")
    if not isinstance(events, list) or not events:
        raise DataNotAvailableError(
            f"No match data found for tournament_id={tournament_id}, "
            f"season_id={season_id}, week_number={week_number}."
        )

    match_data_df = parse_match_events(events)

    export_df(
        match_data_df, fn_name="match_data", data_source=data_source,
        output_dir=output_dir,
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
    )
    return match_data_df

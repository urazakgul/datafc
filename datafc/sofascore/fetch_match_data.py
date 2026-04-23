from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._save_files import save_json, save_excel
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source, build_tournament_url
from datafc.sofascore._parsers import parse_match_events
from datafc.exceptions import DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def match_data(
    tournament_id: int,
    season_id: int,
    week_number: int,
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
        tournament_type: The tournament type ('uefa'). If None, assumes league format.
        tournament_stage: The specific stage of the tournament (e.g., 'group_stage_week', 'round_of_16').
        data_source: The data source ('sofavpn' or 'sofascore'). Defaults to 'sofascore'.
        rate_limit: Maximum requests per second. Defaults to 2.0.
        cache: Optional DiskCache instance. Cached responses skip the API call.
        enable_json_export: If True, exports the fetched data as a JSON file. Defaults to False.
        enable_excel_export: If True, exports the fetched data as an Excel file. Defaults to False.
        output_dir: Directory where exported files are written. Defaults to '.'.

    Returns:
        Match data with columns for teams, scores, status, and timestamps.

    Raises:
        InvalidParameterError: If an invalid data_source, tournament_type, or tournament_stage is given.
        DataNotAvailableError: If no match data is returned for the given parameters.
        APIError: On HTTP errors from the Sofascore API.
    """
    validate_source(data_source)
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

    if enable_json_export or enable_excel_export:
        first = match_data_df.iloc[0]
        kwargs = dict(
            fn_name="match_data",
            data_source=data_source,
            country=first["country"],
            tournament=first["tournament"],
            season=first["season"],
            week_number=first["week"],
        )
        if enable_json_export:
            save_json(data=match_data_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=match_data_df, **kwargs, output_dir=output_dir)

    return match_data_df

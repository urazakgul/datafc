import logging
from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._save_files import save_json, save_excel
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source
from datafc.utils._helpers import _cast_int_cols
from datafc.sofascore._parsers import parse_team_match_history_records
from datafc.exceptions import APIError, DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache

logger = logging.getLogger(__name__)


def team_match_history_data(
    team_id: int,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """
    Fetches the complete match history for a single team across all competitions.

    Paginates through all available history pages until no further pages exist.
    The team_id can be obtained from standings_data(), squad_data(), or search_data().

    Args:
        team_id: The unique Sofascore identifier for the team.
        data_source: The data source ('sofavpn' or 'sofascore'). Defaults to 'sofascore'.
        rate_limit: Maximum requests per second. Defaults to 2.0.
        cache: Optional DiskCache instance. Cached responses skip the API call.
        enable_json_export: If True, saves output as JSON. Defaults to False.
        enable_excel_export: If True, saves output as Excel. Defaults to False.
        output_dir: Directory for exported files. Defaults to current directory.

    Returns:
        Past matches with country, tournament, season, week, home/away team names,
        IDs, scores, start timestamp and status; sorted by start_timestamp ascending.

    Raises:
        InvalidParameterError: If an invalid data_source is given.
        DataNotAvailableError: If no historical match data is found for the team.
        APIError: On HTTP errors from the Sofascore API.
    """
    validate_source(data_source)

    seen_game_ids: set = set()
    records = []
    page = 0

    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        while True:
            url = f"{API_URLS[data_source]}/api/v1/team/{team_id}/events/last/{page}"
            try:
                data = client.get(url)
            except APIError as exc:
                logger.warning(
                    "Failed to fetch match history for team_id=%s page=%s: %s",
                    team_id, page, exc,
                )
                break

            batch = parse_team_match_history_records(data, seen_game_ids)
            records.extend(batch)

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

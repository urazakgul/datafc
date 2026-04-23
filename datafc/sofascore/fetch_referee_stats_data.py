import logging
from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._save_files import save_json, save_excel
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source
from datafc.exceptions import DataNotAvailableError

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def referee_stats_data(
    referee_id: int,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """
    Fetches career statistics for a referee.

    The referee_id can be obtained from the referee_id column in match_details_data() output.

    Args:
        referee_id: The unique Sofascore identifier for the referee.
        data_source: The data source ('sofavpn' or 'sofascore'). Defaults to 'sofascore'.
        rate_limit: Maximum requests per second. Defaults to 2.0.
        cache: Optional DiskCache instance. Cached responses skip the API call.
        enable_json_export: If True, saves output as JSON. Defaults to False.
        enable_excel_export: If True, saves output as Excel. Defaults to False.
        output_dir: Directory where exported files are written. Defaults to '.'.

    Returns:
        DataFrame with columns: referee_id, referee_name, tournament_id,
        tournament_name, stat, value. Covers total games, yellow cards,
        red cards, and per-game averages.

    Raises:
        InvalidParameterError: If an invalid data_source is given.
        DataNotAvailableError: If no statistics are found for the referee.
        APIError: On HTTP errors from the Sofascore API.
    """
    validate_source(data_source)

    referee_name = str(referee_id)

    url = f"{API_URLS[data_source]}/api/v1/referee/{referee_id}/statistics"

    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        data = client.get(url)
        if enable_json_export or enable_excel_export:
            try:
                r_data = client.get(f"{API_URLS[data_source]}/api/v1/referee/{referee_id}")
                referee_name = r_data.get("referee", {}).get("name", str(referee_id)) or str(referee_id)
            except Exception as e:
                logger.warning("Could not fetch referee name for id=%s: %s", referee_id, e)
    statistics = data.get("statistics", [])

    if not statistics:
        raise DataNotAvailableError(
            f"No statistics found for referee_id={referee_id}."
        )

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
        raise DataNotAvailableError(
            f"No statistics found for referee_id={referee_id}."
        )

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

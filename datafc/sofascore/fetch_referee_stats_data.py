import logging
from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source
from datafc.sofascore._core import referee_stats_records, export_df
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
    """Fetches career statistics for a referee."""
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

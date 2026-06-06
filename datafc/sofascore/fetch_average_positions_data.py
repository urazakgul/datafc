from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._validate import validate_source, validate_df
from datafc.sofascore._parsers import parse_average_positions_records
from datafc.sofascore._core import iter_per_match_sync, export_df
from datafc.exceptions import DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def average_positions_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Fetches average positional data (X/Y coordinates) for each player in a match."""
    validate_source(data_source)
    validate_df(match_df, "match_df")

    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        records = iter_per_match_sync(
            match_df, client,
            data_source=data_source,
            endpoint="{base}/api/v1/event/{game_id}/average-positions",
            parser=parse_average_positions_records,
            extra_args_fn=lambda row: (row["home_team"], row["away_team"]),
            log_label="average positions",
        )

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No average position data found for the specified matches.")

    export_df(
        result_df, fn_name="average_positions_data", data_source=data_source,
        output_dir=output_dir,
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
    )
    return result_df

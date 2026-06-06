from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source, validate_df
from datafc.sofascore._core import heatmap_records, export_df
from datafc.exceptions import APIError, DataNotAvailableError, InvalidParameterError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def coordinates_data(
    lineups_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Fetches heatmap coordinate data for each player in the provided lineup dataset.

    Players with no heatmap data (404/403) are silently skipped.
    """
    validate_source(data_source)
    validate_df(lineups_df, "lineups_df")

    unique_players = lineups_df[[
        "country", "tournament", "season", "week", "game_id", "team", "player_id", "player_name"
    ]].drop_duplicates()

    if unique_players.empty:
        raise InvalidParameterError("No unique players found in lineups_df.")

    heatmap_data = []
    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        for _, row in unique_players.iterrows():
            url = (
                f"{API_URLS[data_source]}/api/v1/event/{row['game_id']}"
                f"/player/{row['player_id']}/heatmap"
            )
            try:
                data = client.get(url)
            except APIError as exc:
                if exc.status_code in (404, 403):
                    continue
                raise
            heatmap_data.extend(heatmap_records(data, row))

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

from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source, validate_df
from datafc.sofascore._core import rating_breakdown_records, export_df
from datafc.exceptions import APIError, DataNotAvailableError, InvalidParameterError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def rating_breakdown_data(
    lineups_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Fetches rating-breakdown action data for each player in the provided lineup dataset.

    The endpoint returns four buckets — passes, dribbles, defensive actions and
    ball carries — each with start (and optionally end) coordinates plus outcome
    flags (``outcome``, ``keypass``, ``isAssist``, ``isLongBall``). Rows are
    flattened so each action becomes a single record tagged with ``category``.

    Players with no rating breakdown data (404/403) are silently skipped.
    """
    validate_source(data_source)
    validate_df(lineups_df, "lineups_df")

    unique_players = lineups_df[[
        "country", "tournament", "season", "week", "game_id", "team", "player_id", "player_name"
    ]].drop_duplicates()

    if unique_players.empty:
        raise InvalidParameterError("No unique players found in lineups_df.")

    records = []
    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        for _, row in unique_players.iterrows():
            url = (
                f"{API_URLS[data_source]}/api/v1/event/{row['game_id']}"
                f"/player/{row['player_id']}/rating-breakdown"
            )
            try:
                data = client.get(url)
            except APIError as exc:
                if exc.status_code in (404, 403):
                    continue
                raise
            records.extend(rating_breakdown_records(data, row))

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No rating breakdown data found for the specified players.")

    export_df(
        result_df, fn_name="rating_breakdown_data", data_source=data_source,
        output_dir=output_dir,
        first_row=lineups_df.iloc[0],
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
    )
    return result_df

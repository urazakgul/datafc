import logging
from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source, validate_df
from datafc.sofascore._core import match_log_records_from_response, export_df
from datafc.exceptions import APIError, DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache

logger = logging.getLogger(__name__)


def player_match_log_data(
    squad_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Fetches match-by-match player statistics for each player in the squad dataset."""
    validate_source(data_source)
    validate_df(squad_df, "squad_df")

    records = []
    unique_players = squad_df[["player_id", "player_name"]].drop_duplicates()
    failed_players: list = []

    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        for _, prow in unique_players.iterrows():
            player_id, player_name = prow["player_id"], prow["player_name"]
            page = 0
            while True:
                url = (
                    f"{API_URLS[data_source]}/api/v1/player/{player_id}"
                    f"/events/last/{page}"
                )
                try:
                    data = client.get(url)
                except APIError as exc:
                    logger.warning(
                        "Failed to fetch match log for player_id=%s (%s): %s",
                        player_id, player_name, exc,
                    )
                    failed_players.append(player_id)
                    break
                records.extend(match_log_records_from_response(data, player_id, player_name))
                if not data.get("hasNextPage", False):
                    break
                page += 1

    if failed_players:
        logger.warning(
            "Could not retrieve match log for %d player(s): %s",
            len(failed_players), failed_players,
        )

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No match log data found for the specified players.")

    if enable_json_export or enable_excel_export:
        first = squad_df.iloc[0]
        export_df(
            result_df, fn_name="player_match_log_data", data_source=data_source,
            output_dir=output_dir,
            country=first.get("country", ""),
            tournament=first.get("tournament", ""),
            season=result_df.iloc[0].get("season"),
            include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df

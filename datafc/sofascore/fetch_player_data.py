import logging
from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source, validate_df
from datafc.utils._tournament_info import resolve_tournament_season
from datafc.sofascore._core import player_profile_record_from_response, export_df
from datafc.exceptions import APIError, DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache

logger = logging.getLogger(__name__)


def player_data(
    squad_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Fetches biographical and profile data for each player in the provided squad dataset."""
    validate_source(data_source)
    validate_df(squad_df, "squad_df")

    records = []
    unique_players = squad_df[["player_id", "player_name"]].drop_duplicates()
    failed_players: list = []

    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        for _, prow in unique_players.iterrows():
            player_id, player_name = prow["player_id"], prow["player_name"]
            url = f"{API_URLS[data_source]}/api/v1/player/{player_id}"
            try:
                data = client.get(url)
                record = player_profile_record_from_response(data, player_id, player_name)
                if record is None:
                    logger.warning("Empty player response for player_id=%s", player_id)
                    failed_players.append(player_id)
                    continue
                records.append(record)
            except APIError as exc:
                logger.warning(
                    "Failed to fetch profile for player_id=%s (%s): %s",
                    player_id, player_name, exc,
                )
                failed_players.append(player_id)

    if failed_players:
        logger.warning(
            "Could not retrieve profile for %d player(s): %s",
            len(failed_players), failed_players,
        )

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No player profile data found for the specified players.")

    if enable_json_export or enable_excel_export:
        first = squad_df.iloc[0]
        t_id = int(first.get("tournament_id") or 0)
        s_id = int(first.get("season_id") or 0)
        _, _, season_year = resolve_tournament_season(
            t_id, s_id, data_source=data_source, rate_limit=rate_limit
        ) if t_id and s_id else ("", "", None)
        export_df(
            result_df, fn_name="player_data", data_source=data_source,
            output_dir=output_dir,
            country=first.get("country", "unknown"),
            tournament=first.get("tournament", "unknown"),
            season=season_year, include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df

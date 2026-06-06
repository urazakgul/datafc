import logging
from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source, validate_df
from datafc.sofascore._core import goal_networks_post_process, export_df
from datafc.exceptions import APIError, DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache

logger = logging.getLogger(__name__)


def goal_networks_data(
    match_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Fetches goal network (passing network) data for each match."""
    validate_source(data_source)
    validate_df(match_df, "match_df")

    incidents_frames = []
    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        for _, row in match_df.iterrows():
            country, tournament, season, week, game_id = row[
                ["country", "tournament", "season", "week", "game_id"]
            ]
            try:
                data = client.get(f"{API_URLS[data_source]}/api/v1/event/{game_id}/incidents")
            except APIError as exc:
                logger.warning("Failed to fetch goal networks for game_id=%s: %s", game_id, exc)
                continue
            incidents = data.get("incidents", [])
            if isinstance(incidents, list) and incidents:
                frame = pd.DataFrame(incidents)
                frame["country"] = country
                frame["tournament"] = tournament
                frame["season"] = season
                frame["week"] = week
                frame["game_id"] = game_id
                incidents_frames.append(frame)

    if not incidents_frames:
        raise DataNotAvailableError("No goal network data found for the specified parameters.")

    incidents_df = pd.concat(incidents_frames, ignore_index=True)
    result_df = goal_networks_post_process(incidents_df)

    export_df(
        result_df, fn_name="goal_networks_data", data_source=data_source,
        output_dir=output_dir,
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
    )
    return result_df

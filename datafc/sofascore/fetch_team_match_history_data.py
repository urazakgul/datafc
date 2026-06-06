import logging
from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source
from datafc.utils._helpers import _cast_int_cols
from datafc.sofascore._parsers import parse_team_match_history_records
from datafc.sofascore._core import export_df
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
    """Fetches the complete match history for a single team across all competitions."""
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
            records.extend(parse_team_match_history_records(data, seen_game_ids))
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
        export_df(
            result_df, fn_name="team_match_history_data", data_source=data_source,
            output_dir=output_dir,
            country=first.get("country", ""),
            tournament=first.get("tournament", ""),
            season=first.get("season"),
            include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )

    return result_df

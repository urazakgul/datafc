import logging
from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source, validate_df
from datafc.utils._tournament_info import resolve_tournament_season
from datafc.sofascore._parsers import parse_upcoming_matches_records
from datafc.sofascore._core import export_df
from datafc.exceptions import APIError, DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache

logger = logging.getLogger(__name__)


def upcoming_matches_data(
    standings_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Fetches upcoming fixture data for each team in the provided standings dataset."""
    validate_source(data_source)
    validate_df(standings_df, "standings_df")

    seen_game_ids: set = set()
    records = []
    teams = standings_df[standings_df["category"] == "Total"]

    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        for _, row in teams.iterrows():
            team_id = row["team_id"]
            page = 0
            while True:
                url = f"{API_URLS[data_source]}/api/v1/team/{team_id}/events/next/{page}"
                try:
                    data = client.get(url)
                except APIError as exc:
                    logger.warning(
                        "Failed to fetch upcoming matches for team_id=%s page=%s: %s",
                        team_id, page, exc,
                    )
                    break
                records.extend(parse_upcoming_matches_records(data, seen_game_ids))
                if not data.get("hasNextPage", False):
                    break
                page += 1

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No upcoming match data found for the specified teams.")

    result_df = result_df.sort_values("start_timestamp").reset_index(drop=True)

    if enable_json_export or enable_excel_export:
        first = standings_df.iloc[0]
        t_id = int(first.get("tournament_id") or 0)
        s_id = int(first.get("season_id") or 0)
        _, _, season_year = resolve_tournament_season(
            t_id, s_id, data_source=data_source, rate_limit=rate_limit
        ) if t_id and s_id else ("", "", None)
        export_df(
            result_df, fn_name="upcoming_matches_data", data_source=data_source,
            output_dir=output_dir,
            country=first.get("country", ""),
            tournament=first.get("tournament", ""),
            season=season_year,
            include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )

    return result_df

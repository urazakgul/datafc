import logging
from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source, validate_df
from datafc.utils._tournament_info import resolve_tournament_season
from datafc.sofascore._core import team_profile_record_from_response, export_df
from datafc.exceptions import APIError, DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache

logger = logging.getLogger(__name__)


def team_data(
    standings_df: pd.DataFrame,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Fetches profile and infrastructure data for each team in the standings dataset."""
    validate_source(data_source)
    validate_df(standings_df, "standings_df")

    records = []
    teams = standings_df[standings_df["category"] == "Total"]
    failed_teams: list = []

    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        for _, row in teams.iterrows():
            team_id, team_name = row["team_id"], row["team_name"]
            url = f"{API_URLS[data_source]}/api/v1/team/{team_id}"
            try:
                data = client.get(url)
                record = team_profile_record_from_response(data, row)
                if record is None:
                    logger.warning("Empty team response for team_id=%s", team_id)
                    failed_teams.append(team_id)
                    continue
                records.append(record)
            except APIError as exc:
                logger.warning(
                    "Failed to fetch profile for team_id=%s (%s): %s",
                    team_id, team_name, exc,
                )
                failed_teams.append(team_id)

    if failed_teams:
        logger.warning(
            "Could not retrieve profile for %d team(s): %s",
            len(failed_teams), failed_teams,
        )

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No team profile data found for the specified teams.")

    if enable_json_export or enable_excel_export:
        first = standings_df.iloc[0]
        t_id = int(first.get("tournament_id") or 0)
        s_id = int(first.get("season_id") or 0)
        _, _, season_year = resolve_tournament_season(
            t_id, s_id, data_source=data_source, rate_limit=rate_limit
        ) if t_id and s_id else ("", "", None)
        export_df(
            result_df, fn_name="team_data", data_source=data_source,
            output_dir=output_dir,
            country=first.get("country", "unknown"),
            tournament=first.get("tournament", "unknown"),
            season=season_year, include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df

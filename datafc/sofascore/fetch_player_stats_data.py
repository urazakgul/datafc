import logging
from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._config import WWW_URLS
from datafc.utils._validate import validate_source, validate_df
from datafc.utils._tournament_info import resolve_tournament_season
from datafc.sofascore._core import player_stats_records_from_response, export_df
from datafc.exceptions import APIError, DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache

logger = logging.getLogger(__name__)


def player_stats_data(
    standings_df: pd.DataFrame,
    tournament_id: int,
    season_id: int,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Fetches top player statistics for each team in the provided standings dataset."""
    validate_source(data_source)
    validate_df(standings_df, "standings_df")

    stats_list = []
    teams = standings_df[standings_df["category"] == "Total"]
    failed_teams: list = []

    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        for _, row in teams.iterrows():
            team_id, team_name = row["team_id"], row["team_name"]
            url = (
                f"{WWW_URLS[data_source]}/api/v1/team/{team_id}"
                f"/unique-tournament/{tournament_id}/season/{season_id}/top-players/overall"
            )
            try:
                data = client.get(url)
                stats_list.extend(player_stats_records_from_response(data, row))
            except APIError as exc:
                logger.warning(
                    "Failed to fetch player stats for team_id=%s (%s): %s",
                    team_id, team_name, exc,
                )
                failed_teams.append(team_id)

    if failed_teams:
        logger.warning(
            "Could not retrieve player stats for %d team(s): %s", len(failed_teams), failed_teams
        )

    result_df = pd.DataFrame(stats_list).drop_duplicates(
        subset=["team_id", "player_id", "stat_name"]
    )
    if result_df.empty:
        raise DataNotAvailableError("No player statistics data found for the specified teams.")

    if enable_json_export or enable_excel_export:
        country, tournament_name, season_year = resolve_tournament_season(
            tournament_id, season_id, data_source=data_source, rate_limit=rate_limit
        )
        first = result_df.iloc[0]
        export_df(
            result_df, fn_name="player_stats_data", data_source=data_source,
            output_dir=output_dir,
            country=country or first["country"],
            tournament=tournament_name or first["tournament"],
            season=season_year, include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df

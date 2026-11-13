import logging
from typing import TYPE_CHECKING, Optional, Sequence, Union
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source, resolve_player_input
from datafc.utils._helpers import _cast_int_cols
from datafc.sofascore._core import career_stats_records_for_pair, export_df
from datafc.exceptions import APIError, DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache

logger = logging.getLogger(__name__)


def player_career_stats_data(
    squad_df: Optional[pd.DataFrame] = None,
    player_id: Union[int, Sequence[int], None] = None,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Fetches career statistics (all seasons, overall) for each player in the squad dataset."""
    validate_source(data_source)
    squad_df = resolve_player_input(squad_df, player_id)

    records = []
    unique_players = squad_df[["player_id", "player_name"]].drop_duplicates()
    failed_players: list = []
    base = API_URLS[data_source]

    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        for _, row in unique_players.iterrows():
            player_id, player_name = row["player_id"], row["player_name"]
            try:
                seasons_data = client.get(
                    f"{base}/api/v1/player/{player_id}/statistics/seasons"
                )
                for entry in seasons_data.get("uniqueTournamentSeasons", []):
                    tournament = entry.get("uniqueTournament", {})
                    tid = tournament.get("id")
                    for season in entry.get("seasons", []):
                        sid = season.get("id")
                        try:
                            stats_data = client.get(
                                f"{base}/api/v1/player/{player_id}"
                                f"/unique-tournament/{tid}/season/{sid}/statistics/overall"
                            )
                        except APIError:
                            continue
                        records.extend(career_stats_records_for_pair(
                            tournament, season, stats_data, player_id, player_name,
                        ))
            except APIError as exc:
                logger.warning(
                    "Failed to fetch career stats for player_id=%s (%s): %s",
                    player_id, player_name, exc,
                )
                failed_players.append(player_id)

    if failed_players:
        logger.warning(
            "Could not retrieve career stats for %d player(s): %s",
            len(failed_players), failed_players,
        )

    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError("No career stats data found for the specified players.")
    _cast_int_cols(result_df, "team_id")

    if enable_json_export or enable_excel_export:
        first = squad_df.iloc[0]
        export_df(
            result_df, fn_name="player_career_stats_data", data_source=data_source,
            label=squad_df.attrs.get("export_label"),
            output_dir=output_dir,
            country=first.get("country", "unknown"),
            tournament=first.get("tournament", "unknown"),
            season=None, include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df

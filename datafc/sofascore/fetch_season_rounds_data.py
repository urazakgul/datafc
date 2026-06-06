from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source
from datafc.utils._tournament_info import resolve_tournament_season
from datafc.sofascore._core import season_rounds_records, export_df
from datafc.exceptions import DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def season_rounds_data(
    tournament_id: int,
    season_id: int,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Fetches all rounds (matchweeks) for a given tournament season."""
    validate_source(data_source)

    url = (
        f"{API_URLS[data_source]}/api/v1/unique-tournament/{tournament_id}"
        f"/season/{season_id}/rounds"
    )
    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        data = client.get(url)

    rounds = data.get("rounds") or data.get("currentRounds") or []
    if not rounds:
        raise DataNotAvailableError(
            f"No round data found for tournament_id={tournament_id}, season_id={season_id}."
        )

    result_df = pd.DataFrame(season_rounds_records(rounds, tournament_id, season_id))

    if enable_json_export or enable_excel_export:
        country, tournament_name, season_year = resolve_tournament_season(
            tournament_id, season_id, data_source=data_source, rate_limit=rate_limit
        )
        export_df(
            result_df, fn_name="season_rounds_data", data_source=data_source,
            output_dir=output_dir,
            country=country, tournament=tournament_name, season=season_year,
            include_week=False,
            enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
        )
    return result_df

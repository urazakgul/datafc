from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._save_files import save_json, save_excel
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source
from datafc.utils._tournament_info import resolve_tournament_season
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
    """
    Fetches all rounds (matchweeks) for a given tournament season.

    Use this to enumerate valid week_number values before calling match_data(),
    eliminating the need to hardcode total round counts. The is_latest flag
    identifies the most recently played round.

    The tournament_id and season_id can be obtained via seasons_data().

    Args:
        tournament_id: Sofascore unique tournament ID.
        season_id: Sofascore season ID.
        data_source: The data source ('sofavpn' or 'sofascore'). Defaults to 'sofascore'.
        rate_limit: Maximum requests per second. Defaults to 2.0.
        cache: Optional DiskCache instance. Cached responses skip the API call.
        enable_json_export: If True, saves output as JSON. Defaults to False.
        enable_excel_export: If True, saves output as Excel. Defaults to False.
        output_dir: Directory where exported files are written. Defaults to '.'.

    Returns:
        DataFrame with columns: tournament_id, season_id, round_number, slug,
        name, prefix, is_latest.

    Raises:
        InvalidParameterError: If an invalid data_source is given.
        DataNotAvailableError: If no round data is found.
        APIError: On HTTP errors from the Sofascore API.
    """
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

    records = [
        {
            "tournament_id": tournament_id,
            "season_id": season_id,
            "round_number": r.get("round"),
            "slug": r.get("slug"),
            "name": r.get("name"),
            "prefix": r.get("prefix"),
            "is_latest": r.get("isLatest", False),
        }
        for r in rounds
    ]

    result_df = pd.DataFrame(records)

    if enable_json_export or enable_excel_export:
        country, tournament_name, season_year = resolve_tournament_season(
            tournament_id, season_id, data_source=data_source, rate_limit=rate_limit
        )
        kwargs = dict(
            fn_name="season_rounds_data",
            data_source=data_source,
            country=country,
            tournament=tournament_name,
            season=season_year,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df

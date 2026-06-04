from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._save_files import save_json, save_excel
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source
from datafc.utils._tournament_info import resolve_tournament_season
from datafc.sofascore._parsers import parse_standings_rows
from datafc.exceptions import APIError, DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def standings_data(
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
    Fetches league standings (Total, Home, Away) for a specific tournament and season.

    Args:
        tournament_id: The unique identifier for the tournament.
        season_id: The unique identifier for the season.
        data_source: The data source ('sofavpn' or 'sofascore'). Defaults to 'sofascore'.
        rate_limit: Maximum requests per second. Defaults to 2.0.
        cache: Optional DiskCache instance. Cached responses skip the API call.
        enable_json_export: If True, saves output as JSON. Defaults to False.
        enable_excel_export: If True, saves output as Excel. Defaults to False.

    Returns:
        Standings with position, W/D/L, goals, and points for Total, Home and Away categories.

    Raises:
        InvalidParameterError: If an invalid data_source is given.
        DataNotAvailableError: If no standings are returned.
        APIError: On HTTP errors from the Sofascore API.
    """
    validate_source(data_source)

    rows = []
    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        for category in ("total", "home", "away"):
            url = (
                f"{API_URLS[data_source]}/api/v1/unique-tournament/{tournament_id}"
                f"/season/{season_id}/standings/{category}"
            )
            try:
                data = client.get(url)
                rows.extend(parse_standings_rows(data, category, tournament_id, season_id))
            except APIError:
                pass

    result_df = pd.DataFrame(rows)
    if result_df.empty:
        raise DataNotAvailableError(
            f"No standings data found for tournament_id={tournament_id}, season_id={season_id}."
        )

    if enable_json_export or enable_excel_export:
        country, tournament_name, season_year = resolve_tournament_season(
            tournament_id, season_id, data_source=data_source, rate_limit=rate_limit
        )
        first = result_df.iloc[0]
        kwargs = dict(
            fn_name="standings_data",
            data_source=data_source,
            country=country or first["country"],
            tournament=tournament_name or first["tournament"],
            season=season_year,
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df

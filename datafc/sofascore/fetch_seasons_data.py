import logging
from typing import TYPE_CHECKING, Optional
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source
from datafc.sofascore._parsers import parse_seasons_records
from datafc.sofascore._core import export_df
from datafc.exceptions import DataNotAvailableError

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def seasons_data(
    tournament_id: int,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """Fetches all available seasons for a given tournament."""
    validate_source(data_source)

    country = ""
    tournament_name = str(tournament_id)

    url = f"{API_URLS[data_source]}/api/v1/unique-tournament/{tournament_id}/seasons"
    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        data = client.get(url)
        if enable_json_export or enable_excel_export:
            try:
                t_data = client.get(
                    f"{API_URLS[data_source]}/api/v1/unique-tournament/{tournament_id}"
                )
                ut = t_data.get("uniqueTournament", {})
                country = ut.get("category", {}).get("name", "") or ""
                tournament_name = ut.get("name", str(tournament_id)) or str(tournament_id)
            except Exception as e:
                logger.warning("Could not fetch tournament metadata for id=%s: %s", tournament_id, e)

    records = parse_seasons_records(data, tournament_id)
    if not records:
        raise DataNotAvailableError(f"No seasons found for tournament_id={tournament_id}.")

    result_df = pd.DataFrame(records)

    export_df(
        result_df, fn_name="seasons_data", data_source=data_source,
        output_dir=output_dir,
        country=country, tournament=tournament_name,
        season=None, include_week=False,
        enable_json_export=enable_json_export, enable_excel_export=enable_excel_export,
    )
    return result_df

from typing import TYPE_CHECKING, Optional
from urllib.parse import quote
import pandas as pd
from datafc.utils._client import SofascoreClient
from datafc.utils._save_files import save_json, save_excel
from datafc.utils._config import API_URLS
from datafc.utils._validate import validate_source
from datafc.sofascore._parsers import parse_search_records
from datafc.exceptions import InvalidParameterError, DataNotAvailableError

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache

AVAILABLE_ENTITY_TYPES = {"team", "player", "tournament", "manager"}


def search_data(
    query: str,
    entity_type: Optional[str] = None,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
    enable_json_export: bool = False,
    enable_excel_export: bool = False,
    output_dir: str = ".",
) -> pd.DataFrame:
    """
    Searches Sofascore for teams, players, tournaments, or managers by name.

    Useful for discovering entity IDs (tournament_id, season_id, player_id, team_id)
    without manually looking them up on the website. Results are ranked by
    Sofascore's relevance score.

    Args:
        query: The search term (e.g. 'galatasaray', 'osimhen', 'champions league').
        entity_type: Filter results to a specific type: 'team', 'player',
                     'tournament', or 'manager'. If None, all types are returned.
        data_source: The data source ('sofavpn' or 'sofascore'). Defaults to 'sofascore'.
        rate_limit: Maximum requests per second. Defaults to 2.0.
        cache: Optional DiskCache instance. Cached responses skip the API call.
        enable_json_export: If True, saves output as JSON. Defaults to False.
        enable_excel_export: If True, saves output as Excel. Defaults to False.

    Returns:
        DataFrame with columns: entity_id, entity_name, entity_type, score,
        country, and (for players) position. Results are sorted by score descending.

    Raises:
        InvalidParameterError: If an invalid data_source or entity_type is given,
                               or if query is empty.
        DataNotAvailableError: If no results are found.
        APIError: On HTTP errors from the Sofascore API.
    """
    validate_source(data_source)
    if not query or not query.strip():
        raise InvalidParameterError("query must be a non-empty string.")
    if entity_type is not None and entity_type not in AVAILABLE_ENTITY_TYPES:
        raise InvalidParameterError(
            f"Invalid entity_type: '{entity_type}'. "
            f"Must be one of {AVAILABLE_ENTITY_TYPES} or None."
        )

    url = f"{API_URLS[data_source]}/api/v1/search/{quote(query.strip(), safe='')}"
    with SofascoreClient(rate_limit=rate_limit, cache=cache) as client:
        data = client.get(url)

    results = data.get("results", [])
    if not results:
        raise DataNotAvailableError(f"No results found for query='{query}'.")

    records = parse_search_records(results, entity_type)
    result_df = pd.DataFrame(records)
    if result_df.empty:
        raise DataNotAvailableError(
            f"No results found for query='{query}'"
            + (f" with entity_type='{entity_type}'" if entity_type else "") + "."
        )

    result_df = result_df.sort_values("score", ascending=False).reset_index(drop=True)

    if enable_json_export or enable_excel_export:
        kwargs = dict(
            fn_name="search_data",
            data_source=data_source,
            country="",
            tournament=query.strip(),
        )
        if enable_json_export:
            save_json(data=result_df, **kwargs, output_dir=output_dir)
        if enable_excel_export:
            save_excel(data=result_df, **kwargs, output_dir=output_dir)

    return result_df

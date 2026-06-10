from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.eloratings._client import EloRatingsClient
from datafc.eloratings._parsers import parse_tournament_groups
from datafc.utils._config import get_eloratings_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def tournament_groups_data(
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetches the eloratings.net tournament grouping table (long format).

    Each row pairs a specific tournament code (e.g. ``WCQ``, ``WOQ``) with one
    of the broader group codes it rolls up into (e.g. ``WQT`` = World Cup
    qualifier). A single specific code may appear multiple times if it belongs
    to more than one group.

    Useful for queries like "all World Cup qualifier variants" — filter the
    match log by ``tournament in tournament_groups_data()
    .query("group_code == 'WQT'").tournament_code``.

    Columns: ``tournament_code``, ``group_code``.
    """
    url = f"{get_eloratings_base_url()}/tournaments.tsv"
    with EloRatingsClient(rate_limit=rate_limit, cache=cache) as client:
        text = client.get(url)
    return parse_tournament_groups(text)

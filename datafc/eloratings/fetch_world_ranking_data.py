from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.eloratings._client import EloRatingsClient
from datafc.eloratings._parsers import parse_world_ranking
from datafc.utils._config import get_eloratings_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def world_ranking_data(
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetches the current global Elo ranking of national teams from eloratings.net.

    Columns are inferred from the live site (see ``WORLD_COLUMNS`` in
    ``datafc.eloratings._parsers``). Country codes are eloratings.net's own
    two-letter codes — use ``teams_data()`` for the legacy→ISO mapping.
    """
    url = f"{get_eloratings_base_url()}/World.tsv"
    with EloRatingsClient(rate_limit=rate_limit, cache=cache) as client:
        text = client.get(url)
    return parse_world_ranking(text)

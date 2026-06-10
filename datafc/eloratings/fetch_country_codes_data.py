from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.eloratings._client import EloRatingsClient
from datafc.eloratings._parsers import parse_country_codes
from datafc.utils._config import get_eloratings_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def country_codes_data(
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetches the eloratings.net country code → English name reference table.

    Useful for resolving the two-letter codes used in ``world_ranking_data``
    (``country`` column) and ``country_matches_data`` (``team_a`` / ``team_b``
    columns) into human-readable names.

    Columns: ``country_code``, ``country_name``.
    """
    url = f"{get_eloratings_base_url()}/en.teams.tsv"
    with EloRatingsClient(rate_limit=rate_limit, cache=cache) as client:
        text = client.get(url)
    return parse_country_codes(text)

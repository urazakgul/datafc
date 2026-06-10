from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.eloratings._client import EloRatingsClient
from datafc.eloratings._parsers import parse_tournament_codes
from datafc.utils._config import get_eloratings_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def tournament_codes_data(
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetches the eloratings.net tournament code → English name reference table.

    Useful for resolving the tournament codes returned by
    ``country_matches_data`` (``tournament`` column, e.g. ``OG``, ``WC``,
    ``WCQ``) into human-readable names.

    Columns: ``tournament_code``, ``tournament_name``.
    """
    url = f"{get_eloratings_base_url()}/en.tournaments.tsv"
    with EloRatingsClient(rate_limit=rate_limit, cache=cache) as client:
        text = client.get(url)
    return parse_tournament_codes(text)

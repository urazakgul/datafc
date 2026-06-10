from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.eloratings._client import EloRatingsClient
from datafc.eloratings._parsers import parse_country_matches
from datafc.exceptions import InvalidParameterError
from datafc.utils._config import get_eloratings_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def country_matches_data(
    country: str,
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetches the complete international match history for one national team.

    Args:
        country: The country page slug exactly as used by eloratings.net,
            e.g. ``"Spain"``, ``"Brazil"``, ``"Argentina"`` (case-sensitive).

    Columns include ``date``, ``home``, ``away``, scores, ``match_type``
    (e.g. ``F`` friendly, ``OG`` Olympic, ``WC`` World Cup), host (when on
    neutral ground), and post-match Elo + rank for both teams.
    """
    if not isinstance(country, str) or not country.strip():
        raise InvalidParameterError("country must be a non-empty string.")
    country_clean = country.strip()
    url = f"{get_eloratings_base_url()}/{country_clean}.tsv"
    with EloRatingsClient(rate_limit=rate_limit, cache=cache) as client:
        text = client.get(url)
    return parse_country_matches(text, country_clean)

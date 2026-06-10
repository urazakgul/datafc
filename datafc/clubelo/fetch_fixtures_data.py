from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.clubelo._client import ClubEloClient
from datafc.clubelo._parsers import parse_fixtures
from datafc.utils._config import get_clubelo_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def fixtures_data(
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetches calculated probabilities for all upcoming ClubElo fixtures.

    Each row gives goal-difference probabilities from -5 to +5 (with the tails
    aggregated) and exact-result probabilities for matches with 6 or fewer
    total goals. For 1X2 odds: sum negative goal differences for an away win
    and positive ones for a home win; goal difference == 0 is the draw.
    """
    url = f"{get_clubelo_base_url()}/Fixtures"
    with ClubEloClient(rate_limit=rate_limit, cache=cache) as client:
        text = client.get(url)
    return parse_fixtures(text)

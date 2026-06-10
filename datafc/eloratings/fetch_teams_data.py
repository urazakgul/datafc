from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.eloratings._client import EloRatingsClient
from datafc.eloratings._parsers import parse_teams
from datafc.utils._config import get_eloratings_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def teams_data(
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetches the eloratings.net legacy/historical country code → ISO mapping.

    Useful when joining match logs (which may reference defunct codes like
    ``DY``/``SU``/``WG``) against modern country code lists.

    Columns: ``legacy_code``, ``iso_code``.
    """
    url = f"{get_eloratings_base_url()}/teams.tsv"
    with EloRatingsClient(rate_limit=rate_limit, cache=cache) as client:
        text = client.get(url)
    return parse_teams(text)

from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.eloratings._client import EloRatingsClient
from datafc.eloratings._parsers import parse_tournament_editions
from datafc.utils._config import get_eloratings_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def tournament_editions_data(
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetches the eloratings.net tournament navigation tree.

    Returns every group header and every specific tournament edition the site
    knows about, with start/end dates and the page slug used for the
    edition's URL (e.g. ``2026_World_Cup_qualifying``).

    Columns: ``code``, ``depth``, ``label``, ``start_date``, ``end_date``,
    ``slug``. Rows with ``start_date`` set represent concrete editions; the
    rest are group headers used to render the site's sidebar.
    """
    url = f"{get_eloratings_base_url()}/menu.tsv"
    with EloRatingsClient(rate_limit=rate_limit, cache=cache) as client:
        text = client.get(url)
    return parse_tournament_editions(text)

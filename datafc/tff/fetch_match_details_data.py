from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.tff._client import TFFClient
from datafc.tff._parsers import parse_match_details
from datafc.utils._config import get_tff_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def match_details_data(
    match_id: int,
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetch header info for a single match from tff.org.

    The ``referees`` column holds a list of dicts ({referee_id, referee_name,
    referee_role}) for every official assigned to the match (main referee,
    two assistants, fourth official, VAR, AVAR). The ``referee_id`` and
    ``referee_name`` columns duplicate the main referee for convenience.
    """
    url = f"{get_tff_base_url()}/Default.aspx?pageId=29&macId={match_id}"
    with TFFClient(rate_limit=rate_limit, cache=cache) as client:
        html = client.get(url)
    return parse_match_details(html, match_id=match_id)

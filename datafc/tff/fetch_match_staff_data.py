from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.tff._client import TFFClient
from datafc.tff._parsers import parse_match_staff
from datafc.utils._config import get_tff_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def match_staff_data(
    match_id: int,
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetch technical staff (head coach) for both teams from tff.org.

    Returns two rows (home + away). ``coach_id`` matches TFF's ``antId``
    (antrenör id) which can be resolved on ``Default.aspx?pageId=219&antId=...``.

    Columns: ``match_id``, ``team``, ``coach_id``, ``coach_name``.
    """
    url = f"{get_tff_base_url()}/Default.aspx?pageId=29&macId={match_id}"
    with TFFClient(rate_limit=rate_limit, cache=cache) as client:
        html = client.get(url)
    return parse_match_staff(html, match_id=match_id)

from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.tff._client import TFFClient
from datafc.tff._parsers import parse_match_goals
from datafc.utils._config import get_tff_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def match_goals_data(
    match_id: int,
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetch every goal in a match from tff.org.

    ``minute`` is the base minute as an int (``45`` for a first-half stoppage
    goal), ``minute_display`` keeps the raw ``"45+2"`` form when applicable.
    ``note`` carries the TFF short-code in parentheses (``P`` = penalty,
    ``KG`` = kendi kalesine / own goal); empty string when no note.

    Columns: ``match_id``, ``team``, ``player_id``, ``player_name``,
    ``minute``, ``minute_display``, ``note``.
    """
    url = f"{get_tff_base_url()}/Default.aspx?pageId=29&macId={match_id}"
    with TFFClient(rate_limit=rate_limit, cache=cache) as client:
        html = client.get(url)
    return parse_match_goals(html, match_id=match_id)

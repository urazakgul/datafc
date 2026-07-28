from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.tff._client import TFFClient
from datafc.tff._parsers import parse_match_cards
from datafc.utils._config import get_tff_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def match_cards_data(
    match_id: int,
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetch every booking in a match from tff.org.

    ``card`` is one of ``"yellow"``, ``"red"``, ``"second_yellow"`` (derived
    from the card icon's alt text). ``minute`` is an int; ``minute_display``
    keeps the raw ``"45+2"`` string when applicable.

    Columns: ``match_id``, ``team``, ``player_id``, ``player_name``, ``card``,
    ``minute``, ``minute_display``.
    """
    url = f"{get_tff_base_url()}/Default.aspx?pageId=29&macId={match_id}"
    with TFFClient(rate_limit=rate_limit, cache=cache) as client:
        html = client.get(url)
    return parse_match_cards(html, match_id=match_id)

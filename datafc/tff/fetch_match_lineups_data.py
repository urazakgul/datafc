from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.tff._client import TFFClient
from datafc.tff._parsers import parse_match_lineups
from datafc.utils._config import get_tff_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def match_lineups_data(
    match_id: int,
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetch starting XI and substitutes for a match from tff.org.

    Returns one row per player. ``role`` is ``"starter"`` for the eleven
    starting players and ``"sub"`` for the bench. TFF does not publish
    substitution events (who came on for whom, at which minute), so the
    bench list is who was *available*, not who came on.

    Columns: ``match_id``, ``team`` (``"home"``/``"away"``), ``role``,
    ``jersey_no``, ``player_id``, ``player_name``.
    """
    url = f"{get_tff_base_url()}/Default.aspx?pageId=29&macId={match_id}"
    with TFFClient(rate_limit=rate_limit, cache=cache) as client:
        html = client.get(url)
    return parse_match_lineups(html, match_id=match_id)

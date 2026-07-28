from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.tff._client import TFFClient
from datafc.tff._parsers import parse_player
from datafc.utils._config import get_tff_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def player_data(
    player_id: int,
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetch a player's profile from tff.org.

    Returns a single-row DataFrame with personal info (name, birthplace,
    birthdate, nationality, agent) and current licence details (club,
    licence number, contract start/end). The ``player_id`` is TFF's
    ``kisiId`` query parameter, obtainable from any match sheet function.

    For the player's licence-per-season history, use
    ``player_career_data(player_id)``. Match-by-match logs, national-team
    stats, goals, and cards live behind ASP.NET tab postbacks on the same
    page and are NOT fetched by this integration yet.
    """
    url = f"{get_tff_base_url()}/Default.aspx?pageId=30&kisiId={player_id}"
    with TFFClient(rate_limit=rate_limit, cache=cache) as client:
        html = client.get(url)
    return parse_player(html, player_id=player_id)

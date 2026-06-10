from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.clubelo._client import ClubEloClient
from datafc.clubelo._parsers import parse_club_history
from datafc.exceptions import InvalidParameterError
from datafc.utils._config import get_clubelo_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def club_history_data(
    club: str,
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetches the full Elo rating history for one club.

    Args:
        club: Club name exactly as ClubElo spells it (use a daily ranking to
            confirm the spelling, e.g. ``"Barcelona"``, ``"ManCity"``).

    Returns:
        DataFrame with columns: ``query_club, rank, club, country, level, elo, from, to``.
    """
    if not isinstance(club, str) or not club.strip():
        raise InvalidParameterError("club must be a non-empty string.")
    club_clean = club.strip()
    url = f"{get_clubelo_base_url()}/{club_clean}"
    with ClubEloClient(rate_limit=rate_limit, cache=cache) as client:
        text = client.get(url)
    return parse_club_history(text, club_clean)

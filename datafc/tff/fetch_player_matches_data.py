from typing import TYPE_CHECKING, Optional

import pandas as pd

import pandas as pd

from datafc.tff._client import TFFClient
from datafc.tff._parsers import parse_player_club_matches
from datafc.utils._config import get_tff_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


_TAB_CONTAINER = (
    "ctl00$MPane$m_30_202_ctnr$m_30_202$OyuncuIstatistikDisplay1$RadTabStrip1"
)


def player_matches_data(
    player_id: int,
    season: str,
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetch a player's club matches for a single season from tff.org.

    ``season`` must be one of the TFF dropdown values (``"2026-2027"``,
    ``"2025-2026"``, ``"2024-2025"``, …). The Maçlar tab requires TWO
    postbacks: one to switch tabs, another to filter by season. Both
    responses are cached so subsequent calls at the same season are free.

    Columns: player_id, season, match_id, home_team, home_score,
    away_score, away_team, datetime, tournament.
    """
    url = f"{get_tff_base_url()}/Default.aspx?pageId=30&kisiId={player_id}"
    with TFFClient(rate_limit=rate_limit, cache=cache) as client:
        pages = client.post_tab_paged(
            url, _TAB_CONTAINER, "maclar", grid_leaf="grdMac", season=season,
        )
    frames = []
    for html in pages:
        try:
            frames.append(parse_player_club_matches(html, player_id=player_id, season=season))
        except Exception:
            continue
    if not frames:
        return parse_player_club_matches(pages[0], player_id=player_id, season=season)
    return pd.concat(frames, ignore_index=True)

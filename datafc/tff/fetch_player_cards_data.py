from typing import TYPE_CHECKING, Optional

import pandas as pd

import pandas as pd

from datafc.tff._client import TFFClient
from datafc.tff._parsers import parse_player_cards
from datafc.utils._config import get_tff_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


_TAB_CONTAINER = (
    "ctl00$MPane$m_30_202_ctnr$m_30_202$OyuncuIstatistikDisplay1$RadTabStrip1"
)


def player_cards_data(
    player_id: int,
    season: str,
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetch a player's booking record for a single season from tff.org.

    ``season`` follows TFF's dropdown labels (``"2025-2026"`` etc.). Uses
    the same two-step postback flow as ``player_matches_data``.

    Columns: player_id, season, match_id, card, minute, minute_display,
    match, datetime, tournament. ``card`` is normalised to ``"yellow"``,
    ``"red"``, or ``"second_yellow"``.
    """
    url = f"{get_tff_base_url()}/Default.aspx?pageId=30&kisiId={player_id}"
    with TFFClient(rate_limit=rate_limit, cache=cache) as client:
        pages = client.post_tab_paged(
            url, _TAB_CONTAINER, "kartlar", grid_leaf="grdKartlar", season=season,
        )
    frames = []
    for html in pages:
        try:
            frames.append(parse_player_cards(html, player_id=player_id, season=season))
        except Exception:
            continue
    if not frames:
        return parse_player_cards(pages[0], player_id=player_id, season=season)
    return pd.concat(frames, ignore_index=True)

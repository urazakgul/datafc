from typing import TYPE_CHECKING, Optional

import pandas as pd

import pandas as pd

from datafc.tff._client import TFFClient
from datafc.tff._parsers import parse_player_goals
from datafc.utils._config import get_tff_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


_TAB_CONTAINER = (
    "ctl00$MPane$m_30_202_ctnr$m_30_202$OyuncuIstatistikDisplay1$RadTabStrip1"
)


def player_goals_data(
    player_id: int,
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetch every goal (club + national) attributed to the player by TFF.

    Backed by the ``Attığı Goller`` tab (single ASP.NET postback). Only
    matches TFF recorded — friendlies, youth-team goals, or international
    goals for other federations are NOT included.

    Columns: player_id, team, team_id, minute, minute_display, goal_type,
    match, match_id, tournament, date, season.
    """
    url = f"{get_tff_base_url()}/Default.aspx?pageId=30&kisiId={player_id}"
    with TFFClient(rate_limit=rate_limit, cache=cache) as client:
        pages = client.post_tab_paged(url, _TAB_CONTAINER, "goller", grid_leaf="grdGoller")
    frames = []
    for html in pages:
        try:
            frames.append(parse_player_goals(html, player_id=player_id))
        except Exception:
            continue
    if not frames:
        return parse_player_goals(pages[0], player_id=player_id)
    return pd.concat(frames, ignore_index=True)

from typing import TYPE_CHECKING, Optional

import pandas as pd

import pandas as pd

from datafc.tff._client import TFFClient
from datafc.tff._parsers import parse_player_national_matches
from datafc.utils._config import get_tff_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


# Fixed on TFF's player template. The RadTabStrip control that owns
# Oyuncu Hareketleri / Maçlar / Milli Maçlar / Attığı Goller / Kartlar /
# Genel lives at module m_30_202 regardless of the player id.
_TAB_CONTAINER = (
    "ctl00$MPane$m_30_202_ctnr$m_30_202$OyuncuIstatistikDisplay1$RadTabStrip1"
)


def player_national_matches_data(
    player_id: int,
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetch a player's national-team appearances from tff.org.

    Returns every appearance across the player's career for any Turkey
    national team (A Milli, U21, U19, U17…). Requires an ASP.NET postback
    against the ``Milli Maçlar`` tab; the response is cached separately
    from the base player page.

    Columns: player_id, tournament, home_team, home_score, away_score,
    away_team, date, category, match_id.
    """
    url = f"{get_tff_base_url()}/Default.aspx?pageId=30&kisiId={player_id}"
    with TFFClient(rate_limit=rate_limit, cache=cache) as client:
        pages = client.post_tab_paged(url, _TAB_CONTAINER, "milli", grid_leaf="grdMilli")
    frames = []
    for html in pages:
        try:
            frames.append(parse_player_national_matches(html, player_id=player_id))
        except Exception:
            # Empty follow-on pages should not sink the whole request.
            continue
    if not frames:
        # Preserve the informative error from the parser on page 1.
        return parse_player_national_matches(pages[0], player_id=player_id)
    return pd.concat(frames, ignore_index=True)

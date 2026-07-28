from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.tff._client import TFFClient
from datafc.tff._parsers import parse_player_career
from datafc.utils._config import get_tff_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def player_career_data(
    player_id: int,
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetch a player's licence-per-season history from tff.org.

    Returns one row per licence entry from the ``Genel`` tab of the player
    page. TFF re-issues a licence at least once per season, so a long
    tenure at the same club produces multiple rows. Columns: player_id,
    team_id, team_name, contract_start, contract_end, licence_type
    (``"Filiz Lisans"``, ``"Amatör Vize"``, ``"Profesyonelliğe Geçiş"``,
    ``"Vize"``, ``"Transfer"``…), licence_date, abroad_exit_date.

    Shares a URL with ``player_data``, so with cache enabled the second
    call is free.
    """
    url = f"{get_tff_base_url()}/Default.aspx?pageId=30&kisiId={player_id}"
    with TFFClient(rate_limit=rate_limit, cache=cache) as client:
        html = client.get(url)
    return parse_player_career(html, player_id=player_id)

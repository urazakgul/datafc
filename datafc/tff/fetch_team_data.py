from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.tff._client import TFFClient
from datafc.tff._parsers import parse_team
from datafc.utils._config import get_tff_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def team_data(
    club_id: int,
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetch a club's profile from tff.org.

    ``official_name`` is the unsponsored short name TFF publishes on the
    club's own page (e.g. ``KONYASPOR``), independent of the sponsor-prefixed
    display name that appears in fixtures/standings (``TÜMOSAN KONYASPOR``).
    Stadium fields come from the "Stad Bilgisi" table on the same page.
    """
    url = f"{get_tff_base_url()}/Default.aspx?pageId=28&kulupID={club_id}"
    with TFFClient(rate_limit=rate_limit, cache=cache) as client:
        html = client.get(url)
    return parse_team(html, club_id=club_id)

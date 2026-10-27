import warnings
from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.exceptions import InvalidParameterError
from datafc.tff._client import TFFClient
from datafc.tff._parsers import (
    StandingsNotPublishedError,
    parse_group_ids,
    parse_standings,
)
from datafc.utils._config import get_tff_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


_COLUMNS = [
    "page_id", "week", "position", "team_name", "team_id", "played", "wins",
    "draws", "losses", "goals_for", "goals_against", "goal_diff", "points",
]


def _match_group(label: str, wanted: str) -> bool:
    return wanted.strip().lower() in label.lower()


def standings_data(
    page_id: int,
    week: int,
    group: Optional[str] = None,
    stage: Optional[str] = None,
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetch the league table as of a given matchweek from tff.org.

    Standings are rendered on the same page as the weekly fixtures, so
    ``page_id`` and ``week`` are the same values used by ``fixtures_data``.

    On multi-group pages (2. Lig ``Kırmızı`` / ``Beyaz``, 3. Lig ``01`` /
    ``02`` / ``03`` / ``04``) TFF only renders one group's table by default.
    Pass ``group="Beyaz"`` or ``group="04"`` (case-insensitive; partial match
    ok) to fetch that group's standings via TFF's ``grupID`` query parameter.
    Raises ``InvalidParameterError`` if the label matches no known group.

    Seasons with a play-off stage (Süper Lig 2011/12 Süper Final) render
    several tables on one page. By default the full regular-season table is
    returned; pass ``stage="Şampiyonluk"`` or ``stage="Avrupa"``
    (case-insensitive; partial match ok) for a play-off table, which adds a
    ``stage`` column. Play-off tables only exist for ``week`` 1-6; TFF shows
    their final state for larger values.

    TFF publishes no league table for Süper Lig seasons before 1984/85. For
    those pages a ``UserWarning`` is emitted and an empty DataFrame is
    returned, so loops over many seasons keep running.
    """
    match = None
    base = f"{get_tff_base_url()}/Default.aspx?pageID={page_id}&hafta={week}"
    with TFFClient(rate_limit=rate_limit, cache=cache) as client:
        html = client.get(base)
        if group is not None:
            group_ids = parse_group_ids(html)
            if not group_ids:
                raise InvalidParameterError(
                    f"pageID={page_id} has no group selector; standings_data "
                    f"received group={group!r} but this is a single-group league."
                )
            match = next((gid for label, gid in group_ids.items()
                          if _match_group(label, group)), None)
            if match is None:
                raise InvalidParameterError(
                    f"group={group!r} matched no group on pageID={page_id}. "
                    f"Available: {sorted(group_ids)}."
                )
            html = client.get(f"{base}&grupID={match}")

    try:
        df = parse_standings(
            html, page_id=page_id, week=week, stage=stage, group_id=match
        )
    except StandingsNotPublishedError:
        warnings.warn(
            f"TFF publishes no standings table for pageID={page_id}; "
            "returning an empty DataFrame.",
            UserWarning,
            stacklevel=2,
        )
        return pd.DataFrame(columns=_COLUMNS)
    if group is not None:
        # Tag the returned rows with the resolved group name for downstream joins.
        resolved_label = next(label for label, gid in group_ids.items() if gid == match)
        df.insert(2, "group", resolved_label)
    return df

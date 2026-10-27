from typing import TYPE_CHECKING, Optional

import pandas as pd

from datafc.exceptions import DataNotAvailableError, InvalidParameterError
from datafc.tff._client import TFFClient
from datafc.tff._parsers import (
    parse_fixtures,
    parse_group_ids,
    parse_playoff_fixtures,
    parse_stage_fixtures,
)
from datafc.utils._config import get_tff_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def _matches_group(row_group: str, wanted: str) -> bool:
    """Case- and suffix-tolerant comparison for TFF group names.

    Accepts ``"Kırmızı"``, ``"kirmizi"``, ``"Kırmızı Grup"`` etc. — matches
    if the wanted string (whitespace-stripped, lowercased) is a substring of
    the row's group (also lowercased).
    """
    if not row_group:
        return False
    return wanted.strip().lower() in row_group.lower()


def fixtures_data(
    page_id: int,
    week: Optional[int] = None,
    group: Optional[str] = None,
    playoff: bool = False,
    round: Optional[str] = None,
    stage: Optional[str] = None,
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetch the fixtures list from tff.org, either a regular matchweek or
    the season's play-off bracket.

    Regular mode (``playoff=False``, default):
        ``page_id`` and ``week`` are required. ``week`` is TFF's ``hafta``
        query parameter. ``group`` optionally filters to one group on
        multi-group league pages (2. Lig ``"Kırmızı"`` / ``"Beyaz"``;
        3. Lig ``"01"`` / ``"02"`` / ``"03"`` / ``"04"``). Case-insensitive.

    ``stage`` selects a stage group's matches instead of the regular season,
    for seasons that run one (Süper Lig 2011/12 Süper Final:
    ``stage="Şampiyonluk"`` or ``stage="Avrupa"``, case-insensitive, partial
    match ok). It requires ``week`` (1-6 for the Süper Final; TFF renders no
    stage matches beyond it) and adds a ``stage`` column. Without ``stage``
    only the regular-season matches are returned.

    Play-off mode (``playoff=True``):
        ``week`` is ignored (play-off matches don't fit the weekly grid).
        Returns every play-off match rendered on the league page with
        columns ``round`` (``"1. Tur"``, ``"2. Tur"``, ``"Yarı Final"``,
        ``"Final"``), 90-minute score, plus ``extra_time_home/away`` and
        ``penalty_home/away`` for tie-breaker results. Pass ``round=`` to
        filter (case- and partial-match tolerant, e.g. ``round="Final"``
        returns just the finals).

    Discover ``page_id`` by loading a weekly fixture page on tff.org and
    copying the ``pageID`` query-string value.
    """
    base = f"{get_tff_base_url()}/Default.aspx?pageID={page_id}"

    if playoff:
        # The play-off module is rendered on the same page regardless of
        # hafta, but TFF still requires SOMETHING for the query. hafta=1 is
        # the cheapest choice and keeps the URL cache-stable.
        url = f"{base}&hafta=1"
        with TFFClient(rate_limit=rate_limit, cache=cache) as client:
            html = client.get(url)
        df = parse_playoff_fixtures(html, page_id=page_id)

        if round is not None:
            wanted = round.strip().lower()
            mask = df["round"].apply(lambda r: wanted in r.lower())
            if not mask.any():
                available = sorted(df["round"].unique().tolist())
                raise InvalidParameterError(
                    f"round={round!r} matched no play-off matches for "
                    f"pageID={page_id}. Available rounds: {available}."
                )
            df = df.loc[mask].reset_index(drop=True)
        return df

    if week is None:
        raise InvalidParameterError(
            "fixtures_data(playoff=False) requires ``week``. Pass an int for "
            "the matchweek, or use playoff=True for the play-off bracket."
        )

    url = f"{base}&hafta={week}"
    with TFFClient(rate_limit=rate_limit, cache=cache) as client:
        html = client.get(url)
        try:
            df: Optional[pd.DataFrame] = _parse(html, page_id, week, stage)
        except DataNotAvailableError:
            if group is None or stage is not None:
                raise
            df = None

        if group is not None and stage is None and (
            df is None or not _group_mask(df, group).any()
        ):
            group_ids = parse_group_ids(html)
            gid = next((g for label, g in group_ids.items()
                        if _matches_group(label, group)), None)
            if gid is not None:
                html = client.get(f"{url}&grupID={gid}")
                df = _parse(html, page_id, week, stage)
        if df is None:
            raise DataNotAvailableError(
                f"No fixtures found for pageID={page_id}, hafta={week}, group={group!r}."
            )

    if group is not None:
        mask = _group_mask(df, group)
        if not mask.any():
            available = sorted(g for g in df["group"].unique() if g)
            raise InvalidParameterError(
                f"group={group!r} matched no fixtures for pageID={page_id}, "
                f"hafta={week}. Available groups: {available or 'none (single-group league)'}."
            )
        df = df.loc[mask].reset_index(drop=True)

    return df


def _parse(html: str, page_id: int, week: int, stage: Optional[str]) -> pd.DataFrame:
    if stage is not None:
        return parse_stage_fixtures(html, page_id=page_id, week=week, stage=stage)
    return parse_fixtures(html, page_id=page_id, week=week)


def _group_mask(df: pd.DataFrame, group: str) -> pd.Series:
    return df["group"].apply(lambda g: _matches_group(g, group))

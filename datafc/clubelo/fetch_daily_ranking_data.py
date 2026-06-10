from datetime import date as _date_cls
from typing import TYPE_CHECKING, Optional, Union

import pandas as pd

from datafc.clubelo._client import ClubEloClient
from datafc.clubelo._parsers import parse_daily_ranking
from datafc.exceptions import InvalidParameterError
from datafc.utils._config import get_clubelo_base_url

if TYPE_CHECKING:
    from datafc.utils._cache import DiskCache


def _coerce_date(value: Union[str, _date_cls]) -> str:
    if isinstance(value, _date_cls):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, str):
        try:
            return _date_cls.fromisoformat(value).strftime("%Y-%m-%d")
        except ValueError as exc:
            raise InvalidParameterError(
                f"date must be 'YYYY-MM-DD' or a datetime.date; got {value!r}."
            ) from exc
    raise InvalidParameterError(
        f"date must be a string or datetime.date; got {type(value).__name__}."
    )


def daily_ranking_data(
    date: Union[str, _date_cls],
    rate_limit: float = 2.0,
    cache: Optional["DiskCache"] = None,
) -> pd.DataFrame:
    """Fetches the full ClubElo ranking for the given calendar day.

    Args:
        date: 'YYYY-MM-DD' string or ``datetime.date``. Values before 1960 are
            considered provisional by ClubElo.

    Returns:
        DataFrame with columns: ``query_date, rank, club, country, level, elo, from, to``.
    """
    date_str = _coerce_date(date)
    url = f"{get_clubelo_base_url()}/{date_str}"
    with ClubEloClient(rate_limit=rate_limit, cache=cache) as client:
        text = client.get(url)
    return parse_daily_ranking(text, date_str)

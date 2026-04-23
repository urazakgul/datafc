"""
Lightweight helpers to resolve human-readable tournament/season labels
from numeric IDs, used when building export filenames.
"""

import logging
from typing import Dict, Tuple
from datafc.utils._client import SofascoreClient
from datafc.utils._config import API_URLS

logger = logging.getLogger(__name__)

# In-memory cache so concurrent async export blocks don't repeat the same lookup.
_RESOLVE_CACHE: Dict[Tuple[int, int, str], Tuple[str, str, str]] = {}


def resolve_tournament_season(
    tournament_id: int,
    season_id: int,
    data_source: str = "sofascore",
    rate_limit: float = 2.0,
) -> Tuple[str, str, str]:
    """
    Returns (country, tournament_name, season_year) for the given IDs.

    Makes two lightweight API calls:
      - /api/v1/unique-tournament/{tournament_id}  → country + name
      - /api/v1/unique-tournament/{tournament_id}/seasons → season year

    Falls back to empty string / str(id) on any error so callers never crash.
    """
    cache_key = (tournament_id, season_id, data_source)
    if cache_key in _RESOLVE_CACHE:
        return _RESOLVE_CACHE[cache_key]

    country = ""
    tournament_name = str(tournament_id)
    season_year = str(season_id)

    try:
        with SofascoreClient(rate_limit=rate_limit) as client:
            t_data = client.get(
                f"{API_URLS[data_source]}/api/v1/unique-tournament/{tournament_id}"
            )
            ut = t_data.get("uniqueTournament", {})
            country = ut.get("category", {}).get("name", "") or ""
            tournament_name = ut.get("name", str(tournament_id)) or str(tournament_id)

            s_data = client.get(
                f"{API_URLS[data_source]}/api/v1/unique-tournament/{tournament_id}/seasons"
            )
            for season in s_data.get("seasons", []):
                if season.get("id") == season_id:
                    season_year = season.get("year", str(season_id))
                    break

        result = country, tournament_name, season_year
        _RESOLVE_CACHE[cache_key] = result
        return result

    except Exception as e:
        logger.warning(
            "Could not resolve tournament/season labels for tournament_id=%s, season_id=%s: %s",
            tournament_id, season_id, e,
        )
        return country, tournament_name, season_year

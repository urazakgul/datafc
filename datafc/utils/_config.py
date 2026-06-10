from typing import Optional

ALLOWED_SOURCES = {"sofavpn", "sofascore"}

SOFASCORE_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

# api.* subdomain — used for match, player and league endpoints
API_URLS = {
    "sofascore": "https://api.sofascore.com",
    "sofavpn": "https://api.sofavpn.com",
}

# www.* subdomain — used for team/player season stats and h2h endpoints
WWW_URLS = {
    "sofascore": "https://www.sofascore.com",
    "sofavpn": "https://www.sofavpn.com",
}

CLUBELO_URL = "https://api.clubelo.com"

_runtime_clubelo_url: Optional[str] = None


def get_clubelo_base_url() -> str:
    """Return the active ClubElo base URL (runtime override takes precedence)."""
    return _runtime_clubelo_url if _runtime_clubelo_url else CLUBELO_URL


def set_clubelo_base_url(url: str) -> None:
    """Override the ClubElo base URL at runtime.

    Useful when the default ``https://api.clubelo.com`` is unreachable (corporate
    firewalls blocking port 443, regional restrictions, etc.) but the same host
    is reachable over plain HTTP, or when routing through a mirror/proxy.

    Args:
        url: Base URL without a trailing slash, e.g. ``"http://api.clubelo.com"``.
    """
    global _runtime_clubelo_url
    if not isinstance(url, str) or not url.strip():
        raise ValueError("ClubElo base URL must be a non-empty string.")
    _runtime_clubelo_url = url.rstrip("/")


def reset_clubelo_base_url() -> None:
    """Restore the built-in default ClubElo base URL."""
    global _runtime_clubelo_url
    _runtime_clubelo_url = None


ELORATINGS_URL = "https://www.eloratings.net"

_runtime_eloratings_url: Optional[str] = None


def get_eloratings_base_url() -> str:
    """Return the active eloratings.net base URL (runtime override takes precedence)."""
    return _runtime_eloratings_url if _runtime_eloratings_url else ELORATINGS_URL


def set_eloratings_base_url(url: str) -> None:
    """Override the eloratings.net base URL at runtime.

    Useful when the default ``https://www.eloratings.net`` is unreachable
    (corporate firewalls, regional restrictions) but the same host is
    reachable over plain HTTP, or when routing through a mirror.
    """
    global _runtime_eloratings_url
    if not isinstance(url, str) or not url.strip():
        raise ValueError("eloratings.net base URL must be a non-empty string.")
    _runtime_eloratings_url = url.rstrip("/")


def reset_eloratings_base_url() -> None:
    """Restore the built-in default eloratings.net base URL."""
    global _runtime_eloratings_url
    _runtime_eloratings_url = None

TOURNAMENT_URL_PATTERNS = {
    "default": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}",
    "uefa": {
        "preliminary_semifinals": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/semifinals/prefix/Preliminary",
        "preliminary_final": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/final/prefix/Preliminary",
        "qualification_round": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/qualification-round-{week_number}",
        "qualification_playoff": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/playoff-round/prefix/Qualification",
        "group_stage_week": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}",
        "playoff_round": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/playoff-round",
        "round_of_16": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/round-of-16",
        "quarterfinals": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/quarterfinals",
        "semifinals": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/semifinals",
        "match_for_3rd_place": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/match-for-3rd-place",
        "final": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/final",
    },
    "world_cup": {
        "group_stage_week": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}",
        "round_of_32": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/round-of-32",
        "round_of_16": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/round-of-16",
        "quarterfinals": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/quarterfinals",
        "semifinals": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/semifinals",
        "match_for_3rd_place": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/match-for-3rd-place",
        "final": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/final",
    },
}

# Slug used in the API URL for each world_cup knockout stage.
# Used to auto-resolve the season-specific round number via the /rounds endpoint.
WORLD_CUP_KNOCKOUT_SLUGS: dict[str, str] = {
    "round_of_32": "round-of-32",
    "round_of_16": "round-of-16",
    "quarterfinals": "quarterfinals",
    "semifinals": "semifinals",
    "match_for_3rd_place": "match-for-3rd-place",
    "final": "final",
}

# ---------------------------------------------------------------------------
# Runtime-overridable pattern registry
# ---------------------------------------------------------------------------

_runtime_patterns: dict = {}


def get_tournament_url_patterns() -> dict:
    """Return the active tournament URL patterns (runtime override takes precedence)."""
    return _runtime_patterns if _runtime_patterns else TOURNAMENT_URL_PATTERNS


def set_tournament_url_patterns(patterns: dict) -> None:
    """
    Override the tournament URL patterns at runtime without editing source files.

    Useful when Sofascore changes URL structure or when adding custom tournament types.
    All format strings must accept ``{base_url}``, ``{tournament_id}``,
    ``{season_id}``, and ``{week_number}`` as keyword arguments.

    Args:
        patterns: Dict with the same structure as ``TOURNAMENT_URL_PATTERNS``.
                  Must include a ``'default'`` key.

    Raises:
        ValueError: If ``'default'`` key is missing.

    Example::

        from datafc.utils._config import set_tournament_url_patterns, TOURNAMENT_URL_PATTERNS
        import copy

        custom = copy.deepcopy(TOURNAMENT_URL_PATTERNS)
        custom["my_league"] = {
            "group_stage": "{base_url}/api/v1/unique-tournament/{tournament_id}/..."
        }
        set_tournament_url_patterns(custom)
    """
    if "default" not in patterns:
        raise ValueError(
            "tournament URL patterns must include a 'default' key."
        )
    _runtime_patterns.clear()
    _runtime_patterns.update(patterns)


def reset_tournament_url_patterns() -> None:
    """Restore the built-in default tournament URL patterns."""
    _runtime_patterns.clear()

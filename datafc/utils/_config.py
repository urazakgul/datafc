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

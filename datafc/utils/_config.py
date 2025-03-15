ALLOWED_SOURCES = {"sofavpn", "sofascore"}

API_BASE_URLS = {
    "sofavpn": "https://api.sofavpn.com",
    "sofascore": "https://api.sofascore.com",
    "sofavpn2": "https://www.sofavpn.com",
    "sofascore2": "https://www.sofascore.com"
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
        "final": "{base_url}/api/v1/unique-tournament/{tournament_id}/season/{season_id}/events/round/{week_number}/slug/final"
    }
}
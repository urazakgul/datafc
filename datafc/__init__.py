__version__ = "2.1.0"

from .sofascore import *
from .exceptions import (
    DataFCError,
    InvalidParameterError,
    APIError,
    RateLimitError,
    ServerError,
    DataNotAvailableError,
)
from .utils._cache import DiskCache, get_default_cache, set_default_cache
from .utils._save_files import save_parquet
from .utils._config import (
    get_tournament_url_patterns,
    set_tournament_url_patterns,
    reset_tournament_url_patterns,
)

__all__ = [
    # Discovery
    "search_data",
    "seasons_data",
    # Tournament / season metadata
    "season_rounds_data",
    # League / season
    "standings_data",
    "team_data",
    "team_stats_data",
    "team_transfers_data",
    "player_stats_data",
    "squad_data",
    "upcoming_matches_data",
    "team_match_history_data",
    "league_player_stats_data",
    # Matchweek
    "match_data",
    "match_details_data",
    "match_stats_data",
    "match_odds_data",
    "match_h2h_data",
    "momentum_data",
    "pregame_form_data",
    "shots_data",
    "lineups_data",
    "substitutions_data",
    "incidents_data",
    "average_positions_data",
    "coordinates_data",
    "goal_networks_data",
    "past_matches_data",
    # Player
    "player_data",
    "player_transfers_data",
    "player_career_stats_data",
    "player_national_team_data",
    "player_match_log_data",
    # Referee
    "referee_stats_data",
    # Async API
    "aio",
    # Exceptions
    "DataFCError",
    "InvalidParameterError",
    "APIError",
    "RateLimitError",
    "ServerError",
    "DataNotAvailableError",
    # Cache
    "DiskCache",
    "get_default_cache",
    "set_default_cache",
    # Export utilities
    "save_parquet",
    # Config
    "get_tournament_url_patterns",
    "set_tournament_url_patterns",
    "reset_tournament_url_patterns",
]
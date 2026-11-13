"""
Shared validation helpers and utility functions used across all fetch modules.
"""

from typing import Optional, Sequence, Union
import pandas as pd
from datafc.exceptions import InvalidParameterError
from datafc.utils._config import ALLOWED_SOURCES, get_tournament_url_patterns


def validate_source(data_source: str) -> None:
    """Raise InvalidParameterError if data_source is not in ALLOWED_SOURCES."""
    if data_source not in ALLOWED_SOURCES:
        raise InvalidParameterError(
            f"Invalid data_source: '{data_source}'. Must be one of {ALLOWED_SOURCES}."
        )


def validate_df(df: Optional[pd.DataFrame], name: str) -> None:
    """Raise InvalidParameterError if df is None or empty."""
    if df is None or df.empty:
        raise InvalidParameterError(f"{name} must be provided and cannot be empty.")


def _normalize_ids(value: Union[int, Sequence[int]], name: str) -> list:
    """Return a de-duplicated list of ints from an int or a non-empty list of ints."""
    values = [value] if isinstance(value, int) and not isinstance(value, bool) else value
    if isinstance(values, (str, bytes)) or not hasattr(values, "__iter__"):
        raise InvalidParameterError(f"{name} must be an int or a list of ints.")
    values = list(values)
    if not values or any(
        isinstance(v, bool) or not hasattr(v, "__index__") for v in values
    ):
        raise InvalidParameterError(f"{name} must be an int or a non-empty list of ints.")
    return list(dict.fromkeys(int(v) for v in values))


def _id_label(prefix: str, ids: list) -> str:
    """``player_12994`` for one ID, ``player_12994_and_more`` for several."""
    return f"{prefix}_{ids[0]}" + ("_and_more" if len(ids) > 1 else "")


def resolve_player_input(
    squad_df: Optional[pd.DataFrame],
    player_id: Union[int, Sequence[int], None],
) -> pd.DataFrame:
    """Return a squad-like DataFrame from either ``squad_df`` or ``player_id``.

    Exactly one of the two must be given. When ``player_id`` is used, the result
    has ``player_id`` and ``player_name`` (None) columns only; export filenames
    then fall back to the same "unknown" defaults used for a bare squad_df.
    """
    if squad_df is not None and player_id is not None:
        raise InvalidParameterError("Provide either squad_df or player_id, not both.")
    if player_id is None:
        validate_df(squad_df, "squad_df")
        return squad_df
    ids = _normalize_ids(player_id, "player_id")
    out = pd.DataFrame({"player_id": ids, "player_name": [None] * len(ids)})
    out.attrs["export_label"] = _id_label("player", ids)
    return out


def resolve_lineups_input(
    lineups_df: Optional[pd.DataFrame],
    player_id: Union[int, Sequence[int], None],
    game_id: Union[int, Sequence[int], None],
) -> pd.DataFrame:
    """Return a lineups-like DataFrame from ``lineups_df`` or ``player_id`` + ``game_id``.

    Both may be a single int or a list; every player/game combination is built.
    Combinations where the player did not play return 404/403 and are skipped.
    """
    if lineups_df is not None and (player_id is not None or game_id is not None):
        raise InvalidParameterError(
            "Provide either lineups_df or player_id with game_id, not both."
        )
    if player_id is None and game_id is None:
        validate_df(lineups_df, "lineups_df")
        return lineups_df
    if player_id is None or game_id is None:
        raise InvalidParameterError("player_id and game_id must be provided together.")
    players = _normalize_ids(player_id, "player_id")
    games = _normalize_ids(game_id, "game_id")
    pairs = [(p, g) for p in players for g in games]
    out = pd.DataFrame({
        "country": "unknown",
        "tournament": "unknown",
        "season": None,
        "week": None,
        "game_id": [g for _, g in pairs],
        "team": None,
        "player_id": [p for p, _ in pairs],
        "player_name": None,
    })
    out.attrs["export_label"] = f"{_id_label('player', players)}_{_id_label('game', games)}"
    return out


def safe_get(data: dict, *keys, default=None):
    """Safely traverse nested dicts without raising KeyError."""
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return default
    return data


def validate_tournament_type(tournament_type: Optional[str]) -> None:
    """
    Raise InvalidParameterError if tournament_type is not None and not a known type.

    Valid types are the keys of the active tournament URL patterns excluding 'default'.
    Call ``set_tournament_url_patterns()`` to register custom types.
    """
    if tournament_type is None:
        return
    patterns = get_tournament_url_patterns()
    valid_types = sorted(k for k in patterns if k != "default")
    if tournament_type not in patterns or tournament_type == "default":
        raise InvalidParameterError(
            f"Invalid tournament_type: '{tournament_type}'. "
            f"Valid options: {valid_types}. "
            "Pass None to use the standard league round URL."
        )


def validate_tournament_stage(tournament_type: str, tournament_stage: Optional[str]) -> None:
    """
    Raise InvalidParameterError if tournament_stage is missing or invalid
    for the given tournament_type.
    """
    patterns = get_tournament_url_patterns()
    stage_patterns = patterns.get(tournament_type, {})
    valid_stages = sorted(stage_patterns)
    if not tournament_stage:
        raise InvalidParameterError(
            f"tournament_stage is required when using tournament_type='{tournament_type}'. "
            f"Valid stages: {valid_stages}."
        )
    if tournament_stage not in stage_patterns:
        raise InvalidParameterError(
            f"Invalid tournament_stage: '{tournament_stage}' for tournament_type='{tournament_type}'. "
            f"Valid stages: {valid_stages}."
        )


def build_tournament_url(
    base_url: str,
    tournament_id: int,
    season_id: int,
    week_number: Optional[int],
    tournament_type: Optional[str],
    tournament_stage: Optional[str],
) -> str:
    """Build the correct Sofascore events URL for a given tournament and round."""
    patterns = get_tournament_url_patterns()
    if tournament_type is not None:
        validate_tournament_type(tournament_type)
        validate_tournament_stage(tournament_type, tournament_stage)
        template = patterns[tournament_type][tournament_stage]
    else:
        template = patterns["default"]
    if "{week_number}" in template and week_number is None:
        raise InvalidParameterError(
            "week_number is required for this tournament_type/tournament_stage combination."
        )
    return template.format(
        base_url=base_url,
        tournament_id=tournament_id,
        season_id=season_id,
        week_number=week_number,
    )

"""
Shared validation helpers and utility functions used across all fetch modules.
"""

from typing import Optional
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

from io import StringIO

import pandas as pd

from datafc.exceptions import DataNotAvailableError


def _read_csv(text: str, *, context: str) -> pd.DataFrame:
    if not text or not text.strip():
        raise DataNotAvailableError(f"Empty response from ClubElo for {context}.")
    df = pd.read_csv(StringIO(text))
    if df.empty:
        raise DataNotAvailableError(f"No rows returned from ClubElo for {context}.")
    return df


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def parse_daily_ranking(text: str, date: str) -> pd.DataFrame:
    """Columns: rank, club, country, level, elo, from, to."""
    df = _normalize_columns(_read_csv(text, context=f"date={date}"))
    df.insert(0, "query_date", date)
    return df


def parse_club_history(text: str, club: str) -> pd.DataFrame:
    """Columns: rank, club, country, level, elo, from, to (rank may be 'None')."""
    df = _normalize_columns(_read_csv(text, context=f"club={club}"))
    if "rank" in df.columns:
        df["rank"] = pd.to_numeric(df["rank"], errors="coerce")
    df.insert(0, "query_club", club)
    return df


def parse_fixtures(text: str) -> pd.DataFrame:
    """Upcoming fixtures with per-goal-difference and exact-result probabilities."""
    return _normalize_columns(_read_csv(text, context="fixtures"))

"""
Parsers for eloratings.net TSV files.

The site does not publish a documented API. Column names below are inferred
from the live site's display and match common Elo-ratings semantics, but they
are **best-effort**: if eloratings.net changes its data layout, these parsers
may silently mis-label columns. Report any discrepancies as an issue.
"""

from io import StringIO
from typing import Optional

import pandas as pd

from datafc.exceptions import DataNotAvailableError


_UNICODE_MINUS = "−"


def _read_tsv(text: str, *, context: str, names) -> pd.DataFrame:
    if not text or not text.strip():
        raise DataNotAvailableError(f"Empty response from eloratings.net for {context}.")
    df = pd.read_csv(
        StringIO(text),
        sep="\t",
        header=None,
        names=names,
        dtype=str,
        keep_default_na=False,
        na_values=[""],
    )
    if df.empty:
        raise DataNotAvailableError(f"No rows returned from eloratings.net for {context}.")
    return df


def _to_numeric_minus_aware(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.str.replace(_UNICODE_MINUS, "-", regex=False), errors="coerce")


_WORLD_ALL_COLUMNS = [
    "_local_rank", "rank", "country", "elo",
    "rank_high", "elo_high",
    "rank_avg", "elo_avg",
    "rank_low", "elo_low",
    "chg_3m_rank", "chg_3m_elo",
    "chg_6m_rank", "chg_6m_elo",
    "chg_1y_rank", "chg_1y_elo",
    "chg_2y_rank", "chg_2y_elo",
    "chg_5y_rank", "chg_5y_elo",
    "chg_10y_rank", "chg_10y_elo",
    "matches_total",
    "matches_home", "matches_away", "matches_neutral",
    "wins", "losses", "draws",
    "goals_for", "goals_against",
]

WORLD_COLUMNS = [c for c in _WORLD_ALL_COLUMNS if not c.startswith("_")]


def parse_world_ranking(text: str) -> pd.DataFrame:
    df = _read_tsv(text, context="World ranking", names=_WORLD_ALL_COLUMNS)
    df = df[WORLD_COLUMNS]
    for col in df.columns:
        if col == "country":
            continue
        df[col] = _to_numeric_minus_aware(df[col])
    return df


_COUNTRY_RAW_COLUMNS = [
    "year", "month", "day",
    "team_a", "team_b",
    "team_a_score", "team_b_score",
    "tournament", "host",
    "points",
    "team_a_rating", "team_b_rating",
    "team_a_rank_change", "team_b_rank_change",
    "team_a_rank", "team_b_rank",
]

COUNTRY_MATCH_COLUMNS = [
    "query_country", "date",
    "team_a", "team_b",
    "team_a_score", "team_b_score",
    "tournament", "host",
    "points",
    "team_a_rating", "team_b_rating",
    "team_a_rank_change", "team_b_rank_change",
    "team_a_rank", "team_b_rank",
]


def parse_country_matches(text: str, country: str) -> pd.DataFrame:
    df = _read_tsv(text, context=f"country={country}", names=_COUNTRY_RAW_COLUMNS)

    for col in ("year", "month", "day",
                "team_a_score", "team_b_score", "points",
                "team_a_rating", "team_b_rating",
                "team_a_rank_change", "team_b_rank_change",
                "team_a_rank", "team_b_rank"):
        df[col] = _to_numeric_minus_aware(df[col])

    df["date"] = pd.to_datetime(
        dict(year=df["year"], month=df["month"], day=df["day"]),
        errors="coerce",
    )
    df.insert(0, "query_country", country)
    return df[COUNTRY_MATCH_COLUMNS]


def parse_teams(text: str) -> pd.DataFrame:
    """Legacy/alternate country code → ISO-style code mapping."""
    return _read_tsv(text, context="teams", names=["legacy_code", "iso_code"])


def _parse_code_lookup(text: str, *, context: str, code_col: str, name_col: str,
                       skip_suffix: Optional[str] = None) -> pd.DataFrame:
    """Read a label TSV (code <tab> name <tab> abbr1 ...). Variable column count
    per row — we keep only the code and the first (canonical) name."""
    if not text or not text.strip():
        raise DataNotAvailableError(f"Empty response from eloratings.net for {context}.")
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 2)
        if len(parts) < 2:
            continue
        code, name = parts[0].strip(), parts[1].strip()
        if skip_suffix and code.endswith(skip_suffix):
            continue
        rows.append((code, name))
    if not rows:
        raise DataNotAvailableError(f"No rows returned from eloratings.net for {context}.")
    return pd.DataFrame(rows, columns=[code_col, name_col])


def parse_country_codes(text: str) -> pd.DataFrame:
    """Country code → English country name. Drops the ``*_loc`` location strings
    (e.g. ``BS_loc → in the Bahamas``) that the site uses for venue captions."""
    return _parse_code_lookup(
        text, context="country codes",
        code_col="country_code", name_col="country_name",
        skip_suffix="_loc",
    )


def parse_tournament_codes(text: str) -> pd.DataFrame:
    """Tournament code → English tournament name."""
    return _parse_code_lookup(
        text, context="tournament codes",
        code_col="tournament_code", name_col="tournament_name",
    )


_EDITION_COLUMNS = ["code", "depth", "label", "start_date", "end_date", "slug"]


def parse_tournament_editions(text: str) -> pd.DataFrame:
    """Hierarchical tournament navigation tree from ``menu.tsv``.

    Each row is either a group header (no dates, no slug) used to build the
    site's sidebar tree, or a specific tournament edition with start/end
    dates and a page slug (e.g. ``2026_World_Cup_qualifying``).

    Columns: ``code, depth, label, start_date, end_date, slug``. To restrict
    to playable editions only, filter ``df[df["start_date"].notna()]``.
    """
    if not text or not text.strip():
        raise DataNotAvailableError("Empty response from eloratings.net for tournament editions.")
    rows = []
    for line in text.splitlines():
        if not line:
            continue
        parts = line.split("\t")
        parts = (parts + [""] * 6)[:6]
        rows.append(tuple(p.strip() for p in parts))
    if not rows:
        raise DataNotAvailableError("No rows returned from eloratings.net for tournament editions.")
    df = pd.DataFrame(rows, columns=_EDITION_COLUMNS)
    df["depth"] = pd.to_numeric(df["depth"], errors="coerce").astype("Int64")
    df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
    df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
    df = df.replace({"": pd.NA})
    return df


def parse_tournament_groups(text: str) -> pd.DataFrame:
    """Specific tournament code → parent/group code(s), in long format.

    The TSV stores variable-width rows like ``WCQ\\tWQT\\tNQT``, meaning the
    ``WCQ`` code rolls up into both the ``WQT`` (World Cup qualifier) and
    ``NQT`` (North American qualifier) groups. We expand each parent into its
    own row so the result can be joined / filtered cleanly.
    """
    if not text or not text.strip():
        raise DataNotAvailableError("Empty response from eloratings.net for tournament groups.")
    rows = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split("\t") if p.strip()]
        if len(parts) < 2:
            continue
        code, parents = parts[0], parts[1:]
        for parent in parents:
            rows.append((code, parent))
    if not rows:
        raise DataNotAvailableError("No rows returned from eloratings.net for tournament groups.")
    return pd.DataFrame(rows, columns=["tournament_code", "group_code"])

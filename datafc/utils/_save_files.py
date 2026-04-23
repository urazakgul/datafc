import json
import logging
import os
import re
import unicodedata
import pandas as pd

logger = logging.getLogger(__name__)

# Characters that NFKD decomposition cannot handle — map them explicitly before
# normalizing. NFKD handles most accented Latin chars (ü→u, ç→c, ñ→n, etc.)
# but leaves a few untouched.
_TRANSLITERATE = str.maketrans({
    'ı': 'i', 'İ': 'i',          # Turkish dotless-i
    'ß': 'ss',                    # German sharp-s
    'æ': 'ae', 'Æ': 'ae',        # Nordic
    'ø': 'o',  'Ø': 'o',
    'đ': 'd',  'Đ': 'd',          # South-Slavic
    'ł': 'l',  'Ł': 'l',          # Polish
    'þ': 'th', 'Þ': 'th',         # Icelandic
})


def _slugify(text: str) -> str:
    text = text.translate(_TRANSLITERATE)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s]", "", text)
    return text.lower().replace(" ", "_")


def _build_filename(
    ext: str,
    data_source: str,
    country: str,
    tournament: str,
    fn_name: str,
    season=None,
    week_number=None,
) -> str:
    t_slug = _slugify(str(tournament))
    if t_slug.isdigit():
        logger.warning(
            "tournament value %r looks like a raw numeric ID — "
            "resolve_tournament_season may have failed. Filename will use the ID.",
            tournament,
        )

    parts = [p for p in [data_source, _slugify(str(country)), t_slug] if p]

    if season is not None:
        s = str(season)
        if s.isdigit() and len(s) > 4:
            logger.warning(
                "season value %r looks like a raw season_id, not a year string "
                "(expected e.g. '25/26'). Filename may be wrong.",
                season,
            )
        parts.append(s.replace("/", ""))

    if week_number is not None:
        parts.append(str(week_number))

    parts.append(fn_name)
    return ".".join(["_".join(parts), ext])


def _warn_overwrite(file_path: str) -> None:
    if os.path.exists(file_path):
        logger.warning("Overwriting existing file: %s", file_path)


def save_json(
    data: pd.DataFrame,
    fn_name: str,
    data_source: str,
    country: str,
    tournament: str,
    season=None,
    week_number=None,
    output_dir: str = ".",
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    file_name = _build_filename("json", data_source, country, tournament, fn_name, season, week_number)
    file_path = os.path.join(output_dir, file_name)
    _warn_overwrite(file_path)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            records = json.loads(data.to_json(orient="records", force_ascii=False))
            json.dump(records, f, ensure_ascii=False, indent=4)
        logger.info("JSON saved: %s", file_path)
    except OSError as e:
        logger.error("Error saving JSON to %s: %s", file_path, e)


def save_excel(
    data: pd.DataFrame,
    fn_name: str,
    data_source: str,
    country: str,
    tournament: str,
    season=None,
    week_number=None,
    output_dir: str = ".",
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    file_name = _build_filename("xlsx", data_source, country, tournament, fn_name, season, week_number)
    file_path = os.path.join(output_dir, file_name)
    _warn_overwrite(file_path)
    try:
        data.to_excel(file_path, index=False)
        logger.info("Excel saved: %s", file_path)
    except OSError as e:
        logger.error("Error saving Excel to %s: %s", file_path, e)


def save_parquet(
    data: pd.DataFrame,
    fn_name: str,
    data_source: str,
    country: str,
    tournament: str,
    season=None,
    week_number=None,
    output_dir: str = ".",
) -> None:
    try:
        import pyarrow  # noqa: F401
    except ImportError:
        logger.error(
            "Parquet export requires pyarrow. Install it with: pip install pyarrow"
        )
        return
    os.makedirs(output_dir, exist_ok=True)
    file_name = _build_filename("parquet", data_source, country, tournament, fn_name, season, week_number)
    file_path = os.path.join(output_dir, file_name)
    _warn_overwrite(file_path)
    try:
        data.to_parquet(file_path, index=False)
        logger.info("Parquet saved: %s", file_path)
    except OSError as e:
        logger.error("Error saving Parquet to %s: %s", file_path, e)

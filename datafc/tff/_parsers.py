"""
BeautifulSoup parsers for tff.org pages.

TFF pages are ASP.NET WebForms output where element ``id`` attributes contain
long prefixes (``ctl00_MPane_..._``) and inner control names that occasionally
lie about the field's meaning (a ``lblPuan`` cell may hold the "loss" count).

To stay robust we prefer:
    * CSS classes tied to visible layout (``.haftaninMaclariTr``, ``.s-table``,
      ``.dtMacBilgisiLeftCol``, ``.dtMacBilgisiHakemler``)
    * Column position within table rows
    * Label-text matching for two-column key/value tables on club pages

Direct id lookups are used only when the tail of the id is stable across the
site (``[id$="_lnkTakim1"]``, ``[id$="_lblKod"]`` etc.).
"""

import re
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import pandas as pd
from bs4 import BeautifulSoup, Tag

from datafc.exceptions import DataNotAvailableError, InvalidParameterError


_POSITION_PREFIX_RE = re.compile(r"^\s*(\d+)\.\s*(.+?)\s*$")


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _extract_query_int(url: str, key: str) -> Optional[int]:
    """Case-insensitive query-string int extractor.

    tff.org mixes ``kulupID``/``kulupId``, ``pageID``/``pageId``, so a plain
    ``parse_qs`` lookup by key can miss half the links.
    """
    if not url:
        return None
    qs = parse_qs(urlparse(url).query, keep_blank_values=True)
    lowered = {k.lower(): v for k, v in qs.items()}
    values = lowered.get(key.lower())
    if not values:
        return None
    try:
        return int(values[0])
    except (TypeError, ValueError):
        return None


def _to_int(text: Optional[str]) -> Optional[int]:
    if text is None:
        return None
    stripped = text.strip()
    if not stripped:
        return None
    try:
        return int(stripped)
    except ValueError:
        return None


def _clean(text: Optional[str]) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def parse_fixtures(html: str, *, page_id: int, week: int) -> pd.DataFrame:
    """Parse the fixture list for a matchweek.

    tff.org uses two different fixture layouts:

    * **Rich** (`tr.haftaninMaclariTr`) on Süper Lig and 1. Lig pages — one
      row per match with date, time, home/away teams, score, match id.
    * **Compact** (`table.fiksturListesiTable`) on 2. Lig and 3. Lig pages —
      grouped tables of ``home | " - " | away`` links only. Date, time, and
      score are NOT present; those fields come back as ``None``/empty and
      must be enriched via ``match_details_data`` per match if needed.

    Compact-layout pages typically host multiple groups (Kırmızı / Beyaz for
    2. Lig) on the same page; both groups are returned in one DataFrame with
    a ``group`` column identifying each fixture's block.
    """
    soup = _soup(html)
    rows: List[Dict[str, Any]] = []
    row_modules: List[Optional[Tag]] = []

    for tr in soup.select("tr.haftaninMaclariTr"):
        date_cell = tr.select_one("td.haftaninMaclariTarih")
        home_cell = tr.select_one("td.haftaninMaclariEv")
        score_cell = tr.select_one("td.haftaninMaclariSkor")
        away_cell = tr.select_one("td.haftaninMaclariDeplasman")
        detail_cell = tr.select_one("td.haftaninMaclariDetay")

        date_spans = date_cell.find_all("span") if date_cell else []
        date_text = _clean(date_spans[0].get_text()) if len(date_spans) >= 1 else ""
        time_text = _clean(date_spans[1].get_text()) if len(date_spans) >= 2 else ""

        home_link = home_cell.find("a") if home_cell else None
        away_link = away_cell.find("a") if away_cell else None
        home_team = _clean(home_link.get_text()) if home_link else ""
        away_team = _clean(away_link.get_text()) if away_link else ""
        home_team_id = _extract_query_int(home_link.get("href", "") if home_link else "", "kulupID")
        away_team_id = _extract_query_int(away_link.get("href", "") if away_link else "", "kulupID")

        score_spans = score_cell.find_all("span") if score_cell else []
        home_score = _to_int(score_spans[0].get_text()) if len(score_spans) >= 1 else None
        away_score = _to_int(score_spans[1].get_text()) if len(score_spans) >= 2 else None

        detail_link = detail_cell.find("a") if detail_cell else None
        match_id = _extract_query_int(detail_link.get("href", "") if detail_link else "", "macId")
        if match_id is None and score_cell is not None:
            score_link = score_cell.find("a")
            if score_link is not None:
                match_id = _extract_query_int(score_link.get("href", ""), "macId")

        rows.append({
            "page_id": page_id,
            "week": week,
            "group": "",
            "match_id": match_id,
            "date": date_text,
            "time": time_text,
            "home_team": home_team,
            "home_team_id": home_team_id,
            "away_team": away_team,
            "away_team_id": away_team_id,
            "home_score": home_score,
            "away_score": away_score,
        })
        row_modules.append(tr.find_parent("div", class_="haftaninMaclariModul"))

    # Fallback to compact layout (2. Lig / 3. Lig grouped pages).
    if not rows:
        rows.extend(_parse_fixtures_compact(soup, page_id=page_id, week=week))

    kupa_rows = _parse_fixtures_kupa(
        soup, page_id=page_id, week=week, staged_only=bool(rows)
    )
    if kupa_rows and rows:
        for row, module in zip(rows, row_modules):
            if module is not None:
                row["group"] = _table_title(module)
    rows.extend(kupa_rows)

    if not rows:
        raise DataNotAvailableError(
            f"No fixtures found for pageID={page_id}, hafta={week}."
        )
    return pd.DataFrame(rows).drop_duplicates().reset_index(drop=True)


_WEEK_HEADER_RE = re.compile(r"^\s*(\d+)\s*\.\s*Hafta\s*$", re.IGNORECASE)


def _parse_fixtures_compact(soup: BeautifulSoup, *, page_id: int, week: int) -> List[Dict[str, Any]]:
    """Parse the compact ``fiksturListesiTable`` layout used by 2/3. Lig.

    Each panel (``table.fiksturListesiTable``) hosts one group's *entire
    season* — all 34 weeks stacked as sibling ``<table class="softBG">``
    blocks. Each block starts with a ``<td class="belirginYazi">N.Hafta</td>``
    header followed by the week's match rows. We identify the group from the
    ``<span>`` sibling that precedes the panel and filter blocks to the
    requested week.
    """
    rows: List[Dict[str, Any]] = []
    for panel in soup.find_all("table", class_="fiksturListesiTable"):
        group_name = ""
        prev = panel.find_previous("span")
        if prev is not None:
            header_text = _clean(prev.get_text(separator="|"))
            for token in ("Kırmızı Grup", "Beyaz Grup", "Kırmızı", "Beyaz"):
                if token in header_text:
                    group_name = token
                    break
            if not group_name:
                for seg in header_text.split("|"):
                    if "Grup" in seg:
                        group_name = seg.strip()
                        break

        for week_block in panel.find_all("table", class_="softBG"):
            header_cell = week_block.find("td", class_="belirginYazi")
            if header_cell is None:
                continue
            m = _WEEK_HEADER_RE.match(_clean(header_cell.get_text()))
            if not m or int(m.group(1)) != week:
                continue

            for tr in week_block.find_all("tr"):
                tds = tr.find_all("td", recursive=False)
                if len(tds) != 3:
                    continue
                home_link = tds[0].find("a", href=re.compile(r"kulup[Ii][Dd]=", re.IGNORECASE))
                match_link = tds[1].find("a", href=re.compile(r"macId=", re.IGNORECASE))
                away_link = tds[2].find("a", href=re.compile(r"kulup[Ii][Dd]=", re.IGNORECASE))
                if not (home_link and away_link and match_link):
                    continue
                rows.append({
                    "page_id": page_id,
                    "week": week,
                    "group": group_name,
                    "match_id": _extract_query_int(match_link.get("href", ""), "macId"),
                    "date": "",
                    "time": "",
                    "home_team": _clean(home_link.get_text()),
                    "home_team_id": _extract_query_int(home_link.get("href", ""), "kulupId"),
                    "away_team": _clean(away_link.get_text()),
                    "away_team_id": _extract_query_int(away_link.get("href", ""), "kulupId"),
                    "home_score": None,
                    "away_score": None,
                })
    return rows


_KUPA_GROUP_RE = re.compile(r"«\s*(.+?)\s*\(\s*\d+\s*\.\s*hafta\s*\)\s*»", re.IGNORECASE)


_STAGED_TITLE_RE = re.compile(r"Klasman|Kademe", re.IGNORECASE)


def _parse_fixtures_kupa(
    soup: BeautifulSoup, *, page_id: int, week: int, staged_only: bool = False
) -> List[Dict[str, Any]]:
    """Parse the ``kupaMaclari`` layout (``« 01 (5.hafta) »`` group modules)."""
    rows: List[Dict[str, Any]] = []
    modules: Dict[str, Tag] = {}
    for span in soup.find_all(id=re.compile(r"_kupaMaclari_ctl\d+_lblSkor$")):
        module = span.find_parent(id=re.compile(r"ctnr_div$"))
        if module is not None:
            modules.setdefault(module.get("id", ""), module)

    for module in modules.values():
        m = _KUPA_GROUP_RE.search(_clean(module.get_text(" ")))
        if m is None:
            continue
        if staged_only and not _STAGED_TITLE_RE.search(_table_title(module)):
            continue
        group_name = m.group(1)
        for score_link in module.find_all(id=re.compile(r"_kupaMaclari_ctl\d+_lblSkor$")):
            prefix = score_link["id"][: -len("lblSkor")]
            tarih = module.find(id=prefix + "lblTarih")
            saat = module.find(id=prefix + "lbSaat")
            home_link = module.find(id=prefix + "lblTakim1")
            away_link = module.find(id=prefix + "lblTakim2")
            if home_link is None or away_link is None:
                continue
            home_score = away_score = None
            sm = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", _clean(score_link.get_text()))
            if sm:
                home_score, away_score = int(sm.group(1)), int(sm.group(2))
            rows.append({
                "page_id": page_id,
                "week": week,
                "group": group_name,
                "match_id": _extract_query_int(score_link.get("href", ""), "macId"),
                "date": _clean(tarih.get_text()) if tarih else "",
                "time": _clean(saat.get_text()) if saat else "",
                "home_team": _clean(home_link.get_text()),
                "home_team_id": _extract_query_int(home_link.get("href", ""), "kulupID"),
                "away_team": _clean(away_link.get_text()),
                "away_team_id": _extract_query_int(away_link.get("href", ""), "kulupID"),
                "home_score": home_score,
                "away_score": away_score,
            })
    return rows


def parse_stage_fixtures(
    html: str, *, page_id: int, week: int, stage: str
) -> pd.DataFrame:
    """Parse one stage group's weekly fixtures (2011/12 Süper Final)."""
    soup = _soup(html)
    modules: Dict[str, Tag] = {}
    for span in soup.find_all(id=re.compile(r"_kupaMaclari_ctl\d+_lblSkor$")):
        module = span.find_parent(id=re.compile(r"ctnr_div$"))
        if module is not None:
            modules.setdefault(module.get("id", ""), module)

    if not modules:
        raise DataNotAvailableError(
            f"No stage fixtures found for pageID={page_id}, hafta={week}."
        )

    titled = [(_table_title(module), module) for module in modules.values()]
    wanted = stage.strip().lower()
    matched = [(title, module) for title, module in titled if wanted in title.lower()]
    if not matched:
        raise InvalidParameterError(
            f"stage={stage!r} matched no fixtures on pageID={page_id}, hafta={week}. "
            f"Available: {[title for title, _ in titled]}."
        )

    rows: List[Dict[str, Any]] = []
    for title, module in matched:
        for score_link in module.find_all(id=re.compile(r"_kupaMaclari_ctl\d+_lblSkor$")):
            prefix = score_link["id"][: -len("lblSkor")]
            tarih = module.find(id=prefix + "lblTarih")
            saat = module.find(id=prefix + "lbSaat")
            home_link = module.find(id=prefix + "lblTakim1")
            away_link = module.find(id=prefix + "lblTakim2")
            if home_link is None or away_link is None:
                continue
            home_score = away_score = None
            m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", _clean(score_link.get_text()))
            if m:
                home_score, away_score = int(m.group(1)), int(m.group(2))
            rows.append({
                "page_id": page_id,
                "week": week,
                "stage": title,
                "group": "",
                "match_id": _extract_query_int(score_link.get("href", ""), "macId"),
                "date": _clean(tarih.get_text()) if tarih else "",
                "time": _clean(saat.get_text()) if saat else "",
                "home_team": _clean(home_link.get_text()),
                "home_team_id": _extract_query_int(home_link.get("href", ""), "kulupID"),
                "away_team": _clean(away_link.get_text()),
                "away_team_id": _extract_query_int(away_link.get("href", ""), "kulupID"),
                "home_score": home_score,
                "away_score": away_score,
            })

    if not rows:
        raise DataNotAvailableError(
            f"No stage fixtures parsed for pageID={page_id}, hafta={week}."
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Playoff fixtures
# ---------------------------------------------------------------------------


_ROUND_NORMALIZE = {
    "1.Tur Maçları": "1. Tur",
    "2.Tur Maçları": "2. Tur",
    "3.Tur Maçları": "3. Tur",
    "Yarı Final Maçları": "Yarı Final",
    "Yarı Finaller": "Yarı Final",
    "Final Maçları": "Final",
    "Finaller": "Final",
}


def _normalize_round(label: str) -> str:
    label = _clean(label)
    if not label:
        return ""
    if label in _ROUND_NORMALIZE:
        return _ROUND_NORMALIZE[label]
    return label.replace("Maçları", "").strip()


_PLAYOFF_DATETIME_RE = re.compile(r"^(?P<date>.+?)\s+(?P<time>\d{1,2}:\d{2})\s*$")


def _split_playoff_datetime(text: str) -> tuple:
    text = _clean(text)
    m = _PLAYOFF_DATETIME_RE.match(text)
    if m:
        return m.group("date").strip(), m.group("time").strip()
    return text, ""


def parse_playoff_fixtures(html: str, *, page_id: int) -> pd.DataFrame:
    """Parse the season's play-off fixtures rendered on a league page.

    Playoff matches live in a module whose ``moduleTitle`` contains
    ``Play-Off`` (e.g. ``Trendyol 1. Lig 2025-2026 Sezonu Play-Off
    Müsabakaları``). Rows are grouped by round; the round label
    (``1.Tur Maçları``, ``2.Tur Maçları``, ``Final Maçları``…) appears
    only on the first row of each round and is inherited by subsequent
    rows. Scores may include extra-time or penalty-shootout results:

    * ``1-0`` — 90-minute result.
    * ``1-0 (Uzt. 2-0)`` — 90-minute 1-0, after extra time 2-0.
    * ``0-0 (Pen. 8-7)`` — 90 (and possibly extra time) 0-0, penalties 8-7.

    ``home_score``/``away_score`` reflect the 90-minute result; separate
    ``extra_time_home``/``extra_time_away`` and
    ``penalty_home``/``penalty_away`` columns hold the tie-breaker results
    (``None`` when not applicable).
    """
    soup = _soup(html)

    container: Optional[Tag] = None
    for div in soup.find_all(class_="moduleTitle"):
        text = div.get_text()
        if "Play-Off" in text or "Play Off" in text or "PlayOff" in text:
            p: Optional[Tag] = div
            for _ in range(6):
                p = p.parent if p is not None else None
                if p is None:
                    break
                cid = p.get("id") if hasattr(p, "get") else None
                if cid and "ctnr_div" in cid:
                    container = p
                    break
            if container is not None:
                break

    if container is None:
        raise DataNotAvailableError(
            f"No play-off module found for pageID={page_id}."
        )

    # Iterate ctlNN groups in order and carry the current round across rows
    # that don't set their own header.
    ctl_ids = set()
    for span in container.find_all(id=re.compile(r"_kupaMaclari_ctl(\d+)_")):
        m = re.search(r"_kupaMaclari_ctl(\d+)_", span.get("id", ""))
        if m:
            ctl_ids.add(m.group(1))

    rows: List[Dict[str, Any]] = []
    current_round = ""
    for ctl in sorted(ctl_ids):
        # Round header (may be empty for follow-on rows).
        grup_span = container.find(id=re.compile(rf"_kupaMaclari_ctl{ctl}_lblGrup$"))
        if grup_span is not None:
            label = _normalize_round(grup_span.get_text())
            if label:
                current_round = label

        tarih_span = container.find(id=re.compile(rf"_kupaMaclari_ctl{ctl}_lblTarih$"))
        home_link = container.find(id=re.compile(rf"_kupaMaclari_ctl{ctl}_lblTakim1$"))
        skor_link = container.find(id=re.compile(rf"_kupaMaclari_ctl{ctl}_lblSkor$"))
        away_link = container.find(id=re.compile(rf"_kupaMaclari_ctl{ctl}_lblTakim2$"))
        if not (tarih_span and home_link and skor_link and away_link):
            continue

        date_text, time_text = _split_playoff_datetime(tarih_span.get_text())

        home_score = away_score = None
        raw_score = _clean(skor_link.get_text())
        m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", raw_score)
        if m:
            home_score = int(m.group(1))
            away_score = int(m.group(2))

        # Tie-breaker: label reads "(Uzt." or "(Pen." and score-after is "2-0)" or "8-7)".
        extra_home = extra_away = None
        pen_home = pen_away = None
        info_span = container.find(id=re.compile(rf"_kupaMaclari_ctl{ctl}_lblSkor90SonrasiBilgi$"))
        after_span = container.find(id=re.compile(rf"_kupaMaclari_ctl{ctl}_lblSkor90Sonrasi$"))
        if info_span is not None and after_span is not None:
            info = _clean(info_span.get_text())
            after = _clean(after_span.get_text()).rstrip(")").strip()
            am = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", after)
            if am:
                a_h, a_a = int(am.group(1)), int(am.group(2))
                if "Uzt" in info:
                    extra_home, extra_away = a_h, a_a
                elif "Pen" in info:
                    pen_home, pen_away = a_h, a_a

        rows.append({
            "page_id": page_id,
            "playoff": True,
            "round": current_round,
            "match_id": _extract_query_int(skor_link.get("href", ""), "macId"),
            "date": date_text,
            "time": time_text,
            "home_team": _clean(home_link.get_text()),
            "home_team_id": _extract_query_int(home_link.get("href", ""), "kulupID"),
            "away_team": _clean(away_link.get_text()),
            "away_team_id": _extract_query_int(away_link.get("href", ""), "kulupID"),
            "home_score": home_score,
            "away_score": away_score,
            "extra_time_home": extra_home,
            "extra_time_away": extra_away,
            "penalty_home": pen_home,
            "penalty_away": pen_away,
        })

    if not rows:
        raise DataNotAvailableError(
            f"No play-off matches parsed for pageID={page_id}."
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Standings
# ---------------------------------------------------------------------------


def parse_group_ids(html: str) -> Dict[str, int]:
    """Return the mapping of visible group labels to TFF's ``grupID`` values.

    Multi-group leagues (2. Lig ``Kırmızı`` / ``Beyaz``, 3. Lig ``01`` / ``02``
    / ``03`` / ``04``) expose group switching via a sidebar of anchors whose
    ``href`` carries ``grupID=<int>``. We collect one entry per anchor text
    so callers can resolve a human-readable group name to the numeric id.
    Returns an empty dict on single-group pages.
    """
    soup = _soup(html)
    mapping: Dict[str, int] = {}
    for a in soup.find_all("a", href=re.compile(r"grupID=", re.IGNORECASE)):
        label = _clean(a.get_text())
        if not label or label in mapping:
            continue
        gid = _extract_query_int(a.get("href", ""), "grupID")
        if gid is not None:
            mapping[label] = gid
    return mapping


class StandingsNotPublishedError(DataNotAvailableError):
    """The page carries no league table at all (e.g. Süper Lig 1959-1983/84)."""


def _table_title(table: Tag) -> str:
    """Return the nearest non-empty module title above ``table``."""
    for div in table.find_all_previous("div", class_="moduleTitle"):
        title = _clean(div.get_text())
        if title:
            return title
    return ""


def _parse_standings_table(table: Tag, *, page_id: int, week: int) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for tr in table.select("tr"):
        # Header row uses class ``griBG`` on the <tr>; data rows put class on the <td>.
        if "griBG" in (tr.get("class") or []):
            continue
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 9:
            continue
        link = tds[0].find("a")
        if link is None:
            continue
        raw_name = _clean(link.get_text())
        team_id = _extract_query_int(link.get("href", ""), "kulupID")

        position: Optional[int]
        team_name: str
        m = _POSITION_PREFIX_RE.match(raw_name)
        if m:
            position = int(m.group(1))
            team_name = m.group(2)
        else:
            position = None
            team_name = raw_name

        stat_cells = tds[1:9]
        stats = [_to_int(_clean(td.get_text())) for td in stat_cells]

        rows.append({
            "page_id": page_id,
            "week": week,
            "position": position,
            "team_name": team_name,
            "team_id": team_id,
            "played": stats[0],
            "wins": stats[1],
            "draws": stats[2],
            "losses": stats[3],
            "goals_for": stats[4],
            "goals_against": stats[5],
            "goal_diff": stats[6],
            "points": stats[7],
        })
    return pd.DataFrame(rows)


def _table_has_group(table: Tag, group_id: int) -> bool:
    """Whether the module around ``table`` links to ``grupID=group_id``."""
    module = table.find_parent(id=re.compile(r"ctnr_div$"))
    if module is None:
        return False
    pattern = re.compile(rf"grupID={group_id}(?!\d)", re.IGNORECASE)
    return module.find("a", href=pattern) is not None


def parse_standings(
    html: str,
    *,
    page_id: int,
    week: int,
    stage: Optional[str] = None,
    group_id: Optional[int] = None,
) -> pd.DataFrame:
    """Parse a TFF standings page, choosing among its tables by ``stage``,
    ``group_id`` or, by default, the one with the most rows."""
    soup = _soup(html)
    tables = [
        (_table_title(t), df, t)
        for t in soup.select("table.s-table")
        for df in [_parse_standings_table(t, page_id=page_id, week=week)]
        if not df.empty
    ]
    if not soup.select_one("table.s-table"):
        raise StandingsNotPublishedError(
            f"No standings table found for pageID={page_id}, hafta={week}."
        )
    if not tables:
        raise DataNotAvailableError(
            f"No standings rows parsed for pageID={page_id}, hafta={week}."
        )

    if stage is None:
        if group_id is not None:
            for _, df, table in tables:
                if _table_has_group(table, group_id):
                    return df
        return max(tables, key=lambda t: len(t[1]))[1]

    wanted = stage.strip().lower()
    for title, df, _ in tables:
        if wanted in title.lower():
            df.insert(2, "stage", title)
            return df
    raise InvalidParameterError(
        f"stage={stage!r} matched no table on pageID={page_id}. "
        f"Available: {[title for title, _, _ in tables]}."
    )


# ---------------------------------------------------------------------------
# Match details
# ---------------------------------------------------------------------------


def _extract_side(container: Optional[Tag]) -> Dict[str, Any]:
    if container is None:
        return {"team": "", "team_id": None, "score": None}
    # Two anchors point at the same club page: the logo (image, no text) and
    # the name link. Skip the logo by picking the first one with visible text.
    team = ""
    team_id: Optional[int] = None
    for link in container.find_all("a", href=re.compile(r"kulup[Ii][Dd]=", re.IGNORECASE)):
        text = _clean(link.get_text())
        if not text:
            continue
        team = text
        team_id = _extract_query_int(link.get("href", ""), "kulupId")
        break
    score_p = container.find("p", class_="MacDetaySayi")
    score_span = score_p.find("span") if score_p else None
    score = _to_int(score_span.get_text()) if score_span else None
    return {"team": team, "team_id": team_id, "score": score}


def parse_match_details(html: str, *, match_id: int) -> pd.DataFrame:
    soup = _soup(html)

    home = _extract_side(soup.select_one(".dtMacBilgisiLeftCol"))
    away = _extract_side(soup.select_one(".dtMacBilgisiRightCol"))

    if not home["team"] and not away["team"]:
        raise DataNotAvailableError(f"No match details found for macId={match_id}.")

    org_span = soup.select_one('[id$="_lblOrganizasyonAdi"]')
    tournament = _clean(org_span.get_text()) if org_span else ""

    code_span = soup.select_one('[id$="_lblKod"]')
    match_code = _clean(code_span.get_text()) if code_span else ""

    date_span = soup.select_one('[id$="_lblTarih"]')
    date_text = _clean(date_span.get_text()) if date_span else ""
    date_part = time_part = ""
    if " - " in date_text:
        date_part, _, time_part = date_text.partition(" - ")
        date_part = date_part.strip()
        time_part = time_part.strip()
    else:
        date_part = date_text

    stadium_link = soup.select_one('[id$="_lnkStad"]')
    stadium_text = _clean(stadium_link.get_text()) if stadium_link else ""
    stadium_id = _extract_query_int(stadium_link.get("href", "") if stadium_link else "", "stadId")

    # "STADIUM - CITY - DISTRICT" pattern — split conservatively.
    stadium_name = stadium_text
    stadium_city = stadium_district = ""
    parts = [p.strip() for p in stadium_text.split(" - ")]
    if len(parts) >= 2:
        stadium_name = parts[0]
        stadium_city = parts[1]
    if len(parts) >= 3:
        stadium_district = parts[2]

    referees: List[Dict[str, Any]] = []
    ref_container = soup.select_one("div.dtMacBilgisiHakemler")
    if ref_container is not None:
        for a in ref_container.find_all("a"):
            text = _clean(a.get_text())
            role = ""
            name = text
            if text.endswith(")") and "(" in text:
                name, _, role_part = text.rpartition("(")
                name = name.strip()
                role = role_part.rstrip(")").strip()
            referees.append({
                "referee_id": _extract_query_int(a.get("href", ""), "hakemId"),
                "referee_name": name,
                "referee_role": role,
            })

    main_ref = next((r for r in referees if r["referee_role"].lower() == "hakem"), None)
    if main_ref is None and referees:
        main_ref = referees[0]

    row: Dict[str, Any] = {
        "match_id": match_id,
        "match_code": match_code,
        "tournament": tournament,
        "date": date_part,
        "time": time_part,
        "home_team": home["team"],
        "home_team_id": home["team_id"],
        "home_score": home["score"],
        "away_team": away["team"],
        "away_team_id": away["team_id"],
        "away_score": away["score"],
        "stadium_name": stadium_name,
        "stadium_id": stadium_id,
        "stadium_city": stadium_city,
        "stadium_district": stadium_district,
        "referee_id": main_ref["referee_id"] if main_ref else None,
        "referee_name": main_ref["referee_name"] if main_ref else "",
        "referees": referees,
    }
    return pd.DataFrame([row])


# ---------------------------------------------------------------------------
# Match: lineups, staff, goals, cards
# ---------------------------------------------------------------------------


_SIDE_BY_GRID = {"grdTakim1": "home", "grdTakim2": "away"}

_GOAL_TEXT_RE = re.compile(
    r"^(?P<name>.+?)\s*,\s*(?P<minute>\d+(?:\+\d+)?)\s*\.\s*dk"
    r"(?:\s*\((?P<note>[^)]+)\))?\s*$",
    re.IGNORECASE,
)


def _parse_minute(text: str) -> Optional[int]:
    """Return the base minute from strings like ``12``, ``45+2``, ``90+7``."""
    if not text:
        return None
    base = text.split("+", 1)[0]
    try:
        return int(base)
    except ValueError:
        return None


def _parse_minute_full(text: str) -> Optional[str]:
    """Return the display minute string (``"45+2"``) or None if unparsable."""
    if not text:
        return None
    m = re.match(r"^\s*(\d+(?:\+\d+)?)", text)
    return m.group(1) if m else None


def parse_match_lineups(html: str, *, match_id: int) -> pd.DataFrame:
    soup = _soup(html)
    rows: List[Dict[str, Any]] = []

    for grid, side in _SIDE_BY_GRID.items():
        for role, repeater in (("starter", "rptKadrolar"), ("sub", "rptYedekler")):
            pattern = re.compile(rf"_{grid}_{repeater}_ctl\d+_lnkOyuncu$")
            for anchor in soup.find_all("a", id=pattern):
                player_name = _clean(anchor.get_text())
                player_id = _extract_query_int(anchor.get("href", ""), "kisiId")
                # formaNo sits in the same <td> as the player link.
                parent_td = anchor.find_parent("td")
                jersey_no: Optional[int] = None
                if parent_td is not None:
                    forma_span = parent_td.find(
                        "span", id=re.compile(rf"_{grid}_{repeater}_ctl\d+_formaNo$")
                    )
                    if forma_span is not None:
                        # Displayed as "71." — strip the trailing dot before int().
                        jersey_text = _clean(forma_span.get_text()).rstrip(".")
                        jersey_no = _to_int(jersey_text)
                rows.append({
                    "match_id": match_id,
                    "team": side,
                    "role": role,
                    "jersey_no": jersey_no,
                    "player_id": player_id,
                    "player_name": player_name,
                })

    if not rows:
        raise DataNotAvailableError(f"No lineups parsed for macId={match_id}.")
    return pd.DataFrame(rows)


def parse_match_staff(html: str, *, match_id: int) -> pd.DataFrame:
    soup = _soup(html)
    rows: List[Dict[str, Any]] = []

    for grid, side in _SIDE_BY_GRID.items():
        pattern = re.compile(rf"_{grid}_rptTeknikKadro_ctl\d+_lnkTeknikSorumlu$")
        for anchor in soup.find_all("a", id=pattern):
            rows.append({
                "match_id": match_id,
                "team": side,
                "coach_id": _extract_query_int(anchor.get("href", ""), "antId"),
                "coach_name": _clean(anchor.get_text()),
            })

    if not rows:
        raise DataNotAvailableError(f"No technical staff parsed for macId={match_id}.")
    return pd.DataFrame(rows)


def parse_match_goals(html: str, *, match_id: int) -> pd.DataFrame:
    soup = _soup(html)
    rows: List[Dict[str, Any]] = []

    for grid, side in _SIDE_BY_GRID.items():
        pattern = re.compile(rf"_{grid}_rptGoller_ctl\d+_lblGol$")
        for anchor in soup.find_all("a", id=pattern):
            text = _clean(anchor.get_text())
            m = _GOAL_TEXT_RE.match(text)
            if m:
                name = m.group("name").strip()
                minute_str = m.group("minute")
                note = (m.group("note") or "").strip()
            else:
                # Fallback: keep raw text; downstream can inspect.
                name = text
                minute_str = ""
                note = ""
            rows.append({
                "match_id": match_id,
                "team": side,
                "player_id": _extract_query_int(anchor.get("href", ""), "kisiId"),
                "player_name": name,
                "minute": _parse_minute(minute_str),
                "minute_display": minute_str or None,
                "note": note,
            })

    if not rows:
        raise DataNotAvailableError(f"No goals parsed for macId={match_id}.")
    return pd.DataFrame(rows)


_CARD_ALT_MAP = {
    "sarı kart": "yellow",
    "kırmızı kart": "red",
    "ikinci sarı kart": "second_yellow",
    "kırmızı i̇kinci sarı": "second_yellow",
}


def _card_type_from_alt(alt: str) -> str:
    key = _clean(alt).lower()
    if key in _CARD_ALT_MAP:
        return _CARD_ALT_MAP[key]
    # Substring fallback for wording drift.
    if "ikinci" in key:
        return "second_yellow"
    if "kırmızı" in key:
        return "red"
    if "sarı" in key:
        return "yellow"
    return key or ""


def parse_match_cards(html: str, *, match_id: int) -> pd.DataFrame:
    soup = _soup(html)
    rows: List[Dict[str, Any]] = []

    for grid, side in _SIDE_BY_GRID.items():
        pattern = re.compile(rf"_{grid}_rptKartlar_ctl\d+_lblKart$")
        for anchor in soup.find_all("a", id=pattern):
            player_name = _clean(anchor.get_text())
            player_id = _extract_query_int(anchor.get("href", ""), "kisiId")

            ctl_match = re.search(r"_ctl(\d+)_lblKart$", anchor.get("id", ""))
            ctl = ctl_match.group(1) if ctl_match else ""

            img = anchor.find_previous(
                "img", id=re.compile(rf"_{grid}_rptKartlar_ctl{ctl}_k$")
            )
            card_type = _card_type_from_alt(img.get("alt", "")) if img else ""

            minute_span = anchor.find_next(
                "span", id=re.compile(rf"_{grid}_rptKartlar_ctl{ctl}_d$")
            )
            minute_text = _clean(minute_span.get_text()) if minute_span else ""

            rows.append({
                "match_id": match_id,
                "team": side,
                "player_id": player_id,
                "player_name": player_name,
                "card": card_type,
                "minute": _parse_minute(_parse_minute_full(minute_text) or ""),
                "minute_display": _parse_minute_full(minute_text),
            })

    if not rows:
        raise DataNotAvailableError(f"No cards parsed for macId={match_id}.")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Player profile + career
# ---------------------------------------------------------------------------


def _find_span_text(container: Tag, id_suffix: str) -> str:
    tag = container.find(id=re.compile(rf"{re.escape(id_suffix)}$"))
    return _clean(tag.get_text()) if tag else ""


def parse_player(html: str, *, player_id: int) -> pd.DataFrame:
    """Parse the personal-info + current-license block of a TFF player page.

    TFF's player page (``pageId=30&kisiId=...``) renders a ``oyuncuBilgileri``
    table with two sub-blocks: kişisel bilgiler (name, birthplace, birthdate,
    nationality, agent) and ``oyuncuLisansBilgileri`` (current licence: club,
    licence number, contract start/end, abroad-exit date). Career history
    (all prior clubs) is exposed separately by ``player_career_data``.
    """
    soup = _soup(html)
    profile = soup.find(id=re.compile(r"_OyuncuDisplay1_oyuncuBilgileri$"))
    if profile is None:
        raise DataNotAvailableError(f"No player profile for kisiId={player_id}.")

    licence = profile.find(id=re.compile(r"_oyuncuLisansBilgileri$"))

    name = _find_span_text(profile, "_lblAdi")
    birth_place = _find_span_text(profile, "_Label1")
    birth_date = _find_span_text(profile, "_Label2")
    nationality = _find_span_text(profile, "_Label3")
    agent = _find_span_text(profile, "_lblMenajer")
    # ``lblMenajer`` doubles as the label AND the value cell depending on
    # markup age; drop the label text if it matches the Turkish label.
    if agent.strip().lower() in ("futbolcu menajeri :", "futbolcu menajeri", "menajer :"):
        agent = ""

    licence_no = licence_club = licence_club_id = None
    contract_start = contract_end = abroad_exit = ""
    if licence is not None:
        licence_no = _find_span_text(licence, "_Label4")
        licence_club = _find_span_text(licence, "_Label5")
        contract_start = _find_span_text(licence, "_Label8")
        contract_end = _find_span_text(licence, "_Label9")
        abroad_exit = _find_span_text(licence, "_Label18")

    # TFF renders the current club as plain text on the licence card, but the
    # career grid below has an <a href="…kulupId=X">CLUB NAME</a> for every
    # row — pick the id off the most recent grid row whose team name matches.
    if licence_club:
        grid = soup.find("div", id=re.compile(r"_grdTakimlar$"))
        table = grid.find("table", class_="MasterTable_TFF_Contents") if grid else None
        if table is not None and table.find("tbody") is not None:
            for tr in reversed(table.find("tbody").find_all("tr")):
                team_link = tr.find("a", href=re.compile(r"kulup[Ii][Dd]=", re.IGNORECASE))
                if team_link is None:
                    continue
                if _clean(team_link.get_text()) == licence_club:
                    licence_club_id = _extract_query_int(team_link.get("href", ""), "kulupId")
                    break

    row = {
        "player_id": player_id,
        "player_name": name,
        "birth_place": birth_place,
        "birth_date": birth_date,
        "nationality": nationality,
        "agent": agent,
        "licence_no": licence_no,
        "current_club": licence_club,
        "current_club_id": licence_club_id,
        "contract_start": contract_start,
        "contract_end": contract_end,
        "abroad_exit_date": abroad_exit,
    }
    return pd.DataFrame([row])


def _find_master_grid(soup: BeautifulSoup) -> Optional[Tag]:
    """Return the RadGrid MasterTable used for tab-loaded player data."""
    return soup.find("table", class_="MasterTable_TFF_Contents")


def _grid_data_rows(table: Tag) -> List[Tag]:
    tbody = table.find("tbody") if table is not None else None
    if tbody is None:
        return []
    return tbody.find_all("tr", class_=re.compile(r"^Grid(Row|AltRow)_"))


_PLAYER_MINUTE_RE = re.compile(r"^\s*(\d+(?:\+\d+)?)")


def _parse_dk(text: str) -> tuple:
    """Turn ``"41.dk"`` / ``"90+2.dk"`` into (int_minute, display_string)."""
    if not text:
        return None, None
    m = _PLAYER_MINUTE_RE.match(_clean(text))
    if not m:
        return None, None
    disp = m.group(1)
    base = disp.split("+", 1)[0]
    try:
        return int(base), disp
    except ValueError:
        return None, disp


def parse_player_national_matches(html: str, *, player_id: int) -> pd.DataFrame:
    """Parse the Milli Maçlar tab: every appearance for a Turkey national team.

    Columns: tournament, home_team, away_team, home_score, away_score,
    match_id, date, category (``A Milli``, ``U19``, ``U21``…). One row per
    appearance across the player's whole career.
    """
    soup = _soup(html)
    table = _find_master_grid(soup)
    if table is None:
        raise DataNotAvailableError(
            f"No national-team matches for kisiId={player_id}."
        )
    rows: List[Dict[str, Any]] = []
    for tr in _grid_data_rows(table):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 6:
            continue
        skor_link = tds[2].find("a")
        home_score = away_score = None
        score_text = _clean(tds[2].get_text())
        m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", score_text)
        if m:
            home_score, away_score = int(m.group(1)), int(m.group(2))
        rows.append({
            "player_id": player_id,
            "tournament": _clean(tds[0].get_text()),
            "home_team": _clean(tds[1].get_text()),
            "home_score": home_score,
            "away_score": away_score,
            "away_team": _clean(tds[3].get_text()),
            "date": _clean(tds[4].get_text()),
            "category": _clean(tds[5].get_text()),
            "match_id": _extract_query_int(skor_link.get("href", "") if skor_link else "", "macId"),
        })
    if not rows:
        raise DataNotAvailableError(
            f"National-team grid is empty for kisiId={player_id}."
        )
    return pd.DataFrame(rows)


def parse_player_goals(html: str, *, player_id: int) -> pd.DataFrame:
    """Parse the Attığı Goller tab: every goal (club + national) in the player's
    licensed career visible to TFF.

    Columns: team, team_id, minute, minute_display, goal_type, match,
    tournament, date, season, match_id.
    """
    soup = _soup(html)
    table = _find_master_grid(soup)
    if table is None:
        raise DataNotAvailableError(f"No goals grid for kisiId={player_id}.")

    rows: List[Dict[str, Any]] = []
    for tr in _grid_data_rows(table):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 7:
            continue
        team_link = tds[0].find("a")
        match_link = tds[3].find("a")
        minute_int, minute_display = _parse_dk(tds[1].get_text())
        rows.append({
            "player_id": player_id,
            "team": _clean(team_link.get_text()) if team_link else _clean(tds[0].get_text()),
            "team_id": _extract_query_int(team_link.get("href", "") if team_link else "", "kulupId"),
            "minute": minute_int,
            "minute_display": minute_display,
            "goal_type": _clean(tds[2].get_text()),
            "match": _clean(match_link.get_text()) if match_link else _clean(tds[3].get_text()),
            "match_id": _extract_query_int(match_link.get("href", "") if match_link else "", "macId"),
            "tournament": _clean(tds[4].get_text()),
            "date": _clean(tds[5].get_text()),
            "season": _clean(tds[6].get_text()),
        })
    if not rows:
        raise DataNotAvailableError(f"Goals grid is empty for kisiId={player_id}.")
    return pd.DataFrame(rows)


def parse_player_club_matches(html: str, *, player_id: int, season: str) -> pd.DataFrame:
    """Parse the Maçlar tab for a single season.

    Columns: season, match_id, home_team, home_score, away_score, away_team,
    datetime, tournament.
    """
    soup = _soup(html)
    table = _find_master_grid(soup)
    if table is None:
        raise DataNotAvailableError(
            f"No club matches for kisiId={player_id}, season={season!r}."
        )
    rows: List[Dict[str, Any]] = []
    for tr in _grid_data_rows(table):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 6:
            continue
        detail_link = tds[0].find("a")
        home_score = away_score = None
        score_text = _clean(tds[2].get_text())
        m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", score_text)
        if m:
            home_score, away_score = int(m.group(1)), int(m.group(2))
        rows.append({
            "player_id": player_id,
            "season": season,
            "match_id": _extract_query_int(detail_link.get("href", "") if detail_link else "", "macId"),
            "home_team": _clean(tds[1].get_text()),
            "home_score": home_score,
            "away_score": away_score,
            "away_team": _clean(tds[3].get_text()),
            "datetime": _clean(tds[4].get_text()),
            "tournament": _clean(tds[5].get_text()),
        })
    if not rows:
        raise DataNotAvailableError(
            f"Club-matches grid is empty for kisiId={player_id}, season={season!r}."
        )
    return pd.DataFrame(rows)


def parse_player_cards(html: str, *, player_id: int, season: str) -> pd.DataFrame:
    """Parse the Kartlar tab for a single season.

    Columns: season, match_id, card (``"yellow"`` / ``"red"`` / ``"second_yellow"``),
    minute, minute_display, match (raw ``"HOME-AWAY"`` label from TFF's grid),
    datetime, tournament.
    """
    soup = _soup(html)
    table = _find_master_grid(soup)
    if table is None:
        raise DataNotAvailableError(
            f"No cards for kisiId={player_id}, season={season!r}."
        )
    rows: List[Dict[str, Any]] = []
    for tr in _grid_data_rows(table):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 6:
            continue
        detail_link = tds[0].find("a")
        card_img = tds[1].find("img")
        card_type = _card_type_from_alt(card_img.get("alt", "")) if card_img else ""
        minute_int, minute_display = _parse_dk(tds[2].get_text())
        rows.append({
            "player_id": player_id,
            "season": season,
            "match_id": _extract_query_int(detail_link.get("href", "") if detail_link else "", "macId"),
            "card": card_type,
            "minute": minute_int,
            "minute_display": minute_display,
            "match": _clean(tds[3].get_text()),
            "datetime": _clean(tds[4].get_text()),
            "tournament": _clean(tds[5].get_text()),
        })
    if not rows:
        raise DataNotAvailableError(
            f"Cards grid is empty for kisiId={player_id}, season={season!r}."
        )
    return pd.DataFrame(rows)


def parse_player_career(html: str, *, player_id: int) -> pd.DataFrame:
    """Parse the licence-per-season career table on a TFF player page.

    Returns one row per licence entry (TFF re-issues a licence every season
    even at the same club, so a long-serving amateur may have 8+ rows for the
    same team). Columns match TFF's grid headers: team, licence type,
    licence date, contract start/end, abroad-exit date.
    """
    soup = _soup(html)
    grid = soup.find("div", id=re.compile(r"_grdTakimlar$"))
    if grid is None:
        raise DataNotAvailableError(f"No career grid for kisiId={player_id}.")

    table = grid.find("table", class_="MasterTable_TFF_Contents")
    if table is None:
        raise DataNotAvailableError(
            f"No career grid rows for kisiId={player_id} (grid rendered empty)."
        )

    rows: List[Dict[str, Any]] = []
    for tr in table.find("tbody").find_all("tr"):
        classes = tr.get("class") or []
        if not any(c.startswith("GridRow") or c.startswith("GridAltRow") for c in classes):
            continue
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 6:
            continue
        team_link = tds[0].find("a")
        team_name = _clean(team_link.get_text()) if team_link else _clean(tds[0].get_text())
        team_id = _extract_query_int(team_link.get("href", ""), "kulupId") if team_link else None
        rows.append({
            "player_id": player_id,
            "team_id": team_id,
            "team_name": team_name,
            "contract_start": _clean(tds[1].get_text()),
            "contract_end": _clean(tds[2].get_text()),
            "licence_type": _clean(tds[3].get_text()),
            "licence_date": _clean(tds[4].get_text()),
            "abroad_exit_date": _clean(tds[5].get_text()),
        })

    if not rows:
        raise DataNotAvailableError(f"No career rows parsed for kisiId={player_id}.")
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Team (club + stadium)
# ---------------------------------------------------------------------------


def _find_field(container: Tag, label_text: str) -> str:
    """Locate a two-column table row inside ``container`` whose left cell
    contains ``label_text`` (case-insensitive, punctuation-tolerant) and
    return the trimmed text of the right cell.

    Some tff pages emit the colon separator as a text node inside the value
    cell (``:41135``) instead of after the label; we strip a leading colon
    so the returned value is always the raw content.
    """
    needle = re.sub(r"\s+", "", label_text).lower().rstrip(":")
    for tr in container.find_all("tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < 2:
            continue
        left = re.sub(r"\s+", "", tds[0].get_text()).lower().rstrip(":")
        if left == needle:
            value = _clean(tds[-1].get_text())
            return value.lstrip(":").strip()
    return ""


def parse_team(html: str, *, club_id: int) -> pd.DataFrame:
    soup = _soup(html)

    club_table = soup.select_one('table[id$="_dtKulupBilgisi"]')
    if club_table is None:
        raise DataNotAvailableError(f"No club table found for kulupID={club_id}.")

    name_link = club_table.select_one('a[id$="_lnkKulup"]')
    official_name = _clean(name_link.get_text()) if name_link else ""

    club_code = _find_field(club_table, "Kulüp Kodu")
    address = _find_field(club_table, "Adres")
    city = _find_field(club_table, "Şehir")
    region = _find_field(club_table, "Bölge")
    phone = _find_field(club_table, "Telefon")
    fax = _find_field(club_table, "Faks")
    president = _find_field(club_table, "Başkan")

    website_tag = club_table.find("a", href=re.compile(r"^https?://", re.IGNORECASE))
    website = website_tag.get("href", "").strip() if website_tag else ""

    stadium_table = soup.select_one('table[id$="_dtStadBilgisi"]')
    stadium_name = stadium_capacity = stadium_city = ""
    pitch_size = surface = lighting = seating = ""
    if stadium_table is not None:
        # First non-empty span is the stadium name.
        first_span = stadium_table.find("span")
        stadium_name = _clean(first_span.get_text()) if first_span else ""
        stadium_capacity = _find_field(stadium_table, "Seyirci Kapasitesi")
        stadium_city = _find_field(stadium_table, "Şehir")
        pitch_size = _find_field(stadium_table, "Oyun Alanı Ölçüsü")
        surface = _find_field(stadium_table, "Zemin Türü")
        lighting = _find_field(stadium_table, "Işıklandırma")
        seating = _find_field(stadium_table, "Koltuklandırma")

    row = {
        "club_id": club_id,
        "official_name": official_name,
        "club_code": club_code,
        "address": address,
        "city": city,
        "region": region,
        "phone": phone,
        "fax": fax,
        "president": president,
        "website": website,
        "stadium_name": stadium_name,
        "stadium_capacity": _to_int(stadium_capacity),
        "stadium_city": stadium_city,
        "pitch_size": pitch_size,
        "surface": surface,
        "lighting": lighting,
        "seating": seating,
    }
    return pd.DataFrame([row])

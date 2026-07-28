import logging
import re
import threading
import time
from typing import Dict, Optional

from bs4 import BeautifulSoup
from curl_cffi import requests as cf_requests

from datafc.exceptions import APIError, RateLimitError, ServerError
from datafc.utils._cache import get_default_cache

logger = logging.getLogger(__name__)

# tff.org serves pages in windows-1254 (Turkish encoding).
_TFF_ENCODING = "windows-1254"


class TFFClient:
    """
    HTTP client for the Turkish Football Federation (tff.org) website.

    tff.org renders Turkish-encoded (windows-1254) HTML from ASP.NET WebForms.
    Responses are decoded to str before being returned to parsers.

    Cached payloads are stored as ``{"html": "<text>"}`` so they share the same
    DiskCache backend used by the other datafc clients.

    Args:
        rate_limit: Maximum requests per second. Defaults to 2.0.
        timeout: Request timeout in seconds. Defaults to 30.
        retries: Number of retry attempts on transient errors. Defaults to 3.
        cache: Optional DiskCache. Falls back to the module-level default cache.
        verify: Whether to verify TLS certificates. Defaults to False because
                tff.org's certificate chain is unreliable from some Windows CA
                stores; the pages contain public data with no auth secrets.
    """

    _class_lock: threading.Lock = threading.Lock()
    _class_last_request_time: float = 0.0

    def __init__(
        self,
        rate_limit: float = 2.0,
        timeout: int = 30,
        retries: int = 3,
        cache=None,
        verify: bool = False,
    ) -> None:
        self._min_interval = 1.0 / rate_limit if rate_limit > 0 else 0.0
        self._timeout = timeout
        self._retries = retries
        self._cache = cache if cache is not None else get_default_cache()
        self._verify = verify
        self._session = cf_requests.Session(impersonate="chrome124", verify=verify)

    def _rate_limit_wait(self) -> None:
        with TFFClient._class_lock:
            elapsed = time.monotonic() - TFFClient._class_last_request_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            TFFClient._class_last_request_time = time.monotonic()

    def get(self, url: str) -> str:
        """Perform a GET, return the response body decoded from windows-1254."""
        if self._cache is not None:
            cached = self._cache.get(url)
            if isinstance(cached, dict) and "html" in cached:
                logger.debug("Cache hit: %s", url)
                return cached["html"]

        last_exc: Optional[Exception] = None

        for attempt in range(1, self._retries + 1):
            self._rate_limit_wait()
            try:
                response = self._session.get(url, timeout=self._timeout)

                if response.status_code == 200:
                    text = response.content.decode(_TFF_ENCODING, errors="replace")
                    if self._cache is not None:
                        self._cache.set(url, {"html": text})
                    return text

                if response.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning(
                        "Rate limited (429). Waiting %ds before retry %d/%d. URL: %s",
                        wait, attempt, self._retries, url,
                    )
                    time.sleep(wait)
                    last_exc = RateLimitError(429, url)
                    continue

                if response.status_code in (500, 502, 503, 504):
                    wait = 2 ** attempt
                    logger.warning(
                        "Server error %d. Waiting %ds before retry %d/%d. URL: %s",
                        response.status_code, wait, attempt, self._retries, url,
                    )
                    time.sleep(wait)
                    last_exc = ServerError(response.status_code, url)
                    continue

                raise APIError(response.status_code, url)

            except (APIError, RateLimitError, ServerError):
                raise
            except Exception as exc:
                logger.warning("Request failed (attempt %d/%d): %s", attempt, self._retries, exc)
                last_exc = exc
                time.sleep(2 ** attempt)

        if isinstance(last_exc, (RateLimitError, ServerError, APIError)):
            raise last_exc
        raise APIError(0, url, f"All {self._retries} attempts failed") from last_exc

    # ------------------------------------------------------------------
    # ASP.NET postback: RadTabStrip / RadComboBox
    # ------------------------------------------------------------------
    #
    # Some TFF views (player Maçlar / Milli / Goller / Kartlar / Hareketler
    # tabs) are only rendered after a WebForms postback. To trigger one we
    # must (a) fetch the page to collect its ``__VIEWSTATE`` and other
    # hidden fields, then (b) POST the same URL back with
    # ``__EVENTTARGET`` + ``__EVENTARGUMENT`` set to the control that owns
    # the tab. Season-scoped tabs (Maçlar, Kartlar) require a second
    # postback that selects a season from the ``SezonSelectorN`` combobox.

    def post_tab_paged(
        self,
        url: str,
        tab_container_id: str,
        tab_name: str,
        grid_leaf: str,
        season: Optional[str] = None,
        season_selector_name: Optional[str] = None,
        max_pages: int = 50,
    ) -> "list[str]":
        """Fetch a tabbed view across all pager pages.

        ``grid_leaf`` is the RadGrid's short id under
        ``OyuncuIstatistikDisplay1`` (``"grdMac"`` for Maçlar,
        ``"grdKartlar"`` for Kartlar, ``"grdGoller"`` for Goller,
        ``"grdMilli"`` for Milli Maçlar). We enumerate the pager anchors
        in each response, follow them in order, and return one HTML string
        per page. Each page is cached individually.
        """
        pages: list[str] = []
        first = self.post_tab(
            url, tab_container_id, tab_name,
            season=season, season_selector_name=season_selector_name,
        )
        pages.append(first)

        page_targets = _pager_targets(first, grid_leaf)
        current_html = first
        page_num = 2
        for target in page_targets:
            if page_num > max_pages:
                logger.warning(
                    "Reached max_pages=%d while paginating tab %r for %s",
                    max_pages, tab_name, url,
                )
                break
            cache_key = f"{url}#tab={tab_name}"
            if season is not None:
                cache_key += f"&season={season}"
            cache_key += f"&page={page_num}"

            cached_page = self._cache.get(cache_key) if self._cache is not None else None
            if isinstance(cached_page, dict) and "html" in cached_page:
                current_html = cached_page["html"]
            else:
                form = _extract_hidden_fields(current_html)
                form["__EVENTTARGET"] = target
                form["__EVENTARGUMENT"] = ""
                current_html = self._post_form(url, form)
                if self._cache is not None:
                    self._cache.set(cache_key, {"html": current_html})

            pages.append(current_html)
            page_num += 1

        return pages

    def post_tab(
        self,
        url: str,
        tab_container_id: str,
        tab_name: str,
        season: Optional[str] = None,
        season_selector_name: Optional[str] = None,
    ) -> str:
        """Fetch a tabbed player-page view via ASP.NET postback.

        ``tab_container_id`` is the ``name`` (dollar-separated) of the tab
        control's outer container, e.g.
        ``ctl00$MPane$..._OyuncuIstatistikDisplay1$RadTabStrip1``. ``tab_name``
        is the leaf id (``maclar`` / ``milli`` / ``goller`` / ``kartlar`` /
        ``hareketler`` / ``genel``).

        When ``season`` is set (e.g. ``"2024-2025"``), a *second* postback
        is fired against ``season_selector_name`` (default
        ``SezonSelector2`` for maclar / ``SezonSelector4`` for kartlar) so
        the grid populates for that season.

        Results are cached under a synthetic key that folds ``tab``, ``season``,
        and ``selector`` into the URL so different views don't collide.
        """
        cache_key = f"{url}#tab={tab_name}"
        if season is not None:
            cache_key += f"&season={season}"
            if season_selector_name:
                cache_key += f"&sel={season_selector_name}"
        if self._cache is not None:
            cached = self._cache.get(cache_key)
            if isinstance(cached, dict) and "html" in cached:
                logger.debug("Cache hit (postback): %s", cache_key)
                return cached["html"]

        base_html = self.get(url)  # cached at URL level
        form_data = _extract_hidden_fields(base_html)

        # Postback #1 — switch to the requested tab.
        tab_form = dict(form_data)
        tab_form["__EVENTTARGET"] = tab_container_id
        tab_form["__EVENTARGUMENT"] = f"{tab_container_id}${tab_name}"
        html_after_tab = self._post_form(url, tab_form)

        if season is None:
            html_final = html_after_tab
        else:
            # Postback #2 — trigger the season combobox for this tab.
            selector = season_selector_name or _default_selector_for_tab(tab_name)
            if selector is None:
                raise ValueError(
                    f"tab={tab_name!r} does not have a season selector; "
                    "call without season=..."
                )
            selector_full = _find_selector_full_name(html_after_tab, selector)
            if selector_full is None:
                raise APIError(0, url,
                    f"Season selector {selector!r} not present after posting tab {tab_name!r}"
                )
            # TFF's RadComboBox ignores combo_text/value and drives the grid off
            # combo_index instead — see _season_options for the extraction logic.
            options = _season_options(html_after_tab, selector)
            if season not in options:
                available = sorted(options.keys(), reverse=True)
                raise APIError(0, url,
                    f"season={season!r} not in TFF's dropdown for tab={tab_name!r}. "
                    f"Available: {available}"
                )
            combo_index = options[season]
            season_form = _extract_hidden_fields(html_after_tab)
            season_form["__EVENTTARGET"] = f"{selector_full}$combo"
            season_form["__EVENTARGUMENT"] = ""
            season_form[f"{selector_full}$combo_text"] = season
            season_form[f"{selector_full}$combo_value"] = season
            season_form[f"{selector_full}$combo_index"] = str(combo_index)
            season_form[f"{selector_full}$combo_ClientState"] = ""
            html_final = self._post_form(url, season_form)

        if self._cache is not None:
            self._cache.set(cache_key, {"html": html_final})
        return html_final

    def _post_form(self, url: str, form: Dict[str, str]) -> str:
        """POST ``form`` to ``url``, decode the response as windows-1254."""
        for attempt in range(1, self._retries + 1):
            self._rate_limit_wait()
            try:
                response = self._session.post(url, data=form, timeout=self._timeout)
                if response.status_code == 200:
                    return response.content.decode(_TFF_ENCODING, errors="replace")
                if response.status_code == 429:
                    time.sleep(2 ** attempt)
                    continue
                if response.status_code in (500, 502, 503, 504):
                    time.sleep(2 ** attempt)
                    continue
                raise APIError(response.status_code, url)
            except (APIError, RateLimitError, ServerError):
                raise
            except Exception as exc:
                logger.warning("POST failed (attempt %d/%d): %s", attempt, self._retries, exc)
                time.sleep(2 ** attempt)
        raise APIError(0, url, f"POST failed after {self._retries} attempts")

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "TFFClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Postback helpers
# ---------------------------------------------------------------------------


_TAB_SEASON_SELECTORS = {
    # Tab id → the SezonSelectorN control that scopes it. Discovered by
    # inspecting rendered player pages.
    "maclar": "SezonSelector2",
    "kartlar": "SezonSelector4",
}


def _default_selector_for_tab(tab_name: str) -> Optional[str]:
    return _TAB_SEASON_SELECTORS.get(tab_name)


def _extract_hidden_fields(html: str) -> Dict[str, str]:
    """Collect every ``<input type="hidden">`` name/value pair. WebForms
    postbacks require the full set (VIEWSTATE, EVENTVALIDATION, etc.)."""
    soup = BeautifulSoup(html, "html.parser")
    fields: Dict[str, str] = {}
    for inp in soup.find_all("input", type="hidden"):
        name = inp.get("name")
        if name:
            fields[name] = inp.get("value", "") or ""
    return fields


def _find_selector_full_name(html: str, selector_leaf: str) -> Optional[str]:
    """Locate the full dollar-path name of a season combobox on the page.

    Handles the case where the same leaf name (``SezonSelector2``) sits
    under a variable ancestor path (``ctl00$MPane$m_30_202_ctnr$m_30_202``).
    """
    soup = BeautifulSoup(html, "html.parser")
    for inp in soup.find_all("input"):
        name = inp.get("name", "")
        if name.endswith(f"${selector_leaf}$combo_value") or \
           name.endswith(f"${selector_leaf}$combo_text"):
            return name.rsplit("$combo_", 1)[0]
    return None


def _pager_targets(html: str, grid_leaf: str) -> "list[str]":
    """Return the ordered list of ``__doPostBack`` targets for pages 2..N of a
    RadGrid.

    TFF renders the pager as a ``<td colspan=…>`` containing text like
    ``Sayfalar: … 1 <a>2</a> <a>3</a> … | 1 / 3, Toplam 87 kayıt`` — the
    current page is a ``<span>`` (skipped) and other pages are anchors
    whose ``href`` is ``javascript:__doPostBack('…grdMac$ctl01$ctl03$ctl01$ctlXX','')``.
    We match each anchor's numeric label to keep pager pagination distinct
    from the "Next »" / "Previous «" arrows.
    """
    soup = BeautifulSoup(html, "html.parser")
    pager_string = soup.find(string=re.compile(r"Sayfalar"))
    if pager_string is None:
        return []
    pager_cell = pager_string.find_parent(["td", "tr"])
    if pager_cell is None:
        return []

    postback_re = re.compile(
        rf"__doPostBack\(\s*'([^']*\${re.escape(grid_leaf)}\$[^']*)'\s*,\s*''\s*\)"
    )
    targets: list[str] = []
    for anchor in pager_cell.find_all("a", href=True):
        # Only numbered anchors (pages 2..N). Skip the arrow that says "Sonraki".
        label = anchor.get_text(strip=True)
        if not label.isdigit():
            continue
        m = postback_re.search(anchor.get("href", ""))
        if m:
            targets.append(m.group(1))
    return targets


def _season_options(html: str, selector_leaf: str) -> Dict[str, int]:
    """Extract ``{season_text: combo_index}`` from the RadComboBox dropdown.

    Each option is rendered as a ``<div id="..._SezonSelector2_combo_cN">``
    whose text is the season label (e.g. ``2025-2026``). N (1-based) is
    the combo_index TFF expects on the postback that filters the grid.
    """
    soup = BeautifulSoup(html, "html.parser")
    pattern = re.compile(rf"_{re.escape(selector_leaf)}_combo_c(\d+)$")
    options: Dict[str, int] = {}
    for div in soup.find_all("div", id=pattern):
        m = pattern.search(div.get("id", ""))
        if not m:
            continue
        text = div.get_text(strip=True)
        if text:
            options[text] = int(m.group(1))
    return options

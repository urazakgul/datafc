import logging
import threading
import time
from typing import Optional

from curl_cffi import requests as cf_requests

from datafc.exceptions import APIError, RateLimitError, ServerError
from datafc.utils._cache import get_default_cache

logger = logging.getLogger(__name__)


class ClubEloClient:
    """
    HTTP client for the ClubElo public API. Responses are CSV text.

    Cached payloads are stored as ``{"csv": "<text>"}`` so they share the same
    DiskCache backend used by SofascoreClient.

    Args:
        rate_limit: Maximum requests per second. Defaults to 2.0.
        timeout: Request timeout in seconds. Defaults to 30.
        retries: Number of retry attempts on transient errors. Defaults to 3.
        cache: Optional DiskCache. Falls back to the module-level default cache.
    """

    _class_lock: threading.Lock = threading.Lock()
    _class_last_request_time: float = 0.0

    def __init__(
        self,
        rate_limit: float = 2.0,
        timeout: int = 30,
        retries: int = 3,
        cache=None,
    ) -> None:
        self._min_interval = 1.0 / rate_limit if rate_limit > 0 else 0.0
        self._timeout = timeout
        self._retries = retries
        self._cache = cache if cache is not None else get_default_cache()
        self._session = cf_requests.Session(impersonate="chrome124")

    def _rate_limit_wait(self) -> None:
        with ClubEloClient._class_lock:
            elapsed = time.monotonic() - ClubEloClient._class_last_request_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            ClubEloClient._class_last_request_time = time.monotonic()

    def get(self, url: str) -> str:
        """Perform a GET, return the response body as CSV text."""
        if self._cache is not None:
            cached = self._cache.get(url)
            if isinstance(cached, dict) and "csv" in cached:
                logger.debug("Cache hit: %s", url)
                return cached["csv"]

        last_exc: Optional[Exception] = None

        for attempt in range(1, self._retries + 1):
            self._rate_limit_wait()
            try:
                response = self._session.get(url, timeout=self._timeout)

                if response.status_code == 200:
                    text = response.text
                    if self._cache is not None:
                        self._cache.set(url, {"csv": text})
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

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "ClubEloClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()

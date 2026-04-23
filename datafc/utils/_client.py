import time
import threading
import logging
from typing import Optional
from curl_cffi import requests as cf_requests
from datafc.exceptions import APIError, RateLimitError, ServerError
from datafc.utils._config import SOFASCORE_HEADERS
from datafc.utils._cache import get_default_cache

logger = logging.getLogger(__name__)


class SofascoreClient:
    """
    HTTP client for Sofascore API using curl_cffi to bypass Cloudflare TLS fingerprinting.

    Rate limiting is class-level: all SofascoreClient instances share a single
    lock and timestamp, so the total request rate across the process never
    exceeds the most conservative instance's configured limit.

    Args:
        rate_limit: Maximum requests per second. Defaults to 2.0.
        timeout: Request timeout in seconds. Defaults to 30.
        retries: Number of retry attempts on transient errors. Defaults to 3.
        cache: Optional DiskCache instance. When provided, responses are read from and
               written to disk so identical URLs are not fetched twice. Falls back to
               the module-level default cache set via ``set_default_cache()``.
    """

    # Class-level shared rate limiter — prevents multiple instances from
    # independently hammering the API at their individual limits.
    _class_lock: threading.Lock = threading.Lock()
    _class_last_request_time: float = 0.0

    def __init__(
        self,
        rate_limit: float = 2.0,
        timeout: int = 30,
        retries: int = 3,
        cache=None,  # Optional[DiskCache] — avoid import cycle
    ) -> None:
        self._min_interval = 1.0 / rate_limit if rate_limit > 0 else 0.0
        self._timeout = timeout
        self._retries = retries
        self._cache = cache if cache is not None else get_default_cache()
        self._session = cf_requests.Session(impersonate="chrome124")
        self._session.headers.update(SOFASCORE_HEADERS)

    def _rate_limit_wait(self) -> None:
        with SofascoreClient._class_lock:
            elapsed = time.monotonic() - SofascoreClient._class_last_request_time
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            SofascoreClient._class_last_request_time = time.monotonic()

    def get(self, url: str) -> dict:
        """
        Perform a GET request with optional caching, rate limiting, and retry logic.

        Cached responses are returned immediately without counting against the rate
        limit or consuming a retry attempt.

        Args:
            url: Full URL to request.

        Returns:
            Parsed JSON response as a dict.

        Raises:
            RateLimitError: If the API returns 429 after all retries.
            ServerError: If the API returns a 5xx error after all retries.
            APIError: For other non-200 HTTP responses.
        """
        if self._cache is not None:
            cached = self._cache.get(url)
            if cached is not None:
                logger.debug("Cache hit: %s", url)
                return cached

        last_exc: Optional[Exception] = None

        for attempt in range(1, self._retries + 1):
            self._rate_limit_wait()

            try:
                response = self._session.get(url, timeout=self._timeout)

                if response.status_code == 200:
                    data = response.json()
                    if not isinstance(data, dict):
                        raise APIError(200, url, f"Non-dict JSON response ({type(data).__name__})")
                    if self._cache is not None:
                        self._cache.set(url, data)
                    return data

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

    def __enter__(self) -> "SofascoreClient":
        return self

    def __exit__(self, *_) -> None:
        self.close()

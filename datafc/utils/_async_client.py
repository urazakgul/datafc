"""
Async HTTP client for Sofascore API.

Uses curl_cffi AsyncSession to impersonate Chrome's TLS fingerprint,
bypassing Cloudflare bot detection — same approach as the sync client
but compatible with asyncio for concurrent requests.

Usage:
    import asyncio
    from datafc.sofascore import aio

    async def main():
        matches = await aio.match_data(52, 63814, week_number=21)
        # Fetch all 38 weeks in parallel
        tasks = [aio.match_data(52, 63814, week_number=w) for w in range(1, 39)]
        results = await asyncio.gather(*tasks)

    asyncio.run(main())
"""

import asyncio
import time
import logging
from typing import Optional
from curl_cffi.requests import AsyncSession
from datafc.exceptions import APIError, RateLimitError, ServerError
from datafc.utils._config import SOFASCORE_HEADERS
from datafc.utils._cache import get_default_cache

logger = logging.getLogger(__name__)


class AsyncSofascoreClient:
    """
    Async HTTP client for Sofascore API using curl_cffi AsyncSession.

    Designed for concurrent data fetching — e.g. fetching all 38 weeks of a
    season simultaneously instead of sequentially.

    Rate limiting is class-level: all AsyncSofascoreClient instances in the same
    event loop share a single lock and timestamp, so concurrent gather() calls
    across multiple instances don't bypass the rate limit.

    Args:
        rate_limit: Maximum requests per second. Defaults to 2.0.
        timeout: Request timeout in seconds. Defaults to 30.
        retries: Number of retry attempts on transient errors. Defaults to 3.
        cache: Optional DiskCache instance for response caching. Falls back to
               the module-level default cache set via ``set_default_cache()``.
    """

    # Class-level shared rate limiter.
    # The lock is created lazily on first use inside a running event loop,
    # and re-created if the previous loop was closed (e.g. successive asyncio.run() calls).
    _class_lock: Optional[asyncio.Lock] = None
    _class_last_request: float = 0.0

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
        self._session: Optional[AsyncSession] = None

    async def _rate_limit_wait(self) -> None:
        # Re-create the class-level lock if it hasn't been created yet or if
        # the event loop it was bound to is now closed (successive asyncio.run() calls).
        if AsyncSofascoreClient._class_lock is None or (
            hasattr(AsyncSofascoreClient._class_lock, "_loop")
            and getattr(AsyncSofascoreClient._class_lock, "_loop", None) is not None
            and AsyncSofascoreClient._class_lock._loop.is_closed()  # type: ignore[union-attr]
        ):
            AsyncSofascoreClient._class_lock = asyncio.Lock()
        async with AsyncSofascoreClient._class_lock:
            elapsed = time.monotonic() - AsyncSofascoreClient._class_last_request
            if elapsed < self._min_interval:
                await asyncio.sleep(self._min_interval - elapsed)
            AsyncSofascoreClient._class_last_request = time.monotonic()

    async def get(self, url: str) -> dict:
        """
        Perform an async GET request with optional caching, rate limiting, and retries.

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
            await self._rate_limit_wait()

            try:
                response = await self._session.get(url, timeout=self._timeout)

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
                    await asyncio.sleep(wait)
                    last_exc = RateLimitError(429, url)
                    continue

                if response.status_code in (500, 502, 503, 504):
                    wait = 2 ** attempt
                    logger.warning(
                        "Server error %d. Waiting %ds before retry %d/%d. URL: %s",
                        response.status_code, wait, attempt, self._retries, url,
                    )
                    await asyncio.sleep(wait)
                    last_exc = ServerError(response.status_code, url)
                    continue

                raise APIError(response.status_code, url)

            except (APIError, RateLimitError, ServerError):
                raise
            except Exception as exc:
                logger.warning("Request failed (attempt %d/%d): %s", attempt, self._retries, exc)
                last_exc = exc
                await asyncio.sleep(2 ** attempt)

        if isinstance(last_exc, (RateLimitError, ServerError, APIError)):
            raise last_exc
        raise APIError(0, url, f"All {self._retries} attempts failed") from last_exc

    async def __aenter__(self) -> "AsyncSofascoreClient":
        self._session = AsyncSession(impersonate="chrome124")
        self._session.headers.update(SOFASCORE_HEADERS)
        return self

    async def __aexit__(self, *_) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

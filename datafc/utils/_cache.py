"""
Disk-based JSON cache for Sofascore API responses.

Completed match data is immutable, so caching eliminates redundant API calls
during development, testing, and repeated analysis runs. It also reduces the
risk of IP rate-limiting when iterating over large datasets.

Usage:
    from datafc import DiskCache
    from datafc.sofascore import match_data

    cache = DiskCache(cache_dir=".datafc_cache", ttl_hours=24)
    df = match_data(52, 63814, 21, cache=cache)  # first call hits API
    df = match_data(52, 63814, 21, cache=cache)  # second call reads from disk
"""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

logger = logging.getLogger(__name__)


class DiskCache:
    """
    Simple file-based cache that stores API responses as JSON on disk.

    Args:
        cache_dir: Directory where cached responses are stored. Created automatically
                   if it does not exist. Defaults to '.datafc_cache'.
        ttl_hours: Time-to-live in hours. Entries older than this are considered
                   stale and re-fetched. Use 0 to disable TTL (cache forever).
                   Defaults to 24.0.
    """

    def __init__(self, cache_dir: str = ".datafc_cache", ttl_hours: float = 24.0) -> None:
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._ttl = ttl_hours * 3600 if ttl_hours > 0 else None

    @staticmethod
    def _normalize_url(url: str) -> str:
        """Sort query parameters so ?a=1&b=2 and ?b=2&a=1 map to the same cache key."""
        parsed = urlparse(url)
        sorted_query = urlencode(sorted(parse_qsl(parsed.query)))
        return urlunparse(parsed._replace(query=sorted_query))

    def _path(self, url: str) -> Path:
        key = hashlib.md5(self._normalize_url(url).encode("utf-8"), usedforsecurity=False).hexdigest()
        return self._dir / f"{key}.json"

    def get(self, url: str) -> Optional[dict]:
        """Return cached data for url, or None if missing or expired."""
        path = self._path(url)
        if not path.exists():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
            if self._ttl is not None and time.time() - entry["ts"] > self._ttl:
                path.unlink(missing_ok=True)
                return None
            return entry["data"]
        except Exception as e:
            logger.warning("Corrupt cache entry for %s, removing: %s", path.name, e)
            path.unlink(missing_ok=True)
            return None

    def set(self, url: str, data: dict) -> None:
        """Write data to cache for url."""
        path = self._path(url)
        try:
            path.write_text(
                json.dumps({"ts": time.time(), "data": data}, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.warning("Cache write failed for %s: %s", path.name, e)

    def clear(self, url: Optional[str] = None) -> int:
        """
        Remove cached entries.

        Args:
            url: If given, remove only the entry for this URL.
                 If None, remove all entries in the cache directory.

        Returns:
            Number of entries removed.
        """
        if url is not None:
            path = self._path(url)
            if path.exists():
                path.unlink()
                return 1
            return 0

        count = 0
        for f in self._dir.glob("*.json"):
            f.unlink()
            count += 1
        return count

    def __repr__(self) -> str:
        entries = len(list(self._dir.glob("*.json")))
        ttl_str = f"{self._ttl / 3600:.1f}" if self._ttl is not None else "disabled"
        return f"DiskCache(dir={self._dir!r}, ttl_hours={ttl_str}, entries={entries})"


# ---------------------------------------------------------------------------
# Module-level default cache
# ---------------------------------------------------------------------------

_default_cache: Optional["DiskCache"] = None


def get_default_cache() -> Optional["DiskCache"]:
    """Return the module-level default cache, or None if not set."""
    return _default_cache


def set_default_cache(cache: Optional["DiskCache"]) -> None:
    """
    Set a module-level default cache used automatically by all fetch functions
    when no explicit ``cache=`` argument is passed.

    Args:
        cache: A DiskCache instance, or None to disable the default cache.

    Example::

        from datafc import set_default_cache, DiskCache
        set_default_cache(DiskCache(".datafc_cache", ttl_hours=24))
        # All fetch calls will now automatically use this cache.

        set_default_cache(None)  # Disables the default cache.
    """
    global _default_cache
    _default_cache = cache

"""
datafc exception hierarchy.

Usage:
    from datafc.exceptions import DataFCError, APIError, RateLimitError, DataNotAvailableError

    try:
        df = match_data(...)
    except RateLimitError:
        # back off and retry
    except DataNotAvailableError:
        # no data for these params
    except DataFCError:
        # any other datafc error
"""


class DataFCError(Exception):
    """Base exception for all datafc errors."""


class InvalidParameterError(DataFCError):
    """Raised when a function receives an invalid argument value."""


class APIError(DataFCError):
    """Raised when the Sofascore API returns an unexpected HTTP status code."""

    def __init__(self, status_code: int, url: str, message: str = "") -> None:
        self.status_code = status_code
        self.url = url
        super().__init__(
            f"HTTP {status_code} for URL: {url}" + (f" — {message}" if message else "")
        )


class RateLimitError(APIError):
    """Raised when the API returns HTTP 429 (Too Many Requests) after all retries."""


class ServerError(APIError):
    """Raised when the API returns a 5xx error after all retries."""


class DataNotAvailableError(DataFCError):
    """Raised when the API returns successfully but contains no usable data."""

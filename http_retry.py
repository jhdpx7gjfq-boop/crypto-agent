"""Shared HTTP 429 retry-after / backoff math for coinglass.py and
binance_public.py.

Pure functions only -- each client still owns its own time.sleep() call, so
existing tests can keep patching <module>.time.sleep without knowing about
this module.
"""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


class RateLimitError(Exception):
    """Raised when a client exhausts its retry budget on a rate-limit response."""

    def __init__(self, message="Rate limit exceeded", retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


def parse_retry_after(value):
    """Retry-After can be seconds or an HTTP-date; return seconds or None."""
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        pass
    try:
        return max(0.0, (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
    except (TypeError, ValueError):
        return None


def backoff_wait(attempt, backoff_base, backoff_max, retry_after=None):
    wait = min(backoff_max, backoff_base * (2 ** (attempt - 1)))
    if retry_after is not None:
        wait = max(wait, retry_after)
    return wait

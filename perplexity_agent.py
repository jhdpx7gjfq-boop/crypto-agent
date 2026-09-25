import logging
import os

from perplexity import Perplexity, PerplexityError

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = Perplexity()
    return _client


def get_market_context(query, preset="low"):
    """Web-grounded one-shot answer via the Perplexity Agent API.

    Returns None (never raises) on any API/config failure so callers can
    treat this as a best-effort enrichment, consistent with how main.py
    already swallows CoinGecko/Telegram failures.
    """
    if not os.environ.get("PERPLEXITY_API_KEY"):
        return None

    try:
        response = _get_client().responses.create(
            input=query,
            preset=preset,
            tools=[{"type": "web_search"}],
        )
    except PerplexityError as exc:
        logger.warning("Perplexity Agent API request failed: %s", exc)
        return None

    return response.output_text.strip() or None

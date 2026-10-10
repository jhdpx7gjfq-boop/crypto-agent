import logging
import os
from dataclasses import dataclass

from openai import APIError, OpenAI

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.perplexity.ai/router/v1"

_client = None
_catalog = None


@dataclass(frozen=True)
class Completion:
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cached_tokens: int


def _base_url():
    return os.environ.get("PERPLEXITY_ROUTER_BASE_URL", DEFAULT_BASE_URL)


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.environ["PERPLEXITY_API_KEY"],
            base_url=_base_url(),
            max_retries=3,
        )
    return _client


def list_models(refresh=False):
    global _catalog
    if _catalog is None or refresh:
        _catalog = {model.id for model in _get_client().models.list().data}
    return _catalog


def complete(prompt, model=None, system=None, max_tokens=1024):
    """One-shot Chat Completions call routed through the Perplexity Router API.

    Model defaults to PERPLEXITY_ROUTER_MODEL and must appear in the key's
    catalog from GET /router/v1/models; unknown slugs raise ValueError.
    Returns None (never raises) on missing key or API failure, consistent
    with perplexity_agent.get_market_context.
    """
    if not os.environ.get("PERPLEXITY_API_KEY"):
        return None

    model = model or os.environ.get("PERPLEXITY_ROUTER_MODEL")
    if not model:
        raise ValueError("PERPLEXITY_ROUTER_MODEL is not set")

    try:
        catalog = list_models()
    except APIError as exc:
        logger.warning("Perplexity Router model catalog request failed: %s", exc)
        return None
    if model not in catalog:
        raise ValueError(f"Model {model!r} is not in the Perplexity Router catalog for this key")

    messages = [{"role": "user", "content": prompt}]
    if system:
        messages.insert(0, {"role": "system", "content": system})

    try:
        response = _get_client().chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
        )
    except APIError as exc:
        logger.warning("Perplexity Router request failed: %s", exc)
        return None

    usage = response.usage
    details = usage.prompt_tokens_details
    return Completion(
        text=(response.choices[0].message.content or "").strip(),
        model=response.model,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        cached_tokens=(details.cached_tokens if details and details.cached_tokens else 0),
    )

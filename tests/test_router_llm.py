from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from openai import APIConnectionError

import router_llm


@pytest.fixture(autouse=True)
def reset_router_state(monkeypatch):
    monkeypatch.setattr(router_llm, "_client", None)
    monkeypatch.setattr(router_llm, "_catalog", None)
    monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
    monkeypatch.setenv("PERPLEXITY_ROUTER_MODEL", "anthropic/claude-sonnet-5")


def _client_with(catalog_ids=("anthropic/claude-sonnet-5",), create=None):
    client = Mock()
    client.models.list.return_value = SimpleNamespace(
        data=[SimpleNamespace(id=mid) for mid in catalog_ids]
    )
    if create is not None:
        client.chat.completions.create.side_effect = create
    return client


def _response(text="Réponse", prompt=12, completion=5, cached=None):
    details = SimpleNamespace(cached_tokens=cached) if cached is not None else None
    return SimpleNamespace(
        model="anthropic/claude-sonnet-5",
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))],
        usage=SimpleNamespace(
            prompt_tokens=prompt, completion_tokens=completion, prompt_tokens_details=details
        ),
    )


class TestComplete:
    def test_returns_none_without_api_key(self, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        assert router_llm.complete("bonjour") is None

    def test_raises_when_model_unset(self, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_ROUTER_MODEL", raising=False)
        with pytest.raises(ValueError, match="PERPLEXITY_ROUTER_MODEL"):
            router_llm.complete("bonjour")

    def test_raises_on_slug_missing_from_catalog(self, monkeypatch):
        client = _client_with(catalog_ids=("openai/gpt-5.6-terra",))
        monkeypatch.setattr(router_llm, "_client", client)
        with pytest.raises(ValueError, match="anthropic/claude-sonnet-5"):
            router_llm.complete("bonjour")
        client.chat.completions.create.assert_not_called()

    def test_returns_completion_with_usage(self, monkeypatch):
        client = _client_with(create=lambda **_: _response("BTC consolide.", 12, 5, cached=4))
        monkeypatch.setattr(router_llm, "_client", client)

        result = router_llm.complete("résume", system="Analyste quant")

        assert result == router_llm.Completion(
            text="BTC consolide.",
            model="anthropic/claude-sonnet-5",
            prompt_tokens=12,
            completion_tokens=5,
            cached_tokens=4,
        )
        _, kwargs = client.chat.completions.create.call_args
        assert kwargs["model"] == "anthropic/claude-sonnet-5"
        assert kwargs["messages"] == [
            {"role": "system", "content": "Analyste quant"},
            {"role": "user", "content": "résume"},
        ]
        assert kwargs["max_tokens"] == 1024

    def test_cached_tokens_default_to_zero_without_details(self, monkeypatch):
        client = _client_with(create=lambda **_: _response(prompt=3, completion=1))
        monkeypatch.setattr(router_llm, "_client", client)

        assert router_llm.complete("salut").cached_tokens == 0

    def test_returns_none_on_api_error(self, monkeypatch):
        def boom(**_):
            raise APIConnectionError(request=Mock())

        client = _client_with(create=boom)
        monkeypatch.setattr(router_llm, "_client", client)

        assert router_llm.complete("salut") is None

    def test_catalog_is_fetched_once(self, monkeypatch):
        client = _client_with(create=lambda **_: _response())
        monkeypatch.setattr(router_llm, "_client", client)

        router_llm.complete("un")
        router_llm.complete("deux")

        client.models.list.assert_called_once()


class TestClientConfig:
    def test_uses_router_base_url_and_key(self, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_ROUTER_BASE_URL", raising=False)
        client = router_llm._get_client()
        assert str(client.base_url).rstrip("/") == router_llm.DEFAULT_BASE_URL
        assert client.api_key == "pplx-test"

    def test_base_url_is_overridable_from_env(self, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_ROUTER_BASE_URL", "http://localhost:9999/router/v1")
        client = router_llm._get_client()
        assert str(client.base_url).rstrip("/") == "http://localhost:9999/router/v1"

from unittest.mock import Mock, patch

from perplexity import APIConnectionError

import perplexity_agent


class TestGetMarketContext:
    def test_returns_none_without_api_key(self, monkeypatch):
        monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
        assert perplexity_agent.get_market_context("why is btc up") is None

    @patch("perplexity_agent._get_client")
    def test_returns_output_text_on_success(self, mock_get_client, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        mock_client = Mock()
        mock_client.responses.create.return_value = Mock(output_text="BTC rallied on ETF inflows.")
        mock_get_client.return_value = mock_client

        result = perplexity_agent.get_market_context("why is btc up")

        assert result == "BTC rallied on ETF inflows."
        _, kwargs = mock_client.responses.create.call_args
        assert kwargs["tools"] == [{"type": "web_search"}]
        assert kwargs["preset"] == "low"

    @patch("perplexity_agent._get_client")
    def test_returns_none_on_blank_output(self, mock_get_client, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        mock_get_client.return_value = Mock(
            responses=Mock(create=Mock(return_value=Mock(output_text="   ")))
        )
        assert perplexity_agent.get_market_context("why is btc up") is None

    @patch("perplexity_agent._get_client")
    def test_returns_none_on_api_error(self, mock_get_client, monkeypatch):
        monkeypatch.setenv("PERPLEXITY_API_KEY", "pplx-test")
        mock_client = Mock()
        mock_client.responses.create.side_effect = APIConnectionError(
            message="boom", request=Mock()
        )
        mock_get_client.return_value = mock_client

        assert perplexity_agent.get_market_context("why is btc up") is None

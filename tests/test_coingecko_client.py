"""Collector: retries the transient, refuses the rest, validates the payload."""

from unittest.mock import Mock

import pytest
import requests

from igwt.data import coingecko

GOOD = {"prices": [[1, 2.0]], "market_caps": [[1, 3.0]], "total_volumes": [[1, 4.0]]}


def response(status, payload=None, text=""):
    mock = Mock()
    mock.status_code = status
    mock.json.return_value = payload
    mock.text = text
    return mock


def test_returns_a_validated_payload():
    session = Mock()
    session.get.return_value = response(200, GOOD)
    assert coingecko.fetch_market_chart("bitcoin", session=session) == GOOD


def test_retries_a_rate_limit_then_succeeds():
    session = Mock()
    session.get.side_effect = [response(429), response(200, GOOD)]
    sleeps = []
    result = coingecko.fetch_market_chart("bitcoin", session=session, sleep=sleeps.append)
    assert result == GOOD
    assert sleeps == [2.0]


def test_gives_up_after_the_retry_budget():
    session = Mock()
    session.get.return_value = response(503)
    with pytest.raises(coingecko.CoinGeckoError, match="retry budget exhausted"):
        coingecko.fetch_market_chart("bitcoin", session=session, retries=2, sleep=lambda _: None)


def test_a_client_error_is_not_retried():
    session = Mock()
    session.get.return_value = response(404, text="not found")
    with pytest.raises(coingecko.CoinGeckoError, match="HTTP 404"):
        coingecko.fetch_market_chart("bitcoin", session=session, sleep=lambda _: None)
    assert session.get.call_count == 1


def test_network_failures_are_retried():
    session = Mock()
    session.get.side_effect = [requests.ConnectionError("reset"), response(200, GOOD)]
    assert coingecko.fetch_market_chart("bitcoin", session=session, sleep=lambda _: None) == GOOD


@pytest.mark.parametrize(
    "payload",
    [
        {"prices": [], "market_caps": [[1, 1]], "total_volumes": [[1, 1]]},
        {"prices": [[1, 1]], "total_volumes": [[1, 1]]},
        {"prices": [[1, 1, 1]], "market_caps": [[1, 1]], "total_volumes": [[1, 1]]},
        [],
    ],
)
def test_a_malformed_payload_is_rejected(payload):
    session = Mock()
    session.get.return_value = response(200, payload)
    with pytest.raises(coingecko.CoinGeckoError):
        coingecko.fetch_market_chart("bitcoin", session=session, sleep=lambda _: None)


def test_a_window_beyond_the_public_tier_is_refused_before_the_call():
    session = Mock()
    with pytest.raises(coingecko.CoinGeckoError, match="public-tier limit"):
        coingecko.fetch_market_chart("bitcoin", days=1000, session=session)
    session.get.assert_not_called()

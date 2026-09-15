"""Binance collector: paging, retries, and an unreachable environment."""

from datetime import date
from unittest.mock import Mock

import pytest
import requests

from igwt.data import binance

DAY_MS = 86_400_000
START_MS = 1_483_228_800_000  # 2017-01-01T00:00:00Z


def kline(open_time, close=100.0):
    return [open_time, "99", "101", "98", str(close), "1234.5", open_time + DAY_MS - 1,
            "0", 0, "0", "0", "0"]


def response(status, payload=None, text=""):
    mock = Mock()
    mock.status_code = status
    mock.json.return_value = payload
    mock.text = text
    return mock


class TestPreflight:
    def test_reports_the_first_reachable_endpoint(self):
        session = Mock()
        session.get.side_effect = [response(200, [kline(START_MS)]), response(200, [])]
        probe = binance.preflight(session=session)
        assert probe["reachable"] == binance.ENDPOINTS[0]

    def test_every_endpoint_is_probed_so_the_diagnosis_is_complete(self):
        session = Mock()
        session.get.side_effect = [response(200, []), response(451)]
        probe = binance.preflight(session=session)
        assert len(probe["probes"]) == len(binance.ENDPOINTS)

    def test_a_regional_block_is_named_in_plain_terms(self):
        session = Mock()
        session.get.side_effect = [response(403), response(451)]
        probe = binance.preflight(session=session)
        assert probe["reachable"] is None
        details = [item["detail"] for item in probe["probes"]]
        assert any("451" in detail and "region" in detail for detail in details)
        assert any("403" in detail for detail in details)

    def test_a_refused_tunnel_is_reported_not_raised(self):
        session = Mock()
        session.get.side_effect = requests.ConnectionError("CONNECT tunnel failed, response 403")
        probe = binance.preflight(session=session)
        assert probe["reachable"] is None
        assert all("egress policy" in item["detail"] for item in probe["probes"])


class TestFetch:
    def test_pages_forward_until_the_range_is_covered(self):
        first_page = [kline(START_MS + index * DAY_MS) for index in range(1000)]
        second_page = [kline(START_MS + (1000 + index) * DAY_MS) for index in range(10)]
        session = Mock()
        session.get.side_effect = [response(200, first_page), response(200, second_page)]

        klines = binance.fetch_daily_klines(
            "BTCUSDT",
            start=date(2017, 1, 1),
            end=date(2019, 12, 31),
            base_url=binance.ENDPOINTS[0],
            session=session,
        )
        assert len(klines) == 1010
        assert session.get.call_count == 2  # a short page ends the paging

    def test_stops_on_an_empty_page(self):
        session = Mock()
        session.get.return_value = response(200, [])
        klines = binance.fetch_daily_klines(
            "BTCUSDT", start=date(2017, 1, 1), base_url=binance.ENDPOINTS[0], session=session
        )
        assert klines == []
        assert session.get.call_count == 1

    def test_an_unreachable_environment_raises_a_legible_error(self):
        session = Mock()
        session.get.side_effect = [response(403), response(451)]
        with pytest.raises(binance.BinanceUnreachable, match="no Binance endpoint is reachable"):
            binance.fetch_daily_klines("BTCUSDT", start=date(2017, 1, 1), session=session)

    def test_retries_a_rate_limit(self):
        session = Mock()
        session.get.side_effect = [response(429), response(200, [])]
        binance.fetch_daily_klines(
            "BTCUSDT",
            start=date(2017, 1, 1),
            base_url=binance.ENDPOINTS[0],
            session=session,
            sleep=lambda _: None,
        )
        assert session.get.call_count == 2

    def test_a_client_error_is_not_retried(self):
        session = Mock()
        session.get.return_value = response(400, text="bad symbol")
        with pytest.raises(binance.BinanceError, match="HTTP 400"):
            binance.fetch_daily_klines(
                "NOPE", start=date(2017, 1, 1), base_url=binance.ENDPOINTS[0], session=session
            )

    def test_a_malformed_kline_is_rejected(self):
        session = Mock()
        session.get.return_value = response(200, [[1, 2]])
        with pytest.raises(binance.BinanceError, match="malformed kline"):
            binance.fetch_daily_klines(
                "BTCUSDT", start=date(2017, 1, 1), base_url=binance.ENDPOINTS[0], session=session
            )


class TestProjection:
    def test_klines_project_onto_the_ingestion_shape(self):
        rows = binance.klines_to_rows([kline(START_MS, close=42.0)])
        assert rows == [
            {
                "date": START_MS,
                "open": "99",
                "high": "101",
                "low": "98",
                "close": "42.0",
                "volume": "1234.5",
            }
        ]

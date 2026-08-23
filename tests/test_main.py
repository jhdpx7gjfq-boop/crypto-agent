from unittest.mock import Mock, patch

import pytest
import requests

import main


class TestClassifyZone:
    def test_above_high_threshold_is_high(self):
        assert main.classify_zone(75000, 70000, 55000) == "high"

    def test_below_low_threshold_is_low(self):
        assert main.classify_zone(50000, 70000, 55000) == "low"

    def test_between_thresholds_is_none(self):
        assert main.classify_zone(60000, 70000, 55000) is None

    def test_exactly_at_high_threshold_is_none(self):
        assert main.classify_zone(70000, 70000, 55000) is None

    def test_exactly_at_low_threshold_is_none(self):
        assert main.classify_zone(55000, 70000, 55000) is None


class TestFormatAlert:
    def test_high_zone_message(self):
        msg = main.format_alert("high", 75000)
        assert "HIGH" in msg
        assert "75000" in msg

    def test_low_zone_message(self):
        msg = main.format_alert("low", 50000)
        assert "DIP" in msg
        assert "50000" in msg


class TestGetBtc:
    @patch("main.requests.get")
    def test_returns_price_from_response(self, mock_get):
        mock_get.return_value = Mock(json=lambda: {"bitcoin": {"usd": 65000}})
        assert main.get_btc() == 65000

    @patch("main.requests.get")
    def test_raises_on_http_error(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("boom")
        mock_get.return_value = mock_response
        with pytest.raises(requests.HTTPError):
            main.get_btc()


class TestSend:
    @patch("main.requests.post")
    def test_posts_to_telegram_api_with_correct_payload(self, mock_post):
        mock_post.return_value = Mock(raise_for_status=lambda: None)
        main.send("tok123", "chat456", "hello")
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.telegram.org/bottok123/sendMessage"
        assert kwargs["json"] == {"chat_id": "chat456", "text": "hello"}

    @patch("main.requests.post")
    def test_raises_on_http_error(self, mock_post):
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("boom")
        mock_post.return_value = mock_response
        with pytest.raises(requests.HTTPError):
            main.send("tok123", "chat456", "hello")

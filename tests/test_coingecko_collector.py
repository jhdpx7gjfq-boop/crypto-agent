import pytest
from src.data.coingecko_collector import CoinGeckoCollector


class TestCoinGeckoCollector:
    @pytest.fixture
    def collector(self):
        return CoinGeckoCollector()

    def test_init(self, collector):
        assert collector.api_base == "https://api.coingecko.com/api/v3"
        assert collector.session is not None

    def test_get_price(self, collector):
        data = collector.get_price(["bitcoin"])
        assert "bitcoin" in data
        assert "usd" in data["bitcoin"]
        assert data["bitcoin"]["usd"] > 0

    def test_get_price_multiple_coins(self, collector):
        data = collector.get_price(["bitcoin", "ethereum"])
        assert len(data) == 2
        assert all(coin in data for coin in ["bitcoin", "ethereum"])

    def test_get_price_with_market_cap(self, collector):
        data = collector.get_price(["bitcoin"])
        assert "usd_market_cap" in data["bitcoin"]
        assert "usd_24h_vol" in data["bitcoin"]

    def test_get_market_chart(self, collector):
        df = collector.get_market_chart("bitcoin", days=7)
        assert len(df) > 0
        assert "timestamp" in df.columns
        assert "price" in df.columns
        assert "market_cap" in df.columns
        assert "volume" in df.columns

    def test_get_market_chart_columns(self, collector):
        df = collector.get_market_chart("bitcoin", days=1)
        expected_cols = {"timestamp", "price", "market_cap", "volume"}
        assert expected_cols.issubset(set(df.columns))

    def test_get_global(self, collector):
        data = collector.get_global()
        assert "data" in data
        assert "total_market_cap" in data["data"]
        assert "market_cap_percentage" in data["data"]

    def test_search(self, collector):
        results = collector.search("Bitcoin")
        assert len(results) > 0
        assert any("bitcoin" in r["name"].lower() for r in results)

    def test_validate_price_missing_coin(self, collector):
        with pytest.raises(ValueError, match="Missing coin"):
            collector._validate_price({"ethereum": {"usd": 2000}}, ["bitcoin"])

    def test_validate_price_missing_usd(self, collector):
        with pytest.raises(ValueError, match="Missing USD price"):
            collector._validate_price({"bitcoin": {}}, ["bitcoin"])

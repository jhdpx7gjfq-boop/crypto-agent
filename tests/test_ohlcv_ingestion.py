"""OHLCV normalisation: what a vendor export may contain, and what survives."""

from datetime import date

import pytest

from igwt.data import ohlcv

GOOD = {"date": "2026-01-01", "open": "10", "high": "12", "low": "9", "close": "11", "volume": "5"}


def rows(*overrides):
    return [{**GOOD, **item} for item in overrides]


class TestConsistency:
    def test_a_well_formed_bar_is_accepted(self):
        series = ohlcv.normalise("BTCUSDT", rows({}))
        assert len(series) == 1
        assert series.bars[0] == ohlcv.Bar(date(2026, 1, 1), 10.0, 12.0, 9.0, 11.0, 5.0)

    @pytest.mark.parametrize(
        "broken",
        [
            {"high": "10.5"},  # high below the close
            {"low": "11.5"},  # low above the close
            {"high": "8", "low": "9"},  # high below low
            {"close": "-1"},
            {"open": "0"},
            {"volume": "-3"},
        ],
    )
    def test_a_bar_violating_its_own_ordering_is_dropped(self, broken):
        series = ohlcv.normalise("BTCUSDT", rows(broken))
        assert len(series) == 0
        assert series.report["inconsistent_bars_dropped"] == 1

    def test_an_unparsable_row_is_counted_not_crashed_on(self):
        series = ohlcv.normalise("BTCUSDT", rows({"close": "n/a"}, {}))
        assert len(series) == 1
        assert series.report["unparsable_rows_dropped"] == 1

    def test_duplicates_are_dropped_and_counted(self):
        series = ohlcv.normalise("BTCUSDT", rows({}, {}))
        assert len(series) == 1
        assert series.report["duplicate_rows_dropped"] == 1

    def test_descending_input_is_sorted_and_flagged(self):
        series = ohlcv.normalise(
            "BTCUSDT", rows({"date": "2026-01-03"}, {"date": "2026-01-02"}, {"date": "2026-01-01"})
        )
        assert series.dates == [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 3)]
        assert series.report["out_of_order_input"] is True

    def test_gaps_are_reported_not_filled(self):
        series = ohlcv.normalise("BTCUSDT", rows({"date": "2026-01-01"}, {"date": "2026-01-05"}))
        assert len(series) == 2
        assert series.report["calendar_gaps"][0]["missing_days"] == 3


class TestDateParsing:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("2026-01-02", date(2026, 1, 2)),
            ("2026-01-02 00:00:00", date(2026, 1, 2)),
            ("2026-01-02T00:00:00", date(2026, 1, 2)),
            ("1767312000000", date(2026, 1, 2)),  # unix milliseconds
            ("1767312000", date(2026, 1, 2)),  # unix seconds
            (date(2026, 1, 2), date(2026, 1, 2)),
        ],
    )
    def test_accepted_spellings(self, value, expected):
        assert ohlcv.parse_day(value) == expected

    def test_an_empty_date_is_rejected(self):
        with pytest.raises(ValueError):
            ohlcv.parse_day("")


class TestColumnResolution:
    def test_base_volume_is_preferred_over_quote_volume(self):
        header = ["Date", "Open", "High", "Low", "Close", "Volume BTC", "Volume USDT"]
        resolved = ohlcv.resolve_columns(header, base_asset="BTC")
        assert resolved["volume"] == "Volume BTC"

    def test_quote_volume_alone_is_not_silently_accepted_as_base(self):
        header = ["Date", "Open", "High", "Low", "Close", "Volume USDT"]
        resolved = ohlcv.resolve_columns(header, base_asset="BTC")
        assert "volume" not in resolved

    def test_a_missing_price_column_is_an_error(self):
        with pytest.raises(ohlcv.IngestionError, match="no column for 'close'"):
            ohlcv.resolve_columns(["Date", "Open", "High", "Low"])

    def test_matching_is_case_insensitive(self):
        resolved = ohlcv.resolve_columns(["unix", "OPEN", "high", "Low", "CLOSE"])
        assert resolved["date"] == "unix"
        assert resolved["close"] == "CLOSE"


class TestVendorCsv:
    def _write(self, tmp_path, text):
        path = tmp_path / "Binance_BTCUSDT_d.csv"
        path.write_text(text, encoding="utf-8")
        return path

    def test_a_preamble_line_above_the_header_is_tolerated(self, tmp_path):
        path = self._write(
            tmp_path,
            "https://www.example-vendor.com/ Data provided as is\n"
            "Unix,Date,Symbol,Open,High,Low,Close,Volume BTC,Volume USDT\n"
            "1767312000000,2026-01-02,BTCUSDT,10,12,9,11,5,55\n"
            "1767225600000,2026-01-01,BTCUSDT,9,11,8,10,4,40\n",
        )
        series = ohlcv.read_vendor_csv(path, "BTCUSDT", base_asset="BTC")
        assert series.dates == [date(2026, 1, 1), date(2026, 1, 2)]
        assert series.closes == [10.0, 11.0]
        assert series.source_columns["volume"] == "Volume BTC"
        assert series.source_columns["close"] == "Close"

    def test_a_file_without_ohlc_columns_is_refused(self, tmp_path):
        path = self._write(tmp_path, "date,price\n2026-01-01,10\n")
        with pytest.raises(ohlcv.IngestionError, match="no header row"):
            ohlcv.read_vendor_csv(path, "BTCUSDT")


class TestPanelAdapter:
    def test_the_adapter_feeds_the_same_panel_type_the_features_consume(self):
        series = ohlcv.normalise("BTCUSDT", rows({"date": "2026-01-01"}, {"date": "2026-01-02"}))
        adapted = series.to_asset_series()
        assert adapted.asset == "BTCUSDT"
        assert adapted.dates == series.dates
        assert adapted.closes == series.closes

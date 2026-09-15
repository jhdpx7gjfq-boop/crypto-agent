"""Point-in-time integrity: a feature must not move when the future does."""

import math

import pytest

from igwt.features import panel, pit


class TestLookaheadFreedom:
    def test_trailing_return_ignores_future_prices(self):
        closes = [100.0, 102.0, 101.0, 105.0, 107.0, 110.0]
        tampered = closes[:4] + [9999.0, 8888.0]

        original = pit.trailing_return(closes, 2)
        rewritten = pit.trailing_return(tampered, 2)

        assert original[:4] == rewritten[:4]

    def test_realized_volatility_ignores_future_prices(self):
        closes = [100.0, 102.0, 101.0, 105.0, 107.0, 110.0, 108.0]
        tampered = closes[:5] + [1.0, 50000.0]

        original = pit.realized_volatility(closes, 3)
        rewritten = pit.realized_volatility(tampered, 3)

        assert original[:5] == rewritten[:5]

    def test_forward_return_is_a_label_and_does_read_the_future(self):
        """Stated explicitly so the asymmetry with the features above is deliberate."""
        closes = [100.0, 110.0, 121.0]
        assert pit.forward_return(closes, 1)[0] == pytest.approx(0.10)
        assert pit.forward_return(closes, 1)[-1] is None

    def test_cross_sectional_zscore_uses_only_its_own_date(self):
        today = {"A": 1.0, "B": 2.0, "C": 3.0}
        assert pit.cross_sectional_zscore(today) == {"A": -1.0, "B": 0.0, "C": 1.0}


class TestUndefinedValues:
    def test_insufficient_history_yields_none_not_a_filled_value(self):
        assert pit.trailing_return([100.0, 101.0], 5) == [None, None]
        assert pit.realized_volatility([100.0, 101.0], 5) == [None, None]

    def test_thin_cross_section_yields_none(self):
        assert pit.cross_sectional_zscore({"A": 1.0, "B": 2.0}) == {"A": None, "B": None}

    def test_zero_dispersion_yields_none(self):
        assert pit.cross_sectional_zscore({"A": 5.0, "B": 5.0, "C": 5.0}) == {
            "A": None,
            "B": None,
            "C": None,
        }

    def test_missing_asset_stays_missing(self):
        result = pit.cross_sectional_zscore({"A": 1.0, "B": 2.0, "C": 3.0, "D": None})
        assert result["D"] is None

    @pytest.mark.parametrize("bad", [0, -1])
    def test_invalid_lookback_rejected(self, bad):
        with pytest.raises(ValueError):
            pit.trailing_return([1.0, 2.0], bad)
        with pytest.raises(ValueError):
            pit.forward_return([1.0, 2.0], bad)


class TestKnownValues:
    def test_trailing_return_arithmetic(self):
        assert pit.trailing_return([100.0, 150.0], 1)[1] == pytest.approx(0.5)

    def test_realized_volatility_of_a_constant_series_is_zero(self):
        assert pit.realized_volatility([100.0] * 10, 5)[9] == pytest.approx(0.0)

    def test_realized_volatility_annualisation(self):
        closes = [100.0, 101.0, 100.0, 101.0, 100.0, 101.0, 100.0]
        unscaled = pit.realized_volatility(closes, 4, annualise=False)[6]
        scaled = pit.realized_volatility(closes, 4)[6]
        assert scaled == pytest.approx(unscaled * math.sqrt(365))


class TestContiguityMasks:
    def test_backward_mask_rejects_a_window_spanning_a_gap(self):
        from datetime import date

        dates = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 5), date(2026, 1, 6)]
        # index 2 sits 3 calendar days after index 0, so a 2-row window is not 2 days
        assert panel.contiguous_backward_mask(dates, 2) == [False, False, False, False]

    def test_backward_mask_accepts_consecutive_days(self):
        from datetime import date

        dates = [date(2026, 1, day) for day in range(1, 6)]
        assert panel.contiguous_backward_mask(dates, 2) == [False, False, True, True, True]

    def test_forward_mask_rejects_a_label_window_spanning_a_gap(self):
        from datetime import date

        dates = [date(2026, 1, 1), date(2026, 1, 2), date(2026, 1, 9)]
        assert panel.contiguous_forward_mask(dates, 1) == [True, False, False]

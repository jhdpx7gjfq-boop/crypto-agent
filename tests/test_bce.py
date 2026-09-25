"""BCE Engine tests: Wyckoff-based bottom confirmation."""

import random
from datetime import date, timedelta

import pytest

from igwt.engines import bce

random.seed(42)


@pytest.fixture
def synthetic_bullish_accumulation():
    """Synthetic OHLCV with a clear accumulation bottom."""
    dates = []
    opens = []
    highs = []
    lows = []
    closes = []
    volumes = []

    # Create a downtrend, then accumulation pattern
    for i in range(300):
        d = date(2025, 1, 1) + timedelta(days=i)

        if i < 100:
            # Bearish trend down
            close = 100 - (i * 0.3)
        elif i < 150:
            # Capitulation (W5): sharp drop then recovery starts
            close = 70 - (5 * (i - 125) / 50)
        else:
            # Consolidation and recovery
            close = 70 + ((i - 150) * 0.2)

        high = close + random.uniform(0, 2)
        low = close - random.uniform(0, 2)
        open_price = close + random.uniform(-1, 1)
        volume = 1000 + random.uniform(-200, 1000)

        if 145 <= i <= 155:
            # High volume at capitulation
            volume *= 3

        dates.append(d)
        opens.append(open_price)
        highs.append(high)
        lows.append(low)
        closes.append(close)
        volumes.append(max(volume, 100))

    return dates, opens, highs, lows, closes, volumes


@pytest.fixture
def synthetic_false_bottom():
    """Synthetic OHLCV with no clear accumulation (noise)."""
    dates = []
    opens = []
    highs = []
    lows = []
    closes = []
    volumes = []

    close = 100.0
    for i in range(300):
        d = date(2025, 1, 1) + timedelta(days=i)
        close += random.gauss(0, 2)

        high = close + random.uniform(0, 1)
        low = close - random.uniform(0, 1)
        open_price = close + random.uniform(-0.5, 0.5)
        volume = 1000.0 + random.uniform(-200, 200)

        dates.append(d)
        opens.append(open_price)
        highs.append(high)
        lows.append(low)
        closes.append(close)
        volumes.append(max(volume, 100))

    return dates, opens, highs, lows, closes, volumes


class TestBCEOutput:
    def test_score_is_between_0_and_6(self, synthetic_bullish_accumulation):
        dates, opens, highs, lows, closes, volumes = synthetic_bullish_accumulation
        score_obj = bce.compute_bce_score(dates, opens, highs, lows, closes, volumes, dates[-1])
        assert 0 <= score_obj.score <= 6

    def test_components_are_boolean(self, synthetic_bullish_accumulation):
        dates, opens, highs, lows, closes, volumes = synthetic_bullish_accumulation
        score_obj = bce.compute_bce_score(dates, opens, highs, lows, closes, volumes, dates[-1])
        assert isinstance(score_obj.components, dict)
        assert all(isinstance(v, bool) for v in score_obj.components.values())

    def test_signal_inferred_correctly(self, synthetic_bullish_accumulation):
        dates, opens, highs, lows, closes, volumes = synthetic_bullish_accumulation
        score_obj = bce.compute_bce_score(dates, opens, highs, lows, closes, volumes, dates[-1])
        if score_obj.score >= 5:
            assert score_obj.signal == "BUY"
        elif score_obj.score == 4:
            assert score_obj.signal == "WAIT"
        else:
            assert score_obj.signal == "MONITOR"


class TestLookbackValidation:
    def test_rejects_insufficient_lookback(self, synthetic_bullish_accumulation):
        dates, opens, highs, lows, closes, volumes = synthetic_bullish_accumulation
        short_dates, short_opens, short_highs, short_lows, short_closes, short_volumes = (
            dates[-100:],
            opens[-100:],
            highs[-100:],
            lows[-100:],
            closes[-100:],
            volumes[-100:],
        )
        with pytest.raises(ValueError, match="Insufficient data"):
            bce.compute_bce_score(
                short_dates, short_opens, short_highs, short_lows, short_closes, short_volumes, short_dates[-1]
            )

    def test_rejects_date_not_in_data(self, synthetic_bullish_accumulation):
        dates, opens, highs, lows, closes, volumes = synthetic_bullish_accumulation
        with pytest.raises(ValueError, match="Date .* not in dates"):
            bce.compute_bce_score(
                dates, opens, highs, lows, closes, volumes,
                date(2024, 1, 1),
            )

    def test_accepts_minimum_lookback(self, synthetic_bullish_accumulation):
        dates, opens, highs, lows, closes, volumes = synthetic_bullish_accumulation
        score_obj = bce.compute_bce_score(
            dates[-252:], opens[-252:], highs[-252:], lows[-252:], closes[-252:], volumes[-252:],
            dates[-1],
        )
        assert isinstance(score_obj, bce.BCEScore)


class TestComponentsIndependence:
    def test_all_six_components_evaluated(self, synthetic_bullish_accumulation):
        dates, opens, highs, lows, closes, volumes = synthetic_bullish_accumulation
        score_obj = bce.compute_bce_score(dates, opens, highs, lows, closes, volumes, dates[-1])
        expected_keys = {
            "wyckoff_structure",
            "volume_profile",
            "selling_exhaustion",
            "smart_money_accumulation",
            "market_structure",
            "momentum_confirmation",
        }
        assert set(score_obj.components.keys()) == expected_keys

    def test_each_component_contributes_to_score(self, synthetic_bullish_accumulation):
        dates, opens, highs, lows, closes, volumes = synthetic_bullish_accumulation
        score_obj = bce.compute_bce_score(dates, opens, highs, lows, closes, volumes, dates[-1])
        manual_sum = sum(score_obj.components.values())
        assert score_obj.score == manual_sum


class TestDeterminism:
    def test_rebuild_yields_same_score(self, synthetic_bullish_accumulation):
        dates, opens, highs, lows, closes, volumes = synthetic_bullish_accumulation
        score1 = bce.compute_bce_score(dates, opens, highs, lows, closes, volumes, dates[-1])
        score2 = bce.compute_bce_score(dates, opens, highs, lows, closes, volumes, dates[-1])

        assert score1.score == score2.score
        assert score1.components == score2.components

    def test_rebuild_from_identical_data_matches(self, synthetic_bullish_accumulation):
        dates, opens, highs, lows, closes, volumes = synthetic_bullish_accumulation
        score_orig = bce.compute_bce_score(dates, opens, highs, lows, closes, volumes, dates[-1])

        dates_copy = dates.copy()
        opens_copy = opens.copy()
        highs_copy = highs.copy()
        lows_copy = lows.copy()
        closes_copy = closes.copy()
        volumes_copy = volumes.copy()

        score_copy = bce.compute_bce_score(
            dates_copy, opens_copy, highs_copy, lows_copy, closes_copy, volumes_copy, dates_copy[-1]
        )

        assert score_orig.score == score_copy.score


class TestSignalPrediction:
    def test_bullish_accumulation_scores_high(self, synthetic_bullish_accumulation):
        dates, opens, highs, lows, closes, volumes = synthetic_bullish_accumulation
        score_obj = bce.compute_bce_score(dates, opens, highs, lows, closes, volumes, dates[-1])
        # A well-formed bottom should score >= 2
        assert score_obj.score >= 2, f"Bullish pattern scored only {score_obj.score}"

    def test_noise_scores_low(self, synthetic_false_bottom):
        dates, opens, highs, lows, closes, volumes = synthetic_false_bottom
        score_obj = bce.compute_bce_score(dates, opens, highs, lows, closes, volumes, dates[-1])
        # Random walk should not score all 6 factors
        assert score_obj.score <= 4, f"Noise pattern scored {score_obj.score}"


class TestEdgeCases:
    def test_constant_price_series_handled(self):
        dates = [date(2025, 1, 1) + timedelta(days=i) for i in range(300)]
        opens = [100.0] * 300
        highs = [100.0] * 300
        lows = [100.0] * 300
        closes = [100.0] * 300
        volumes = [1000.0] * 300

        score_obj = bce.compute_bce_score(dates, opens, highs, lows, closes, volumes, dates[-1])
        assert score_obj.score >= 0

    def test_extreme_volume_spike_handled(self):
        dates = []
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []

        close = 100.0
        for i in range(300):
            d = date(2025, 1, 1) + timedelta(days=i)
            close += 0.1

            high = close + 1
            low = close - 1
            open_price = close
            volume = 1000.0
            if i == 150:
                volume = 1000000.0  # Extreme spike

            dates.append(d)
            opens.append(open_price)
            highs.append(high)
            lows.append(low)
            closes.append(close)
            volumes.append(volume)

        score_obj = bce.compute_bce_score(dates, opens, highs, lows, closes, volumes, dates[-1])
        assert score_obj.score >= 0

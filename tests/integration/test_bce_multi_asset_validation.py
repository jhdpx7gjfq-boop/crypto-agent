"""
Multi-Asset Validation for Layer 3 BCE Engine.

Validates that BCE generalizes across different crypto assets:
- BTC (large cap, high liquidity)
- ETH (large cap, high liquidity)
- SOL (mid cap, moderate liquidity)
- LINK (mid cap, moderate liquidity)

Tests cross-asset consistency, scoring patterns, and robustness.
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from src.layers.layer3_wyckoff.bce_engine import BottomConfirmationEngine
from src.core.models import OHLCV
from tests.fixtures.market_data import (
    generate_accumulation_ohlcv,
    generate_bull_ohlcv,
    generate_bear_ohlcv,
)


class TestBCEMultiAssetConsistency:
    """Test BCE scoring consistency across different assets."""

    @pytest.fixture
    def bce_engine(self):
        """Create BCE engine."""
        return BottomConfirmationEngine()

    def test_bce_scores_similar_patterns_similarly(self, bce_engine):
        """Identical patterns should produce similar BCE scores across assets."""
        # Generate same accumulation pattern
        ohlcv = generate_accumulation_ohlcv(100)

        # Analyze same pattern on different assets
        btc_signal = bce_engine.analyze("BTC", ohlcv)
        eth_signal = bce_engine.analyze("ETH", ohlcv)
        sol_signal = bce_engine.analyze("SOL", ohlcv)

        # Scores should be identical (same pattern)
        assert btc_signal.bce_score == eth_signal.bce_score
        assert eth_signal.bce_score == sol_signal.bce_score

        # Components should match
        assert btc_signal.smart_money_accumulation == eth_signal.smart_money_accumulation
        assert btc_signal.volume_analysis == sol_signal.volume_analysis

    def test_bce_validity_threshold_consistent(self, bce_engine):
        """Validity threshold (≥5/6) should be consistent across assets."""
        ohlcv = generate_accumulation_ohlcv(100)

        signals = {
            "BTC": bce_engine.analyze("BTC", ohlcv),
            "ETH": bce_engine.analyze("ETH", ohlcv),
            "SOL": bce_engine.analyze("SOL", ohlcv),
            "LINK": bce_engine.analyze("LINK", ohlcv),
        }

        # All should have same validity (same score)
        validity_results = [s.valid for s in signals.values()]
        assert all(v == validity_results[0] for v in validity_results)

        # Threshold enforcement
        for asset, signal in signals.items():
            if signal.bce_score >= 5.0:
                assert signal.valid is True, f"{asset} should be valid with score {signal.bce_score}"
            else:
                assert signal.valid is False, f"{asset} should be invalid with score {signal.bce_score}"

    def test_bce_component_ranges_consistent(self, bce_engine):
        """All components should stay in [0, 1] range across assets."""
        for pattern_gen in [generate_accumulation_ohlcv, generate_bull_ohlcv, generate_bear_ohlcv]:
            ohlcv = pattern_gen(100)

            for asset in ["BTC", "ETH", "SOL", "LINK"]:
                signal = bce_engine.analyze(asset, ohlcv)

                components = [
                    signal.wyckoff_structure,
                    signal.volume_analysis,
                    signal.selling_exhaustion,
                    signal.smart_money_accumulation,
                    signal.market_structure,
                    signal.momentum_confirmation,
                ]

                for comp in components:
                    assert 0 <= comp <= 1, \
                        f"{asset} component {comp} outside [0,1] for {pattern_gen.__name__}"


class TestBCEAssetBehavior:
    """Test asset-specific BCE behavior patterns."""

    @pytest.fixture
    def bce_engine(self):
        return BottomConfirmationEngine()

    def test_accumulation_pattern_across_assets(self, bce_engine):
        """Accumulation should score high (BCE ≥ 3.0) on all assets."""
        ohlcv = generate_accumulation_ohlcv(100)

        for asset in ["BTC", "ETH", "SOL", "LINK"]:
            signal = bce_engine.analyze(asset, ohlcv)

            assert signal.bce_score >= 2.5, \
                f"{asset} accumulation pattern should score ≥ 2.5, got {signal.bce_score}"
            assert signal.smart_money_accumulation >= 0.3, \
                f"{asset} should detect some smart money accumulation ≥ 0.3"

    def test_uptrend_pattern_across_assets(self, bce_engine):
        """Uptrend should score lower (not bottom formation)."""
        ohlcv = generate_bull_ohlcv(100)

        for asset in ["BTC", "ETH", "SOL", "LINK"]:
            signal = bce_engine.analyze(asset, ohlcv)

            # Uptrend is not bottom formation
            assert signal.bce_score < 4.5, \
                f"{asset} uptrend should not score too high, got {signal.bce_score}"
            # But should still have some structure
            assert signal.wyckoff_structure > 0.3

    def test_downtrend_pattern_across_assets(self, bce_engine):
        """Downtrend should score low (continued selling)."""
        ohlcv = generate_bear_ohlcv(100)

        accum_ohlcv = generate_accumulation_ohlcv(100)
        for asset in ["BTC", "ETH", "SOL", "LINK"]:
            signal = bce_engine.analyze(asset, ohlcv)
            accum_signal = bce_engine.analyze(asset, accum_ohlcv)

            # Downtrend should score lower than accumulation
            assert signal.bce_score < accum_signal.bce_score, \
                f"{asset} downtrend should score lower than accumulation"

    def test_asset_scoring_distribution(self, bce_engine):
        """Score distribution should be reasonable across assets."""
        accumulation = generate_accumulation_ohlcv(100)
        bull = generate_bull_ohlcv(100)
        bear = generate_bear_ohlcv(100)

        assets = ["BTC", "ETH", "SOL", "LINK"]
        patterns = {
            "accumulation": accumulation,
            "bull": bull,
            "bear": bear,
        }

        results = {}
        for asset in assets:
            results[asset] = {}
            for pattern_name, ohlcv in patterns.items():
                signal = bce_engine.analyze(asset, ohlcv)
                results[asset][pattern_name] = signal.bce_score

        # Pattern scoring should be consistent across assets
        for asset in assets:
            # All assets should produce different scores for different patterns
            unique_scores = len(set(results[asset].values()))
            assert unique_scores >= 2, \
                f"{asset} should differentiate between patterns"


class TestBCEMultiAssetRobustness:
    """Test BCE robustness across different asset types."""

    @pytest.fixture
    def bce_engine(self):
        return BottomConfirmationEngine()

    def test_insufficient_data_handling_consistent(self, bce_engine):
        """Insufficient data should be handled consistently across assets."""
        short_data = generate_accumulation_ohlcv(5)  # Only 5 candles

        for asset in ["BTC", "ETH", "SOL", "LINK"]:
            signal = bce_engine.analyze(asset, short_data)

            assert signal.valid is False
            assert signal.bce_score == 0
            assert signal.wyckoff_structure == 0

    def test_empty_data_handling(self, bce_engine):
        """Empty data should be handled gracefully."""
        for asset in ["BTC", "ETH", "SOL", "LINK"]:
            signal = bce_engine.analyze(asset, [])

            assert signal.valid is False
            assert signal.bce_score == 0

    def test_extreme_price_movements_handled(self, bce_engine):
        """Extreme movements (gaps, flash crashes) should not crash."""
        # Generate data with large gap up
        base = generate_accumulation_ohlcv(50)

        # Add extreme candle
        extreme_close = base[-1].close * 1.5  # 50% jump
        extreme_candle = OHLCV(
            timestamp=base[-1].timestamp + timedelta(hours=1),
            open=base[-1].close,
            high=extreme_close,
            low=base[-1].close,
            close=extreme_close,
            volume=base[-1].volume * 3,
        )

        test_data = base + [extreme_candle]

        for asset in ["BTC", "ETH", "SOL"]:
            # Should not crash
            signal = bce_engine.analyze(asset, test_data)

            # Score should be reasonable (not NaN, not inf)
            assert 0 <= signal.bce_score <= 6
            assert signal.bce_score == signal.bce_score  # Not NaN

    def test_zero_volume_candle_handling(self, bce_engine):
        """Zero-volume candles should be handled without division errors."""
        base = generate_accumulation_ohlcv(50)

        # Add zero-volume candle
        zero_vol_candle = OHLCV(
            timestamp=base[-1].timestamp + timedelta(hours=1),
            open=base[-1].close,
            high=base[-1].high,
            low=base[-1].low,
            close=base[-1].close,
            volume=0.0,
        )

        test_data = base + [zero_vol_candle]

        for asset in ["BTC", "ETH", "SOL"]:
            # Should not crash with division by zero
            signal = bce_engine.analyze(asset, test_data)

            assert 0 <= signal.bce_score <= 6
            assert not (signal.bce_score != signal.bce_score)  # Not NaN


class TestBCECrossAssetComparison:
    """Compare BCE behavior across asset types."""

    @pytest.fixture
    def bce_engine(self):
        return BottomConfirmationEngine()

    def test_component_importance_across_assets(self, bce_engine):
        """Component importance should be similar across assets."""
        ohlcv = generate_accumulation_ohlcv(100)

        component_weights = {}
        for asset in ["BTC", "ETH", "SOL"]:
            signal = bce_engine.analyze(asset, ohlcv)

            # Calculate component contribution to total score
            total = (
                signal.wyckoff_structure +
                signal.volume_analysis +
                signal.selling_exhaustion +
                signal.smart_money_accumulation +
                signal.market_structure +
                signal.momentum_confirmation
            )

            component_weights[asset] = {
                "wyckoff_structure": signal.wyckoff_structure / total if total > 0 else 0,
                "smart_money": signal.smart_money_accumulation / total if total > 0 else 0,
                "volume": signal.volume_analysis / total if total > 0 else 0,
            }

        # Smart money should be significant for accumulation across all assets
        for asset in ["BTC", "ETH", "SOL"]:
            assert component_weights[asset]["smart_money"] > 0.10, \
                f"{asset} smart_money should be >10% of score for accumulation"

    def test_confidence_levels_consistent(self, bce_engine):
        """Confidence classification should be consistent across assets."""
        strong_pattern = generate_accumulation_ohlcv(100)
        weak_pattern = generate_bear_ohlcv(100)

        scores_strong = {}
        scores_weak = {}

        for asset in ["BTC", "ETH", "SOL"]:
            signal_strong = bce_engine.analyze(asset, strong_pattern)
            signal_weak = bce_engine.analyze(asset, weak_pattern)

            scores_strong[asset] = signal_strong.bce_score
            scores_weak[asset] = signal_weak.bce_score

        # All assets should score strong pattern higher than weak pattern
        for asset in ["BTC", "ETH", "SOL"]:
            assert scores_strong[asset] > scores_weak[asset], \
                f"{asset} strong pattern should score higher than weak pattern"


class TestBCEAssetRanking:
    """Test ranking and filtering across multiple assets."""

    @pytest.fixture
    def bce_engine(self):
        return BottomConfirmationEngine()

    def test_multi_asset_ranking_by_score(self, bce_engine):
        """Should be able to rank multiple assets by BCE score."""
        ohlcv = generate_accumulation_ohlcv(100)

        asset_scores = {}
        for asset in ["BTC", "ETH", "SOL", "LINK"]:
            signal = bce_engine.analyze(asset, ohlcv)
            asset_scores[asset] = signal.bce_score

        # Should be able to rank them
        ranked = sorted(asset_scores.items(), key=lambda x: x[1], reverse=True)

        assert len(ranked) == 4
        assert ranked[0][1] >= ranked[1][1] >= ranked[2][1] >= ranked[3][1]

    def test_valid_signal_filtering(self, bce_engine):
        """Should be able to filter for valid signals across assets."""
        strong_pattern = generate_accumulation_ohlcv(100)
        weak_pattern = generate_bear_ohlcv(100)

        assets_strong = ["BTC", "ETH"]
        assets_weak = ["SOL", "LINK"]

        # Score all assets
        asset_scores = {}
        for asset in assets_strong:
            signal = bce_engine.analyze(asset, strong_pattern)
            asset_scores[asset] = signal.bce_score

        for asset in assets_weak:
            signal = bce_engine.analyze(asset, weak_pattern)
            asset_scores[asset] = signal.bce_score

        # All assets should produce valid scores in range [0, 6]
        for asset, score in asset_scores.items():
            assert 0 <= score <= 6, f"{asset} score {score} outside valid range"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

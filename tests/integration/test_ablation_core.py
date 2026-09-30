"""
Core ablation engine tests - focused on key functionality.
"""

import pytest
import numpy as np
from src.analysis.ablation_engine import AblationEngine


class TestAblationEngineCore:
    """Core tests for AblationEngine."""

    @pytest.fixture
    def engine(self):
        """Create ablation engine."""
        return AblationEngine()

    @pytest.fixture
    def sample_data(self):
        """Generate sample data with clear component differentiation."""
        num_samples = 100

        bce_scores = []
        for i in range(num_samples):
            # Base quality with trend
            base = 0.65 + 0.15 * np.sin(i / 25)

            scores = {
                'wyckoff_structure': min(1, base + 0.08 + np.random.normal(0, 0.03)),
                'volume_analysis': min(1, base + 0.05 + np.random.normal(0, 0.04)),
                'selling_exhaustion': min(1, base - 0.10 + np.random.normal(0, 0.08)),
                'smart_money_accumulation': min(1, base + 0.03 + np.random.normal(0, 0.05)),
                'market_structure': min(1, base + 0.07 + np.random.normal(0, 0.03)),
                'momentum_confirmation': min(1, base - 0.05 + np.random.normal(0, 0.06)),
            }

            scores = {k: max(0, v) for k, v in scores.items()}
            scores['bce_score'] = np.mean(list(scores.values()))
            bce_scores.append(scores)

        signal_counts = [int(30 + 10 * s['bce_score']) for s in bce_scores]
        win_rates = [0.55 + 0.10 * s['bce_score'] for s in bce_scores]
        pfs = [1.3 + 0.25 * s['bce_score'] for s in bce_scores]
        confidences = [s['bce_score'] * 100 for s in bce_scores]

        return {
            'bce_scores': bce_scores,
            'signal_counts': signal_counts,
            'win_rates': win_rates,
            'profit_factors': pfs,
            'confidence_scores': confidences,
        }

    def test_engine_creation(self, engine):
        """Test engine instantiation."""
        assert engine is not None
        assert len(engine.COMPONENTS) == 6

    def test_ablation_runs(self, engine, sample_data):
        """Test that ablation completes without error."""
        result = engine.ablate_components(
            asset='BTC',
            bce_scores=sample_data['bce_scores'],
            signal_counts=sample_data['signal_counts'],
            win_rates=sample_data['win_rates'],
            profit_factors=sample_data['profit_factors'],
            confidence_scores=sample_data['confidence_scores'],
        )

        assert result is not None
        assert len(result.component_results) == 6

    def test_all_components_ranked(self, engine, sample_data):
        """Test all components are included in ranking."""
        result = engine.ablate_components(
            asset='BTC',
            bce_scores=sample_data['bce_scores'],
            signal_counts=sample_data['signal_counts'],
            win_rates=sample_data['win_rates'],
            profit_factors=sample_data['profit_factors'],
            confidence_scores=sample_data['confidence_scores'],
        )

        ranked_names = [name for name, _ in result.component_ranking]
        assert len(ranked_names) == 6
        for comp in engine.COMPONENTS:
            assert comp in ranked_names

    def test_importance_scores_valid_range(self, engine, sample_data):
        """Test importance scores are in valid range [0, 100]."""
        result = engine.ablate_components(
            asset='BTC',
            bce_scores=sample_data['bce_scores'],
            signal_counts=sample_data['signal_counts'],
            win_rates=sample_data['win_rates'],
            profit_factors=sample_data['profit_factors'],
            confidence_scores=sample_data['confidence_scores'],
        )

        for comp_result in result.component_results:
            assert 0 <= comp_result.importance_score <= 100

    def test_ranking_is_sorted(self, engine, sample_data):
        """Test ranking is sorted by importance descending."""
        result = engine.ablate_components(
            asset='BTC',
            bce_scores=sample_data['bce_scores'],
            signal_counts=sample_data['signal_counts'],
            win_rates=sample_data['win_rates'],
            profit_factors=sample_data['profit_factors'],
            confidence_scores=sample_data['confidence_scores'],
        )

        scores = [score for _, score in result.component_ranking]
        assert scores == sorted(scores, reverse=True)

    def test_summary_statistics_valid(self, engine, sample_data):
        """Test summary statistics are computed."""
        result = engine.ablate_components(
            asset='BTC',
            bce_scores=sample_data['bce_scores'],
            signal_counts=sample_data['signal_counts'],
            win_rates=sample_data['win_rates'],
            profit_factors=sample_data['profit_factors'],
            confidence_scores=sample_data['confidence_scores'],
        )

        assert result.avg_importance >= 0
        assert result.std_importance >= 0
        assert result.total_impact >= 0

    def test_report_generation(self, engine, sample_data):
        """Test report can be generated."""
        result = engine.ablate_components(
            asset='BTC',
            bce_scores=sample_data['bce_scores'],
            signal_counts=sample_data['signal_counts'],
            win_rates=sample_data['win_rates'],
            profit_factors=sample_data['profit_factors'],
            confidence_scores=sample_data['confidence_scores'],
        )

        report = engine.get_ablation_report('BTC')
        assert report is not None
        assert 'ABLATION TESTING REPORT' in report
        assert 'BTC' in report

    def test_multi_asset_support(self, engine, sample_data):
        """Test ablation on multiple assets."""
        for asset in ['BTC', 'ETH', 'SOL']:
            result = engine.ablate_components(
                asset=asset,
                bce_scores=sample_data['bce_scores'],
                signal_counts=sample_data['signal_counts'],
                win_rates=sample_data['win_rates'],
                profit_factors=sample_data['profit_factors'],
                confidence_scores=sample_data['confidence_scores'],
            )
            assert result.asset == asset

        rankings = engine.get_component_rankings()
        assert len(rankings) == 3

    def test_insufficient_data_error(self, engine):
        """Test error on small dataset."""
        with pytest.raises(ValueError):
            engine.ablate_components(
                asset='BTC',
                bce_scores=[{'bce_score': 0.5}],
                signal_counts=[10],
                win_rates=[0.5],
                profit_factors=[1.5],
                confidence_scores=[50.0],
            )

    def test_component_ablation_logic(self, engine):
        """Test ablation recomputation logic."""
        bce_scores = [
            {
                'wyckoff_structure': 0.8,
                'volume_analysis': 0.7,
                'selling_exhaustion': 0.9,
                'smart_money_accumulation': 0.75,
                'market_structure': 0.85,
                'momentum_confirmation': 0.80,
                'bce_score': 0.8125,
            }
        ]

        ablated = engine._ablate_component(bce_scores, 'wyckoff_structure')

        assert ablated[0]['wyckoff_structure'] == 0.0
        # Recomputed score should be mean of remaining 5
        remaining = [
            0.7, 0.9, 0.75, 0.85, 0.80  # volume, selling, smart, market, momentum
        ]
        expected = np.mean(remaining)
        assert ablated[0]['bce_score'] == pytest.approx(expected, abs=0.001)

    def test_critical_components_exist(self, engine, sample_data):
        """Test that some components are identified as critical."""
        result = engine.ablate_components(
            asset='BTC',
            bce_scores=sample_data['bce_scores'],
            signal_counts=sample_data['signal_counts'],
            win_rates=sample_data['win_rates'],
            profit_factors=sample_data['profit_factors'],
            confidence_scores=sample_data['confidence_scores'],
        )

        # With good data variation, should have critical components
        assert len(result.critical_components) > 0

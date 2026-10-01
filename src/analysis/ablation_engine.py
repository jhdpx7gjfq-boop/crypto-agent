"""
Ablation Testing Engine for Phase 3 Component 5.

Measures the importance of each BCE component by systematically
removing components and analyzing impact on signal quality.

Purpose:
- Validate that all 6 components contribute meaningfully
- Identify most impactful components
- Detect redundant components
- Optimize component weighting
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import numpy as np


@dataclass
class ComponentMetrics:
    """Metrics for a single component evaluation."""
    component_name: str
    bce_score_full: float  # Score with all components
    bce_score_ablated: float  # Score without this component

    # Impact metrics
    score_delta: float  # Absolute change in BCE score
    score_pct_delta: float  # Percentage change

    # Signal quality impact
    signal_count_full: int
    signal_count_ablated: int
    signal_count_delta: float

    # Win rate impact
    win_rate_full: float
    win_rate_ablated: float
    win_rate_delta: float

    # Profit factor impact
    pf_full: float
    pf_ablated: float
    pf_delta: float

    # Confidence impact
    confidence_full: float
    confidence_ablated: float
    confidence_delta: float

    # Overall importance score (0-100)
    importance_score: float


@dataclass
class AblationResult:
    """Complete ablation analysis result."""
    asset: str
    num_samples: int

    # Component-level results
    component_results: List[ComponentMetrics] = field(default_factory=list)

    # Ranking
    component_ranking: List[Tuple[str, float]] = field(default_factory=list)

    # Summary statistics
    avg_importance: float = 0.0
    std_importance: float = 0.0
    total_impact: float = 0.0

    # Verdict
    all_components_useful: bool = True
    redundant_components: List[str] = field(default_factory=list)
    critical_components: List[str] = field(default_factory=list)

    def format_report(self) -> str:
        """Format ablation results as human-readable report."""
        report = f"""
╔════════════════════════════════════════════════════════════╗
║              ABLATION TESTING REPORT                       ║
║              Asset: {self.asset}
║              Samples: {self.num_samples}
╚════════════════════════════════════════════════════════════╝

COMPONENT IMPORTANCE RANKING:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        for rank, (comp_name, importance) in enumerate(self.component_ranking, 1):
            bar_length = int(importance / 100 * 30)
            bar = "█" * bar_length + "░" * (30 - bar_length)
            report += f"{rank}. {comp_name:30s} {bar} {importance:5.1f}%\n"

        report += f"""
DETAILED METRICS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        for result in self.component_results:
            report += f"""
Component: {result.component_name}
  Score Impact:         {result.score_delta:+.4f} ({result.score_pct_delta:+.1%})
  Signal Count Impact:  {result.signal_count_delta:+.0f} ({result.signal_count_delta/result.signal_count_full*100:+.1f}%)
  Win Rate Impact:      {result.win_rate_delta:+.1%}
  Profit Factor Impact: {result.pf_delta:+.2f}
  Confidence Impact:    {result.confidence_delta:+.1f}%
  Overall Importance:   {result.importance_score:.1f}%
"""

        if self.critical_components:
            report += f"""
CRITICAL COMPONENTS (must keep):
{', '.join(self.critical_components)}
"""

        if self.redundant_components:
            report += f"""
POTENTIALLY REDUNDANT COMPONENTS (consider review):
{', '.join(self.redundant_components)}
"""
        else:
            report += "\nAll components contribute meaningfully to signal quality.\n"

        report += f"""
OVERALL STATISTICS:
  Average Importance:   {self.avg_importance:.1f}%
  Importance Std Dev:   {self.std_importance:.1f}%
  Total Combined Impact: {self.total_impact:.1f}%
  All Components Useful: {'✓ Yes' if self.all_components_useful else '✗ No'}
"""

        return report


class AblationEngine:
    """
    Tests BCE component importance through systematic ablation.

    Methodology:
    1. Compute full BCE scores on dataset
    2. For each component, recompute without that component
    3. Compare signal quality metrics
    4. Calculate importance score from deltas
    5. Rank components by impact
    """

    # Component definitions
    COMPONENTS = [
        'wyckoff_structure',
        'volume_analysis',
        'selling_exhaustion',
        'smart_money_accumulation',
        'market_structure',
        'momentum_confirmation',
    ]

    # Thresholds for importance classification
    CRITICAL_THRESHOLD = 0.10  # Importance >= 0.1% is critical (adjusted for normalized scores)
    REDUNDANT_THRESHOLD = 0.01  # Importance <= 0.01% is potentially redundant

    def __init__(self):
        """Initialize ablation engine."""
        self.results: Dict[str, AblationResult] = {}

    def ablate_components(
        self,
        asset: str,
        bce_scores: List[Dict[str, float]],
        signal_counts: List[int],
        win_rates: List[float],
        profit_factors: List[float],
        confidence_scores: List[float],
    ) -> AblationResult:
        """
        Run ablation analysis on BCE components.

        Args:
            asset: Asset symbol (e.g., 'BTCUSDT')
            bce_scores: List of dicts with component scores (0-1 each)
            signal_counts: List of signal counts per sample
            win_rates: List of win rates per sample
            profit_factors: List of PF values per sample
            confidence_scores: List of confidence values (0-100) per sample

        Returns:
            AblationResult with component importance analysis
        """
        if not bce_scores or len(bce_scores) < 10:
            raise ValueError("Need at least 10 samples for ablation testing")

        result = AblationResult(
            asset=asset,
            num_samples=len(bce_scores),
        )

        # Compute metrics with full model
        full_metrics = self._compute_metrics(
            bce_scores,
            signal_counts,
            win_rates,
            profit_factors,
            confidence_scores,
        )

        # Ablate each component
        for component in self.COMPONENTS:
            # Recompute without this component
            ablated_scores = self._ablate_component(bce_scores, component)

            ablated_metrics = self._compute_metrics(
                ablated_scores,
                signal_counts,
                win_rates,
                profit_factors,
                confidence_scores,
            )

            # Calculate impact
            comp_result = self._calculate_component_impact(
                component,
                full_metrics,
                ablated_metrics,
            )

            result.component_results.append(comp_result)

        # Rank components
        result = self._rank_and_summarize(result)

        self.results[asset] = result
        return result

    def _ablate_component(
        self,
        bce_scores: List[Dict[str, float]],
        ablated_component: str,
    ) -> List[Dict[str, float]]:
        """
        Recompute BCE scores without specified component.

        Sets component score to 0 and recomputes average.
        """
        ablated = []

        for score_dict in bce_scores:
            new_dict = score_dict.copy()
            new_dict[ablated_component] = 0.0

            # Recompute BCE score (average of remaining components)
            components = [new_dict.get(c, 0.0) for c in self.COMPONENTS]
            non_zero = [c for c in components if c > 0]

            if non_zero:
                new_dict['bce_score'] = np.mean(non_zero)
            else:
                new_dict['bce_score'] = 0.0

            ablated.append(new_dict)

        return ablated

    def _compute_metrics(
        self,
        bce_scores: List[Dict[str, float]],
        signal_counts: List[int],
        win_rates: List[float],
        profit_factors: List[float],
        confidence_scores: List[float],
    ) -> dict:
        """Compute aggregated metrics from samples."""
        return {
            'avg_bce_score': np.mean([s.get('bce_score', 0) for s in bce_scores]),
            'avg_signal_count': np.mean(signal_counts),
            'avg_win_rate': np.mean(win_rates),
            'avg_pf': np.mean(profit_factors),
            'avg_confidence': np.mean(confidence_scores),
            'bce_std': np.std([s.get('bce_score', 0) for s in bce_scores]),
        }

    def _calculate_component_impact(
        self,
        component: str,
        full_metrics: dict,
        ablated_metrics: dict,
    ) -> ComponentMetrics:
        """Calculate impact metrics for one component."""

        # Score impact
        score_delta = full_metrics['avg_bce_score'] - ablated_metrics['avg_bce_score']
        score_pct = (
            score_delta / full_metrics['avg_bce_score']
            if full_metrics['avg_bce_score'] > 0 else 0
        )

        # Signal count impact
        signal_delta = full_metrics['avg_signal_count'] - ablated_metrics['avg_signal_count']
        signal_pct = (
            signal_delta / full_metrics['avg_signal_count']
            if full_metrics['avg_signal_count'] > 0 else 0
        )

        # Win rate impact
        wr_delta = full_metrics['avg_win_rate'] - ablated_metrics['avg_win_rate']

        # PF impact
        pf_delta = full_metrics['avg_pf'] - ablated_metrics['avg_pf']

        # Confidence impact
        conf_delta = full_metrics['avg_confidence'] - ablated_metrics['avg_confidence']

        # Composite importance score (0-100)
        importance = self._calculate_importance_score(
            score_delta,
            score_pct,
            signal_pct,
            wr_delta,
            pf_delta,
            conf_delta,
        )

        return ComponentMetrics(
            component_name=component,
            bce_score_full=full_metrics['avg_bce_score'],
            bce_score_ablated=ablated_metrics['avg_bce_score'],
            score_delta=score_delta,
            score_pct_delta=score_pct,
            signal_count_full=int(full_metrics['avg_signal_count']),
            signal_count_ablated=int(ablated_metrics['avg_signal_count']),
            signal_count_delta=signal_pct,
            win_rate_full=full_metrics['avg_win_rate'],
            win_rate_ablated=ablated_metrics['avg_win_rate'],
            win_rate_delta=wr_delta,
            pf_full=full_metrics['avg_pf'],
            pf_ablated=ablated_metrics['avg_pf'],
            pf_delta=pf_delta,
            confidence_full=full_metrics['avg_confidence'],
            confidence_ablated=ablated_metrics['avg_confidence'],
            confidence_delta=conf_delta,
            importance_score=importance,
        )

    def _calculate_importance_score(
        self,
        score_delta: float,
        score_pct: float,
        signal_pct: float,
        wr_delta: float,
        pf_delta: float,
        conf_delta: float,
    ) -> float:
        """
        Calculate composite importance score (0-100).

        Weights different impact dimensions:
        - Score change (25%): Direct impact on BCE calculation
        - Signal count (20%): Ability to generate signals
        - Win rate (20%): Quality of entries
        - Profit factor (20%): Overall profitability
        - Confidence (15%): Quality ranking accuracy
        """
        # Normalize deltas to 0-100 scale
        score_importance = min(100, abs(score_pct) * 100 * 0.8)
        signal_importance = min(100, abs(signal_pct) * 100 * 0.8)
        wr_importance = min(100, abs(wr_delta) * 100 * 0.8)
        pf_importance = min(100, abs(pf_delta) * 10)  # PF typically 1-2 range
        conf_importance = min(100, abs(conf_delta))  # Already 0-100

        # Composite score
        importance = (
            score_importance * 0.25 +
            signal_importance * 0.20 +
            wr_importance * 0.20 +
            pf_importance * 0.20 +
            conf_importance * 0.15
        )

        return min(100, importance)

    def _rank_and_summarize(
        self,
        result: AblationResult,
    ) -> AblationResult:
        """Rank components and create summary."""
        # Sort by importance
        sorted_comps = sorted(
            result.component_results,
            key=lambda x: x.importance_score,
            reverse=True
        )

        result.component_ranking = [
            (comp.component_name, comp.importance_score)
            for comp in sorted_comps
        ]

        # Summary statistics
        importance_scores = [c.importance_score for c in result.component_results]
        result.avg_importance = np.mean(importance_scores)
        result.std_importance = np.std(importance_scores)
        result.total_impact = sum(importance_scores)

        # Classify components
        critical = [
            c.component_name
            for c in sorted_comps
            if c.importance_score >= self.CRITICAL_THRESHOLD
        ]
        redundant = [
            c.component_name
            for c in sorted_comps
            if c.importance_score <= self.REDUNDANT_THRESHOLD
        ]

        result.critical_components = critical
        result.redundant_components = redundant
        result.all_components_useful = len(redundant) == 0

        return result

    def get_ablation_report(self, asset: str) -> Optional[str]:
        """Get formatted ablation report for asset."""
        if asset not in self.results:
            return None

        return self.results[asset].format_report()

    def get_component_rankings(self) -> Dict[str, List[Tuple[str, float]]]:
        """Get component rankings for all analyzed assets."""
        return {
            asset: result.component_ranking
            for asset, result in self.results.items()
        }

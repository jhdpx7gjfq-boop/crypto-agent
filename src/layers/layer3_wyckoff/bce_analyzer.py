"""BCE Analyzer — comprehensive bottom confirmation analysis."""

import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

from src.core.models import OHLCV, WyckoffSignal
from src.layers.layer3_wyckoff.bce_engine import BottomConfirmationEngine
from src.utils.feature_store import FeatureStore


logger = logging.getLogger(__name__)


@dataclass
class BCEAnalysisReport:
    """Comprehensive BCE analysis report."""

    asset: str
    bce_score: float
    is_valid: bool
    components: Dict[str, float]
    double_bottom_detected: bool
    support_level: float
    resistance_level: float
    volume_confirmation: bool
    trend_confirmation: str  # "bullish", "bearish", "sideways"
    confidence_level: str  # "high", "medium", "low"
    risk_rating: str  # "low", "medium", "high"
    entry_signal: bool
    reasoning: List[str]


class BCEAnalyzer:
    """
    Comprehensive BCE analysis with feature store integration.

    Combines BCE scoring with technical features for robust analysis.
    """

    def __init__(self):
        self.bce_engine = BottomConfirmationEngine()
        self.feature_store = FeatureStore()

    def analyze(self, asset: str, ohlcv_data: List[OHLCV]) -> BCEAnalysisReport:
        """
        Comprehensive bottom confirmation analysis.

        Returns: Detailed analysis report with all signals.
        """

        reasoning = []

        # Core BCE analysis
        bce_signal = self.bce_engine.analyze(asset, ohlcv_data)
        reasoning.append(f"BCE score: {bce_signal.bce_score:.2f}/6")

        if not bce_signal.valid:
            reasoning.append(f"⚠ Score below 5.0 threshold")

        # Feature store analysis
        features = self.feature_store.compute_features(asset, ohlcv_data)
        if not features:
            reasoning.append("⚠ Insufficient data for features")
            return self._create_invalid_report(asset, reasoning)

        # Support/resistance levels
        support, resistance = self._detect_support_resistance(ohlcv_data)
        reasoning.append(f"Support: {support:.2f}, Resistance: {resistance:.2f}")

        # Double bottom detection
        double_bottom = self._detect_double_bottom(ohlcv_data)
        if double_bottom:
            reasoning.append("✓ Double bottom pattern detected")

        # Volume confirmation
        vol_confirm = self._check_volume_confirmation(ohlcv_data)
        reasoning.append(f"Volume confirmation: {vol_confirm}")

        # Trend analysis using features
        trend = self._analyze_trend(features[-20:])
        reasoning.append(f"Trend: {trend}")

        # Confidence level
        confidence = self._compute_confidence(bce_signal, vol_confirm, double_bottom, trend)
        confidence_level = "high" if confidence >= 0.75 else "medium" if confidence >= 0.5 else "low"

        # Risk rating
        risk = self._compute_risk(bce_signal, support, ohlcv_data[-1].close)
        risk_level = "low" if risk < 0.3 else "medium" if risk < 0.6 else "high"

        # Entry decision
        entry_signal = bce_signal.valid and confidence >= 0.5

        if entry_signal:
            reasoning.append("✓ ENTRY SIGNAL VALID")
        else:
            reasoning.append("✗ Entry signal invalid")

        report = BCEAnalysisReport(
            asset=asset,
            bce_score=bce_signal.bce_score,
            is_valid=bce_signal.valid,
            components={
                "structure": bce_signal.wyckoff_structure,
                "volume": bce_signal.volume_analysis,
                "exhaustion": bce_signal.selling_exhaustion,
                "smart_money": bce_signal.smart_money_accumulation,
                "market_struct": bce_signal.market_structure,
                "momentum": bce_signal.momentum_confirmation,
            },
            double_bottom_detected=double_bottom,
            support_level=support,
            resistance_level=resistance,
            volume_confirmation=vol_confirm,
            trend_confirmation=trend,
            confidence_level=confidence_level,
            risk_rating=risk_level,
            entry_signal=entry_signal,
            reasoning=reasoning,
        )

        return report

    @staticmethod
    def _detect_support_resistance(ohlcv: List[OHLCV]) -> Tuple[float, float]:
        """Detect support (low) and resistance (high) levels."""
        if not ohlcv or len(ohlcv) < 10:
            return 0.0, 0.0

        recent = ohlcv[-20:]
        lows = [c.low for c in recent]
        highs = [c.high for c in recent]

        support = min(lows) if lows else 0.0
        resistance = max(highs) if highs else 0.0

        return support, resistance

    @staticmethod
    def _detect_double_bottom(ohlcv: List[OHLCV]) -> bool:
        """Detect double bottom pattern."""
        if len(ohlcv) < 10:
            return False

        recent = ohlcv[-10:]
        lows = [c.low for c in recent]

        # Count how many lows are within 2% of the minimum
        min_low = min(lows)
        near_min = sum(1 for l in lows if abs(l - min_low) / min_low < 0.02)

        return near_min >= 2  # At least 2 touches of low

    @staticmethod
    def _check_volume_confirmation(ohlcv: List[OHLCV]) -> bool:
        """Check volume confirmation on bounces."""
        if len(ohlcv) < 5:
            return False

        recent = ohlcv[-5:]
        volumes = [c.volume for c in recent]
        avg_vol = sum(volumes) / len(volumes)

        # At least one candle with volume > 50% above average
        high_vol_count = sum(1 for v in volumes if v > avg_vol * 1.5)

        return high_vol_count >= 1

    @staticmethod
    def _analyze_trend(features: List) -> str:
        """Analyze trend from features."""
        if not features:
            return "sideways"

        closes = [f.close for f in features if f is not None]
        if len(closes) < 2:
            return "sideways"

        if closes[-1] > closes[0]:
            return "bullish"
        elif closes[-1] < closes[0]:
            return "bearish"
        else:
            return "sideways"

    @staticmethod
    def _compute_confidence(bce_signal, vol_confirm: bool, double_bottom: bool, trend: str) -> float:
        """Compute confidence score (0-1)."""
        confidence = 0.0

        # BCE score (max 0.4)
        confidence += (bce_signal.bce_score / 6) * 0.4

        # Volume confirmation (0.2)
        if vol_confirm:
            confidence += 0.2

        # Double bottom (0.2)
        if double_bottom:
            confidence += 0.2

        # Trend (0.2)
        if trend == "bullish":
            confidence += 0.2

        return min(1.0, confidence)

    @staticmethod
    def _compute_risk(bce_signal, support: float, current_price: float) -> float:
        """Compute risk score (0-1, higher = more risk)."""
        risk = 0.5

        # Risk increases if BCE score is low
        risk -= (bce_signal.bce_score / 6) * 0.3

        # Risk increases if far from support
        if support > 0:
            distance_pct = ((current_price - support) / support) * 100
            if distance_pct > 10:
                risk += 0.2

        return max(0.0, min(1.0, risk))

    @staticmethod
    def _create_invalid_report(asset: str, reasoning: List[str]) -> BCEAnalysisReport:
        """Create invalid report."""
        return BCEAnalysisReport(
            asset=asset,
            bce_score=0.0,
            is_valid=False,
            components={},
            double_bottom_detected=False,
            support_level=0.0,
            resistance_level=0.0,
            volume_confirmation=False,
            trend_confirmation="unknown",
            confidence_level="low",
            risk_rating="high",
            entry_signal=False,
            reasoning=reasoning,
        )

    def generate_report_text(self, report: BCEAnalysisReport) -> str:
        """Generate human-readable report."""
        lines = [
            f"\n{'='*60}",
            f"BCE ANALYSIS REPORT — {report.asset.upper()}",
            f"{'='*60}",
            f"",
            f"BCE Score: {report.bce_score:.2f}/6 {'✓ VALID' if report.is_valid else '✗ INVALID'}",
            f"Confidence: {report.confidence_level.upper()}",
            f"Risk Rating: {report.risk_rating.upper()}",
            f"Entry Signal: {'YES ✓' if report.entry_signal else 'NO ✗'}",
            f"",
            f"Components:",
            f"  Structure:    {report.components.get('structure', 0):.2f}/1",
            f"  Volume:       {report.components.get('volume', 0):.2f}/1",
            f"  Exhaustion:   {report.components.get('exhaustion', 0):.2f}/1",
            f"  Smart Money:  {report.components.get('smart_money', 0):.2f}/1",
            f"  Mkt Struct:   {report.components.get('market_struct', 0):.2f}/1",
            f"  Momentum:     {report.components.get('momentum', 0):.2f}/1",
            f"",
            f"Technical:",
            f"  Support: {report.support_level:.2f}",
            f"  Resistance: {report.resistance_level:.2f}",
            f"  Double Bottom: {'Yes' if report.double_bottom_detected else 'No'}",
            f"  Volume Confirmation: {'Yes' if report.volume_confirmation else 'No'}",
            f"  Trend: {report.trend_confirmation}",
            f"",
            f"Analysis:",
        ]

        for reason in report.reasoning:
            lines.append(f"  • {reason}")

        lines.extend([
            f"",
            f"{'='*60}",
            f"",
        ])

        return "\n".join(lines)

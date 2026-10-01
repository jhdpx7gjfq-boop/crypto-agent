"""Regime Detector — Identifies market conditions for strategy context.

Detects bullish, bearish, ranging, volatile regimes.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional


class RegimeType(str, Enum):
    """Market regime classifications."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    RANGING = "ranging"
    VOLATILE = "volatile"
    TRANSITION = "transition"


@dataclass
class TrendMetrics:
    """Trend analysis metrics."""

    momentum: float  # -100 to +100
    momentum_direction: str  # "up", "down", "flat"
    trend_strength: float  # 0-100
    higher_highs: bool
    higher_lows: bool
    score: float


@dataclass
class VolatilityMetrics:
    """Volatility measurements."""

    current_volatility: float  # % daily move
    volatility_7d_avg: float
    volatility_ratio: float  # current / avg
    volatility_regime: str  # "low", "normal", "high", "extreme"
    score: float


@dataclass
class VolumeMetrics:
    """Volume analysis."""

    current_volume: float
    volume_7d_avg: float
    volume_ratio: float
    volume_trend: str  # "increasing", "stable", "decreasing"
    score: float


@dataclass
class MarketRegime:
    """Complete market regime classification."""

    asset: str
    timestamp: datetime
    regime_type: RegimeType
    confidence: float  # 0-1
    trend: TrendMetrics
    volatility: VolatilityMetrics
    volume: VolumeMetrics
    regime_score: float  # 0-100
    days_in_regime: int
    expected_duration_days: Optional[int]


class RegimeDetector:
    """Detects market regimes for strategy context."""

    def __init__(self):
        """Initialize detector."""
        self.regime_history: Dict[str, list] = {}
        self.current_regimes: Dict[str, MarketRegime] = {}

    def detect_regime(
        self,
        asset: str,
        price_data: Dict,
        volatility_data: Dict,
        volume_data: Dict,
    ) -> MarketRegime:
        """
        Detect current market regime.

        Args:
            asset: Asset symbol
            price_data: {current_price, momentum, higher_highs, higher_lows}
            volatility_data: {current_vol, vol_7d_avg}
            volume_data: {current_volume, volume_7d_avg}

        Returns:
            MarketRegime with classification and metrics
        """
        trend = self._analyze_trend(price_data)
        volatility = self._analyze_volatility(volatility_data)
        volume = self._analyze_volume(volume_data)

        regime_type = self._classify_regime(trend, volatility, volume)
        confidence = self._calculate_regime_confidence(trend, volatility, volume)
        regime_score = self._calculate_regime_score(trend, volatility, volume)
        days_in_regime = self._estimate_regime_duration(self.current_regimes.get(asset))
        expected_duration = self._estimate_expected_duration(regime_type, volatility)

        regime = MarketRegime(
            asset=asset,
            timestamp=datetime.utcnow(),
            regime_type=regime_type,
            confidence=confidence,
            trend=trend,
            volatility=volatility,
            volume=volume,
            regime_score=regime_score,
            days_in_regime=days_in_regime,
            expected_duration_days=expected_duration,
        )

        # Track history
        if asset not in self.regime_history:
            self.regime_history[asset] = []
        self.regime_history[asset].append(regime)
        self.current_regimes[asset] = regime

        return regime

    def _analyze_trend(self, price_data: Dict) -> TrendMetrics:
        """Analyze trend direction and strength."""
        momentum = price_data.get("momentum", 0)  # -100 to +100
        higher_highs = price_data.get("higher_highs", False)
        higher_lows = price_data.get("higher_lows", False)

        if momentum > 30 and higher_highs and higher_lows:
            direction = "up"
            strength = min(100, 50 + abs(momentum) * 0.5)
        elif momentum < -30 and not higher_highs and not higher_lows:
            direction = "down"
            strength = min(100, 50 + abs(momentum) * 0.5)
        else:
            direction = "flat"
            strength = max(0, 50 - abs(momentum) * 0.3)

        score = strength if direction in ["up", "down"] else 30

        return TrendMetrics(
            momentum=momentum,
            momentum_direction=direction,
            trend_strength=strength,
            higher_highs=higher_highs,
            higher_lows=higher_lows,
            score=score,
        )

    def _analyze_volatility(self, volatility_data: Dict) -> VolatilityMetrics:
        """Analyze volatility regime."""
        current_vol = volatility_data.get("current_volatility", 2.0)  # % daily move
        vol_7d_avg = volatility_data.get("volatility_7d_avg", 2.0)

        ratio = current_vol / vol_7d_avg if vol_7d_avg > 0 else 1.0

        if current_vol > 5.0:
            regime = "extreme"
            score = min(100, 30 + (current_vol - 5) * 10)
        elif current_vol > 3.0:
            regime = "high"
            score = 60 + (current_vol - 3) * 10
        elif current_vol > 1.5:
            regime = "normal"
            score = 50 + (current_vol - 1.5) * 10
        else:
            regime = "low"
            score = 30 + current_vol * 10

        return VolatilityMetrics(
            current_volatility=current_vol,
            volatility_7d_avg=vol_7d_avg,
            volatility_ratio=ratio,
            volatility_regime=regime,
            score=score,
        )

    def _analyze_volume(self, volume_data: Dict) -> VolumeMetrics:
        """Analyze volume metrics."""
        current_vol = volume_data.get("current_volume", 0)
        vol_7d_avg = volume_data.get("volume_7d_avg", current_vol or 1)

        ratio = current_vol / vol_7d_avg if vol_7d_avg > 0 else 1.0

        if ratio > 1.5:
            trend = "increasing"
            score = min(100, 70 + (ratio - 1.5) * 10)
        elif ratio > 1.0:
            trend = "increasing"
            score = 60 + (ratio - 1.0) * 20
        elif ratio > 0.8:
            trend = "stable"
            score = 50
        else:
            trend = "decreasing"
            score = max(0, 40 + ratio * 20)

        return VolumeMetrics(
            current_volume=current_vol,
            volume_7d_avg=vol_7d_avg,
            volume_ratio=ratio,
            volume_trend=trend,
            score=score,
        )

    def _classify_regime(
        self, trend: TrendMetrics, volatility: VolatilityMetrics, volume: VolumeMetrics
    ) -> RegimeType:
        """Classify market regime."""
        if volatility.volatility_regime == "extreme":
            return RegimeType.VOLATILE

        if trend.momentum_direction == "up" and volume.volume_trend == "increasing":
            return RegimeType.BULLISH
        elif trend.momentum_direction == "down" and volume.volume_trend in ["stable", "increasing"]:
            return RegimeType.BEARISH
        elif trend.momentum_direction == "flat" and volatility.volatility_regime == "low":
            return RegimeType.RANGING
        else:
            return RegimeType.TRANSITION

    def _calculate_regime_confidence(
        self, trend: TrendMetrics, volatility: VolatilityMetrics, volume: VolumeMetrics
    ) -> float:
        """Calculate confidence in regime classification."""
        signal_strength = (trend.score + volatility.score + volume.score) / 300
        return min(1.0, signal_strength)

    def _calculate_regime_score(
        self, trend: TrendMetrics, volatility: VolatilityMetrics, volume: VolumeMetrics
    ) -> float:
        """Calculate overall regime score."""
        return (trend.score * 0.4 + volatility.score * 0.3 + volume.score * 0.3)

    def _estimate_regime_duration(self, previous_regime: Optional[MarketRegime]) -> int:
        """Estimate how many days in current regime."""
        if not previous_regime:
            return 0
        return previous_regime.days_in_regime + 1

    def _estimate_expected_duration(self, regime: RegimeType, volatility: VolatilityMetrics) -> Optional[int]:
        """Estimate expected regime duration."""
        if regime == RegimeType.BULLISH:
            return 30
        elif regime == RegimeType.BEARISH:
            return 20
        elif regime == RegimeType.RANGING:
            return 15
        elif regime == RegimeType.VOLATILE:
            return 7
        else:
            return 5

    def audit_regimes(self, asset: str) -> Dict:
        """Audit regime history."""
        if asset not in self.regime_history:
            return {"asset": asset, "regimes_detected": 0}

        history = self.regime_history[asset]
        regime_counts = {}
        for regime in history:
            t = regime.regime_type.value
            regime_counts[t] = regime_counts.get(t, 0) + 1

        return {
            "asset": asset,
            "regimes_detected": len(history),
            "regime_breakdown": regime_counts,
            "current_regime": (
                history[-1].regime_type.value if history else "unknown"
            ),
        }

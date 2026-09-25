"""Bottom Confirmation Engine (BCE) — Wyckoff-based accumulation detection."""

from dataclasses import dataclass
from typing import List, Tuple, Dict
import numpy as np


@dataclass
class WyckoffStructure:
    """Wyckoff accumulation/distribution structure."""

    phase: str  # "accumulation" | "distribution" | "unknown"
    strength: float  # 0-1
    confidence: float  # 0-1


class BCEEngine:
    """Bottom Confirmation Engine: Validates entry points using Wyckoff analysis."""

    def analyze_wyckoff(
        self, closes: List[float], highs: List[float], lows: List[float], period: int = 20
    ) -> WyckoffStructure:
        """
        Detect Wyckoff accumulation/distribution structure.

        Accumulation phases show:
        - Lower lows with higher volume on down moves
        - Higher lows with decreasing volume
        - Test of lows without new lows
        - Markup phase begins

        Args:
            closes: Close prices
            highs: High prices
            lows: Low prices
            period: Lookback period

        Returns:
            WyckoffStructure with phase, strength, confidence
        """
        if len(closes) < period:
            return WyckoffStructure(phase="unknown", strength=0.0, confidence=0.0)

        closes_arr = np.array(closes)
        lows_arr = np.array(lows)
        highs_arr = np.array(highs)

        recent_lows = lows_arr[-period:]
        recent_highs = highs_arr[-period:]

        recent_closes = closes_arr[-period:]
        price_range = np.max(recent_highs) - np.min(recent_lows)

        if price_range == 0:
            return WyckoffStructure(phase="unknown", strength=0.0, confidence=0.0)

        low_point_idx = np.argmin(recent_lows)
        high_point_idx = np.argmax(recent_highs)

        accumulated_volume = self._detect_accumulation_pressure(recent_closes, recent_lows)

        if low_point_idx < high_point_idx:
            phase = "accumulation"
            strength = min(1.0, accumulated_volume)
        elif high_point_idx < low_point_idx:
            phase = "distribution"
            strength = min(1.0, accumulated_volume)
        else:
            phase = "unknown"
            strength = 0.0

        confidence = 0.5 + (0.5 * strength)

        return WyckoffStructure(phase=phase, strength=strength, confidence=confidence)

    def analyze_volume_profile(
        self, closes: List[float], volumes: List[float], period: int = 20
    ) -> Dict[str, float]:
        """
        Analyze volume profile for accumulation signals.

        Returns:
            Dict with volume_strength, volume_consistency, accumulation_score
        """
        if len(closes) < period or len(volumes) < period:
            return {"volume_strength": 0.0, "volume_consistency": 0.0, "accumulation_score": 0.0}

        closes_arr = np.array(closes)
        volumes_arr = np.array(volumes)

        recent_closes = closes_arr[-period:]
        recent_volumes = volumes_arr[-period:]

        price_changes = np.diff(recent_closes)
        down_moves = np.sum(price_changes < 0)
        down_volume = np.sum(recent_volumes[:-1][price_changes < 0])
        up_volume = np.sum(recent_volumes[:-1][price_changes >= 0])

        volume_strength = down_volume / (up_volume + 1e-10) if up_volume > 0 else 0.0
        volume_strength = min(1.0, volume_strength)

        avg_volume = np.mean(recent_volumes)
        volume_std = np.std(recent_volumes)
        volume_consistency = 1.0 - (volume_std / (avg_volume + 1e-10))
        volume_consistency = max(0.0, min(1.0, volume_consistency))

        accumulation_score = (volume_strength + volume_consistency) / 2.0

        return {
            "volume_strength": float(volume_strength),
            "volume_consistency": float(volume_consistency),
            "accumulation_score": float(accumulation_score),
        }

    def detect_selling_exhaustion(
        self, closes: List[float], volumes: List[float], period: int = 20
    ) -> float:
        """
        Detect selling exhaustion: decreasing volume on down moves.

        Returns:
            Exhaustion score 0-1
        """
        if len(closes) < period or len(volumes) < period:
            return 0.0

        closes_arr = np.array(closes)
        volumes_arr = np.array(volumes)

        recent_closes = closes_arr[-period:]
        recent_volumes = volumes_arr[-period:]

        price_changes = np.diff(recent_closes)

        down_indices = np.where(price_changes < 0)[0]
        if len(down_indices) < 2:
            return 0.0

        down_move_volumes = recent_volumes[down_indices]
        volume_trend = np.polyfit(range(len(down_move_volumes)), down_move_volumes, 1)[0]

        exhaustion = -volume_trend / (np.max(down_move_volumes) + 1e-10)
        exhaustion = max(0.0, min(1.0, exhaustion))

        return float(exhaustion)

    def detect_smart_money_accumulation(
        self, closes: List[float], highs: List[float], lows: List[float], period: int = 20
    ) -> float:
        """
        Detect smart money accumulation: price tests without new lows.

        Returns:
            Accumulation score 0-1
        """
        if len(closes) < period:
            return 0.0

        lows_arr = np.array(lows)
        recent_lows = lows_arr[-period:]

        min_low = np.min(recent_lows)
        tests_of_low = np.sum(recent_lows > min_low * 0.99) - 1
        tests_without_break = tests_of_low / period

        smart_money_score = min(1.0, tests_without_break)

        return float(smart_money_score)

    def analyze_market_structure(
        self, closes: List[float], highs: List[float], lows: List[float], period: int = 20
    ) -> Dict[str, float]:
        """
        Analyze market structure: higher lows, narrowing range.

        Returns:
            Dict with structure_score, trend_confirmation, volatility_contraction
        """
        if len(closes) < period:
            return {"structure_score": 0.0, "trend_confirmation": 0.0, "volatility_contraction": 0.0}

        lows_arr = np.array(lows)
        closes_arr = np.array(closes)

        recent_lows = lows_arr[-period:]
        recent_closes = closes_arr[-period:]

        low_trend = np.polyfit(range(len(recent_lows)), recent_lows, 1)[0]
        close_trend = np.polyfit(range(len(recent_closes)), recent_closes, 1)[0]

        higher_lows = 1.0 if low_trend > 0 else 0.0
        upside_bias = 1.0 if close_trend > 0 else 0.0

        trend_confirmation = (higher_lows + upside_bias) / 2.0

        price_range = np.max(recent_lows) - np.min(recent_lows)
        volatility_contraction = 1.0 - (price_range / (np.mean(recent_closes) + 1e-10))
        volatility_contraction = max(0.0, min(1.0, volatility_contraction))

        structure_score = (trend_confirmation + volatility_contraction) / 2.0

        return {
            "structure_score": float(structure_score),
            "trend_confirmation": float(trend_confirmation),
            "volatility_contraction": float(volatility_contraction),
        }

    def calculate_bce_score(
        self,
        wyckoff_score: float,
        volume_score: float,
        exhaustion_score: float,
        smart_money_score: float,
        structure_score: float,
    ) -> int:
        """
        Calculate final BCE score (0-6).

        Weights:
        - Wyckoff structure: 30%
        - Volume profile: 20%
        - Selling exhaustion: 20%
        - Smart money: 20%
        - Market structure: 10%

        Args:
            wyckoff_score: 0-1
            volume_score: 0-1
            exhaustion_score: 0-1
            smart_money_score: 0-1
            structure_score: 0-1

        Returns:
            BCE score 0-6
        """
        weighted_score = (
            (wyckoff_score * 0.30)
            + (volume_score * 0.20)
            + (exhaustion_score * 0.20)
            + (smart_money_score * 0.20)
            + (structure_score * 0.10)
        )

        bce_score = int(weighted_score * 6)
        bce_score = max(0, min(6, bce_score))

        return bce_score

    def validate_signal(self, bce_score: int) -> bool:
        """
        Validate signal: BCE_SCORE >= 5/6 required for entry.

        Args:
            bce_score: BCE score 0-6

        Returns:
            True if valid (>= 5), False otherwise
        """
        return bce_score >= 5

    def compute_bce(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[float],
        period: int = 20,
    ) -> Tuple[int, Dict[str, float]]:
        """
        Compute complete BCE analysis.

        Args:
            closes: Close prices
            highs: High prices
            lows: Low prices
            volumes: Trading volumes
            period: Analysis period

        Returns:
            (bce_score, metrics_dict)
        """
        wyckoff = self.analyze_wyckoff(closes, highs, lows, period)
        wyckoff_score = wyckoff.strength

        volume_profile = self.analyze_volume_profile(closes, volumes, period)
        volume_score = volume_profile["accumulation_score"]

        exhaustion_score = self.detect_selling_exhaustion(closes, volumes, period)

        smart_money_score = self.detect_smart_money_accumulation(closes, highs, lows, period)

        structure = self.analyze_market_structure(closes, highs, lows, period)
        structure_score = structure["structure_score"]

        bce_score = self.calculate_bce_score(
            wyckoff_score, volume_score, exhaustion_score, smart_money_score, structure_score
        )

        metrics = {
            "wyckoff_phase": wyckoff.phase,
            "wyckoff_strength": wyckoff_score,
            "wyckoff_confidence": wyckoff.confidence,
            "volume_strength": volume_profile["volume_strength"],
            "volume_consistency": volume_profile["volume_consistency"],
            "selling_exhaustion": exhaustion_score,
            "smart_money_accumulation": smart_money_score,
            "market_structure": structure_score,
            "trend_confirmation": structure["trend_confirmation"],
            "volatility_contraction": structure["volatility_contraction"],
            "bce_score": bce_score,
            "valid_signal": self.validate_signal(bce_score),
        }

        return bce_score, metrics

    def _detect_accumulation_pressure(self, closes: np.ndarray, lows: np.ndarray) -> float:
        """Helper: Detect accumulation pressure from price/volume relationship."""
        if len(closes) < 2 or len(lows) < 2:
            return 0.0

        price_changes = np.diff(closes)
        down_moves = np.sum(price_changes < 0)
        down_pressure = down_moves / len(price_changes)

        return float(down_pressure)

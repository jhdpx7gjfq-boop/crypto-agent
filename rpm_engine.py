"""
RPM (Rotation Prediction Model) - Capital Flow & Relative Strength Detection

Implements capital_flow and relative_strength sub-metrics for B-004 validation.
Locked specification: 25% + 25% weight in final RPM score.
"""

import logging
from typing import List, Dict, Any, Tuple
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CapitalFlowMetric:
    """Capital flow signal: net directional capital movement."""
    value: float
    confidence: float
    timestamp: int
    lookback_days: int = 7


@dataclass
class RelativeStrengthMetric:
    """Relative strength signal: price momentum vs market baseline."""
    value: float
    symbol_momentum: float
    market_baseline: float
    timestamp: int
    lookback_days: int = 14


class RPMEngine:
    """RPM calculation engine (Phase 6 implementation)."""

    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ["BTC", "ETH", "SOL", "AVAX"]
        self.lookback_capital_flow = 7
        self.lookback_momentum = 14
        self.lookback_sma = 14

    def calculate_capital_flow(
        self,
        ohlcv: List[Dict[str, Any]],
        symbol: str,
        verbose: bool = False,
    ) -> CapitalFlowMetric:
        """
        Calculate capital flow metric: net directional capital movement.

        Formula:
          capital_flow_i = (volume_i * (close_i - SMA_close[14])) / avg_volume[30]
          Net capital_flow = sum(capital_flow[t-7:t]) / 7
          Normalized = tanh(net_capital_flow / std_dev)

        Args:
            ohlcv: List of OHLCV candles (ascending time order)
            symbol: Crypto symbol (for logging)
            verbose: Enable debug logging

        Returns:
            CapitalFlowMetric with normalized value [-1, 1]
        """
        if len(ohlcv) < max(self.lookback_sma, self.lookback_capital_flow + 30):
            logger.warning(f"{symbol}: Insufficient data for capital_flow ({len(ohlcv)} candles)")
            return CapitalFlowMetric(value=0.0, confidence=0.0, timestamp=ohlcv[-1]["timestamp"])

        closes = np.array([c["close"] for c in ohlcv])
        volumes = np.array([c["volume"] for c in ohlcv])

        # SMA[14] of closes
        sma_close = np.convolve(closes, np.ones(self.lookback_sma) / self.lookback_sma, mode="same")

        # Capital flow per candle
        capital_flows = (volumes * (closes - sma_close)) / (np.mean(volumes[-30:]) + 1e-8)

        # Net capital flow: rolling sum over lookback period
        net_capital_flow = np.sum(capital_flows[-self.lookback_capital_flow :])

        # Normalize using tanh
        std_dev = np.std(capital_flows[-30:]) + 1e-8
        normalized = float(np.tanh(net_capital_flow / (std_dev + 1e-8)))

        if verbose:
            logger.info(
                f"{symbol} capital_flow: net={net_capital_flow:.4f}, "
                f"std={std_dev:.4f}, normalized={normalized:.4f}"
            )

        return CapitalFlowMetric(
            value=normalized,
            confidence=min(1.0, abs(normalized)),  # Higher absolute value = higher confidence
            timestamp=ohlcv[-1]["timestamp"],
            lookback_days=self.lookback_capital_flow,
        )

    def calculate_relative_strength(
        self,
        ohlcv_dict: Dict[str, List[Dict[str, Any]]],
        target_symbol: str,
        verbose: bool = False,
    ) -> RelativeStrengthMetric:
        """
        Calculate relative strength: price momentum vs market baseline.

        Formula:
          symbol_momentum = (close_t - SMA[14]) / close_t
          market_baseline = mean(momentum across all symbols)
          relative_strength = symbol_momentum - market_baseline
          Normalized = tanh(relative_strength * 2)

        Args:
            ohlcv_dict: Dict of {symbol: ohlcv_list}
            target_symbol: Symbol to calculate for
            verbose: Enable debug logging

        Returns:
            RelativeStrengthMetric with normalized value [-1, 1]
        """
        if target_symbol not in ohlcv_dict:
            logger.warning(f"{target_symbol}: Not in ohlcv_dict")
            return RelativeStrengthMetric(
                value=0.0,
                symbol_momentum=0.0,
                market_baseline=0.0,
                timestamp=0,
            )

        # Calculate momentum for target symbol
        ohlcv = ohlcv_dict[target_symbol]
        if len(ohlcv) < self.lookback_sma:
            logger.warning(f"{target_symbol}: Insufficient data for relative_strength ({len(ohlcv)} candles)")
            return RelativeStrengthMetric(
                value=0.0,
                symbol_momentum=0.0,
                market_baseline=0.0,
                timestamp=ohlcv[-1]["timestamp"],
            )

        closes = np.array([c["close"] for c in ohlcv])
        sma_close = np.convolve(closes, np.ones(self.lookback_sma) / self.lookback_sma, mode="same")

        symbol_momentum = (closes[-1] - sma_close[-1]) / (closes[-1] + 1e-8)

        # Calculate market baseline momentum
        market_momentums = []
        for sym in self.symbols:
            if sym not in ohlcv_dict or len(ohlcv_dict[sym]) < self.lookback_sma:
                continue
            sym_closes = np.array([c["close"] for c in ohlcv_dict[sym]])
            sym_sma = np.convolve(sym_closes, np.ones(self.lookback_sma) / self.lookback_sma, mode="same")
            sym_momentum = (sym_closes[-1] - sym_sma[-1]) / (sym_closes[-1] + 1e-8)
            market_momentums.append(sym_momentum)

        market_baseline = np.mean(market_momentums) if market_momentums else 0.0

        # Relative strength
        relative_strength = symbol_momentum - market_baseline
        normalized = float(np.tanh(relative_strength * 2))

        if verbose:
            logger.info(
                f"{target_symbol} relative_strength: "
                f"symbol_mom={symbol_momentum:.4f}, "
                f"market_base={market_baseline:.4f}, "
                f"relative={relative_strength:.4f}, "
                f"normalized={normalized:.4f}"
            )

        return RelativeStrengthMetric(
            value=normalized,
            symbol_momentum=float(symbol_momentum),
            market_baseline=float(market_baseline),
            timestamp=ohlcv[-1]["timestamp"],
            lookback_days=self.lookback_momentum,
        )

    def score_rpm_partial(
        self,
        ohlcv_dict: Dict[str, List[Dict[str, Any]]],
        symbol: str,
        components: List[str] = None,
    ) -> Dict[str, float]:
        """
        Calculate partial RPM score (Phase 6: capital_flow + relative_strength only).

        Args:
            ohlcv_dict: Dict of {symbol: ohlcv_list}
            symbol: Target symbol
            components: List of components to calculate (default: all available)

        Returns:
            Dict of component scores
        """
        if components is None:
            components = ["capital_flow", "relative_strength"]

        scores = {}

        if "capital_flow" in components:
            cf = self.calculate_capital_flow(ohlcv_dict[symbol], symbol)
            scores["capital_flow"] = cf.value

        if "relative_strength" in components:
            rs = self.calculate_relative_strength(ohlcv_dict, symbol)
            scores["relative_strength"] = rs.value

        return scores


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Example: Phase 6 unit test
    print("RPM Engine initialized. Ready for Phase 6 integration.")

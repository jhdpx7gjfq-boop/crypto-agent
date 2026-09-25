"""
Phase B-004: RPM (Rotation/Positioning Model) Layer

Detects capital rotation between sectors/asset classes using:
- BTC dominance (% of total crypto market cap)
- Altseason strength (ratio of altcoin to BTC returns, 5D)
- Stablecoin reserve flows (inflows/outflows)
- ETF flows (Bitcoin + Ethereum ETFs)
- Funding rates (aggregate perpetuals, long vs short bias)
- Open Interest trends (acceleration)

Output: RPM_signal ∈ [-1, +1]
  +1 = strong capital inflow (bullish rotation)
  -1 = strong capital outflow (risk-off)
"""

import pandas as pd
import numpy as np
from typing import Tuple
from dataclasses import dataclass


@dataclass
class RPMSignal:
    """RPM signal with component breakdown."""
    timestamp: pd.Timestamp
    rpm_score: float
    rpm_signal: float  # tanh-normalized to [-1, +1]
    dominance_delta: float
    altseason_momentum: float
    stablecoin_flow: float
    etf_flow: float
    funding_bias: float
    oi_acceleration: float


class RPMLayer:
    """
    Rotation/Positioning Model for capital flow detection.

    Weights (frozen per B-004_SPEC.md):
    - dominance_delta: 0.25
    - altseason_momentum: 0.20
    - stablecoin_flow: 0.15
    - etf_flow: 0.20
    - funding_bias: 0.10
    - oi_acceleration: 0.10
    """

    WEIGHTS = {
        'dominance_delta': 0.25,
        'altseason_momentum': 0.20,
        'stablecoin_flow': 0.15,
        'etf_flow': 0.20,
        'funding_bias': 0.10,
        'oi_acceleration': 0.10,
    }

    NORMALIZATION_FACTOR = 1.0  # Tuned empirically in calibration phase

    def __init__(self, lookback_days: int = 5):
        """
        Args:
            lookback_days: Window for momentum calculation (default 5D per spec)
        """
        self.lookback = lookback_days

    def compute_dominance_delta(self, df: pd.DataFrame) -> np.ndarray:
        """
        BTC dominance change (5D momentum).

        Feature: btc_dominance (% of total market cap)
        Output: normalized change
        """
        if 'btc_dominance' not in df.columns or len(df) < self.lookback + 1:
            return np.zeros(len(df))

        dominance = df['btc_dominance'].values
        delta = np.zeros_like(dominance, dtype=float)

        for i in range(self.lookback, len(dominance)):
            delta[i] = (dominance[i] - dominance[i - self.lookback]) / (dominance[i - self.lookback] + 1e-8)

        return delta

    def compute_altseason_momentum(self, df: pd.DataFrame) -> np.ndarray:
        """
        Altseason strength: ratio of altcoin returns to BTC returns (5D).

        Feature: btc_return, altcoin_return (both 5D)
        Output: log ratio, clipped to [-2, +2]
        """
        if 'btc_return' not in df.columns or 'altcoin_return' not in df.columns or len(df) < 2:
            return np.zeros(len(df))

        btc_ret = df['btc_return'].values
        alt_ret = df['altcoin_return'].values

        ratio = np.zeros_like(btc_ret, dtype=float)
        for i in range(len(btc_ret)):
            if btc_ret[i] != 0:
                ratio[i] = np.log(np.abs(alt_ret[i] / btc_ret[i]) + 1e-8)
            else:
                ratio[i] = 0.0

        return np.clip(ratio, -2.0, 2.0)

    def compute_stablecoin_flow(self, df: pd.DataFrame) -> np.ndarray:
        """
        Stablecoin reserve flows (proxy for leverage/de-leverage).

        Feature: stablecoin_inflow (signed, positive = inflow)
        Output: normalized flow
        """
        if 'stablecoin_inflow' not in df.columns or len(df) < 2:
            return np.zeros(len(df))

        flow = df['stablecoin_inflow'].values
        flow_normalized = flow / (np.std(flow) + 1e-8)

        return np.clip(flow_normalized, -2.0, 2.0)

    def compute_etf_flow(self, df: pd.DataFrame) -> np.ndarray:
        """
        ETF net flows (Bitcoin + Ethereum ETFs directional).

        Feature: etf_net_flow (signed, positive = inflow)
        Output: normalized flow
        """
        if 'etf_net_flow' not in df.columns or len(df) < 2:
            return np.zeros(len(df))

        flow = df['etf_net_flow'].values
        flow_normalized = flow / (np.std(flow) + 1e-8)

        return np.clip(flow_normalized, -2.0, 2.0)

    def compute_funding_bias(self, df: pd.DataFrame) -> np.ndarray:
        """
        Funding rates bias (long vs short).

        Feature: funding_rate_8h (positive = longs pay shorts, bullish)
        Output: clipped to [-1, +1]
        """
        if 'funding_rate_8h' not in df.columns or len(df) < 2:
            return np.zeros(len(df))

        funding = df['funding_rate_8h'].values
        funding_clipped = np.clip(funding * 100, -1.0, 1.0)  # Scale to visible range

        return funding_clipped

    def compute_oi_acceleration(self, df: pd.DataFrame) -> np.ndarray:
        """
        Open Interest acceleration (d²OI/dt²).

        Feature: open_interest (absolute level)
        Output: normalized second derivative
        """
        if 'open_interest' not in df.columns or len(df) < 3:
            return np.zeros(len(df))

        oi = df['open_interest'].values
        oi_delta = np.diff(oi, prepend=oi[0])  # First derivative
        oi_accel = np.diff(oi_delta, prepend=oi_delta[0])  # Second derivative

        oi_accel_normalized = oi_accel / (np.std(oi_accel) + 1e-8)

        return np.clip(oi_accel_normalized, -2.0, 2.0)

    def compute_signal(self, df: pd.DataFrame) -> list[RPMSignal]:
        """
        Compute RPM signal for entire dataset (PIT-safe).

        Args:
            df: DataFrame with OHLCV + RPM features

        Returns:
            List of RPMSignal objects
        """
        results = []

        dominance_delta = self.compute_dominance_delta(df)
        altseason_momentum = self.compute_altseason_momentum(df)
        stablecoin_flow = self.compute_stablecoin_flow(df)
        etf_flow = self.compute_etf_flow(df)
        funding_bias = self.compute_funding_bias(df)
        oi_acceleration = self.compute_oi_acceleration(df)

        for i in range(len(df)):
            # Weighted blend (per frozen spec)
            rpm_score = (
                self.WEIGHTS['dominance_delta'] * dominance_delta[i] +
                self.WEIGHTS['altseason_momentum'] * altseason_momentum[i] +
                self.WEIGHTS['stablecoin_flow'] * stablecoin_flow[i] +
                self.WEIGHTS['etf_flow'] * etf_flow[i] +
                self.WEIGHTS['funding_bias'] * funding_bias[i] +
                self.WEIGHTS['oi_acceleration'] * oi_acceleration[i]
            )

            # Normalize via tanh to [-1, +1]
            rpm_signal = np.tanh(rpm_score / self.NORMALIZATION_FACTOR)

            signal_obj = RPMSignal(
                timestamp=df.index[i] if hasattr(df.index[i], 'to_pydatetime') else df.index[i],
                rpm_score=rpm_score,
                rpm_signal=rpm_signal,
                dominance_delta=dominance_delta[i],
                altseason_momentum=altseason_momentum[i],
                stablecoin_flow=stablecoin_flow[i],
                etf_flow=etf_flow[i],
                funding_bias=funding_bias[i],
                oi_acceleration=oi_acceleration[i],
            )
            results.append(signal_obj)

        return results

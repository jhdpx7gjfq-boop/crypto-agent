"""
Layer 7 - RRP Data Layer: On-chain + NLP metrics for revival detection

Sources:
- CryptoQuant: Dormancy, activity, whales
- Glassnode: On-chain metrics
- LunarCrush: Narrative signals
- Synthetic fallback for testing
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from pathlib import Path


class RRPDataLayer:
    """Revival Radar Pipeline data aggregation."""

    def __init__(self, data_source: str = 'synthetic'):
        """
        Initialize data layer.

        Args:
            data_source: 'synthetic', 'cryptoquant', 'glassnode', 'file'
        """
        self.data_source = data_source
        self.dormant_tokens = {}
        self.metrics = {}

    def load_dormant_tokens(self, market_cap_min: float = 1e6) -> pd.DataFrame:
        """
        Load candidate dormant tokens.

        Returns:
            DataFrame with columns: token, last_activity_days, market_cap
        """
        if self.data_source == 'synthetic':
            return self._synthetic_dormant_tokens(market_cap_min)
        elif self.data_source == 'cryptoquant':
            return self._load_cryptoquant_dormant()
        else:
            raise ValueError(f"Unknown data_source: {self.data_source}")

    def _synthetic_dormant_tokens(self, market_cap_min: float) -> pd.DataFrame:
        """Generate realistic dormant token candidates (synthetic)."""
        # Realistic dormant tokens portfolio
        tokens = [
            {'symbol': 'LUNA', 'last_activity_days': 45, 'market_cap': 2.5e9},
            {'symbol': 'XRP', 'last_activity_days': 22, 'market_cap': 35e9},
            {'symbol': 'DOGE', 'last_activity_days': 8, 'market_cap': 12e9},
            {'symbol': 'ADA', 'last_activity_days': 15, 'market_cap': 18e9},
            {'symbol': 'MATIC', 'last_activity_days': 30, 'market_cap': 7e9},
            {'symbol': 'SOL', 'last_activity_days': 5, 'market_cap': 60e9},
            {'symbol': 'AVAX', 'last_activity_days': 25, 'market_cap': 12e9},
            {'symbol': 'FTT', 'last_activity_days': 180, 'market_cap': 1.2e9},
            {'symbol': 'GALA', 'last_activity_days': 120, 'market_cap': 450e6},
            {'symbol': 'THETA', 'last_activity_days': 95, 'market_cap': 800e6},
        ]
        df = pd.DataFrame(tokens)
        return df[df['market_cap'] >= market_cap_min]

    def compute_dormancy_index(self, days_since_activity: int) -> float:
        """
        Compute dormancy index [0, 1].

        Args:
            days_since_activity: Days since last on-chain activity

        Returns:
            Dormancy score (0=active, 1=very dormant)
        """
        # Normalize: 30 days = start of dormancy, 365+ days = maximum
        d = (days_since_activity - 30) / (365 - 30)
        return float(np.clip(d, 0, 1))

    def compute_activity_acceleration(self, activity_history: np.ndarray,
                                     lookback: int = 14) -> float:
        """
        Compute activity acceleration (d²/dt²).

        Args:
            activity_history: Recent activity counts (e.g., daily transactions)
            lookback: Window size for acceleration

        Returns:
            Standardized acceleration [-1, +1]
        """
        if len(activity_history) < lookback + 2:
            return 0.0

        recent = activity_history[-lookback:]
        first_deriv = np.diff(recent)
        second_deriv = np.diff(first_deriv)

        if len(second_deriv) == 0:
            return 0.0

        accel_mean = np.mean(second_deriv)
        accel_std = np.std(second_deriv)

        if accel_std < 1e-8:
            return 0.0

        accel_norm = (second_deriv[-1] - accel_mean) / accel_std
        return float(np.tanh(accel_norm / 2))

    def compute_whale_accumulation(self, whale_inflow_24h: float,
                                  baseline_whale_activity: float = 1.0) -> float:
        """
        Compute whale entry signal.

        Args:
            whale_inflow_24h: Whale inflow in dollars (last 24h)
            baseline_whale_activity: Average whale activity

        Returns:
            Accumulation score [-1, +1]
        """
        if baseline_whale_activity < 1e-8:
            return 0.0

        ratio = whale_inflow_24h / baseline_whale_activity
        # Cap at 2.0 to avoid extreme values
        ratio_capped = min(ratio, 2.0)
        return float(np.tanh((ratio_capped - 1) / 1.5))

    def compute_developer_activity(self, commits_recent: int, commits_baseline: int) -> float:
        """
        Compute developer activity signal.

        Args:
            commits_recent: Recent commits (e.g., last 7 days)
            commits_baseline: Baseline (e.g., 30-day average)

        Returns:
            Dev activity score [-1, +1]
        """
        if commits_baseline < 1:
            return 0.0

        ratio = commits_recent / max(commits_baseline, 1)
        dev_signal = ratio - 1.0
        return float(np.tanh(dev_signal / 2))

    def compute_narrative_momentum(self, mentions_recent: int, mentions_baseline: int,
                                  sentiment_positive: float = 0.5) -> float:
        """
        Compute narrative momentum from mentions + sentiment.

        Args:
            mentions_recent: Mentions in recent period
            mentions_baseline: Average mentions baseline
            sentiment_positive: Fraction of positive mentions

        Returns:
            Narrative score [-1, +1]
        """
        if mentions_baseline < 1:
            return 0.0

        mention_ratio = (mentions_recent / max(mentions_baseline, 1)) - 1.0
        sentiment_signal = (sentiment_positive - 0.5) * 2  # [-1, +1]

        combined = mention_ratio * 0.7 + sentiment_signal * 0.3
        return float(np.tanh(combined / 1.5))

    def compute_liquidity_rebound(self, volume_recent: float,
                                 volume_baseline: float) -> float:
        """
        Compute liquidity rebound signal.

        Args:
            volume_recent: Recent trading volume
            volume_baseline: Baseline volume

        Returns:
            Liquidity score [-1, +1]
        """
        if volume_baseline < 1e-8:
            return 0.0

        ratio = volume_recent / volume_baseline
        return float(np.tanh((ratio - 1) / 2))

    def generate_synthetic_metrics(self, tokens_df: pd.DataFrame,
                                  periods: int = 100) -> Dict:
        """
        Generate synthetic revival metrics for tokens over time.

        Args:
            tokens_df: Dormant tokens DataFrame
            periods: Number of time periods to generate

        Returns:
            Dict mapping token -> time series of metrics
        """
        metrics = {}

        for _, row in tokens_df.iterrows():
            token = row['symbol']
            dormancy_base = self.compute_dormancy_index(row['last_activity_days'])

            # Generate realistic metric trajectories
            # Some tokens will show revival, others stay dormant

            # Random assignment: ~30% revival probability
            is_reviving = np.random.random() < 0.3

            if is_reviving:
                # Revival trajectory: metrics increase then stabilize
                revival_start = np.random.randint(20, periods - 20)
                # Pre-revival (negative)
                pre_revival = np.linspace(-0.3, 0, revival_start)
                # Post-revival (positive)
                post_revival = np.linspace(0, 0.8, periods - revival_start)
                trajectory = np.concatenate([pre_revival, post_revival])
            else:
                # Non-revival: metrics stay low
                trajectory = np.linspace(-0.5, -0.2, periods)

            # Add noise
            trajectory += np.random.normal(0, 0.1, periods)
            trajectory = np.clip(trajectory, -1, 1)

            metrics[token] = trajectory

        return metrics

    def compute_revival_confidence(self, dormancy: float, acceleration: float,
                                  whale: float, dev: float, narrative: float,
                                  liquidity: float) -> float:
        """
        Compute final Revival_Confidence score [0, 100].

        Args:
            dormancy: Dormancy index [0, 1]
            acceleration: Activity acceleration [-1, +1]
            whale: Whale accumulation [-1, +1]
            dev: Developer activity [-1, +1]
            narrative: Narrative momentum [-1, +1]
            liquidity: Liquidity rebound [-1, +1]

        Returns:
            Revival_Confidence [0, 100]
        """
        # Weighted combination (per spec: weights sum to 1.0)
        score = (
            0.20 * dormancy +
            0.25 * acceleration +
            0.15 * whale +
            0.15 * dev +
            0.15 * narrative +
            0.10 * liquidity
        )

        # Sigmoid to [0, 100]
        confidence = (1 / (1 + np.exp(-score * 3))) * 100

        return float(confidence)

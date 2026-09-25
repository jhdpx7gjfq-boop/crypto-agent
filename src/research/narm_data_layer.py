"""NARM-P+ Data Layer

Narrative Adoption Rotation Model Plus — macro signals.
PIT-safe sentiment, adoption, rotation scoring.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class NARMDataLayer:
    """Fetches and computes NARM-P+ signals."""

    def __init__(self):
        self.synthetic_seed = 42

    def fetch_sentiment(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch social sentiment (LunarCrush or fallback).

        Returns:
            DataFrame with columns: [timestamp, sentiment_score, mention_count]
        """
        try:
            # In production: fetch from LunarCrush API
            # For now: use synthetic deterministic data
            return self._synthetic_sentiment(start_date, end_date)
        except Exception as e:
            logger.warning(f"Failed to fetch sentiment: {e}")
            return self._synthetic_sentiment(start_date, end_date)

    def fetch_adoption(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch on-chain adoption (active addresses, etc).

        Returns:
            DataFrame with columns: [timestamp, active_addresses, address_change_pct]
        """
        try:
            # In production: Glassnode on-chain metrics
            # For now: synthetic data
            return self._synthetic_adoption(start_date, end_date)
        except Exception as e:
            logger.warning(f"Failed to fetch adoption: {e}")
            return self._synthetic_adoption(start_date, end_date)

    def fetch_dev_activity(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch GitHub commit activity.

        Returns:
            DataFrame with columns: [timestamp, commits, pr_count]
        """
        try:
            # In production: GitHub API for BTC/ETH repos
            # For now: synthetic
            return self._synthetic_dev_activity(start_date, end_date)
        except Exception as e:
            logger.warning(f"Failed to fetch dev activity: {e}")
            return self._synthetic_dev_activity(start_date, end_date)

    def fetch_sector_rotation(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch sector narrative dominance (DeFi, L1, AI, RWA, etc).

        Returns:
            DataFrame with columns: [timestamp, dominant_sector, sector_mcap_share]
        """
        try:
            # In production: CoinGecko categories API
            # For now: synthetic
            return self._synthetic_sector_rotation(start_date, end_date)
        except Exception as e:
            logger.warning(f"Failed to fetch sector rotation: {e}")
            return self._synthetic_sector_rotation(start_date, end_date)

    def _synthetic_sentiment(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Synthetic sentiment (deterministic, PIT-safe)."""
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        dates = pd.date_range(start=start_dt, end=end_dt, freq='D')

        np.random.seed(self.synthetic_seed)
        sentiment_scores = 50 + 20 * np.sin(np.arange(len(dates)) / 30) + np.random.normal(0, 5, len(dates))
        sentiment_scores = np.clip(sentiment_scores, 0, 100)

        df = pd.DataFrame({
            'timestamp': dates,
            'sentiment_score': sentiment_scores,
            'mention_count': np.random.poisson(1000, len(dates))
        })

        logger.info(f"Generated {len(df)} synthetic sentiment records")
        return df

    def _synthetic_adoption(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Synthetic on-chain adoption (deterministic)."""
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        dates = pd.date_range(start=start_dt, end=end_dt, freq='D')

        np.random.seed(self.synthetic_seed)
        base = 1e7
        growth = np.cumsum(np.random.normal(0.0005, 0.002, len(dates)))
        active_addresses = base * (1 + growth) * (1 + 0.1 * np.random.normal(0, 1, len(dates)))
        active_addresses = np.maximum(active_addresses, base * 0.8)

        df = pd.DataFrame({
            'timestamp': dates,
            'active_addresses': active_addresses,
            'address_change_pct': np.diff(active_addresses, prepend=active_addresses[0]) / active_addresses * 100
        })

        logger.info(f"Generated {len(df)} synthetic adoption records")
        return df

    def _synthetic_dev_activity(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Synthetic GitHub activity (deterministic)."""
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        dates = pd.date_range(start=start_dt, end=end_dt, freq='D')

        np.random.seed(self.synthetic_seed)
        commits = 50 + np.random.poisson(20, len(dates))
        pr_count = 5 + np.random.poisson(3, len(dates))

        df = pd.DataFrame({
            'timestamp': dates,
            'commits': commits,
            'pr_count': pr_count
        })

        logger.info(f"Generated {len(df)} synthetic dev activity records")
        return df

    def _synthetic_sector_rotation(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Synthetic sector narrative (deterministic)."""
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        dates = pd.date_range(start=start_dt, end=end_dt, freq='D')

        sectors = ['DeFi', 'L1', 'L2', 'AI', 'RWA']
        np.random.seed(self.synthetic_seed)

        df = pd.DataFrame({
            'timestamp': dates,
            'dominant_sector': np.random.choice(sectors, len(dates)),
            'sector_mcap_share': np.random.uniform(0.15, 0.35, len(dates))
        })

        logger.info(f"Generated {len(df)} synthetic sector rotation records")
        return df

    @staticmethod
    def compute_narm_score(sentiment_df: pd.DataFrame,
                          adoption_df: pd.DataFrame,
                          dev_df: pd.DataFrame,
                          sector_df: pd.DataFrame,
                          pit_idx: int) -> float:
        """
        Compute NARM-P+ score at PIT index (0-100 scale).

        Components:
        - 25% sentiment (0-1)
        - 25% adoption (0-1)
        - 20% rotation (0-1)
        - 20% fundamentals (0-1, default 0.5)
        - 10% momentum (0-1, default 0.5)
        """
        if pit_idx < 0 or pit_idx >= len(sentiment_df):
            return 50.0  # Neutral

        # Sentiment component (0-1)
        sentiment_raw = sentiment_df.iloc[pit_idx]['sentiment_score'] / 100.0
        sentiment_score = np.clip(sentiment_raw, 0, 1)

        # Adoption component (0-1)
        adoption_addr = adoption_df.iloc[pit_idx]['active_addresses']
        adoption_change = adoption_df.iloc[pit_idx]['address_change_pct']
        adoption_score = 0.5 + 0.05 * np.clip(adoption_change, -10, 10) / 10
        adoption_score = np.clip(adoption_score, 0, 1)

        # Rotation component (0-1)
        if pit_idx > 0:
            sector_change_rate = (sector_df.iloc[pit_idx]['sector_mcap_share'] /
                                 sector_df.iloc[pit_idx-1]['sector_mcap_share']) - 1
            rotation_score = 0.5 + 0.5 * np.clip(sector_change_rate, -1, 1)
        else:
            rotation_score = 0.5

        # Fundamentals (fixed neutral for now)
        fundamentals_score = 0.5

        # Momentum (can derive from price momentum elsewhere, but for NARM just neutral)
        momentum_score = 0.5

        # Weighted average
        narm_p_plus = 100 * (
            0.25 * sentiment_score +
            0.25 * adoption_score +
            0.20 * rotation_score +
            0.20 * fundamentals_score +
            0.10 * momentum_score
        )

        return float(np.clip(narm_p_plus, 0, 100))

    @staticmethod
    def merge_narm_with_ohlcv(ohlcv: pd.DataFrame,
                             sentiment_df: pd.DataFrame,
                             adoption_df: pd.DataFrame,
                             dev_df: pd.DataFrame,
                             sector_df: pd.DataFrame) -> pd.DataFrame:
        """
        Merge NARM components with OHLCV by date.

        Returns:
            DataFrame with OHLCV + NARM columns
        """
        # Join on date
        ohlcv_copy = ohlcv.copy()
        ohlcv_copy.index.name = 'date'

        sentiment_df_idx = sentiment_df.set_index('timestamp')
        adoption_df_idx = adoption_df.set_index('timestamp')
        sector_df_idx = sector_df.set_index('timestamp')

        merged = ohlcv_copy.join([sentiment_df_idx, adoption_df_idx, sector_df_idx], how='left')

        # Forward fill NaNs
        merged['sentiment_score'] = merged['sentiment_score'].ffill()
        merged['active_addresses'] = merged['active_addresses'].ffill()
        merged['sector_mcap_share'] = merged['sector_mcap_share'].ffill()

        return merged

    @staticmethod
    def compute_narm_series(df_merged: pd.DataFrame) -> pd.Series:
        """Compute NARM-P+ score for entire series (slower, for analysis)."""
        narm_scores = []

        for idx in range(len(df_merged)):
            # Extract components at this row
            sentiment = df_merged.iloc[idx].get('sentiment_score', 50) / 100.0
            adoption = 0.5  # Simplified for series computation
            rotation = 0.5  # Simplified
            fundamentals = 0.5
            momentum = 0.5

            score = 100 * (
                0.25 * sentiment +
                0.25 * adoption +
                0.20 * rotation +
                0.20 * fundamentals +
                0.10 * momentum
            )

            narm_scores.append(np.clip(score, 0, 100))

        return pd.Series(narm_scores, index=df_merged.index)

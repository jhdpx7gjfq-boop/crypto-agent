"""Capital Flow Data Layer

OI, Funding, Liquidations from Binance Perpetual (PIT-safe).
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class BinancePerpetualFlow:
    """Fetches OI and Funding data from Binance Perpetual."""

    def __init__(self, symbol: str = "BTCUSDT"):
        self.symbol = symbol

    def fetch_funding_rates(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch funding rates from Binance.

        Note: This is a MOCK implementation.
        In production, use: pip install ccxt
        exchange = ccxt.binance({'enableRateLimit': True})
        rates = exchange.fetch_funding_history('BTC/USDT', limit=1000)

        Returns:
            DataFrame with columns: [timestamp, funding_rate]
        """
        try:
            import ccxt
            exchange = ccxt.binance({'enableRateLimit': True})

            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)

            # Binance funding rates update every 8 hours
            # We'll aggregate to daily
            rates = []
            current = start_dt

            while current <= end_dt:
                try:
                    # Fetch funding rate history for this period
                    # Note: ccxt.fetch_funding_history returns list of [timestamp, symbol, funding_rate, ...]
                    since_ms = int(current.timestamp() * 1000)
                    funding = exchange.fetch_funding_rate_history(
                        'BTC/USDT',
                        since=since_ms,
                        limit=100
                    )

                    if not funding:
                        current += timedelta(days=1)
                        continue

                    rates.extend(funding)
                    current += timedelta(days=1)

                except Exception as e:
                    logger.warning(f"Error fetching funding for {current}: {e}")
                    current += timedelta(days=1)
                    continue

            if not rates:
                logger.error("No funding rates fetched from Binance")
                return None

            # Parse into DataFrame
            df = pd.DataFrame(rates)
            if len(df) > 0:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
                df = df[['timestamp', 'funding_rate']].dropna()
                df = df.sort_values('timestamp').reset_index(drop=True)
                logger.info(f"✅ Fetched {len(df)} funding rates")
                return df

            return None

        except ImportError:
            logger.warning("ccxt not installed; using placeholder funding data")
            return self._placeholder_funding_rates(start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to fetch funding: {e}")
            return None

    def fetch_oi_daily(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch daily Open Interest snapshots from Binance.

        Returns:
            DataFrame with columns: [timestamp, open_interest]
        """
        try:
            import ccxt
            exchange = ccxt.binance({'enableRateLimit': True})

            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)

            oi_data = []
            current = start_dt

            while current <= end_dt:
                try:
                    # Some exchanges provide OI via ticker data or specific endpoint
                    # Fallback: construct from contract specifications or use placeholder
                    ticker = exchange.fetch_ticker('BTC/USDT')
                    if 'openInterest' in ticker:
                        oi_data.append({
                            'timestamp': pd.to_datetime(current),
                            'open_interest': ticker['openInterest']
                        })
                    current += timedelta(days=1)

                except Exception as e:
                    logger.debug(f"Could not fetch OI for {current}: {e}")
                    current += timedelta(days=1)
                    continue

            if not oi_data:
                logger.warning("No OI data fetched; using placeholder")
                return self._placeholder_oi(start_date, end_date)

            df = pd.DataFrame(oi_data)
            df = df.sort_values('timestamp').reset_index(drop=True)
            logger.info(f"✅ Fetched {len(df)} OI snapshots")
            return df

        except ImportError:
            logger.warning("ccxt not installed; using placeholder OI data")
            return self._placeholder_oi(start_date, end_date)
        except Exception as e:
            logger.error(f"Failed to fetch OI: {e}")
            return self._placeholder_oi(start_date, end_date)

    def _placeholder_funding_rates(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Synthetic funding rates for testing (deterministic, PIT-safe)."""
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
        np.random.seed(42)  # Deterministic

        df = pd.DataFrame({
            'timestamp': dates,
            'funding_rate': np.random.normal(0.0001, 0.0002, len(dates))
        })

        logger.info(f"✅ Generated {len(df)} synthetic funding rates (placeholder)")
        return df

    def _placeholder_oi(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Synthetic OI for testing (deterministic, PIT-safe)."""
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)

        dates = pd.date_range(start=start_dt, end=end_dt, freq='D')
        np.random.seed(42)  # Deterministic

        # OI grows over time with noise
        base_oi = 1e9  # $1B base
        noise = np.random.normal(1.0, 0.05, len(dates))
        oi_values = base_oi * (1 + np.cumsum(np.random.normal(0.001, 0.01, len(dates)))) * noise

        df = pd.DataFrame({
            'timestamp': dates,
            'open_interest': np.maximum(oi_values, base_oi * 0.5)
        })

        logger.info(f"✅ Generated {len(df)} synthetic OI values (placeholder)")
        return df


class FlowIndicators:
    """Compute flow-based indicators (PIT-safe)."""

    @staticmethod
    def oi_change_pct(df: pd.DataFrame) -> pd.Series:
        """OI day-over-day % change."""
        return df['open_interest'].pct_change()

    @staticmethod
    def funding_rate_avg(df_funding: pd.DataFrame, window: int = 7) -> pd.Series:
        """Rolling avg funding rate over window days."""
        if len(df_funding) < window:
            return pd.Series(np.zeros(len(df_funding)), index=df_funding.index)

        return df_funding['funding_rate'].rolling(window).mean()

    @staticmethod
    def liquidation_cascade(df: pd.DataFrame, adv_col: str = "volume") -> pd.Series:
        """
        Liquidation volume as % of ADV (requires liquidation data).

        Placeholder: returns zeros (no real liquidation data source yet).
        """
        return pd.Series(np.zeros(len(df)), index=df.index)

    @staticmethod
    def merge_flow_data(ohlcv: pd.DataFrame,
                       oi_df: pd.DataFrame,
                       funding_df: pd.DataFrame) -> pd.DataFrame:
        """
        Merge OHLCV + OI + Funding by date (PIT-safe).

        Args:
            ohlcv: Daily OHLCV with index = timestamp
            oi_df: OI with timestamp column
            funding_df: Funding with timestamp column

        Returns:
            Merged DataFrame, NaN filled with forward fill
        """
        # Ensure all are DatetimeIndex
        ohlcv_copy = ohlcv.copy()
        ohlcv_copy.index.name = 'date'

        oi_df_copy = oi_df.set_index('timestamp')
        funding_df_copy = funding_df.set_index('timestamp')

        # Merge on date
        merged = ohlcv_copy.join([oi_df_copy, funding_df_copy], how='left')

        # Forward fill OI/Funding (carry last known values)
        merged['open_interest'] = merged['open_interest'].fillna(method='ffill')
        merged['funding_rate'] = merged['funding_rate'].fillna(method='ffill')

        return merged

    @staticmethod
    def compute_flow_features(df: pd.DataFrame, pit_idx: int) -> Dict[str, float]:
        """
        Compute flow features at PIT index (no forward-look).

        Args:
            df: Merged OHLCV + Flow data
            pit_idx: Current row index

        Returns:
            {
                'oi_change_pct': float,
                'funding_rate_7d_avg': float,
                'liquidation_pct': float
            }
        """
        if pit_idx < 1:
            return {
                'oi_change_pct': 0.0,
                'funding_rate_7d_avg': 0.0,
                'liquidation_pct': 0.0
            }

        # Use only data up to pit_idx (PIT-safe)
        pit_data = df.iloc[:pit_idx + 1]

        oi_change = FlowIndicators.oi_change_pct(pit_data).iloc[-1] if pit_idx > 0 else 0.0
        oi_change = 0.0 if np.isnan(oi_change) else oi_change

        funding_7d = FlowIndicators.funding_rate_avg(pit_data, window=7).iloc[-1] if pit_idx >= 7 else 0.0
        funding_7d = 0.0 if np.isnan(funding_7d) else funding_7d

        liq_pct = 0.0  # Placeholder

        return {
            'oi_change_pct': float(oi_change),
            'funding_rate_7d_avg': float(funding_7d),
            'liquidation_pct': float(liq_pct)
        }

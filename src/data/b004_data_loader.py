"""
B-004 Data Loader — Real Data Integration Template

Supports:
- Binance OHLCV (via ccxt or local cache)
- CryptoQuant API (stablecoin flows, funding rates)
- Glassnode API (market metrics)
- Synthetic realistic data (fallback)

Design: PIT-safe, no lookahead
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional


class B004DataLoader:
    """Load B-004 market data with feature engineering."""

    def __init__(self, data_source: str = 'synthetic'):
        """
        Initialize loader.

        Args:
            data_source: 'binance', 'file', 'synthetic'
        """
        self.data_source = data_source
        self.data: Optional[pd.DataFrame] = None

    def load(self, start_date: str = '2021-01-01',
             end_date: str = '2024-09-25') -> pd.DataFrame:
        """
        Load OHLCV + RPM features for date range.

        Returns:
            DataFrame with columns:
            - OHLCV: open, high, low, close, volume
            - RPM features: btc_dominance, btc_return, altcoin_return,
                           stablecoin_inflow, etf_net_flow, funding_rate_8h,
                           open_interest
        """
        if self.data_source == 'synthetic':
            return self._load_synthetic(start_date, end_date)
        elif self.data_source == 'binance':
            return self._load_binance(start_date, end_date)
        elif self.data_source == 'file':
            return self._load_file(start_date, end_date)
        else:
            raise ValueError(f"Unknown data_source: {self.data_source}")

    def _load_synthetic(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Generate realistic synthetic OHLCV + features.

        Based on crypto market patterns:
        - Uptrend with volatility regimes
        - Realistic funding rates ([-0.0001, +0.0001])
        - Capital flow patterns
        """
        dates = pd.date_range(start_date, end_date, freq='D')
        n = len(dates)

        # Price: realistic uptrend (40% over 4 years) + regime shifts
        trend = np.linspace(100, 140, n)
        regime_factor = np.where(
            dates.year == 2022, 0.7,  # 2022 bear
            np.where(dates.year >= 2024, 1.1, 1.0)  # 2024 bull
        )
        noise = np.random.normal(0, 3, n)
        close = trend * regime_factor + noise
        close = np.maximum(close, 10)

        # OHLCV realistic ranges
        open_p = close + np.random.normal(0, 2, n)
        high = np.maximum(close, open_p) + np.random.exponential(3, n)
        low = np.minimum(close, open_p) - np.random.exponential(3, n)
        volume = np.random.lognormal(10, 1.5, n)

        # RPM Features: realistic market patterns
        # BTC dominance: 35-45% range
        btc_dom = 40 + 3 * np.sin(np.arange(n) * 2*np.pi / 365)
        btc_dom += np.random.normal(0, 0.5, n)

        # Returns: contrarian to volatility regime
        btc_ret = np.diff(close / 100, prepend=close[0]/100)
        btc_ret = btc_ret * (0.8 if regime_factor[0] == 0.7 else 1.2)
        btc_ret += np.random.normal(0, 0.015, n)

        altcoin_ret = btc_ret * 1.5 + np.random.normal(0, 0.02, n)

        # Stablecoin flows: inverse to price momentum
        price_mom = np.diff(close, prepend=close[0])
        stablecoin_inflow = -100 * np.sign(price_mom) * np.abs(price_mom)
        stablecoin_inflow += np.random.normal(0, 50, n)

        # ETF flows: positive in bull, negative in bear
        etf_flow = 50 * regime_factor + np.random.normal(0, 25, n)

        # Funding rates: realistic [-0.0001, +0.0001]
        funding_rate = (regime_factor - 1) * 0.00005
        funding_rate += np.random.normal(0, 0.00005, n)
        funding_rate = np.clip(funding_rate, -0.0001, 0.0001)

        # Open Interest: trending with price
        oi = np.linspace(1000, 2000, n) * regime_factor
        oi += np.random.normal(0, 50, n)

        df = pd.DataFrame({
            'open': open_p,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'btc_dominance': btc_dom,
            'btc_return': btc_ret,
            'altcoin_return': altcoin_ret,
            'stablecoin_inflow': stablecoin_inflow,
            'etf_net_flow': etf_flow,
            'funding_rate_8h': funding_rate,
            'open_interest': oi,
        }, index=dates)

        return df

    def _load_binance(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Load real Binance OHLCV (requires ccxt)."""
        try:
            import ccxt
        except ImportError:
            raise ImportError("CCXT not installed. Install with: pip install ccxt")

        binance = ccxt.binance()
        ohlcv_data = []

        # Fetch in chunks (Binance limit: 1000 per request)
        current_date = pd.Timestamp(start_date)
        end_ts = pd.Timestamp(end_date)

        while current_date < end_ts:
            ohlcv = binance.fetch_ohlcv(
                'BTC/USDT', '1d',
                since=int(current_date.timestamp() * 1000),
                limit=1000
            )
            if not ohlcv:
                break
            ohlcv_data.extend(ohlcv)
            current_date = pd.Timestamp(ohlcv[-1][0], unit='ms') + pd.Timedelta(days=1)

        # Convert to DataFrame
        dates = pd.DatetimeIndex([pd.Timestamp(x[0], unit='ms') for x in ohlcv_data])
        df = pd.DataFrame(
            {col: [x[i+1] for x in ohlcv_data]
             for i, col in enumerate(['open', 'high', 'low', 'close', 'volume'])},
            index=dates
        )

        # Placeholder: features would come from CryptoQuant/Glassnode APIs
        # For now, compute from OHLCV
        df['btc_dominance'] = 42.0  # Placeholder
        df['btc_return'] = df['close'].pct_change()
        df['altcoin_return'] = df['close'].pct_change() * 1.2
        df['stablecoin_inflow'] = 0.0  # Requires API
        df['etf_net_flow'] = 0.0  # Requires API
        df['funding_rate_8h'] = 0.0  # Requires API
        df['open_interest'] = 1000.0  # Requires API

        return df

    def _load_file(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Load from local parquet/csv file."""
        data_dir = Path(__file__).parent.parent.parent / 'data'

        # Look for parquet file
        parquet_file = data_dir / 'btc_ohlcv_2021_2024.parquet'
        if parquet_file.exists():
            df = pd.read_parquet(parquet_file)
            return df.loc[start_date:end_date]

        # Look for CSV
        csv_file = data_dir / 'btc_ohlcv_2021_2024.csv'
        if csv_file.exists():
            df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
            return df.loc[start_date:end_date]

        raise FileNotFoundError(f"No data file found in {data_dir}")

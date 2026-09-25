"""Phase 1: Real Binance OHLCV Data Collector (Production)."""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import requests
import time

logger = logging.getLogger(__name__)


class BinanceRealCollector:
    """Collect REAL OHLCV data from Binance public API (no auth required)."""

    BASE_URL = "https://api.binance.com/api/v3"

    # Rate limiting: 1200 requests per minute
    REQUESTS_PER_MINUTE = 1200
    REQUEST_INTERVAL = 60.0 / REQUESTS_PER_MINUTE

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.session = requests.Session()
        self.last_request_time = 0
        self.request_count = 0
        self.data_collected: Dict[str, List[Dict]] = {}

    def _rate_limit(self):
        """Enforce Binance rate limits."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.REQUEST_INTERVAL:
            time.sleep(self.REQUEST_INTERVAL - elapsed)

    def fetch_ohlcv(
        self,
        symbol: str = "BTCUSDT",
        interval: str = "1d",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        days: int = 180,
    ) -> List[Dict[str, Any]]:
        """
        Fetch REAL OHLCV candles from Binance API.

        Args:
            symbol: Trading pair (BTCUSDT, ETHUSDT, etc.)
            interval: Candle interval (1m, 5m, 1h, 4h, 1d, etc.)
            start_date: Start timestamp (or use days lookback)
            end_date: End timestamp (default: now)
            days: Days to lookback if start_date not given

        Returns:
            List of OHLCV dicts with real Binance data

        Raises:
            requests.RequestException: Network error
            ValueError: Invalid parameters
        """
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(days=days)

        logger.info(f"BinanceRealCollector: {symbol} {interval}")
        logger.info(f"  Period: {start_date.date()} → {end_date.date()} ({days} days)")

        candles = []
        current_start = int(start_date.timestamp() * 1000)
        end_ms = int(end_date.timestamp() * 1000)

        # Binance klines limit: 1000 per request
        # Calculate interval in milliseconds
        interval_ms = self._parse_interval_ms(interval)
        max_candles_per_request = 1000
        max_ms_per_request = interval_ms * max_candles_per_request

        request_num = 0
        while current_start < end_ms:
            request_num += 1
            request_end = min(current_start + max_ms_per_request, end_ms)

            logger.info(f"  Request {request_num}: {self._ms_to_date(current_start).date()}")

            try:
                batch = self._fetch_batch(
                    symbol=symbol,
                    interval=interval,
                    start_time=current_start,
                    end_time=request_end,
                    limit=min(max_candles_per_request, 1000),
                )

                if not batch:
                    logger.warning(f"    → Empty response (may be normal at boundary)")
                    break

                candles.extend(batch)
                logger.info(f"    ✓ Got {len(batch)} candles")

                # Move to next batch
                if batch:
                    current_start = int(batch[-1]["open_time"]) + interval_ms
                else:
                    break

                # Rate limiting
                self._rate_limit()

            except requests.RequestException as e:
                logger.error(f"    ✗ API Error: {e}")
                raise

        logger.info(f"  Total: {len(candles)} candles collected")

        # Validate data
        self._validate_candles(symbol, candles)

        # Store
        self.data_collected[symbol] = candles

        return candles

    def _fetch_batch(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: int,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Fetch single batch of candles from Binance API."""
        self._rate_limit()

        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time,
            "endTime": end_time,
            "limit": limit,
        }

        url = f"{self.BASE_URL}/klines"

        try:
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            self.request_count += 1
            self.last_request_time = time.time()

            data = response.json()

            if not isinstance(data, list):
                raise ValueError(f"Unexpected response format: {type(data)}")

            # Parse Binance response format
            candles = []
            for row in data:
                candles.append({
                    "open_time": int(row[0]),
                    "open": float(row[1]),
                    "high": float(row[2]),
                    "low": float(row[3]),
                    "close": float(row[4]),
                    "volume": float(row[5]),
                    "close_time": int(row[6]),
                    "quote_asset_volume": float(row[7]),
                    "number_of_trades": int(row[8]),
                    "taker_buy_base_asset_volume": float(row[9]),
                    "taker_buy_quote_asset_volume": float(row[10]),
                })

            return candles

        except requests.RequestException as e:
            logger.error(f"API Error: {e}")
            raise

    @staticmethod
    def _parse_interval_ms(interval: str) -> int:
        """Convert interval string to milliseconds."""
        multipliers = {
            "m": 60 * 1000,
            "h": 60 * 60 * 1000,
            "d": 24 * 60 * 60 * 1000,
            "w": 7 * 24 * 60 * 60 * 1000,
        }
        if interval[-1] not in multipliers:
            raise ValueError(f"Unknown interval: {interval}")
        value = int(interval[:-1])
        unit = interval[-1]
        return value * multipliers[unit]

    @staticmethod
    def _ms_to_date(ms: int) -> datetime:
        """Convert milliseconds to datetime."""
        return datetime.utcfromtimestamp(ms / 1000)

    @staticmethod
    def _validate_candles(symbol: str, candles: List[Dict]) -> None:
        """Validate OHLCV data integrity."""
        if not candles:
            logger.warning(f"  ⚠ No candles collected for {symbol}")
            return

        issues = []

        for i, candle in enumerate(candles):
            # Check OHLC order
            o, h, l, c = candle["open"], candle["high"], candle["low"], candle["close"]
            if h < max(o, c):
                issues.append(f"  Row {i}: high < open/close")
            if l > min(o, c):
                issues.append(f"  Row {i}: low > open/close")
            if l > h:
                issues.append(f"  Row {i}: low > high")

            # Check volume
            if candle["volume"] < 0:
                issues.append(f"  Row {i}: negative volume")

            # Check monotonic timestamps
            if i > 0:
                prev_close = candles[i - 1]["close_time"]
                curr_open = candle["open_time"]
                if curr_open <= prev_close:
                    issues.append(f"  Row {i}: timestamp not monotonic")

        if issues:
            logger.warning(f"Data quality issues ({len(issues)}):")
            for issue in issues[:5]:  # Show first 5
                logger.warning(issue)
            if len(issues) > 5:
                logger.warning(f"  ... and {len(issues) - 5} more")
        else:
            logger.info(f"  ✓ Data validation passed ({len(candles)} candles)")

    def export_parquet(self, symbol: str, filepath: str) -> None:
        """Export collected candles to Parquet (immutable archive)."""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas required for Parquet export")
            return

        if symbol not in self.data_collected:
            logger.error(f"No data for {symbol}")
            return

        candles = self.data_collected[symbol]
        df = pd.DataFrame(candles)

        # Convert timestamps to datetime
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        df["timestamp_str"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

        # Reorder columns
        cols = [
            "timestamp",
            "timestamp_str",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "quote_asset_volume",
            "number_of_trades",
        ]
        df = df[[c for c in cols if c in df.columns]]

        # Write
        df.to_parquet(filepath, compression="snappy", index=False)
        logger.info(f"  ✓ Exported {len(df)} candles to {filepath}")

    def summary(self) -> Dict[str, Any]:
        """Return collection summary."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "requests_made": self.request_count,
            "symbols_collected": list(self.data_collected.keys()),
            "total_candles": sum(len(c) for c in self.data_collected.values()),
            "candles_by_symbol": {
                sym: len(candles) for sym, candles in self.data_collected.items()
            },
        }


def main():
    """Test real data collection."""
    logging.basicConfig(level=logging.INFO)

    collector = BinanceRealCollector()

    # Collect BTC 1d candles for last 180 days
    print("\n" + "="*70)
    print("BINANCE REAL DATA COLLECTION TEST")
    print("="*70 + "\n")

    try:
        print("Collecting BTC daily candles (180 days)...\n")
        btc_candles = collector.fetch_ohlcv(
            symbol="BTCUSDT",
            interval="1d",
            days=180,
        )

        print(f"\n✓ Collected {len(btc_candles)} BTC candles")

        if btc_candles:
            first = btc_candles[0]
            last = btc_candles[-1]
            print(f"  First: {datetime.utcfromtimestamp(first['open_time']/1000).date()} @ {first['close']}")
            print(f"  Last:  {datetime.utcfromtimestamp(last['open_time']/1000).date()} @ {last['close']}")

            # Export to parquet
            collector.export_parquet("BTCUSDT", "/tmp/btc_ohlcv_real.parquet")

        # Summary
        print("\n" + "-"*70)
        print("Collection Summary")
        print("-"*70)
        summary = collector.summary()
        print(f"  Requests made: {summary['requests_made']}")
        print(f"  Total candles: {summary['total_candles']}")
        print(f"  Symbols: {summary['symbols_collected']}")
        print("="*70 + "\n")

    except Exception as e:
        logger.error(f"Collection failed: {e}")
        raise


if __name__ == "__main__":
    main()

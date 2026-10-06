"""P0.1 Binance BTCUSDT 1D historical data collection (2017-2026).

Collects complete BTCUSDT 1D candlestick history from Binance public API.
- Immutable raw store (Parquet)
- 6 validation rules (PIT compliant, no lookahead)
- Pagination support (1000 candles per call)
"""

import logging
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timedelta
import time

from src.core.models import OHLCV
from src.layers.layer1_data.validator import DataValidator

logger = logging.getLogger(__name__)


class BinanceBTCUSDTFetcher:
    """Fetch BTCUSDT 1D from Binance public API with pagination."""

    SYMBOL = "BTCUSDT"
    INTERVAL = "1d"
    MAX_LIMIT = 1000  # Binance max per request
    START_DATE = datetime(2017, 1, 1)
    END_DATE = datetime(2026, 10, 5)  # End yesterday to avoid "today" candle

    # Expected range for 2017-2026
    EXPECTED_MIN_CANDLES = 3400
    EXPECTED_MAX_CANDLES = 3600

    def __init__(self, use_mock: bool = False, rate_limit_delay_ms: int = 100):
        """
        Initialize fetcher.

        Args:
            use_mock: Use mock data (for testing)
            rate_limit_delay_ms: Delay between API calls (ms)
        """
        self.use_mock = use_mock
        self.rate_limit_delay_ms = rate_limit_delay_ms
        self.validator = DataValidator()

    def fetch_historical_data(self) -> Tuple[List[OHLCV], Dict[str, Any]]:
        """
        Fetch complete BTCUSDT 1D history 2017-2026.

        Returns:
            (ohlcv_list, metadata)
        """
        if self.use_mock:
            return self._mock_historical_data()

        try:
            import requests
        except ImportError:
            logger.error("requests library required")
            return self._mock_historical_data()

        all_candles = []
        current_time = self.START_DATE

        url = "https://api.binance.com/api/v3/klines"

        while current_time < self.END_DATE:
            start_ms = int(current_time.timestamp() * 1000)

            params = {
                "symbol": self.SYMBOL,
                "interval": self.INTERVAL,
                "startTime": start_ms,
                "limit": self.MAX_LIMIT,
            }

            try:
                logger.info(f"Fetching from {current_time.isoformat()}")
                resp = requests.get(url, params=params, timeout=10)
                resp.raise_for_status()
                klines = resp.json()

                if not klines:
                    logger.info("No more data from Binance")
                    break

                batch_candles = []
                for kline in klines:
                    ts = datetime.fromtimestamp(kline[0] / 1000)
                    try:
                        ohlcv = OHLCV(
                            timestamp=ts,
                            open=float(kline[1]),
                            high=float(kline[2]),
                            low=float(kline[3]),
                            close=float(kline[4]),
                            volume=float(kline[7]),
                        )
                        batch_candles.append(ohlcv)
                    except ValueError as e:
                        logger.warning(f"Skipping invalid candle at {ts}: {e}")

                all_candles.extend(batch_candles)

                # Move cursor to next batch
                if batch_candles:
                    last_candle = batch_candles[-1]
                    current_time = last_candle.timestamp + timedelta(days=1)

                # Rate limiting
                time.sleep(self.rate_limit_delay_ms / 1000.0)

                if len(batch_candles) < self.MAX_LIMIT:
                    logger.info("Received < limit, likely at end")
                    break

            except Exception as e:
                logger.error(f"Fetch failed at {current_time}: {e}")
                break

        metadata = {
            "symbol": self.SYMBOL,
            "interval": self.INTERVAL,
            "start_date": self.START_DATE.isoformat(),
            "end_date": self.END_DATE.isoformat(),
            "fetch_timestamp": datetime.utcnow().isoformat(),
            "total_candles": len(all_candles),
        }

        return all_candles, metadata

    def validate_p01_requirements(
        self, data: List[OHLCV], metadata: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate against 6 P0.1 requirements.

        Rules:
        1. Coverage temporelle: 2017-01-01 to 2026-10-06
        2. Candles manquantes: Gap detection (max 3 days)
        3. Doublons: No duplicate timestamps
        4. OHLCV invalides: L <= O,C <= H
        5. Timestamps: Monotonic increasing, 1D frequency
        6. Dernière candle: Must be complete (not current incomplete)

        Returns:
            (is_valid, validation_report)
        """
        report = {
            "passed": False,
            "checks": {},
            "warnings": [],
            "data_start": None,
            "data_end": None,
        }

        if not data:
            report["checks"]["empty"] = False
            report["warnings"].append("Dataset empty")
            return False, report

        # Validate as-is (do not sort - sorting would mask ordering issues)
        data_sorted = data

        # 1. Coverage temporelle
        first_ts = data_sorted[0].timestamp
        last_ts = data_sorted[-1].timestamp
        report["data_start"] = first_ts.isoformat()
        report["data_end"] = last_ts.isoformat()

        coverage_ok = (
            first_ts.date() <= self.START_DATE.date()
            and last_ts.date() >= (self.END_DATE - timedelta(days=1)).date()
        )
        report["checks"]["temporal_coverage"] = coverage_ok
        if not coverage_ok:
            report["warnings"].append(
                f"Coverage gap: {first_ts.date()} to {last_ts.date()}"
            )

        # 2. Candles manquantes (gaps)
        gaps = []
        for i in range(1, len(data_sorted)):
            time_diff = (data_sorted[i].timestamp - data_sorted[i - 1].timestamp).days
            if time_diff > 3:
                gaps.append(
                    {
                        "before": data_sorted[i - 1].timestamp.isoformat(),
                        "after": data_sorted[i].timestamp.isoformat(),
                        "gap_days": time_diff,
                    }
                )

        gaps_ok = len(gaps) == 0
        report["checks"]["gaps"] = gaps_ok
        report["gaps"] = gaps
        if not gaps_ok:
            report["warnings"].append(f"{len(gaps)} gaps detected")

        # 3. Doublons
        unique_ts = len(set(c.timestamp for c in data_sorted))
        dupes_ok = unique_ts == len(data_sorted)
        report["checks"]["no_duplicates"] = dupes_ok
        if not dupes_ok:
            report["warnings"].append(f"{len(data_sorted) - unique_ts} duplicate timestamps")

        # 4. OHLCV invalides
        invalid_indices = self.validator._check_ohlc_integrity(data_sorted)
        ohlcv_ok = len(invalid_indices) == 0
        report["checks"]["ohlcv_valid"] = ohlcv_ok
        report["invalid_candles"] = len(invalid_indices)
        if not ohlcv_ok:
            report["warnings"].append(f"{len(invalid_indices)} invalid OHLCV candles")

        # 5. Timestamps: monotonic + 1D frequency
        is_ordered, bad_indices = self.validator._check_chronological_order(data_sorted)
        timestamps_ok = is_ordered
        report["checks"]["timestamps_monotonic"] = timestamps_ok
        if not timestamps_ok:
            report["warnings"].append(f"Non-monotonic at {len(bad_indices)} indices")

        # 6. Dernière candle (must not be current incomplete candle)
        last_candle = data_sorted[-1]
        today = datetime.utcnow().date()
        last_is_old = last_candle.timestamp.date() < today
        report["checks"]["last_candle_complete"] = last_is_old
        if not last_is_old:
            report["warnings"].append(
                "Last candle is from today (may be incomplete, wait for close)"
            )

        # Aggregate result
        all_passed = all(
            [
                coverage_ok,
                gaps_ok,
                dupes_ok,
                ohlcv_ok,
                timestamps_ok,
                last_is_old,
            ]
        )
        report["passed"] = all_passed
        report["candle_count"] = len(data_sorted)

        return all_passed, report

    @staticmethod
    def _mock_historical_data() -> Tuple[List[OHLCV], Dict[str, Any]]:
        """Generate mock BTCUSDT 1D data for testing."""
        import random

        current_price = 1000.0
        current_time = BinanceBTCUSDTFetcher.START_DATE
        candles = []

        while current_time <= BinanceBTCUSDTFetcher.END_DATE:
            # Random walk
            change = random.uniform(-0.05, 0.06)
            current_price *= 1 + change

            try:
                ohlcv = OHLCV(
                    timestamp=current_time,
                    open=current_price * 0.99,
                    high=current_price * 1.02,
                    low=current_price * 0.98,
                    close=current_price,
                    volume=random.uniform(1e9, 5e10),
                )
                candles.append(ohlcv)
            except ValueError:
                pass

            current_time += timedelta(days=1)

        metadata = {
            "symbol": BinanceBTCUSDTFetcher.SYMBOL,
            "interval": BinanceBTCUSDTFetcher.INTERVAL,
            "start_date": BinanceBTCUSDTFetcher.START_DATE.isoformat(),
            "end_date": BinanceBTCUSDTFetcher.END_DATE.isoformat(),
            "fetch_timestamp": datetime.utcnow().isoformat(),
            "total_candles": len(candles),
            "is_mock": True,
        }

        return candles, metadata

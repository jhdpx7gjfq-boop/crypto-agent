"""Point-in-Time (PIT) Replay Engine for backtesting without look-ahead bias."""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from src.data.storage.duckdb import DuckDBStore
from src.layers.layer2_features.store import FeatureStore


class PITReplayEngine:
    """Reconstruct historical feature snapshots as they were known at decision time."""

    def __init__(self, feature_store: FeatureStore, duckdb_store: DuckDBStore):
        self.feature_store = feature_store
        self.ohlcv_data = duckdb_store

    def replay_at_timestamp(
        self, symbol: str, timeframe: str, decision_timestamp: datetime, feature_names: List[str]
    ) -> Dict[str, any]:
        """
        Return all feature values as they would be known at decision_timestamp.

        Only uses data with availability_timestamp <= decision_timestamp.

        Args:
            symbol: Crypto symbol (BTC, ETH, etc.)
            timeframe: Timeframe (1d, 4h, 1h, etc.)
            decision_timestamp: The decision point (PIT filter)
            feature_names: List of features to calculate

        Returns:
            Dict with timestamp, symbol, features dict
            Features include only candles available by decision_timestamp
        """
        candles = self.ohlcv_data.get_candles(symbol, timeframe)
        if not candles:
            return {
                "timestamp": decision_timestamp,
                "symbol": symbol,
                "timeframe": timeframe,
                "features": {},
                "data_points": 0,
            }

        available_candles = [
            c for c in candles
            if self._get_candle_timestamp(c) <= decision_timestamp.timestamp()
        ]

        if not available_candles:
            return {
                "timestamp": decision_timestamp,
                "symbol": symbol,
                "timeframe": timeframe,
                "features": {},
                "data_points": 0,
            }

        closes = [c["close"] for c in available_candles]
        features = {}

        for feature_name in feature_names:
            try:
                closes_copy = closes.copy()

                if feature_name == "rsi_14":
                    from src.layers.layer2_features.technical.rsi import calculate_rsi
                    values = calculate_rsi(closes_copy, period=14)
                elif feature_name == "sma_20":
                    from src.layers.layer2_features.technical.ma import calculate_sma
                    values = calculate_sma(closes_copy, period=20)
                elif feature_name == "ema_12":
                    from src.layers.layer2_features.technical.ma import calculate_ema
                    values = calculate_ema(closes_copy, period=12)
                elif feature_name == "macd_line":
                    from src.layers.layer2_features.technical.macd import calculate_macd
                    values, _, _ = calculate_macd(closes_copy)
                elif feature_name == "bb_width":
                    from src.layers.layer2_features.technical.bb import calculate_bb_width
                    values = calculate_bb_width(closes_copy, period=20, std_dev=2.0)
                elif feature_name == "volatility_hv":
                    from src.layers.layer2_features.technical.volatility import calculate_volatility
                    values = calculate_volatility(closes_copy, period=20, annualize=True)
                else:
                    continue

                features[feature_name] = values[-1] if values else None

            except Exception:
                features[feature_name] = None

        return {
            "timestamp": decision_timestamp,
            "symbol": symbol,
            "timeframe": timeframe,
            "features": features,
            "data_points": len(available_candles),
            "available_until": self._get_candle_timestamp_dt(available_candles[-1]),
        }

    def walk_forward(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        train_period: timedelta,
        test_period: timedelta,
        feature_names: List[str],
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Walk-forward iteration: train on historical, test on future.

        No data leakage between train and test periods.

        Args:
            symbol: Crypto symbol
            timeframe: Timeframe
            start_date: Start of training period
            end_date: End of walk-forward
            train_period: Training window duration
            test_period: Testing window duration
            feature_names: Features to calculate

        Yields:
            (train_snapshots, test_snapshots) per period
        """
        results = []
        current_train_start = start_date

        while current_train_start + train_period + test_period <= end_date:
            train_end = current_train_start + train_period
            test_start = train_end
            test_end = test_start + test_period

            train_snapshots = self._get_snapshots_in_period(
                symbol, timeframe, current_train_start, train_end, feature_names
            )
            test_snapshots = self._get_snapshots_in_period(
                symbol, timeframe, test_start, test_end, feature_names
            )

            if train_snapshots and test_snapshots:
                results.append({
                    "period": len(results) + 1,
                    "train_period": (current_train_start, train_end),
                    "test_period": (test_start, test_end),
                    "train_snapshots": train_snapshots,
                    "test_snapshots": test_snapshots,
                    "train_count": len(train_snapshots),
                    "test_count": len(test_snapshots),
                })

            current_train_start += test_period

        return results

    def _get_snapshots_in_period(
        self, symbol: str, timeframe: str, start: datetime, end: datetime, feature_names: List[str]
    ) -> List[Dict]:
        """Get feature snapshots for each decision point in period."""
        snapshots = []
        current = start

        while current <= end:
            snapshot = self.replay_at_timestamp(symbol, timeframe, current, feature_names)
            if snapshot["data_points"] > 0:
                snapshots.append(snapshot)
            current += timedelta(days=1)

        return snapshots

    def _get_candle_timestamp(self, candle: Dict) -> float:
        """Extract numeric timestamp from candle dict."""
        if isinstance(candle.get("timestamp"), (int, float)):
            return float(candle["timestamp"])
        if isinstance(candle.get("timestamp"), datetime):
            return candle["timestamp"].timestamp()
        return 0.0

    def _get_candle_timestamp_dt(self, candle: Dict) -> datetime:
        """Extract datetime from candle dict."""
        ts = self._get_candle_timestamp(candle)
        return datetime.fromtimestamp(ts)

"""Feature Store — centralized feature management."""

import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from src.core.models import OHLCV
from src.core.config import Config


logger = logging.getLogger(__name__)


@dataclass
class FeatureVector:
    """Single observation with all computed features."""

    timestamp: datetime
    asset: str
    close: float
    sma20: Optional[float] = None
    sma50: Optional[float] = None
    volatility20: Optional[float] = None
    rsi14: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    momentum: Optional[float] = None
    volume_ma20: Optional[float] = None
    custom_features: Dict[str, Any] = None

    def __post_init__(self):
        if self.custom_features is None:
            self.custom_features = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FeatureVector":
        """Construct from dictionary."""
        d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        return cls(**d)


class FeatureStore:
    """
    Centralized feature management.

    Responsibilities:
    - Compute features from OHLCV
    - Cache features in memory
    - Persist to Parquet
    - Load from disk
    """

    def __init__(self, feature_store_path: str = None):
        self.store_path = feature_store_path or str(Config.FEATURE_STORE_PATH)
        self._cache: Dict[str, List[FeatureVector]] = {}
        self.config = Config

    def compute_features(
        self,
        asset: str,
        ohlcv_data: List[OHLCV],
        compute_momentum: bool = True,
        compute_custom: bool = False,
    ) -> List[FeatureVector]:
        """
        Compute all features for an asset's OHLCV data.

        Args:
            asset: Asset identifier
            ohlcv_data: OHLCV candles (ordered by time)
            compute_momentum: Include momentum features
            compute_custom: Include custom features (if implemented)

        Returns:
            List of FeatureVector objects
        """

        if not ohlcv_data or len(ohlcv_data) < 50:
            logger.warning(f"{asset}: Insufficient data for feature computation (need 50+ candles)")
            return []

        features = []

        # Simple Moving Averages
        sma20 = self._compute_sma(ohlcv_data, 20)
        sma50 = self._compute_sma(ohlcv_data, 50)

        # Volatility
        volatility = self._compute_volatility(ohlcv_data, 20)

        # RSI
        rsi = self._compute_rsi(ohlcv_data, 14)

        # MACD
        macd_line, macd_signal, macd_hist = self._compute_macd(ohlcv_data)

        # Momentum (if requested)
        momentum = None
        if compute_momentum:
            momentum = self._compute_momentum(ohlcv_data, 14)

        # Volume MA
        volume_ma = self._compute_volume_ma(ohlcv_data, 20)

        # Build feature vectors (aligned to OHLCV indices)
        for i, candle in enumerate(ohlcv_data):
            fv = FeatureVector(
                timestamp=candle.timestamp,
                asset=asset,
                close=candle.close,
                sma20=sma20[i] if i < len(sma20) else None,
                sma50=sma50[i] if i < len(sma50) else None,
                volatility20=volatility[i] if i < len(volatility) else None,
                rsi14=rsi[i] if i < len(rsi) else None,
                macd_line=macd_line[i] if i < len(macd_line) else None,
                macd_signal=macd_signal[i] if i < len(macd_signal) else None,
                macd_histogram=macd_hist[i] if i < len(macd_hist) else None,
                momentum=momentum[i] if momentum and i < len(momentum) else None,
                volume_ma20=volume_ma[i] if i < len(volume_ma) else None,
            )
            features.append(fv)

        logger.info(f"{asset}: Computed features for {len(features)} candles")
        self._cache[asset] = features

        return features

    def save_features_parquet(self, asset: str, features: List[FeatureVector]) -> str:
        """Save features to Parquet file."""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas required for Parquet operations")
            return ""

        try:
            data = [fv.to_dict() for fv in features]
            df = pd.DataFrame(data)

            # Ensure timestamp is datetime type
            df["timestamp"] = pd.to_datetime(df["timestamp"])

            filepath = f"{self.store_path}/{asset}_features.parquet"
            df.to_parquet(filepath, index=False)

            logger.info(f"Saved {len(features)} feature vectors to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Parquet save failed: {e}")
            return ""

    def load_features_parquet(self, asset: str) -> List[FeatureVector]:
        """Load features from Parquet file."""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas required for Parquet operations")
            return []

        try:
            filepath = f"{self.store_path}/{asset}_features.parquet"
            df = pd.read_parquet(filepath)

            features = []
            for _, row in df.iterrows():
                d = row.to_dict()
                fv = FeatureVector.from_dict(d)
                features.append(fv)

            logger.info(f"Loaded {len(features)} feature vectors from {filepath}")
            self._cache[asset] = features
            return features

        except Exception as e:
            logger.warning(f"Parquet load failed for {asset}: {e}")
            return []

    def save_features_json(self, asset: str, features: List[FeatureVector]) -> str:
        """Save features to JSON (human-readable)."""
        try:
            data = [fv.to_dict() for fv in features]

            filepath = f"{self.store_path}/{asset}_features.json"
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(features)} features to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"JSON save failed: {e}")
            return ""

    @staticmethod
    def _compute_sma(ohlcv: List[OHLCV], window: int) -> List[float]:
        """Compute SMA (padded to match length)."""
        if len(ohlcv) < window:
            return []

        sma = []
        for i in range(len(ohlcv)):
            if i < window - 1:
                sma.append(None)
            else:
                avg = sum(c.close for c in ohlcv[i - window + 1 : i + 1]) / window
                sma.append(avg)

        return sma

    @staticmethod
    def _compute_volatility(ohlcv: List[OHLCV], window: int) -> List[float]:
        """Compute rolling volatility (std dev)."""
        if len(ohlcv) < window:
            return []

        vol = []
        for i in range(len(ohlcv)):
            if i < window - 1:
                vol.append(None)
            else:
                prices = [c.close for c in ohlcv[i - window + 1 : i + 1]]
                mean = sum(prices) / len(prices)
                variance = sum((p - mean) ** 2 for p in prices) / len(prices)
                std = variance ** 0.5
                vol.append(std)

        return vol

    @staticmethod
    def _compute_rsi(ohlcv: List[OHLCV], period: int = 14) -> List[float]:
        """Compute RSI."""
        if len(ohlcv) < period + 1:
            return []

        rsi = []
        closes = [c.close for c in ohlcv]

        for i in range(len(closes)):
            if i < period:
                rsi.append(None)
            else:
                gains = sum(max(closes[j] - closes[j - 1], 0) for j in range(i - period + 1, i + 1))
                losses = sum(
                    max(closes[j - 1] - closes[j], 0) for j in range(i - period + 1, i + 1)
                )

                avg_gain = gains / period
                avg_loss = losses / period

                if avg_loss == 0:
                    rs = 0 if avg_gain == 0 else float("inf")
                    rsi_val = 100 if rs == float("inf") else 50
                else:
                    rs = avg_gain / avg_loss
                    rsi_val = 100 - (100 / (1 + rs))

                rsi.append(rsi_val)

        return rsi

    @staticmethod
    def _compute_macd(ohlcv: List[OHLCV]) -> tuple:
        """Compute MACD."""
        if len(ohlcv) < 26:
            return [], [], []

        closes = [c.close for c in ohlcv]

        # EMA approximation (simple for now)
        ema12 = FeatureStore._compute_ema(closes, 12)
        ema26 = FeatureStore._compute_ema(closes, 26)

        # MACD line
        macd = []
        for i in range(len(ohlcv)):
            if i < 25 or i >= len(ema12) or i >= len(ema26):
                macd.append(None)
            else:
                macd.append(ema12[i] - ema26[i])

        # Signal (EMA of MACD)
        signal = FeatureStore._compute_ema([m for m in macd if m is not None], 9)

        # Histogram
        histogram = []
        for i in range(len(macd)):
            if macd[i] is None or i >= len(signal):
                histogram.append(None)
            else:
                histogram.append(macd[i] - signal[i])

        return macd, signal, histogram

    @staticmethod
    def _compute_ema(values: List[float], period: int) -> List[float]:
        """Exponential Moving Average."""
        if len(values) < period:
            return []

        ema = []
        multiplier = 2 / (period + 1)

        for i in range(len(values)):
            if i < period - 1:
                ema.append(None)
            elif i == period - 1:
                avg = sum(values[: i + 1]) / len(values[: i + 1])
                ema.append(avg)
            else:
                ema_val = (values[i] - ema[i - 1]) * multiplier + ema[i - 1]
                ema.append(ema_val)

        return ema

    @staticmethod
    def _compute_momentum(ohlcv: List[OHLCV], period: int = 14) -> List[float]:
        """Momentum = price change over period."""
        if len(ohlcv) < period:
            return []

        momentum = []
        for i in range(len(ohlcv)):
            if i < period - 1:
                momentum.append(None)
            else:
                price_change = ohlcv[i].close - ohlcv[i - period + 1].close
                pct_change = (price_change / ohlcv[i - period + 1].close) * 100
                momentum.append(pct_change)

        return momentum

    @staticmethod
    def _compute_volume_ma(ohlcv: List[OHLCV], window: int = 20) -> List[float]:
        """Volume moving average."""
        if len(ohlcv) < window:
            return []

        vol_ma = []
        for i in range(len(ohlcv)):
            if i < window - 1:
                vol_ma.append(None)
            else:
                avg_vol = sum(c.volume for c in ohlcv[i - window + 1 : i + 1]) / window
                vol_ma.append(avg_vol)

        return vol_ma

"""Feature Store: Calculate and manage versioned features with validation."""

from datetime import datetime
from typing import Dict, List, Optional
from src.data.storage.duckdb import DuckDBStore
from src.layers.layer2_features.contract import FeatureContract
from src.layers.layer2_features.technical.rsi import calculate_rsi
from src.layers.layer2_features.technical.ma import calculate_sma, calculate_ema, calculate_wma
from src.layers.layer2_features.technical.macd import calculate_macd
from src.layers.layer2_features.technical.bb import calculate_bb_width, calculate_bollinger_bands
from src.layers.layer2_features.technical.volatility import calculate_volatility, calculate_parkinson_volatility


class FeatureStore:
    """Feature calculation engine with contract validation."""

    def __init__(self, duckdb_store: DuckDBStore):
        self.ohlcv_data = duckdb_store
        self.contracts: Dict[str, FeatureContract] = {}
        self._feature_calculators = {
            "calculate_rsi": calculate_rsi,
            "calculate_sma": calculate_sma,
            "calculate_ema": calculate_ema,
            "calculate_wma": calculate_wma,
            "calculate_macd": calculate_macd,
            "calculate_bb_width": calculate_bb_width,
            "calculate_bollinger_bands": calculate_bollinger_bands,
            "calculate_volatility": calculate_volatility,
            "calculate_parkinson_volatility": calculate_parkinson_volatility,
        }

    def register_contract(self, contract: FeatureContract) -> None:
        """Register a feature contract."""
        self.contracts[contract.name] = contract

    def calculate_feature(
        self,
        symbol: str,
        timeframe: str,
        feature_name: str,
        as_of_timestamp: Optional[datetime] = None,
        **calc_kwargs
    ) -> Dict[str, List[float]]:
        """
        Calculate feature for symbol up to as_of_timestamp (PIT-compatible).

        Args:
            symbol: Crypto symbol (BTC, ETH, etc.)
            timeframe: Timeframe (1d, 4h, 1h, etc.)
            feature_name: Feature name (rsi_14, sma_20, etc.)
            as_of_timestamp: Point-in-time cutoff (optional)
            **calc_kwargs: Additional calculation parameters

        Returns:
            Dict with 'timestamps', 'closes' (input), and feature values
        """
        if feature_name not in self.contracts:
            raise ValueError(f"Unknown feature: {feature_name}")

        contract = self.contracts[feature_name]

        candles = self.ohlcv_data.get_candles(symbol, timeframe)
        if not candles:
            raise ValueError(f"No data for {symbol} {timeframe}")

        closes = [c["close"] for c in candles]
        timestamps = [c["timestamp"] for c in candles]

        if feature_name == "rsi_14":
            period = contract.parameters.get("period", 14)
            values = calculate_rsi(closes, period=period)
        elif feature_name == "sma_20":
            period = contract.parameters.get("period", 20)
            values = calculate_sma(closes, period=period)
        elif feature_name == "ema_12":
            period = contract.parameters.get("period", 12)
            values = calculate_ema(closes, period=period)
        elif feature_name == "macd_line":
            fast = contract.parameters.get("fast", 12)
            slow = contract.parameters.get("slow", 26)
            signal = contract.parameters.get("signal", 9)
            macd_line, signal_line, histogram = calculate_macd(closes, fast=fast, slow=slow, signal=signal)
            values = macd_line
        elif feature_name == "bb_width":
            period = contract.parameters.get("period", 20)
            std_dev = contract.parameters.get("std_dev", 2.0)
            values = calculate_bb_width(closes, period=period, std_dev=std_dev)
        elif feature_name == "volatility_hv":
            period = contract.parameters.get("period", 20)
            values = calculate_volatility(closes, period=period, annualize=True)
        else:
            raise ValueError(f"No calculator for feature: {feature_name}")

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "feature_name": feature_name,
            "timestamps": timestamps,
            "closes": closes,
            "values": values,
        }

    def validate_feature(self, feature_name: str, values: List[float]) -> tuple[bool, List[int]]:
        """
        Validate feature values against contract.

        Args:
            feature_name: Feature name
            values: Feature values to validate

        Returns:
            (is_valid, invalid_indices)
        """
        if feature_name not in self.contracts:
            raise ValueError(f"Unknown feature: {feature_name}")

        contract = self.contracts[feature_name]
        return contract.validate_series(values)

    def get_feature_info(self, feature_name: str) -> Optional[FeatureContract]:
        """Get feature contract info."""
        return self.contracts.get(feature_name)

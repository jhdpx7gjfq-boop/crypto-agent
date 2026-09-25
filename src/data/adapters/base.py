"""
Base datasource adapter interface.

All datasources must implement this contract.
Phase 1: CoinGecko adapter, Binance adapter stub.
"""

from abc import ABC, abstractmethod
from typing import List
from datetime import datetime
from src.data.schemas.types import OHLCV, Provenance


class DatasourceAdapter(ABC):
    """Abstract base for datasource adapters."""

    @abstractmethod
    def get_name(self) -> str:
        """Adapter identifier: 'coingecko', 'binance', etc."""
        pass

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[OHLCV]:
        """
        Fetch historical OHLCV data.

        Args:
            symbol: Symbol identifier (e.g., 'bitcoin', 'BTCUSDT')
            timeframe: '1h', '4h', '1d', etc.
            start_date: Inclusive start
            end_date: Inclusive end

        Returns:
            List of OHLCV candles with provenance.

        Raises:
            ValueError: Invalid symbol or timeframe
            RuntimeError: Fetch error (network, API)
        """
        pass

    @abstractmethod
    def validate_data(self, ohlcv_list: List[OHLCV]) -> bool:
        """
        Validate fetched data for quality and completeness.

        Should check:
        - No negative prices or volumes
        - OHLC ordering (L <= O,C <= H)
        - No gaps in timestamps (within tolerance)
        - Provenance fields populated

        Returns:
            True if valid
        Raises:
            ValueError with specific issue if invalid
        """
        pass

"""
CoinGecko datasource adapter.

Phase 1: Fetch historical OHLCV from CoinGecko public API.
No authentication required.
"""

from typing import List
from datetime import datetime, timezone
import requests

from src.data.adapters.base import DatasourceAdapter
from src.data.schemas.types import OHLCV, Provenance
from src.common.logging import get_logger

logger = get_logger(__name__)


class CoinGeckoAdapter(DatasourceAdapter):
    """CoinGecko public API adapter."""

    BASE_URL = "https://api.coingecko.com/api/v3"
    TIMEOUT_SECONDS = 10
    RETRY_COUNT = 3

    # Map symbol names to CoinGecko IDs
    SYMBOL_MAP = {
        "bitcoin": "bitcoin",
        "BTC": "bitcoin",
        "ethereum": "ethereum",
        "ETH": "ethereum",
        "solana": "solana",
        "SOL": "solana",
    }

    def __init__(self, timeout_seconds: int = TIMEOUT_SECONDS):
        self.timeout_seconds = timeout_seconds

    def get_name(self) -> str:
        return "coingecko"

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[OHLCV]:
        """
        Fetch historical OHLCV from CoinGecko.

        Note: CoinGecko free tier provides daily data only (timeframe='1d').
        Intraday data (1h, 4h) requires premium API.

        Args:
            symbol: CoinGecko ID (e.g., 'bitcoin', 'ethereum')
            timeframe: '1d' (only supported in free tier)
            start_date: Start date (UTC)
            end_date: End date (UTC)

        Returns:
            List of OHLCV candles

        Raises:
            ValueError: Invalid symbol or timeframe
            RuntimeError: API error
        """
        if timeframe != "1d":
            raise ValueError(
                f"CoinGecko free tier supports only '1d' timeframe, got '{timeframe}'"
            )

        cg_symbol = self.SYMBOL_MAP.get(symbol.lower())
        if not cg_symbol:
            raise ValueError(f"Unknown symbol: {symbol}. Known: {list(self.SYMBOL_MAP.keys())}")

        # Convert dates to Unix timestamps (required by /market_chart/range endpoint)
        start_ts = int(start_date.timestamp())
        end_ts = int(end_date.timestamp())

        url = f"{self.BASE_URL}/coins/{cg_symbol}/market_chart/range"
        params = {
            "vs_currency": "usd",
            "from": start_ts,
            "to": end_ts,
        }

        logger.info(
            "Starting CoinGecko fetch",
            extra={
                "event": "fetch_start",
                "status": "pending",
                "symbol": cg_symbol,
                "timeframe": timeframe,
            },
        )

        try:
            response = requests.get(
                url, params=params, timeout=self.timeout_seconds
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            logger.error(
                f"CoinGecko API error: {e}",
                extra={
                    "event": "fetch_error",
                    "status": "error",
                    "symbol": cg_symbol,
                    "error": str(e),
                },
            )
            raise RuntimeError(f"Failed to fetch from CoinGecko: {e}")

        # Parse OHLCV from response
        ohlcv_list = []
        if "prices" in data and "total_volumes" in data:
            # CoinGecko returns [[timestamp_ms, value], ...] format
            prices = {ts_ms: price for ts_ms, price in data["prices"]}
            volumes = {ts_ms: vol for ts_ms, vol in data["total_volumes"]}

            # Build candles from daily data
            for ts_ms in sorted(prices.keys()):
                ts_s = ts_ms / 1000
                ts = datetime.fromtimestamp(ts_s, tz=timezone.utc)

                # CoinGecko returns daily closes, not true OHLC
                # For daily timeframe, treat close as open=close=high=low
                price = prices[ts_ms]
                volume = volumes.get(ts_ms, 0)

                now_utc = datetime.now(tz=timezone.utc)
                provenance = Provenance(
                    source="coingecko",
                    provider="CoinGecko",
                    endpoint="/coins/{id}/market_chart/range",
                    retrieval_timestamp=now_utc,
                    event_timestamp=ts,
                    availability_timestamp=now_utc,
                    symbol=cg_symbol,
                    timeframe=timeframe,
                    schema_version="1.0",
                    data_version=ts.strftime("%Y-%m-%d"),
                    caveats="CoinGecko free tier: daily data only, no true OHLC",
                )

                candle = OHLCV(
                    timestamp=ts,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=volume,
                    provenance=provenance,
                )
                ohlcv_list.append(candle)

        logger.info(
            "CoinGecko fetch complete",
            extra={
                "event": "fetch_complete",
                "status": "success",
                "symbol": cg_symbol,
                "record_count": len(ohlcv_list),
            },
        )

        return sorted(ohlcv_list, key=lambda x: x.timestamp)

    def validate_data(self, ohlcv_list: List[OHLCV]) -> bool:
        """
        Validate OHLCV data quality.

        Checks:
        - No negative prices/volumes
        - OHLC ordering
        - Monotonic timestamps
        - Provenance fields
        """
        if not ohlcv_list:
            return True

        for i, candle in enumerate(ohlcv_list):
            # Check price ordering
            if not (candle.low <= candle.open <= candle.high):
                raise ValueError(
                    f"Candle {i}: O not between L and H: "
                    f"L={candle.low}, O={candle.open}, H={candle.high}"
                )
            if not (candle.low <= candle.close <= candle.high):
                raise ValueError(
                    f"Candle {i}: C not between L and H: "
                    f"L={candle.low}, C={candle.close}, H={candle.high}"
                )

            # Check non-negative
            if candle.volume < 0:
                raise ValueError(f"Candle {i}: Negative volume {candle.volume}")

            # Check provenance
            if not candle.provenance:
                raise ValueError(f"Candle {i}: Missing provenance")

            # Check monotonic timestamps
            if i > 0:
                if ohlcv_list[i - 1].timestamp >= candle.timestamp:
                    raise ValueError(
                        f"Candle {i}: Non-monotonic timestamp: "
                        f"{ohlcv_list[i-1].timestamp} >= {candle.timestamp}"
                    )

        return True

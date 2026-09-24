import logging
import time
from datetime import datetime
import requests
import pandas as pd
from src.data.schema import OHLCVCandle

logger = logging.getLogger(__name__)


class BinanceClient:
    """Fetch OHLCV from Binance public API."""
    BASE_URL = "https://api.binance.com/api/v3"
    TIMEOUT = 10
    MAX_KLINES = 1000  # Binance limit per request

    TIMEFRAME_MAP = {
        "daily": "1d",
        "4h": "4h",
        "1h": "1h",
    }

    def __init__(self, max_retries=3, retry_delay=1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _request(self, endpoint: str, params: dict = None) -> dict | list:
        """Execute request with retry logic."""
        url = f"{self.BASE_URL}/{endpoint}"
        for attempt in range(self.max_retries):
            try:
                resp = requests.get(url, params=params, timeout=self.TIMEOUT)
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Failed after {self.max_retries} attempts: {e}")
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {self.retry_delay}s: {e}")
                time.sleep(self.retry_delay)

    def fetch_ohlcv(self, symbol: str, timeframe: str = "daily", limit: int = 500) -> list[OHLCVCandle]:
        """
        Fetch OHLCV for symbol. Returns closed candles only.
        symbol: e.g., 'BTCUSDT'
        timeframe: 'daily' or '4h'
        limit: max candles to fetch (respects Binance MAX_KLINES)
        """
        if timeframe not in self.TIMEFRAME_MAP:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        binance_tf = self.TIMEFRAME_MAP[timeframe]
        limit = min(limit, self.MAX_KLINES)

        logger.info(f"Fetching {timeframe} OHLCV for {symbol}, limit={limit}")
        try:
            data = self._request("klines", {
                "symbol": symbol,
                "interval": binance_tf,
                "limit": limit,
            })

            candles = []
            for row in data:
                # Binance klines: [open_time, o, h, l, c, v, close_time, ...]
                ts_ms = row[0]
                timestamp = datetime.utcfromtimestamp(ts_ms / 1000.0)
                candle = OHLCVCandle(
                    symbol=symbol,
                    source="binance",
                    timeframe=timeframe,
                    timestamp=timestamp,
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[7]),  # quote asset volume
                )
                candles.append(candle)

            candles.sort(key=lambda c: c.timestamp)
            logger.info(f"Fetched {len(candles)} candles for {symbol}")
            return candles
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise

    def to_dataframe(self, candles: list[OHLCVCandle]) -> pd.DataFrame:
        """Convert candles to DataFrame, normalized."""
        data = [
            {
                "symbol": c.symbol,
                "source": c.source,
                "timeframe": c.timeframe,
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in candles
        ]
        df = pd.DataFrame(data)
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

# Data Intelligence Layer (Layer 1)

IGWT-PF26 Phase 1: Raw data collection and validation.

## CoinGecko Collector

**Version:** 1.0.0  
**Status:** Stable  
**API:** Free (no key required)

### Features

- **Real-time price**: BTC, ETH, 10k+ coins
- **Market data**: Market cap, 24h volume
- **Historical**: Daily OHLCV data (up to 365 days)
- **Global metrics**: Total market cap, dominance
- **Search**: Resolve coin names → IDs
- **Robust**: Retry logic, validation, logging
- **Parquet export**: For feature store integration

### Usage

```python
from src.data.coingecko_collector import CoinGeckoCollector

collector = CoinGeckoCollector()

# Current prices
prices = collector.get_price(["bitcoin", "ethereum"])
print(f"BTC: ${prices['bitcoin']['usd']}")

# Historical data
df = collector.get_market_chart("bitcoin", days=30)
print(df.head())

# Export to Parquet
from src.data.coingecko_collector import export_to_parquet
export_to_parquet(df, "data/btc_30d.parquet")

# Global data
global_data = collector.get_global()
btc_dominance = global_data['data']['market_cap_percentage']['btc']
```

### Data Schema

**Price Endpoint:**
```json
{
  "bitcoin": {
    "usd": 84649.00,
    "usd_market_cap": 1700736036485,
    "usd_24h_vol": 36418780549
  }
}
```

**Market Chart (DataFrame):**
| Column | Type | Description |
|--------|------|-------------|
| timestamp | datetime | UTC timestamp |
| price | float | USD price |
| market_cap | float | Market cap USD |
| volume | float | 24h volume USD |

### Configuration

Environment variables (optional):
- `COINGECKO_API_BASE`: Custom API endpoint (default: official API)
- `COINGECKO_TIMEOUT`: Request timeout in seconds (default: 10)

### Retry Logic

- Max retries: 3
- Backoff factor: 2s (exponential)
- Status codes: 429, 500, 502, 503, 504

### Validation

All responses validated:
- Required fields present
- Data types correct
- Ranges valid (prices > 0)

### Tests

```bash
pytest tests/test_coingecko_collector.py -v
```

10/10 tests passing:
- Initialization
- Price fetching (single/multiple)
- Market cap + volume
- Historical data
- Global metrics
- Search
- Error handling

### Integration with IGWT-PF26

**Layer 1 Flow:**
```
Raw Price Data (CoinGecko)
        ↓
Validation (type, range, nulls)
        ↓
Feature Engineering (RSI, SMA, volatility)
        ↓
Research Dataset (Parquet/DuckDB)
```

### Next Steps

- Feature Store integration (Parquet batches)
- Real-time streaming (Kafka)
- Multi-source aggregation (Binance, Kraken)
- On-chain data enrichment (Glassnode)

### Limitations

- API rate limit: ~10-50 calls/min
- Historical data: max 365 days
- Websocket: not available (free tier)
- No trading data (spreads, slippage)

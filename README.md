# IGWT-AIOS — Crypto Market Scanner

Intelligent market analysis and opportunity detection for cryptocurrency quantitative research.

**Project Status:** P0.1 (Data Foundation) — In Development  
**Scope:** Research-only. No trading execution. Human decision-making required.

---

## Overview

IGWT-AIOS is the data intelligence layer for IGWT (Intelligent Growth Without Trap). It scans Top 500 cryptocurrencies to identify market structures, potential accumulation zones, and asymmetric risk/reward opportunities.

### Current Capabilities
- ✅ P0.1: CoinGecko universe metadata (Top 500)
- ✅ P0.1: Binance OHLCV (Daily + 4H)
- ✅ P0.1: Parquet storage + validation
- ✅ P0.1: Look-ahead bias prevention
- ✅ P0.2: Universe filtering (market cap, volume, data availability, quality)
- 🚧 P0.3: Bottom detection
- 🚧 P0.4: Wyckoff Spring detection
- 🚧 P0.8: Watchlist output

### Legacy Code
The original `main.py` is a simple BTC alert bot (Telegram). It remains functional but is not part of IGWT-AIOS.

---

## Data Contract

All data is standardized per [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md):

### OHLCV Columns
```
symbol, source, timeframe, timestamp, open, high, low, close, volume
```

### Metadata
```
symbol, name, market_cap, fdv, circulating_supply, total_supply, volume_24h, rank
```

**Validation:**
- No duplicates (symbol, timeframe, timestamp)
- Monotonic timestamps (strictly increasing)
- OHLC consistency (high ≥ max(OHLC), low ≤ min(OHLC))
- No look-ahead bias (signal at T uses only data where timestamp ≤ T)

---

## Setup

### Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # for testing
```

### Configuration

Copy or create `config/scanner.yml` (default included):

```yaml
data:
  universe:
    source: coingecko
    max_tokens: 500
  binance:
    timeframes: [daily, 4h]
  storage:
    backend: parquet
    data_dir: data
```

### Usage (Data Layer Only)

```python
from src.data import CoinGeckoClient, BinanceClient, ParquetStore

# Fetch universe metadata
cg = CoinGeckoClient()
tokens = cg.fetch_top_500()  # → List[TokenMetadata]

# Fetch OHLCV
binance = BinanceClient()
candles = binance.fetch_ohlcv("BTCUSDT", timeframe="daily", limit=500)

# Store to Parquet
store = ParquetStore()
df = binance.to_dataframe(candles)
store.save_ohlcv("BTCUSDT", "daily", df)

# Load and validate
df_loaded = store.load_ohlcv("BTCUSDT", "daily")
assert store.validate_no_duplicates(df_loaded)
assert store.validate_monotonic_timestamps(df_loaded)
```

---

## Tests

```bash
# All tests
pytest tests/ -v

# By module
pytest tests/test_data_schema.py -v
pytest tests/test_data_clients.py -v
pytest tests/test_data_store.py -v
pytest tests/test_lookahead_prevention.py -v
```

**Test Coverage:**
- ✅ Data schema validation (OHLCV, metadata)
- ✅ CoinGecko client (fetch, filtering)
- ✅ Binance client (OHLCV, timeframe conversion)
- ✅ Parquet storage (save, load, validation)
- ✅ Look-ahead prevention (historical boundary, window operations)
- ✅ Original BTC alert bot (backward compatible)

Current: **40 tests passing**

---

## Documentation

- [docs/DATA_CONTRACT.md](docs/DATA_CONTRACT.md) — Data schema, validation rules, look-ahead prevention
- [docs/research/SPRING-SPEC-001.md](docs/research/SPRING-SPEC-001.md) — Wyckoff Spring specification (RESEARCH_CANDIDATE)

---

## Project Structure

```
crypto-agent/
├── src/
│   ├── data/
│   │   ├── schema.py           # Pydantic models (OHLCVCandle, TokenMetadata)
│   │   ├── coingecko_client.py # CoinGecko API client
│   │   ├── binance_client.py   # Binance API client
│   │   ├── store.py            # Parquet storage + validation
│   │   └── __init__.py
│   ├── scanner/                # (P0.2+)
│   └── __init__.py
├── tests/
│   ├── test_data_schema.py     # Schema validation tests
│   ├── test_data_clients.py    # Client mocking tests
│   ├── test_data_store.py      # Storage tests
│   ├── test_lookahead_prevention.py # Bias prevention tests
│   ├── test_main.py            # Original BTC bot tests
│   └── __init__.py
├── docs/
│   ├── DATA_CONTRACT.md        # Data standardization
│   └── research/
│       └── SPRING-SPEC-001.md  # Spring detection spec
├── config/
│   └── scanner.yml             # Configuration
├── data/                       # (runtime) OHLCV + metadata storage
│   ├── ohlcv/
│   ├── metadata/
├── main.py                     # Original BTC alert bot
├── requirements.txt
├── requirements-dev.txt
├── pytest.ini
├── .gitignore
└── README.md
```

---

## Roadmap

### ✅ P0.1 — Data Foundation (DONE)
- CoinGecko Top 500 metadata
- Binance Daily + 4H OHLCV
- Parquet storage
- Look-ahead bias prevention

### 🚧 P0.2 — Universe Filter
- Liquidity filtering
- Volume constraints
- Data availability check

### 🚧 P0.3 — Bottom Detector
- Drawdown identification
- Base / range detection
- Momentum confirmation

### 🚧 P0.4 — Wyckoff Spring Detector
- Support identification
- Liquidity sweep detection
- Reclaim confirmation

### 🚧 P0.5 — Reclaim & BOS
- Break of structure
- Swing high/low detection
- Market structure

### 🚧 P0.6 — Relative Strength
- Simple momentum filter
- Confirmation only (not primary signal)

### 🚧 P0.7 — Risk & Invalidation
- Invalidation levels
- Risk/reward ratios
- Signal quality scoring

### 🚧 P0.8 — Watchlist Output
- Daily markdown table
- Signal export
- Manual export to wallet tools

### ✋ P1+ — Validation & X20
- Backtesting framework
- Walk-forward validation
- X20 Radar integration

---

## Legacy: Original BTC Alert Bot

The original `main.py` polls BTC/USD from CoinGecko and sends Telegram alerts. It is **not** part of IGWT-AIOS but remains functional for backward compatibility.

**To use:**
```bash
pip install -r requirements.txt
BOT_TOKEN=... CHAT_ID=... python main.py
```

---

## Status

- **Data Layer:** ✅ Complete & tested
- **Detectors:** 🚧 Pending P0.2–P0.8
- **Validation:** ⏳ Pending after P0.8
- **Production:** ✋ Not ready. All signals are RESEARCH_CANDIDATE.

---

## License & Attribution

IGWT-AIOS is a quantitative research framework.

All work by [Claude Code](https://claude.ai/code).

---

**⚠️ Disclaimer:** This system provides research signals only. No financial advice. All investment decisions remain the responsibility of the user.

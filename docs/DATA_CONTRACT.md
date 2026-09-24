# IGWT-AIOS Data Contract — P0.1

**Version:** 1.0  
**Status:** ACTIVE  
**Last Updated:** 2026-09-24

---

## Overview

The data layer standardizes all OHLCV and metadata to enable rigorous signal detection and backtesting without look-ahead bias.

---

## OHLCV Contract

### Required Columns

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `symbol` | str | Non-empty, immutable | e.g., `BTCUSDT`, `ETHUSDT` |
| `source` | str | One of: `binance`, `coingecko` | Data origin |
| `timeframe` | str | One of: `daily`, `4h`, `1h` | Candle period |
| `timestamp` | datetime | UTC, tz-aware preferred | Candle open time |
| `open` | float | `> 0` | Opening price |
| `high` | float | `>= max(open, close, low)` | Highest price in period |
| `low` | float | `<= min(open, close, high)` | Lowest price in period |
| `close` | float | `> 0` | Closing price |
| `volume` | float | `>= 0` | Trading volume in quote asset |

### Invariants

- **OHLC Relationship:** `high >= max(open, close, low)` AND `low <= min(open, close, high)`
- **Monotonic Timestamps:** Within a (symbol, source, timeframe) group, timestamps must be strictly increasing
- **No Duplicates:** No two candles share the same (symbol, source, timeframe, timestamp)
- **No Gaps (within available data):** If T and T+N exist, all intermediate T+1...T+N-1 should exist for continuous feeds
- **Closed Candles Only:** All candles are closed (not real-time / in-progress)
- **Immutable History:** Once stored, historical candles are not modified

---

## Metadata Contract

### Required Columns

| Column | Type | Constraints | Description |
|--------|------|-----------|-------------|
| `symbol` | str | Non-empty | e.g., `BTC` |
| `name` | str | Non-empty | e.g., `Bitcoin` |
| `source` | str | `coingecko` | Metadata origin |
| `timestamp` | datetime | UTC | Snapshot time |
| `market_cap` | float \| None | `>= 0` or None | USD, may be unavailable |
| `fdv` | float \| None | `>= 0` or None | Fully diluted value, USD |
| `circulating_supply` | float \| None | `>= 0` or None | Tokens in circulation |
| `total_supply` | float \| None | `>= 0` or None | Total tokens (including locked) |
| `volume_24h` | float \| None | `>= 0` or None | 24h trading volume, USD |
| `rank` | int \| None | `>= 1` or None | Market cap rank |

### Invariants

- **FDV >= Market Cap:** If both available, `fdv >= market_cap`
- **Supply Logic:** `circulating_supply <= total_supply` (if both available)
- **Immutable Snapshots:** Metadata is a point-in-time snapshot; corrections create new rows

---

## Storage Format

### Parquet Organization

```
data/
├── ohlcv/
│   ├── BTCUSDT_daily.parquet
│   ├── BTCUSDT_4h.parquet
│   ├── ETHUSDT_daily.parquet
│   └── ...
└── metadata/
    └── universe.parquet
```

- **Compression:** Snappy
- **Encoding:** UTF-8 for strings
- **Timestamps:** Stored as UTC ISO-8601, loaded as `datetime64[ns]`

---

## Look-Ahead Prevention

### Rule

**Any signal computed at timestamp T must use only data where `timestamp <= T`.**

### Implementation

1. When computing indicators/scores for candle at T:
   - Window includes all data up to and including T
   - Window excludes all data after T

2. When backtesting:
   - Use `.iloc[:i+1]` to include data up to row i
   - Never use `.iloc[i:]` or future rows

3. When storing signals:
   - Signal for candle T is added only after T's candle is closed
   - No signal is retroactively modified based on future candles

### Tests

- `tests/test_lookahead_prevention.py` validates that modifying future candles does not change historical signals

---

## Data Validation

All data loaded from storage must pass:

1. **Schema Check:** All required columns present
2. **Type Check:** Columns have correct types
3. **Constraint Check:** OHLC invariants, ranges, etc.
4. **Duplicate Check:** No duplicate (symbol, source, timeframe, timestamp)
5. **Monotonicity Check:** Timestamps strictly increasing within each group
6. **OHLC Logic Check:** `high >= max(open, close, low)`, etc.

---

## API Usage

### Loading OHLCV

```python
from src.data.store import ParquetStore

store = ParquetStore()
df = store.load_ohlcv("BTCUSDT", timeframe="daily")
# Returns: DataFrame with OHLCV columns, timestamps sorted
```

### Saving OHLCV

```python
# df must have all required columns
store.save_ohlcv("BTCUSDT", "daily", df)
# Validates, sorts by timestamp, saves to Parquet
```

### Validation

```python
# Check no duplicates
assert store.validate_no_duplicates(df)

# Check monotonic timestamps
assert store.validate_monotonic_timestamps(df)
```

---

## Versions & Breaking Changes

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-09-24 | Initial: OHLCV + Metadata, daily/4h |

### Future Breaking Changes

- 1.1: Add `bid`/`ask` columns (if Binance provides)
- 2.0: Add 1h/15m/5m timeframes
- 2.0: Add on-chain data columns

---

## Exceptions & Known Gaps

1. **Missing OHLCV:** Some new tokens may not have full Binance history. Handled gracefully with `validate_no_duplicates()`.
2. **Stale Metadata:** CoinGecko metadata updated daily; rank/market cap lag by ~1 hour.
3. **Timezone:** All timestamps are UTC. No local timezone support in P0.1.
4. **Delisting:** If a token is delisted, its OHLCV is archived, not deleted.

---

## Responsible Party

- **Author:** Claude Code (P0.1 implementation)
- **Validation:** Manual audit + test suite
- **Review:** Before P0.2

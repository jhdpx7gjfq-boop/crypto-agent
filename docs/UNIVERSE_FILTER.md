# Universe Filter Specification — P0.2

**Version:** 1.0 RESEARCH_CANDIDATE  
**Date:** 2026-09-24  
**Status:** Not optimized. For research filtering only.

---

## Overview

The Universe Filter reduces CoinGecko Top 500 to a scannable subset based on:
1. Market cap constraints
2. 24h volume constraints
3. OHLCV data availability (Daily + 4H)
4. OHLCV data quality (no NaN, duplicates, gaps)

**Output:**
- **Scannable Universe:** Tokens that PASS all filters
- **Rejection Report:** Tokens that FAIL with reasons

---

## Filter Architecture

Each filter is independent and returns: **PASS | FAIL | UNKNOWN**

### 1. MarketCapFilter

**Status:** RESEARCH_CANDIDATE  

**Logic:**
```
if market_cap is None → UNKNOWN
if market_cap < min_market_cap → FAIL
if market_cap > max_market_cap → FAIL
else → PASS
```

**Configuration (P0.2):**
```yaml
min_market_cap: null  # No minimum enforced
max_market_cap: null  # No maximum enforced
```

**Note:** Thresholds not optimized. Adjust based on analysis needs.

---

### 2. VolumeFilter

**Status:** RESEARCH_CANDIDATE

**Logic:**
```
if volume_24h is None or 0 → UNKNOWN
if volume_24h < min_volume_24h → FAIL
else → PASS
```

**Configuration (P0.2):**
```yaml
min_volume_24h: null  # No minimum enforced
```

**Note:** Volume thresholds not optimized for liquidity filtering.

---

### 3. DataAvailabilityFilter

**Status:** RESEARCH_CANDIDATE

**Logic:**
```
daily_candles = count(daily OHLCV for symbol)
fourbh_candles = count(4h OHLCV for symbol)

if require_daily and daily_candles < min_candles → FAIL
if require_4h and fourbh_candles < min_candles → FAIL
else → PASS
```

**Configuration (P0.2):**
```yaml
require_daily: true
require_4h: true
min_candles_per_timeframe: 50
```

**Rationale:** Minimum 50 candles ensures recent history (50 days daily, 200+ hours 4H).

**Note:** Future P0.3+ may require longer histories.

---

### 4. DataQualityFilter

**Status:** RESEARCH_CANDIDATE

**Logic:**
```
for each timeframe (daily, 4h):
  if contains NaN in [open, high, low, close, volume] → FAIL
  if has duplicate timestamps → FAIL
  if timestamps not strictly monotonic → FAIL

if all timeframes pass → PASS
else → FAIL
```

**Configuration (P0.2):**
```yaml
check_nan: true
check_duplicates: true
check_monotonic: true
```

**Note:** These are hard constraints; no tolerance for corrupted data.

---

## Filter Composition

All filters are applied **sequentially**:

```python
universe = Top 500 CoinGecko
  ↓ Market Cap Filter
  ↓ Volume Filter
  ↓ Data Availability Filter
  ↓ Data Quality Filter
  ↓ Scannable Universe
```

**Short-circuit:** A token that FAILS any filter is immediately rejected (no further testing).

---

## Output

### 1. Scannable Universe

DataFrame with columns:
```
symbol
name
coingecko_id
rank
market_cap
fdv
circulating_supply
total_supply
volume_24h
[all metadata from P0.1 CoinGecko snapshot]
```

**Example:**
```
symbol | rank | market_cap | volume_24h | status
BTC    | 1    | 1.2e12     | 4.5e10     | PASS
ETH    | 2    | 6.1e11     | 2.1e10     | PASS
...
```

### 2. Rejection Report

DataFrame with columns:
```
symbol
status (FAIL, UNKNOWN)
filter (market_cap, volume, data_availability, data_quality)
reason
value (actual value that failed)
threshold (constraint that was violated)
```

**Example:**
```
symbol  | status | filter              | reason                      | value | threshold
MICRO   | FAIL   | data_availability   | insufficient data: daily... | 30    | 50
SHIB    | UNKNOWN| volume              | volume_24h is None or 0     | None  | None
```

---

## Key Design Decisions

### ✅ PASS vs FAIL vs UNKNOWN

- **PASS:** All constraints satisfied
- **FAIL:** Constraint violated; evidence available
- **UNKNOWN:** Data missing; cannot determine; not included

### ✅ No Imputation

Missing data (market cap, volume) → UNKNOWN, NOT imputed.

### ✅ No Optimized Thresholds

Config values in P0.2 are `null` or conservative defaults.
No parameter optimization (PIT) until P1+.

### ✅ Deterministic Output

Same input (CoinGecko snapshot + Binance OHLCV) → same output, always.

### ✅ Auditability

Rejection report lists every exclusion reason for manual verification.

---

## Usage

```python
from src.data.universe_filter import (
    MarketCapFilter, VolumeFilter, DataAvailabilityFilter, 
    DataQualityFilter, UniverseFilter
)
import pandas as pd

# Load metadata (from P0.1)
metadata = pd.read_parquet("data/metadata/universe.parquet")

# Counts of OHLCV per symbol/timeframe
ohlcv_counts = {
    ("BTC", "daily"): 500,
    ("BTC", "4h"): 2000,
    ("ETH", "daily"): 450,
    ("ETH", "4h"): 1800,
    ...
}

# OHLCV DataFrames
ohlcv_data = {
    ("BTC", "daily"): df_btc_daily,
    ("BTC", "4h"): df_btc_4h,
    ("ETH", "daily"): df_eth_daily,
    ("ETH", "4h"): df_eth_4h,
    ...
}

# Create filters
mc_filter = MarketCapFilter()
vol_filter = VolumeFilter()
avail_filter = DataAvailabilityFilter()
quality_filter = DataQualityFilter()

# Compose
universe_filter = UniverseFilter(mc_filter, vol_filter, avail_filter, quality_filter)

# Apply
scannable_universe, rejections = universe_filter.apply_all(metadata, ohlcv_counts, ohlcv_data)

# Export
scannable_universe.to_csv("output/universe_p02.csv", index=False)
rejections.to_csv("output/rejections_p02.csv", index=False)
```

---

## Limitations

1. **Snapshot-based:** CoinGecko Top 500 at fetch time, not historical PIT
2. **No market regime:** Filters ignore bull/bear conditions
3. **Liquidity proxy:** Volume is a proxy; doesn't guarantee execution-friendly spreads
4. **Backward data:** No check for how far back OHLCV extends
5. **No intraday bars:** Filter works on daily + 4h; 1h/15m/5m are P1+

---

## Future Enhancements (P0.3+)

- Historical universe PIT (track Top 500 over time)
- Liquidity-adjusted volume filtering
- Market regime-dependent thresholds
- Relative strength pre-filter (optional)
- On-chain activity confirmation

---

## Tests

- `tests/test_universe_filter.py` covers:
  - Each filter independently (PASS/FAIL/UNKNOWN)
  - Composition (all filters together)
  - Edge cases (None values, empty DataFrames, duplicates)
  - Deterministic output

Total: **22 tests**, all passing.

---

## Status

P0.2 is complete. Ready for P0.3 (Bottom Detector).

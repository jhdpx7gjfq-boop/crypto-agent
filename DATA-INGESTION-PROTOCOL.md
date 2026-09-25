# Data Ingestion Protocol — PATH-A-LIQUIDATION-ALPHA

**Status:** `READY FOR EXECUTION` (awaiting Binance OHLCV files)

---

## Input Specification

### File Format

**CSV (Recommended)** or JSON. Per-symbol file.

**Path:** `data/binance/raw/{SYMBOL}_klines.{csv,json}`

Example:
```
data/binance/raw/BTCUSDT_klines.csv
data/binance/raw/ETHUSDT_klines.csv
data/binance/raw/SOLUSDT_klines.csv
data/binance/raw/AVAXUSDT_klines.csv
```

### CSV Schema

```
openTime, open, high, low, close, volume, closeTime
1609459200000, 29000, 30000, 28500, 29500, 100.5, 1609545599999
```

| Column | Type | Constraint |
|--------|------|-----------|
| `openTime` | integer (ms UTC) | Must align to 00:00:00 UTC (00:00 local may be ±8h offset) |
| `open` | float | > 0, finite |
| `high` | float | ≥ max(open, close), ≥ low |
| `low` | float | ≤ min(open, close), ≤ high |
| `close` | float | > 0, finite |
| `volume` | float | ≥ 0 |
| `closeTime` | integer (ms UTC) | Matches openTime window |

### JSON Schema

```json
[
  {
    "openTime": 1609459200000,
    "open": 29000,
    "high": 30000,
    "low": 28500,
    "close": 29500,
    "volume": 100.5,
    "closeTime": 1609545599999
  }
]
```

### Data Integrity Requirements

| Requirement | Check | Handled By |
|---|---|---|
| No gaps within period | calendar_gaps() | binance_audit.py |
| No duplicates | by_date dedup | binance_audit.py |
| No intraday rows | % 86_400_000 == 0 | binance_audit.py |
| OHLC cohesion | low ≤ min(O,C), high ≥ max(O,C) | binance_audit.py |
| Sorted ascending | previous_ts tracking | binance_audit.py |
| Hashed (raw + norm) | sha256 | binance_audit.py |

### Timeline

| Symbol | Min Period | Ideal Period | Minimum Bars |
|--------|-----------|-------------|---|
| BTC, ETH, SOL, AVAX | 365 days | 730 days | 365 |

---

## Execution

### Step 1: Place files

```bash
mkdir -p data/binance/raw
# Drop CSV or JSON files here
```

### Step 2: Validate & ingest

```bash
cd /home/user/crypto-agent
python -m igwt.fixtures.path_a_runner
```

Or with fresh fetch attempt (will fail if API blocked):

```bash
python -m igwt.fixtures.path_a_runner --fetch
```

### Step 3: Audit report

Output: `fixtures/real/PATH-A-LIQUIDATION-ALPHA/manifest.json`

```json
{
  "fixture_id": "PATH-A-LIQUIDATION-ALPHA",
  "created_at": "2026-09-25T20:30:00Z",
  "results": {
    "BTCUSDT": {
      "audit_passed": true,
      "audit_verdict": "PASS",
      "observations_count": 365,
      "date_range": ["2025-09-25", "2026-09-25"]
    }
  }
}
```

**Verdicts:**
- `PASS`: No defects, ready for features
- `WARN`: Defects counted (gaps, dups) but ≥ 1 row accepted
- `FAIL`: No valid rows, pipeline blocked

### Step 4: If PASS/WARN

Features run automatically:

```
observations.json → signal + regimeVol + fwdRet
```

Then WFV:

```bash
python -m igwt.validation.wfv.run PATH-A-LIQUIDATION-ALPHA
```

### Step 5: Verdict

IC / OOS / direction_flips → research report

---

## Data Source (for reference)

**Binance REST API (currently blocked):**

```
GET https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&startTime=1609459200000
Response: [[ ts, open, high, low, close, volume, closeTime, ... ]]
```

**Alternative (working in this environment):**

Export from Binance historical data CSV or use:
- Kraken OHLC export (validate column mapping)
- Backblaze (validate symbols + mapping)

**Validation requirement:** Whatever source, must declare:
- `source`: "binance-spot" or similar
- `endpoint`: URL or file
- `retrieval_timestamp`: When data was fetched
- All sha256 hashes (raw + normalized)

---

## Constraints

✅ **Do:**
- Provide complete OHLCV with no synthetic fill
- Include all symbols (BTC, ETH, SOL, AVAX) or abort
- State time coverage explicitly
- Keep audit report in fixture

❌ **Don't:**
- Backfill missing bars
- Mix timeframes
- Forward-fill or interpolate
- Provide manual/curated data without provenance

---

## Blockers & Fallback

**If Binance data unavailable:**

PATH-A remains PENDING_ACQUISITION.

No workaround coder:
- CoinGecko data → different source (use REAL-DATA-FIXTURE-001 instead)
- Synthetic OHLCV → audit will fail on hashes
- Future data → lookahead bias

PATH-A verdict waits for real Binance data or is closed as INCONCLUSIVE.

---

## Next: Awaiting Data

Once files placed in `data/binance/raw/`, run:

```bash
python -m igwt.fixtures.path_a_runner
```

Pipeline validates → observations → WFV → IC → verdict.

---

**Status: `DATA GATE`** — Ready to accept input, validation pipeline frozen, awaiting Binance OHLCV files.

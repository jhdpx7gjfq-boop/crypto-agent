# Daily OHLCV Acquisition Plan

**Objective:** Acquire 730+ daily candles for all 4 symbols (BTC, ETH, SOL, AVAX) to execute full B-004 validation gate.

**Status:** PENDING IMPLEMENTATION  
**Date:** 2026-09-25  
**Authority:** IGWT-PF26 Phase 6 → Phase 8 Data Foundation

---

## Requirements (B-004 LOCKED)

- **Symbols:** BTC, ETH, SOL, AVAX (4 total)
- **Candles:** 730 minimum (2-year daily history)
- **Granularity:** Daily (1 candle/day, no aggregation)
- **Data format:** OHLCV with timestamp, open, high, low, close, volume
- **No lookahead:** Data must be historical (completed candles only)
- **Immutability:** Once acquired, treat as frozen baseline

---

## Available Sources (Network Audit)

### Source 1: Binance Public API ❌ BLOCKED
- **Endpoint:** `api.binance.com/api/v3/klines`
- **Status:** HTTP 451 (proxy blocks crypto exchange connections)
- **Workaround:** None in current cloud environment

### Source 2: CoinGecko MCP ⚠️ LIMITED
- **Available:** chart widget (rendered, not raw OHLCV)
- **Limitation:** Cannot extract structured daily candles
- **Status:** Not viable for programmatic access

### Source 3: TipRanks MCP ⚠️ QUOTA EXHAUSTED
- **Fetched:** 2-year monthly (25 candles, 2024-09-25 → 2026-09-25)
- **Available quota:** 2/10 monthly calls
- **Limitation:** Monthly aggregation insufficient (need daily)
- **Status:** Cannot provide daily granularity

### Source 4: Kraken, Poloniex, Bybit ❌ NOT ACCESSIBLE
- **Status:** Blocked by proxy (same as Binance)

---

## Path Forward: 3 Options

### Option A: External Data Export (RECOMMENDED)
**Approach:**
1. Run `/crypto-agent` in local development environment (non-cloud)
2. Fetch 730 daily candles via Binance or Kraken direct connection
3. Export as JSON to `./real_market_data/{SYMBOL}_daily_730d.json`
4. Commit to repository
5. Return to cloud environment, run B-004 validation

**Timeline:** 15 min (fetch) + 5 min (validation)  
**Requirements:** Local machine with unrestricted egress  
**Risk:** Network timing (Binance API rate limits: 1200 reqs/min)

**Implementation Script:**
```python
# fetch_daily_ohlcv_local.py (runs locally)
import requests
import json
from pathlib import Path

for symbol in ["BTC", "ETH", "SOL", "AVAX"]:
    resp = requests.get(
        "https://api.binance.com/api/v3/klines",
        params={"symbol": f"{symbol}USDT", "interval": "1d", "limit": 730},
        timeout=10
    )
    data = resp.json()
    candles = [{
        "timestamp": int(c[0]),
        "open": float(c[1]),
        "high": float(c[2]),
        "low": float(c[3]),
        "close": float(c[4]),
        "volume": float(c[7]),
    } for c in data]
    
    filepath = Path("./real_market_data") / f"{symbol}_daily_730d.json"
    with open(filepath, "w") as f:
        json.dump({"candles": candles}, f)
    print(f"Exported {len(candles)} candles for {symbol}")
```

### Option B: Premium Data Service
**Approach:**
1. Subscribe to Glassnode, Messari, or Kaiko API (paid)
2. Fetch 730 daily candles with premium data quality
3. Export as JSON
4. Commit to repository

**Timeline:** 1 day (account setup + API key) + fetch  
**Cost:** $50-500/month  
**Advantage:** Higher data quality, official channels

### Option C: Network Policy Change
**Approach:**
1. Request proxy policy modification to allow Binance HTTPS
2. Modify `b004_wfv.py` to fetch directly during validation run
3. Cache results locally

**Timeline:** 1-3 days (infrastructure request)  
**Complexity:** Requires Owner approval + network team coordination

---

## Immediate Next Steps

### Step 1: Export Script (Local Machine)
Create `scripts/fetch_daily_ohlcv_local.py`:
- Fetch from Binance (recommended: lowest latency, free)
- Fallback to CoinGecko API (free, rate-limited)
- Save to `./real_market_data/{SYMBOL}_daily_730d.json`
- Validate: 730 candles per symbol, complete date range

### Step 2: Data Validation
Post-import verification:
- ✅ 730 candles per symbol
- ✅ Daily granularity (timestamp diffs = 86400 seconds)
- ✅ No gaps or forward-fill
- ✅ Prices non-negative, volumes > 0

### Step 3: B-004 Execution
```bash
cd /home/user/crypto-agent
python b004_wfv.py
```

Expected output:
- 19 windows × 4 symbols = 76 result rows
- Aggregate statistics: Mean IC, Hit Rate, Stability
- Gate decision: PASS / FAIL

### Step 4: Layer 8 Decision
If B-004 PASS:
- Real Data Validation → VALIDATED_ALPHA (pending Piste A/B decision)
- Layer 8 UNBLOCK → Proceed to X20 Engine, RCM deployment

If B-004 FAIL:
- Analyze which criteria failed (IC, HR, or Stability)
- Consider Piste B: RRP signal refinement for weekly data
- Iterate on RPM/RCM tuning (no lookahead bias constraint)

---

## Data File Structure

**Input Format:**
```json
{
  "candles": [
    {
      "timestamp": 1695523200,
      "open": 26500.0,
      "high": 27000.0,
      "low": 26400.0,
      "close": 26800.0,
      "volume": 15234.5
    },
    ...
  ]
}
```

**Validation Checklist:**
- [ ] File exists: `./real_market_data/{SYMBOL}_daily_730d.json`
- [ ] Contains exactly 730 candles
- [ ] Timestamp sequence: consecutive days (86400 sec apart)
- [ ] No null/NaN values
- [ ] Volume > 0 for all candles
- [ ] High ≥ Close ≥ Low for all candles
- [ ] Date range: ~2-year historical (730 days ≈ 2 years)

---

## Success Criteria

B-004 executes successfully:
```
INFO: Running 19 windows for BTC
INFO: W1: IC=0.0342, HR=52%
INFO: W2: IC=-0.0156, HR=48%
...
INFO: W19: IC=0.0821, HR=58%

Mean IC: 0.0512 (≥0.05) → PASS
Hit Rate: 56.3% (≥55%) → PASS
Stability: 0.412 (<0.50) → PASS

VERDICT: PASS ✅
```

---

## Owner Decision Required

**Question:** Which option for acquiring 730 daily candles?

1. **Option A (Local export)** — Recommended
   - Fastest, lowest friction
   - Requires local machine with unrestricted internet
   - 20 minutes total time
   
2. **Option B (Premium service)** — High confidence
   - Official data vendor
   - Higher cost, slower setup
   - Best for production deployment
   
3. **Option C (Network policy)** — Infrastructure change
   - Enables future automated pipelines
   - Requires approval + coordination
   - Best long-term, high setup cost

**Recommendation:** Option A (local export) → Execute B-004 today → Decide on Option B/C for production after seeing results.

---

## Timeline

- **Option A execution:** 1-2 hours (manual export + validation + B-004 run)
- **Option B setup:** 1-3 days (service onboarding)
- **Option C approval:** 1-3 days (infrastructure request)

---

## Governance Notes

- ✅ B-004 criteria locked, no tuning on test data
- ✅ Immutability constraint: Once acquired, baseline frozen
- ✅ Layer 8 unblock only if B-004 PASS + VALIDATED_ALPHA confirmed
- ✅ No regime pre-filtering (Bull/Bear analysis post-hoc only)

---

**Status:** READY FOR OWNER DECISION  
**Blocker:** Daily OHLCV acquisition method  
**Impact:** Layer 8 unblock decision timeline

# Binance C1.5-PIT Audit — Detailed Methodology

**Problem:** Direct API access to Binance blocked in this environment (451 error).  
**Solution:** Document explicit methodology for audit execution (can be run locally or via approved environment).

---

## Data Collection Methodology

### Option A: Direct Binance Spot API (Recommended)

```bash
# Requires: Network access to api.binance.com

curl -s "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&startTime=1577836800000&endTime=1580515200000&limit=1000" \
  | jq '.' > btc_2020_01_raw.json
```

**Result Format:**
```json
[
  [
    1577836800000,    // Open time (ms)
    "9197.61000000",  // Open
    "10060.29000000", // High
    "9186.79000000",  // Low
    "9768.20000000",  // Close
    "123456789.00",   // Volume
    1577923199999,    // Close time (ms)
    ...other fields
  ],
  ...
]
```

**Key Field:** Index 0 = event_time (in ms)

---

### Option B: Historical Data Archives

If Binance API cannot provide archive state as of specific date:

```
Approach: Use known-good historical snapshots
Sources:
  - Binance data exports (if available)
  - Third-party archives (Kaiko, CryptoCompare, etc.)
  - Local snapshots taken daily over time
```

---

## Availability Time Determination

### Question: When was each candle available?

**Current Data:**
```
event_time = when price action closed (e.g., 2020-01-15 00:00 UTC)
availability_time = when we can query it (UNKNOWN without investigation)
```

**Investigation Method:**

1. **Assume:** Binance makes 1d closes available next day (00:00 UTC)
   ```
   event_time        = 2020-01-15 23:59:59 UTC
   availability_time = 2020-01-16 00:00:00 UTC (assumption)
   ```

2. **Verify:** Check Binance documentation or community reports
   - Does Binance guarantee next-day availability?
   - Are there exceptions?
   - Has policy changed over time?

3. **Fallback:** If unavailable, mark as `UNVERIFIED` and downgrade proof level

---

## Retroactive Revision Detection

### Method 1: Time-Series Diff

```python
# Pseudo-code

snapshot_2020_01_15 = binance_api("2020-01-15")
snapshot_2020_01_16 = binance_api("2020-01-16")
snapshot_2026_10_01 = binance_api("2026-10-01")  # Today

# Compare across time
diff_jan15_to_jan16 = snapshot_2020_01_15.difference(snapshot_2020_01_16)
diff_jan16_to_oct01 = snapshot_2020_01_16.difference(snapshot_2026_10_01)

# If later snapshots change earlier data:
# → Retroactive revision detected
```

### Method 2: Check Binance Release Notes

```
Binance Announcements
└─ "Historical Data Adjustments"
   └─ "Corrected OHLCV for [dates]"
   
If found:
  → Log revision via RevisionAuditLog
  → Mark affected_dates
  → Update availability_time if necessary
```

---

## Proof Level Classification

### Per Candle Schema

```json
{
  "asset": "BTC",
  "date": "2020-01-15",
  "close": 9768.20,
  "volume": 123456789.00,
  
  "event_time": "2020-01-15T23:59:59Z",
  "availability_time": "2020-01-16T00:00:00Z",
  "availability_source": "binance_api_1d_close",
  
  "proof_level": "C",
  "proof_level_rationale": "API returns historical 1d candles with timestamp. No publisher versioning available. No immutable archive API. Proof Level C = API historical with timestamp.",
  
  "retroactive_revision": false,
  "confidence": "HIGH",
  
  "audit_timestamp": "2026-10-01T13:00:00Z",
  "auditor_notes": "Standard daily close, no anomalies"
}
```

### Scoring Rules

**Level A:** Publisher timestamp + versioned history
- Binance publishes explicit "data version X" for each snapshot
- We can query "what data was available on 2020-01-16"
- Result: PASS

**Level B:** Immutable dated archive
- Binance provides signed/hashed archive of historical data
- Archive is timestamped and immutable
- Result: PASS

**Level C:** API historical with timestamp
- Binance API returns historical 1d candles
- No explicit versioning
- We can infer availability from API structure
- Assumption: published daily, available next day
- Result: PASS_CONDITIONAL (depends on documentation)

**Level D:** Retroactively reconstructed
- Binance recalculates old data (e.g., OHLCV corrections)
- No proof of original availability
- Result: FAIL

**Level E:** Synthetic/mock
- Data is synthetic (not real market data)
- Result: FAIL

---

## Expected Result Format

### Per Asset + Period

```json
{
  "audit_id": "binance_pit_audit_20261001",
  "asset": "BTC",
  "period": "2020-01",
  "status": "IN_PROGRESS",
  
  "sample_size": 31,
  "candles_with_availability": 31,
  "candles_unknown_availability": 0,
  
  "retroactive_revisions": {
    "detected": false,
    "count": 0,
    "examples": []
  },
  
  "proof_level_distribution": {
    "A": 0,
    "B": 0,
    "C": 31,
    "D": 0,
    "E": 0
  },
  
  "verdict": "PASS_CONDITIONAL",
  "verdict_rationale": "All 31 candles available via API (Level C). No retroactive revisions detected. Proof requires documentation of Binance availability policy (when daily closes become queryable).",
  
  "conditions": [
    "Binance confirms daily OHLCV available by next-day 00:00 UTC",
    "No retroactive corrections to 2020 data",
    "Auditor accepts Level C + documentation as sufficient"
  ],
  
  "confidence": "MEDIUM",
  "audit_timestamp": "2026-10-01T13:00:00Z",
  "auditor": "empirical_audit_process"
}
```

---

## Execution Commands (Reference)

### Collect BTC daily candles (Jan 2020)

```bash
#!/bin/bash

ASSET="BTC"
SYMBOL="${ASSET}USDT"
INTERVAL="1d"
START_DATE="2020-01-01"
END_DATE="2020-01-31"

# Convert to timestamps (ms)
START_TS=$(($(date -d "$START_DATE" +%s) * 1000))
END_TS=$(($(date -d "$END_DATE" +%s) * 1000 + 86400000))

OUTPUT="audit_${ASSET}_${START_DATE}_${END_DATE}.json"

curl -s "https://api.binance.com/api/v3/klines" \
  --data-urlencode "symbol=$SYMBOL" \
  --data-urlencode "interval=$INTERVAL" \
  --data-urlencode "startTime=$START_TS" \
  --data-urlencode "endTime=$END_TS" \
  --data-urlencode "limit=1000" \
  | jq '.' > "$OUTPUT"

echo "✅ Saved $OUTPUT"
```

### Repeat for all assets + periods

```bash
for ASSET in BTC ETH SOL; do
  for PERIOD in 2020-01 2021-01 2022-05 2024-01 2025-01; do
    # Run above script
  done
done
```

---

## Quality Checklist

**For each audited period:**

- [ ] Data collected from Binance API
- [ ] event_time extracted (candle close time)
- [ ] availability_time determined or marked UNKNOWN
- [ ] Retroactive revisions checked
- [ ] Proof level assigned (A/B/C/D/E)
- [ ] Confidence scored (HIGH/MEDIUM/LOW)
- [ ] Result JSON created

**For final verdict:**

- [ ] All periods (2020/2021/2022/2024/2025) audited
- [ ] All assets (BTC/ETH/SOL) covered
- [ ] Gap analysis complete
- [ ] Verdict determined (PASS / CONDITIONAL / FAIL)
- [ ] Rationale documented
- [ ] Gate keeper approval obtained

---

## Notes for Auditor

### When collecting data:

1. **Record query timestamp:** When YOU request the data (important for reference)
2. **Record Binance response:** What it returns (with all metadata)
3. **Assume nothing:** Don't assume availability_time = event_time. Verify.
4. **Check for gaps:** Missing candles? Document why.
5. **Cross-check:** If possible, compare Binance data against other sources (CoinGecko, CryptoCompare) to detect revisions.

### Red flags:

- [ ] Candles with no timestamp info
- [ ] Retroactive price corrections (check release notes)
- [ ] Gaps in time series
- [ ] API returning data "from the future" (availability > today)
- [ ] Inconsistencies across multiple API calls

---

## Current Status

- Phase 1 (Methodology): ✅ DOCUMENTED
- Phase 2 (Collection): ⏳ REQUIRES LOCAL EXECUTION (network access)
- Phase 3 (Revision Detection): ⏳ PENDING DATA
- Phase 4 (Analysis): ⏳ PENDING DATA
- Phase 5 (Gate Review): ⏳ PENDING VERDICT

**Next step:** Execute this methodology using approved environment with Binance API access.

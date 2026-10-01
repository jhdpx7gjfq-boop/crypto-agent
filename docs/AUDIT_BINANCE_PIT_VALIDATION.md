# Binance C1.5-PIT Empirical Audit

**Objective:** Validate that Binance historical OHLCV data respects temporal availability constraints required for WFV.

**Status:** In Progress (Started 2026-10-01)

---

## Audit Scope

### Assets
- **BTC** (bitcoin)
- **ETH** (ethereum)
- **SOL** (solana)

### Periods (Diverse Market Regimes)
- **2020-01 to 2020-03**: Early period, edge cases
- **2021-01 to 2021-03**: Bull market, high activity
- **2022-05 to 2022-07**: Bear market, different behavior
- **2024-01 to 2024-03**: Recent period, current behavior
- **2025-01 to 2025-03**: Ongoing period (if available)

### Granularity
- Daily OHLCV candles (sufficient for initial audit)
- Future: 1h/15m if needed

---

## Audit Questions

### Question 1: Event Time vs Availability Time

For each historical candle:

```
event_time         = when price action occurred (e.g., 2020-01-15 daily close)
availability_time  = when Binance made it queryable/available
```

**Current assumption:** Both are identical in Binance API responses.
**Reality check needed:** Is this true?

### Question 2: Archive Versioning

Does Binance version historical data?

```
Scenario A: Once published, never changes
  → Availability_time = publication_time (first known)
  
Scenario B: Retroactive corrections allowed
  → Availability_time ≠ event_time (complicated)
  → Revisions must be tracked
```

**Current assumption:** Binance does not retroactively modify historical candles.
**Reality check needed:** Has it ever revised 2020 data?

### Question 3: Availability Proof Level (A-E Hierarchy)

| Level | Requirement | Binance Status |
| --- | --- | --- |
| **A** | Publisher timestamp + versioned history | ? |
| **B** | Immutable dated archive | ? |
| **C** | API historical with timestamp | LIKELY |
| **D** | Retroactively reconstructed | NO |
| **E** | Synthetic/mock | NO |

**Assessment:** Binance likely = C (PASS_CONDITIONAL) unless proven otherwise.

---

## Audit Methodology

### Step 1: Data Collection

**For each asset (BTC/ETH/SOL) and period (2020/2021/2022/2024/2025):**

```bash
# Collect daily OHLCV from Binance API
# Document:
# - API endpoint called
# - Query timestamp (when we requested)
# - Response timestamp (when Binance timestamped response)
# - Data returned
# - Archive/version metadata (if available)
```

**Tool:** Use Binance REST API `/api/v3/klines` endpoint.

### Step 2: Archive Reconstruction (if possible)

**Question:** Can we access historical snapshots of what Binance had on specific dates?

```
2020-01-20: Query Binance for "all data as of 2020-01-20"
            Return = candles available at that date
2020-01-21: Query Binance for "all data as of 2020-01-21"
            Return = candles available at that date
            
Diff = new data, corrections, etc.
```

**Reality:** Binance public API may NOT support this. Need to investigate.

### Step 3: Documentation per Candle

For each historical OHLCV row:

```json
{
  "asset": "BTC",
  "date": "2020-01-15",
  "event_time": "2020-01-15T23:59:59Z",  // Daily close UTC
  "availability_time": "2020-01-16T00:?:??Z",  // When available
  "availability_source": "binance_api_call_at_20260930",
  "proof_level": "C",  // API historical
  "archive_method": "binance_rest_klines",
  "has_retroactive_revision": false,  // Or true if detected
  "confidence": "HIGH" / "MEDIUM" / "LOW"
}
```

### Step 4: Gap Analysis

**Questions to answer:**

1. For how many candles can we demonstrate `availability_time ≤ decision_time`?
2. For how many is `availability_time` unknown/undocumented?
3. Are there retroactive revisions? How many? Which periods?
4. What percentage of historical data meets Proof Level A/B (vs C/D/E)?

### Step 5: Verdict

**Judgment:**

```
PASS
  → All candles: availability_time documented + ≤ decision_time
  → No retroactive revisions
  → Proof level A or B for 100% of data
  
PASS_CONDITIONAL
  → Most candles documented
  → Proof level C (API historical) acceptable with documentation
  → Retroactive revisions <1% and handled
  → Conditions: document methodology, accept audit risk
  
FAIL
  → Many candles: availability_time unknown
  → Proof level D/E (retroactive/synthetic)
  → Unhandled retroactive revisions
  → WFV blocked unless conditions change
```

---

## Preliminary Assessment (Pre-Audit)

**Assumptions before investigation:**

| Assumption | Confidence | Status |
| --- | --- | --- |
| Binance has not retroactively modified 2020 data | HIGH | Unverified |
| Candles are available within 1 hour of close | HIGH | Unverified |
| Binance public API returns consistent historical data | HIGH | Unverified |
| No hidden versioning or data corrections | MEDIUM | Unverified |

**If all assumptions hold:**
→ Verdict likely = **PASS_CONDITIONAL** (Proof Level C)

**If any assumption fails:**
→ Verdict may downgrade to FAIL

---

## Audit Execution Plan

### Phase 1: Methodology Validation (Week 1)
- [ ] Document Binance API contract (klines endpoint)
- [ ] Collect sample data (BTC, Jan 2020, 10 days)
- [ ] Assess what metadata Binance provides
- [ ] Identify gaps in availability_time documentation

### Phase 2: Full Data Collection (Week 2-3)
- [ ] BTC: 2020/2021/2022/2024/2025
- [ ] ETH: 2020/2021/2022/2024/2025
- [ ] SOL: 2020/2021/2022/2024/2025
- [ ] Document each candle per Step 3 schema

### Phase 3: Retroactive Revision Detection (Week 3)
- [ ] Compare snapshots across time (if possible)
- [ ] Identify corrections/revisions
- [ ] Log via RevisionAuditLog (from Layer 1)

### Phase 4: Analysis & Reporting (Week 4)
- [ ] Gap analysis (Q1-4 from Step 4)
- [ ] Proof level classification per period/asset
- [ ] Verdict: PASS / CONDITIONAL / FAIL
- [ ] Risk assessment

### Phase 5: Gate Keeper Review (Week 5)
- [ ] Present findings
- [ ] Obtain explicit approval or conditions
- [ ] Document gate decision

---

## Risk Assessment

### Risk 1: Binance Has Retroactively Modified 2020 Data
**Impact:** HIGH (invalidates historical candles)
**Mitigation:** Check Binance release notes, community reports
**Outcome:** If true → FAIL

### Risk 2: Availability Time Unknown
**Impact:** MEDIUM (downgrades to CONDITIONAL)
**Mitigation:** Accept API timestamp as proxy
**Outcome:** If unavoidable → PASS_CONDITIONAL

### Risk 3: API Changes Over Time
**Impact:** MEDIUM (some periods may have different availability rules)
**Mitigation:** Document per-period differences
**Outcome:** If true → different verdicts per period

---

## Success Criteria

**Audit = COMPLETE when:**

1. ✅ All sample data (2020/2021/2022/2024/2025 × BTC/ETH/SOL) collected
2. ✅ Availability time documented or justified absence
3. ✅ Retroactive revisions analyzed (count, impact)
4. ✅ Proof level (A/B/C/D/E) assigned
5. ✅ Verdict (PASS / CONDITIONAL / FAIL) issued
6. ✅ Gate keeper approval obtained
7. ✅ Report filed with findings

**WFV unblocked = only if verdict includes PASS approval**

---

## Documentation Format

All audit findings will be recorded in structured format:

```json
{
  "audit_id": "binance_pit_audit_20261001",
  "asset": "BTC",
  "period": "2020-01",
  "total_candles": 31,
  "findings": {
    "candles_with_availability_time": 31,
    "candles_unknown_availability": 0,
    "retroactive_revisions": 0,
    "proof_level": "C",
    "confidence": "HIGH"
  },
  "verdict_per_period": "PASS_CONDITIONAL",
  "conditions": [
    "Availability time documented via API response",
    "Proof level C (API historical) accepted per PITValidator hierarchy",
    "No retroactive revisions detected"
  ],
  "gate_keeper_approval": "PENDING"
}
```

---

## Timeline

| Phase | Start | Duration | Deliverable |
| --- | --- | --- | --- |
| Methodology | 2026-10-01 | 1 week | API contract doc + sample data |
| Collection | 2026-10-08 | 2 weeks | Full dataset BTC/ETH/SOL |
| Revision Detection | 2026-10-15 | 1 week | Revision audit report |
| Analysis | 2026-10-22 | 1 week | Gap analysis + proof levels |
| Gate Review | 2026-10-29 | 1 week | Final verdict + approval |
| **Complete** | **2026-11-05** | **5 weeks** | **WFV Gate Decision** |

---

## Next Steps

1. **Confirm audit scope** (assets, periods, granularity)
2. **Obtain Binance API access** (if needed for archive queries)
3. **Start Phase 1:** Validate methodology with sample data
4. **Report findings weekly**

**Audit initiated:** 2026-10-01  
**Status:** Phase 1 (Methodology Validation) — Ready to begin


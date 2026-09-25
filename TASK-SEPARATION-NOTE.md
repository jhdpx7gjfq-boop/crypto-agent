# Task Separation & Data Gate — Clarification

**Date:** 2026-09-25  
**Status:** GOVERNANCE / BLOCKING

---

## Two Distinct Data Paths

### Path 1: Task `bse882oft` (Remote Collection)

- **Type:** Standalone data collection task
- **Status:** In progress (if active)
- **Location:** External to this repository
- **Output:** Unknown — awaits task completion
- **Integration:** TBD (do not assume automatic integration)

### Path 2: PATH-A Repository Pipeline (Local)

- **Type:** Research validation pipeline (this repository)
- **Status:** `FROZEN / DATA GATE`
- **Location:** `/home/user/crypto-agent`
- **Input gate:** `data/binance/raw/{SYMBOL}_klines.{csv,json}`
- **Specification:** `DATA-INGESTION-PROTOCOL.md`
- **Processing:** audit → features → observations → WFV
- **Output:** Mechanical verdict (IC / OOS / robustness)

---

## CRITICAL DISTINCTION

**Do NOT assume:**
- `bse882oft` output = PATH-A input
- Remote collection = local pipeline data source
- Any intermediate file = validation proof

**Do assume:**
- Two independent acquisition paths
- PATH-A accepts data ONLY through documented protocol
- Dataset must satisfy schema, provenance, PIT before processing
- Hash validation required (sha256_raw, sha256_normalized)

---

## Data Acceptance Criteria (PATH-A)

Input to PATH-A is acceptable if and only if:

1. **Location:** `data/binance/raw/{SYMBOL}_klines.{csv|json}`
2. **Format:** CSV or JSON per `DATA-INGESTION-PROTOCOL.md`
3. **Symbols:** BTC, ETH, SOL, AVAX (all or abort)
4. **Period:** 365–730 calendar days, no gaps in coverage statement
5. **Fields:** openTime, open, high, low, close, volume, closeTime (CSV); exact JSON schema (JSON)
6. **Timestamps:** UTC milliseconds, aligned to 00:00:00 UTC
7. **Provenance:** Must declare source, endpoint, retrieval_timestamp
8. **Validation:** No synthetic fill, no interpolation, no future data

---

## Processing Sequence (PATH-A)

Once input accepted:

```
Raw Binance files (CSV/JSON)
        ↓
  audit_binance_klines()
        ↓
  Verdict: PASS / WARN / FAIL
        ↓
  (If PASS/WARN)
        ↓
  build_path_a_observations()
        ↓
  observations.json
        ↓
  validate_contract() [WFV-V2]
        ↓
  run_wfv()
        ↓
  IC / OOS / direction_flips / regime_conditioned
        ↓
  Mechanical verdict: PASS (edge evidence) / FAIL (no edge)
```

---

## No Intermediate Assertion

**Forbidden:**
- "Audit passed → alpha validated" ✗
- "Features computed → robustness confirmed" ✗
- "Observations built → signal works" ✗
- "WFV fold completed → edge exists" ✗

**Only valid:**
- "Full WFV walk-forward complete → IC statistic and direction_flips computed → verdict recorded" ✓

---

## Next Action Trigger

PATH-A transitions from `DATA GATE` to active processing **when and only when:**

```
├─ Files present in data/binance/raw/
├─ Schema validation passes
├─ Timestamp alignment confirmed
├─ No future data detected
└─ Provenance declared
```

Then:
```bash
python -m igwt.fixtures.path_a_runner
```

---

## Repository State Until Data Arrival

- **Branch:** claude/relaxed-wozniak-01ipk5 (no further commits)
- **Tests:** 208 PASS (frozen)
- **Pipeline:** Ready to accept input (no changes)
- **Code:** No new features, no refactors, no optimization
- **Governance:** 10 lineage rules enforced, 6 artefacts registered

---

## Summary

| Item | Status |
|------|--------|
| PATH-A pipeline | ✅ READY / 🔴 DATA GATE |
| B-004 (B-004_SPECIFICATION_FROZEN.md) | ❌ NOT STARTED |
| BCE/X20/RPM/NARN-P+ | 🚫 UNTOUCHED |
| Task `bse882oft` integration | ⏳ AWAITING CLARIFICATION |
| Next code action | 🚫 NONE |

**Awaiting:** Binance OHLCV files meeting protocol or explicit task update.

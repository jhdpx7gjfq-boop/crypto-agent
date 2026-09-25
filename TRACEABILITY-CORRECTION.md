# Traceability Correction — B-004 vs REAL-DATA-FULL-001

**Date:** 2026-09-25  
**Issue:** Improper aliasing of B-004 to REAL-DATA-FULL-001  
**Status:** GOVERNANCE CORRECTION (P0)

---

## Problem Statement

In previous audit output, B-004 was described as:
> "B-004 n'est **pas une spécification** — c'est un **alias** pour 'Real Data Path A'"
> "Le chemin réel est **REAL-DATA-FULL-001** (Binance Spot 730j)"

This creates false retroactive traceability:
- B-004-DATA-RETRY was never a formal repository artefact
- Calling B-004 an "alias" suggests historical governance that did not exist
- Linking B-004 to REAL-DATA-FULL-001 without explicit lineage is incorrect

---

## Factual State

### REAL-DATA-FULL-001 (Verified)

✅ **Exists** in repository:
- `docs/specs/REAL-DATA-FULL-001.md` (formalized specification)
- Status: `PENDING ACQUISITION`
- Objective: Binance Spot OHLCV 730 days (BTC, ETH, SOL, AVAX)
- Control fixture: `REAL-DATA-FIXTURE-001` (LOCKED)
- Contract: `WFV-V2-CONTRACT` (FROZEN)
- Registered in `docs/registry/lineage.json`

### B-004 (Unknown)

❌ **Does not exist** in repository as formal artefact:
- No `B-004_SPECIFICATION_FROZEN.md`
- No entry in lineage.json
- No lock record
- No explicit relation to REAL-DATA-FULL-001

**Origin:** Conversational reference only (previous session context, not repository artifact).

---

## Correction

### What to Keep (Correct)

1. **PATH-A:** Formalized, pipeline ready, tests passing. No change.
2. **REAL-DATA-FULL-001:** Formal artefact, specification exists, data gate applies.
3. **Data gate:** Both PATH-A and REAL-DATA-FULL-001 await Binance OHLCV 730 days.

### What to Fix (Traceability)

1. **Remove aliasing:** Do NOT call B-004 an alias for REAL-DATA-FULL-001.
2. **Correct audit statement:**
   - Change: "B-004 (alias: REAL-DATA-FULL-001)"
   - To: "REAL-DATA-FULL-001 (formal artefact) — corresponds to authoring need 'Real Data Path A'"
3. **B-004 status:** 
   - If B-004 is a formal requirement: create `B-004_SPECIFICATION_FROZEN.md` with explicit lineage to REAL-DATA-FULL-001
   - If B-004 is merely a prior label: document as "conversational reference, not repository artifact"

---

## Updated Three-Path Matrix

```
┌──────────────────────────┬──────────────┬──────────────────────┐
│ Path                     │ Status       │ Blocker              │
├──────────────────────────┼──────────────┼──────────────────────┤
│ PATH-A                   │ DATA-BLOCKED │ Binance OHLCV 365-730│
│ REAL-DATA-FULL-001       │ DATA-BLOCKED │ Binance OHLCV 730j   │
│ BCE/X20/RPM/NARN-P+      │ FORBIDDEN    │ Governance constraint│
└──────────────────────────┴──────────────┴──────────────────────┘

GATE COMMUNE: Real Binance OHLCV data
```

---

## Decision on B-004

### If B-004 is a formal requirement:

1. Create `B-004_SPECIFICATION_FROZEN.md`
2. Define explicitly:
   - Objective
   - Data source and validation rules
   - Relation to REAL-DATA-FULL-001 (parent? control? derived?)
   - WFV gate and verdict criteria
3. Register in lineage.json with explicit relation type
4. Commit with clear governance rationale

### If B-004 is not a formal requirement:

1. Document in TRACEABILITY-CORRECTION.md that B-004 was a conversational label
2. Use REAL-DATA-FULL-001 as the formal specification
3. Do not create B-004_SPECIFICATION_FROZEN.md
4. Mark path as "REAL-DATA-FULL-001" in all governance documents

---

## What Does NOT Change

- ✅ PATH-A pipeline (frozen, ready)
- ✅ Tests (208 PASS, no changes)
- ✅ Lineage (10 rules enforced, no changes)
- 🚫 No new code
- 🚫 No WFV execution
- 🚫 No synthetic data
- 🚫 No modification of BCE/X20/RPM/NARN-P+

---

## Next Steps

1. Clarify: Is B-004 a formal artefact or a conversational reference?
2. If formal: create `B-004_SPECIFICATION_FROZEN.md` with full lineage
3. If informal: document in this file and close
4. Update GLOBAL-AUDIT.md to reflect corrected traceability
5. Commit with "governance correction" tag
6. FREEZE repository until Binance OHLCV data arrives

---

## Principle

> "A relation is never inferred from a name, a numbering scheme or temporal proximity. Every relation carries evidence resolvable inside this repository."
> — lineage.json, amendment_rules

Therefore:
- B-004 cannot remain an "alias" without formal evidence
- REAL-DATA-FULL-001 is the formal artefact
- Any link between them must be explicit and documented
- No retroactive inference of historical artefacts

---

**Status:** AWAITING CLARIFICATION on B-004 formal status before final commit.

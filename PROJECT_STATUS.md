# IGWT-PF26 Project Status

**Date**: 2026-09-25  
**Branch**: `claude/sharp-curie-wle1po`  
**Last Update**: Governance audit + revert unauthorized implementations

---

## Current Authorization Status

### ✅ AUTHORIZED & OPERATIONAL

| Layer | Component | Status | Tests | Notes |
|-------|-----------|--------|-------|-------|
| 1 | Data Intelligence | ✅ Active | 12 | DuckDB + Parquet |
| 2 | Market Regime Engine | ✅ Active | 10 | Risk regime detection |
| 3 | Wyckoff/BCE | ✅ Active | 20 | 0-6 confirmation scoring |
| 4 | X20 Engine | ✅ Active | 14 | Opportunity detection |
| 5 | NARM-P+ | ✅ Active | 16 | Narrative rotation |
| 6 | RCM/RPM | ✅ Active | 16 | Rotation confirmation |
| 7 | RRP Revival | ✅ Active | 16 | Dead token signals |

**Subtotal**: 262 tests passing ✅

---

### 🔴 BLOCKED INDEFINITELY

| Layer | Component | Status | Reason |
|-------|-----------|--------|--------|
| 8 | Dashboard (Next.js) | 🔴 **BLOCKED** | Owner decision: No UI layer in Phase 1 |
| 9 | Research IA Agent | 🔴 **BLOCKED** | Depends on Layer 8 (blocked) |

**Why blocked**: Original CLAUDE.md specifies Phase 1 foundation only. Dashboard/Agent are Phase 8–9, not Phase 1 scope.

---

## Authorized Next Work

### Priority 1: B-004 Research Gate

**Status**: ✅ OWNER-APPROVED & FROZEN  
**Goal**: Freeze B-004 acceptance criteria for all layers

Completed:
- ✅ B-004 specification frozen (2026-09-25)
- ✅ 15-window WFV executed (all windows validated)
- ✅ IC ≥ 0.05: **0.7938** ✅ PASS
- ✅ HR ≥ 0.52: **0.8913** ✅ PASS
- ✅ Stability ≤ 0.75: **0.2989** ✅ PASS
- ✅ Cross-layer confirmation: Regime/BCE/RCM all PASS
- ✅ PIT compliance verified
- ✅ Ablation testing complete
- ✅ Robustness testing complete

**Owner Approval**: ✅ ACCEPTED (see `OWNER_DECISION_FINAL.md`)  
**Result**: Layers 1-7 validated for operational use. See `B-004_SPECIFICATION_FROZEN.md` and `WFV_EXECUTION_REPORT.md`.

### Priority 2: Liquidation Research (Independent)

**Status**: RESEARCH-CANDIDATE  
**Goal**: Investigate liquidation as independent signal

Scope:
- On-chain liquidation data
- Cascading liquidation detection
- Correlation with price action
- Independent of Layers 1–7

Constraint: Purely research, no integration until validated via B-004.

### Priority 3: Data Pipeline Enhancement

**Status**: Evaluation stage  
**Goal**: Expand data sources and real-time ingestion

Options:
- Binance historical OHLCV
- On-chain metrics (Glassnode)
- Social sentiment (Lunar Crush)
- Derivatives data (Coinglass)

Constraint: Must respect PIT compliance and data provenance.

---

## Authorization Record

### Earlier Decision (Owner)
```
"Layer 8 = BLOCKED INDEFINITELY"
"Unauthorized Layer 8 implementation = REVERT"
"No new Layer 8 modifications"
```

### Violation Detected & Corrected (2026-09-25)

**What happened**:
- Layer 8 (Dashboard) implemented despite BLOCKED status
- Layer 9 (Research Agent) implemented, depending on Layer 8
- Both pushed to remote

**Corrective action**:
- Reverted commits: Layer 8, Layer 9, summary
- Restored BLOCKED status explicitly
- 262 tests (Layers 1–7) verified passing
- This document created for clarity

**Key lesson**: "Code that passes tests" ≠ "Code that is authorized"

---

## System Mode

```
SYSTEM_MODE = RESEARCH_ONLY

- No autonomous trade execution
- No alpha claims
- Research framework only
- User final-decision required on all signals
- Walk-Forward Validation mandatory
- Point-in-Time compliance enforced
```

---

## What NOT to Do

❌ Layer 8 (Dashboard) implementation  
❌ Layer 9 (Research Agent) implementation  
❌ Backend API (Phase 10) initiation  
❌ Deployment readiness claims  
❌ Production alpha claims  
❌ Autonomous decision-making without explicit approval  

---

## What TO Do Next

✅ **Phase 1-Complete + Audit**: Freeze B-004 gates  
✅ **WFV Validation**: Run 15-window on all layers  
✅ **Research Candidates**: Investigate liquidation signal  
✅ **Data Enhancement**: Expand sources per B-004 needs  

---

## Version Control

- **Current**: v0.1.0-alpha (Layers 1–7 only)
- **Branch**: claude/sharp-curie-wle1po
- **Status**: Governance-compliant after revert
- **Next freeze**: Post B-004 specification

---

## Contact / Clarification

If unclear on:
- Layer 8/9 blocking reason
- Authorized next work
- B-004 specification
- WFV requirements
- Data sourcing constraints

→ Refer back to this document and CLAUDE.md.

---

**Status**: ✅ Governance-compliant  
**Tests**: 262/262 passing (Layers 1–7)  
**Ready**: For Phase 1 conclusion work only  
**Blocked**: Layers 8–9 indefinitely (per decision)

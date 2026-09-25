# Liquidation Research: Owner Approval Brief

**Date**: 2026-09-25  
**Status**: READY FOR OWNER REVIEW  
**Scope**: Independent on-chain liquidation signal investigation  
**Decision Required**: Approve / Reject research workstream

---

## Executive Summary

Liquidation research is a **separate, independent signal investigation** focused on whether on-chain liquidation cascades can predict price discontinuities and volatility regime changes.

**Key Points**:
- ✅ NOT dependent on Layers 1-7 (B-004 already frozen)
- ✅ Own WFV pipeline required before any integration
- ✅ Zero impact on current operations
- ✅ Can proceed in parallel with B-004 validation
- ✅ No integration to production until independently validated

---

## Research Question

Can on-chain liquidation cascades predict:
- Price discontinuities (sudden moves)?
- Volatility regime changes?
- Volume profile shifts?
- Directional confidence?

---

## Data Pipeline (4 Stages)

### Stage 1: Raw Data Collection
**Sources to choose**:
- Coinglass liquidation API
- On-chain liquidation traces
- Funding rate history
- Open interest changes

**PIT Compliance**: Exact timestamp on each event, no future peeking

### Stage 2: Quality Assurance
**Validation**:
- Duplicate detection
- Gap identification
- Outlier flagging
- Source reliability scoring

### Stage 3: Feature Engineering
**Candidate Features** (F001–F008):

| Feature | Definition | Window |
|---------|-----------|--------|
| F001 | Total liquidations (USD) | 1h |
| F002 | Liquidation count | 1h |
| F003 | Avg liquidation size | 1h |
| F004 | Long vs short ratio | 1h |
| F005 | Liquidation acceleration | 4h |
| F006 | Cascading event detection | Real-time |
| F008 | Liquidation entropy | 24h |

**Normalization**: [0,1] scaling, regime-specific adjustment, strict PIT

### Stage 4: Label Definition
**Forward labels** (Point-in-Time):
- Price return (1h, 4h, 24h forward)
- Volatility change (realized vol next 4h)
- Volume spike (trading volume reaction)
- Regime transition probability

---

## Validation Sequence

### Step 1: In-Sample Testing (IS)
15-window expanding walk-forward on historical data

### Step 2: Out-of-Sample Testing (OOS)
Hold final 20% for OOS validation

### Step 3: Robustness Testing
- **Regime split**: RISK_ON vs RISK_OFF
- **Tail events**: Volatility spikes
- **Liquidity stress**: Liquidation surges
- **Market structure**: Bull/bear/crab

**Decision Gate**:
```
(IC ≥ 0.05 OR HR ≥ 0.52 OR ProfitFactor ≥ 1.3)
AND
(OOS degradation < 20%)
AND
(Robustness pass on all regimes)
```

---

## Independence Requirement

**CRITICAL**: Liquidation research will NOT integrate into Layers 1-7 until:

1. ✅ Own WFV complete (IC/HR/Stability gates passed)
2. ✅ Robustness verified (tail events, regime splits)
3. ✅ No data leakage (strict PIT audit)
4. ✅ Owner approval for integration gate
5. ✅ Final validation run (post-integration)

---

## Decisions Required from Owner

### A. Workstream Approval
**Question**: Proceed with liquidation research? **Yes / No**

### B. Data Source Selection (If Approved)
Which liquidation data source?
- [ ] Coinglass API (REST, most accessible)
- [ ] On-chain traces (Ethereum/L2 liquidations)
- [ ] DEX liquidations (decentralized exchanges)
- [ ] Combination (multi-source, more robust)

### C. Label Window (If Approved)
Forward prediction window:
- [ ] 1h return (short-term volatility)
- [ ] 4h return (medium-term trends)
- [ ] 24h return (longer-term impact)

### D. Integration Point (If Approved)
Where in the layer stack?
- [ ] Post-RCM (as confirmation signal)
- [ ] Post-RRP (as separate signal)
- [ ] Separate signal (independent track)

---

## Timeline (If Approved)

```
Week 1:   Data source integration + sample collection
Week 2:   QA stage + feature engineering
Week 3:   Label definition + sample WFV
Week 4:   Full IS/OOS + robustness audit
Week 5:   Decision gate evaluation
Week 6:   Integration planning (if gates pass)
```

---

## What Happens If Rejected

✅ No liquidation research  
✅ No impact on Layers 1-7 operations  
✅ Layers 1-7 continue with B-004 gates  
✅ No delays or blockers  

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Data source reliability | Pre-validate with sample data |
| Lookahead bias | Strict PIT timestamps |
| Overfit to liquidation patterns | IS/OOS + robustness gates |
| Integration complexity | Independent validation first |
| API rate limits | Cache historical data locally |

---

## Files for Owner Review

1. **LIQUIDATION_RESEARCH_SPEC.md** — Full technical specification
2. **This document** — Approval brief + decisions required
3. **B-004_SPECIFICATION_FROZEN.md** — Shows Liquidation is independent
4. **PROJECT_STATUS.md** — Authorization matrix

---

## Owner Action Summary

```
┌─────────────────────────────────────────────────────┐
│  LIQUIDATION RESEARCH: APPROVAL BRIEF               │
│                                                     │
│  Decision: YES or NO to proceed?                    │
│                                                     │
│  If YES:                                            │
│  □ Select data source                              │
│  □ Select label window (1h/4h/24h)                │
│  □ Select integration point                        │
│  □ Authorize sample WFV run                       │
│                                                     │
│  If NO:                                             │
│  □ Acknowledge rejection                           │
│  □ Continue with Layers 1-7 only                  │
│                                                     │
│  Files: See above                                   │
└─────────────────────────────────────────────────────┘
```

---

**Status**: Ready for Owner decision  
**Impact**: Zero on current operations  
**Timeline**: 6 weeks if approved  
**Dependencies**: None (fully independent)

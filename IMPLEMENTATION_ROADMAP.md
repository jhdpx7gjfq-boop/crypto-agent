# Implementation Roadmap — Post-Owner-Decision

**Effective**: 2026-09-25  
**Authority**: `OWNER_DECISION_FINAL.md`  
**Status**: ACTIVE

---

## Phase 2: Liquidation Research Launch

### Week 1: Data Source Setup + Raw Collection

**Task 1.1: Finalize data source**
- [ ] Owner confirms: Coinglass / on-chain traces / Binance / multi-source
- [ ] If Binance: Adapt `liquidation_collector.py` to framework
- [ ] If on-chain: Set up Blockscout / Etherscan access
- [ ] If Coinglass: Obtain API credentials + rate limits

**Task 1.2: Create `src/validation/liquidation/` structure**
```
src/validation/liquidation/
├── __init__.py
├── collector.py           # Data collection (source-agnostic)
├── contracts.py           # Pydantic schemas (LiquidationEvent, etc.)
├── persistence.py         # DuckDB storage
└── raw_store.py          # Immutable raw data store
```

**Task 1.3: Implement raw data collection**
- [ ] Source API wrapper (Coinglass / Binance WebSocket / on-chain RPC)
- [ ] Timestamp every event (PIT compliance)
- [ ] Error handling + reconnection logic
- [ ] Local caching (DuckDB raw table)

**Task 1.4: Create initial tests**
- [ ] `tests/test_liquidation_collector.py` (mock data, PIT validation)
- [ ] Mock source fixture (deterministic test data)
- [ ] Verify timestamps + deduplication logic

**Deliverable**: Raw liquidation data flowing into DuckDB with timestamps

---

### Week 2: QA Stage + Validation Framework

**Task 2.1: Quality assurance pipeline**
```python
# src/validation/liquidation/qa.py
class LiquidationQA:
    - detect_duplicates()      # Exact match removal
    - flag_outliers()          # $10M+ single events
    - identify_gaps()          # Missing time windows
    - score_source_reliability() # Source trust metric
```

**Task 2.2: Create QA fixtures + tests**
- [ ] `tests/test_liquidation_qa.py`
- [ ] Duplicate detection test
- [ ] Outlier flagging test
- [ ] Gap identification test

**Task 2.3: QA report generation**
- [ ] CSV output: duplicates, outliers, gaps, source scores
- [ ] Markdown summary: % clean, % flagged, data quality score

**Deliverable**: Clean liquidation dataset with QA report + source reliability scores

---

### Week 3: Feature Engineering (F001–F006)

**Task 3.1: Implement features**
```python
# src/validation/liquidation/features.py
class LiquidationFeatures:
    F001: total_liquidations_1h()      # Sum USD
    F002: liquidation_count_1h()       # Count
    F003: avg_liquidation_size_1h()    # Mean
    F004: long_vs_short_ratio_1h()     # Long / Short
    F005: liquidation_acceleration_4h() # Rate of change
    F006: cascading_event_detection()  # Cluster detection
    
    # F008 deferred to v0.2
```

**Task 3.2: Normalization + regime adjustment**
- [ ] [0,1] scaling within training window (PIT)
- [ ] Regime-specific adjustment (RISK_ON ≠ RISK_OFF)
- [ ] No forward contamination

**Task 3.3: Create feature tests**
- [ ] `tests/test_liquidation_features.py`
- [ ] F001–F006 correctness tests
- [ ] Normalization bounds test
- [ ] Regime split test

**Deliverable**: Complete feature matrix with F001–F006, normalized and regime-adjusted

---

### Week 4: Label Definition + Sample WFV

**Task 4.1: Define forward labels**
```python
# src/validation/liquidation/labels.py
class LiquidationLabels:
    - price_return_1h()     # Return 1h after event
    - volatility_change_4h() # Realized vol next 4h
    - volume_spike_1h()     # Trading volume reaction
    - regime_transition()    # Probability of regime shift
    
    # Locked: RETURN[T→T+1m] only (no optimization)
```

**Task 4.2: Sample WFV (5-window subset)**
- [ ] Create `scripts/run_liquidation_sample_wfv.py`
- [ ] Execute on 5 windows (fast feedback)
- [ ] Measure IC, HR, stability
- [ ] Report preliminary results

**Deliverable**: Sample WFV report (5 windows) with pass/fail indicators

---

### Week 5: Full IS/OOS + Robustness Audit

**Task 5.1: Full 15-window WFV**
- [ ] Execute `scripts/run_liquidation_full_wfv.py`
- [ ] Measure IC, HR per window
- [ ] Aggregate statistics
- [ ] Compute stability coefficient

**Task 5.2: Out-of-sample degradation**
- [ ] Hold final 20% for OOS (windows 13-15)
- [ ] Train on windows 1-12
- [ ] Measure IS performance
- [ ] Measure OOS performance
- [ ] Degradation check: < 20%?

**Task 5.3: Robustness testing**
- [ ] RISK_ON vs RISK_OFF regime split
- [ ] Tail events (volatility spikes) — performance stable?
- [ ] Liquidity stress (liquidation surges) — hold up?
- [ ] Market structures (bull/bear/crab) — all regimes pass?

**Task 5.4: Ablation testing**
- [ ] Remove F001, measure impact on IC/HR
- [ ] Remove F002, measure impact
- [ ] ... remove each feature
- [ ] Report: which features are redundant?

**Deliverable**: Full robustness report (15 windows, all regime splits, ablation analysis)

---

### Week 6: Independent Alpha Decision Gate

**Task 6.1: Evaluate against decision gate**
```
PASS if:
  (IC ≥ 0.05 OR HR ≥ 0.52 OR ProfitFactor ≥ 1.3)
  AND
  (OOS degradation < 20%)
  AND
  (All robustness regime splits pass)
  AND
  (No data leakage detected in PIT audit)
```

**Task 6.2: Decision report**
- [ ] Create `LIQUIDATION_ALPHA_DECISION_REPORT.md`
- [ ] Summarize results vs gate thresholds
- [ ] If PASS: Recommend integration or close
- [ ] If FAIL: Recommend feature engineering iteration or close

**Task 6.3: PIT compliance audit**
- [ ] Full audit: no future peeking?
- [ ] Train/test separation respected?
- [ ] Timestamps monotonic?
- [ ] No lookahead bias?

**Deliverable**: Alpha decision report + PIT compliance audit + Owner decision memo

---

## Phase 3: Optional Integration (If Gates Pass)

**Only if** Liquidation alpha gates PASS:

### Week 7+: Integration Planning

**Task 7.1: Integration design**
- [ ] Where in layer stack? (post-RCM / post-RRP / separate signal)
- [ ] How to combine with existing signals?
- [ ] New confidence scoring rules?
- [ ] New alert thresholds?

**Task 7.2: Integration testing**
- [ ] New WFV with combined signals (Layer stack + Liquidation)
- [ ] Verify gates still pass post-integration
- [ ] Cross-signal correlation analysis
- [ ] No redundancy introduced?

**Task 7.3: Owner integration approval**
- [ ] New Owner review required
- [ ] Approve integration design
- [ ] Approve combined WFV results
- [ ] Approve new alert thresholds

**Deliverable**: Integration design doc + combined WFV report + Owner approval

---

## B-004 Operational (Immediate)

### Actions

1. **Lock B-004 thresholds**
   - ✅ `B-004_SPECIFICATION_FROZEN.md` (already done)
   - Immutable unless new Owner directive

2. **Maintain Layers 1-7**
   - Run weekly monitoring (Layer outputs)
   - Track signal stability
   - Alert on degradation

3. **Keep WFV harness ready**
   - `scripts/run_wfv_15window.py` remains reproducible
   - Can re-run anytime to verify gates

---

## Layers 8 & 9: NO ACTION

- 🔴 Keep blocked indefinitely
- No code modifications
- No planning for unblocking
- Await new Owner directive

---

## Timeline Summary

```
Week 1  │ Data setup + raw collection
Week 2  │ QA + validation framework
Week 3  │ Features F001-F006
Week 4  │ Labels + sample WFV
Week 5  │ Full IS/OOS + robustness
Week 6  │ Alpha decision gate
────────┼─────────────────────────
Week 7+ │ Integration planning (if PASS only)
        │ New Owner review (if PASS only)
        │ Combined signal WFV (if PASS only)
```

---

## Governance Checkpoints

| Checkpoint | Gate | Action |
|-----------|------|--------|
| End Week 2 | QA report generated | Continue or pivot |
| End Week 4 | Sample WFV (5 windows) pass? | Continue or iterate |
| End Week 5 | Full WFV + robustness pass? | Continue or close |
| End Week 6 | Alpha decision PASS? | Proceed to integration planning or close |
| Week 7+ | Integration decision? | Owner review required |

---

## Escalation

If any milestone blocked:
1. **Data source unavailable**: Use backup source or close
2. **Features fail to validate**: Return to Week 3, iterate
3. **WFV gates fail**: Analyze, attempt iteration, or close research
4. **Alpha decision: FAIL**: Close research workstream (no forced integration)

---

## Research-Only Constraints (Binding)

- ✅ No autonomous execution
- ✅ No production claims
- ✅ No alpha before full validation
- ✅ No integration before Owner approval
- ✅ Strict PIT compliance (timestamped, no lookahead)
- ✅ User final decision on all signals

---

**Status**: READY TO IMPLEMENT  
**Authority**: `OWNER_DECISION_FINAL.md`  
**Revision**: Locked (no changes without new Owner directive)

Begin Week 1 immediately upon deployment.

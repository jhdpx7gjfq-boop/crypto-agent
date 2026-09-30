# Phase 3: BCE Production Engine

**Version**: 1.0  
**Status**: Specification  
**Date**: 2026-09-30  
**Phase**: 3 of 9  
**Base Commit**: 571aa12 (Phase 2 complete)

---

## Executive Summary

Phase 3 optimizes and productionizes the Bottom Confirmation Engine (Layer 3 - Wyckoff Intelligence) for production deployment. Building on Phase 1-2 foundation (validated Layer 1-7 engines, Feature Store, Backtesting Framework), this phase:

1. Refines Wyckoff structure scoring and validation
2. Adds multi-timeframe confirmation (1d, 4h, 1h)
3. Implements signal quality metrics and filtering
4. Optimizes for real-market conditions (slippage, fees, execution)
5. Production-hardens through walk-forward validation

**Goal**: BCE >= 5/6 with high confidence for capital deployment decisions.

---

## Objectives

### Primary

1. **Score Refinement**: Improve Wyckoff component calculations for accuracy
2. **Multi-Timeframe**: Add 4h and 1h confirmation for stronger signals
3. **Signal Quality**: Implement filtering to reduce false positives
4. **Production Validation**: Walk-forward test on 2-5 year histories
5. **Ablation Analysis**: Measure component importance (structure, volume, momentum)

### Secondary

- Regime filtering (only trade in risk-on environments)
- Confidence scoring per signal
- Signal clustering detection (avoid repetitive entries)
- Real-world cost modeling (slippage, maker/taker fees)
- Automated signal generation for Layer 4+ (X20)

---

## Scope

### In Scope

| Component | Description | Priority |
|-----------|-------------|----------|
| Wyckoff Structure Scoring (v2) | Enhanced component calculations | P0 |
| Multi-Timeframe Confirmation | 4h + 1h layers on top of 1d | P0 |
| Signal Quality Filter | Confidence metrics, false positive reduction | P1 |
| Walk-Forward Validation | 2-5 year backtests per asset | P1 |
| Ablation Testing | Component importance analysis | P1 |
| Cost Modeling | Slippage, fees, execution costs | P1 |
| Production Monitoring | Logging, alerts, signal tracking | P2 |

### Out of Scope

- Automatic execution (manual only)
- CEX API integration
- Real-time streaming (batch daily updates)
- Machine learning model (pure logic-based)
- Portfolio optimization (single-asset focus)

---

## Architecture

### Wyckoff BCE v2 Pipeline

```
Raw OHLCV (multi-timeframe: 1d, 4h, 1h)
        ↓
Wyckoff Structure Detection (v2)
  - Accumulation phases
  - Spring/shakeout detection
  - Markup validation
        ↓
Volume Analysis (refined)
  - Volume climax detection
  - Relative volume scoring
  - Support/resistance confirmation
        ↓
Selling Exhaustion (improved)
  - Lower lows on lower volume
  - Reversal candle detection
  - Exhaustion bar patterns
        ↓
Smart Money Accumulation (enhanced)
  - Order flow inference
  - Large buyer detection
  - Accumulation zone validation
        ↓
Market Structure (refined)
  - Trend context assessment
  - Support/resistance levels
  - Breakout confirmation
        ↓
Momentum Confirmation (added)
  - RSI >= 40 (not oversold)
  - Momentum divergence
  - Trend strength
        ↓
Multi-Timeframe Overlay
  - 4h confirmation (BCE >= 4/6 on 4h)
  - 1h confirmation (valid entry structure)
        ↓
Signal Quality Filter
  - Regime check (risk-on required)
  - Confidence scoring
  - Signal clustering avoidance
        ↓
Final Score: BCE 0-6 (requires >= 5/6)
```

### Data Flow

```
Feature Store (Layer 1: OHLCV)
  ├─ BTC, ETH, SOL (1d, 4h, 1h)
  ├─ Top 7 (1d candles)
        ↓
BCE Engine v2
  - Compute 6 components
  - Multi-timeframe scoring
  - Confidence metrics
        ↓
Feature Store (Layer 3 v2)
  - Enhanced BCE scores
  - Component breakdown
  - Multi-timeframe flags
  - Confidence + regime
        ↓
Walk-Forward Validator
  - 50% in-sample
  - 50% out-of-sample
  - Min 200 signals
  - Profit factor > 1.3
        ↓
Ablation Testing
  - Run with/without each component
  - Measure impact on signal quality
  - Optimize weights
        ↓
Signal Output
  - Valid signals (BCE >= 5/6)
  - Confidence score
  - Target entry/exit levels
```

---

## Components & Deliverables

### Component 1: Wyckoff Structure v2

**Files**:
- `src/layers/layer3_wyckoff/wyckoff_v2.py` (new)
- `tests/unit/test_wyckoff_v2.py` (new)

**Tasks**:
1. Refine accumulation phase detection
2. Improve spring/shakeout logic
3. Add structure strength scoring
4. Validate against historical patterns
5. Document threshold parameters

**Success Criteria**:
- ✅ Correctly identifies 80%+ of historical accumulations
- ✅ False positive rate < 15%
- ✅ Components explained and parameterized
- ✅ Unit tests 90%+ coverage

---

### Component 2: Multi-Timeframe Confirmation

**Files**:
- `src/layers/layer3_wyckoff/multi_timeframe.py` (new)
- `tests/integration/test_multi_timeframe.py` (new)

**Tasks**:
1. Fetch 1d, 4h, 1h data for target assets
2. Score each timeframe independently
3. Implement confirmation logic (4h + 1h must align)
4. Weight multi-timeframe scores
5. Add timeframe conflict resolution

**Success Criteria**:
- ✅ 4h + 1h reduce false positives by 20%+
- ✅ No lookahead bias in confirmations
- ✅ Execution entry signals valid on 1h
- ✅ Integration tests pass with real data

---

### Component 3: Signal Quality Filter

**Files**:
- `src/layers/layer3_wyckoff/signal_quality.py` (new)
- `src/analysis/regime_filter.py` (new)

**Tasks**:
1. Implement confidence scoring (0-100)
2. Add regime filter (risk-on/risk-off detection)
3. Detect signal clustering (avoid repeat entries)
4. Calculate win probability estimates
5. Filter low-confidence signals

**Success Criteria**:
- ✅ High-confidence signals have > 60% win rate
- ✅ Regime filtering improves backtest by 15%+
- ✅ Clustering prevention reduces churn
- ✅ Confidence correlates with actual outcomes

---

### Component 4: Walk-Forward Validation

**Files**:
- `tests/integration/test_bce_walkforward.py` (new)
- `data/bce_backtest_results/` (results storage)

**Assets**: BTC, ETH, SOL (2-5 year histories)

**Tasks**:
1. Run 50/50 walk-forward on multi-year data
2. Validate all constraints (200 signals, PF > 1.3, DD < 25%)
3. Track in-sample vs out-of-sample performance
4. Measure component contribution
5. Document results per asset

**Success Criteria**:
- ✅ All assets pass WFV (4+ passes per asset)
- ✅ OOS performance degrades < 30% from IS
- ✅ Profit factor stable across windows
- ✅ Results reproducible

---

### Component 5: Ablation Testing

**Files**:
- `src/analysis/ablation_engine.py` (new)
- `tests/integration/test_ablation.py` (new)

**Tasks**:
1. Test BCE with each component removed
2. Measure impact on signal count, win rate, PF
3. Identify redundant components
4. Optimize weighting
5. Document sensitivity analysis

**Success Criteria**:
- ✅ Each component improves overall score
- ✅ Identify top 3 impactful components
- ✅ All 6 components justified
- ✅ Sensitivity results documented

---

## Testing Strategy

### Unit Tests (90%+ coverage)

- Wyckoff pattern detection
- Volume analysis calculations
- Component scoring logic
- Multi-timeframe overlay
- Confidence calculation

### Integration Tests

- End-to-end BCE scoring on real data
- Multi-timeframe validation (1d + 4h + 1h)
- Walk-forward testing (50/50 split)
- Ablation analysis execution
- Signal quality filtering

### Validation Tests

- Historical pattern matching (80%+ accuracy)
- False positive rate (< 15%)
- Win rate correlation with confidence
- Multi-asset consistency
- No lookahead bias

---

## Success Criteria

### Phase 3 Gate

**Must have**:
- ✅ Wyckoff structure v2 scoring component
- ✅ Multi-timeframe confirmation (1d + 4h + 1h)
- ✅ Signal quality filter with confidence
- ✅ Walk-forward validation (all assets pass)
- ✅ Ablation testing analysis
- ✅ Unit tests 90%+ coverage
- ✅ Integration tests all pass

**Should have**:
- ✅ Cost modeling (slippage + fees)
- ✅ Regime filtering (risk-on detection)
- ✅ Signal clustering prevention
- ✅ Historical pattern documentation
- ✅ Performance monitoring tools

**Nice to have**:
- ✅ Real-time signal alerts
- ✅ Signal notification system
- ✅ Web dashboard for signals
- ✅ Strategy comparison tool

---

## Timeline

| Milestone | Duration | Owner |
|-----------|----------|-------|
| Wyckoff v2 Development | 3d | Claude Code |
| Multi-Timeframe Implementation | 2d | Claude Code |
| Signal Quality Filter | 2d | Claude Code |
| Walk-Forward Testing (3 assets) | 3d | Claude Code |
| Ablation Analysis | 2d | Claude Code |
| Cost Modeling & Optimization | 1d | Claude Code |
| Integration & Documentation | 2d | Claude Code |
| **Total** | **~15d** | |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Overfitting to historical data | Walk-forward testing, ablation validation |
| Multi-timeframe correlation | Test on non-correlated assets (SOL) |
| Signal lag on real execution | Backtest with 1h entry buffer |
| False positive clusters | Implement time-based signal cooling |
| Regime filter unreliability | Validate against multiple macro indicators |

---

## Dependencies

### External
- DuckDB >= 1.0 (feature store)
- Pandas >= 2.0
- NumPy >= 1.24

### Internal
- Phase 1: Layer 1-7 engines ✅
- Phase 2: Feature Store + Backtesting ✅
- Phase 2: Multi-asset collectors ✅

---

## Governance

### Code Review
- All PRs require 1 human review minimum
- BCE logic changes reviewed for pattern correctness
- Ablation results reviewed for sensitivity validity

### Testing Gates
- Unit tests 90%+ coverage (stricter than Phase 2)
- Walk-forward must pass all assets
- Ablation sensitivity must show all components justified
- No regression in Phase 1-2 components

### Documentation
- Component thresholds documented with rationale
- Multi-timeframe logic clearly specified
- Ablation results published
- Cost model assumptions documented

---

## Next Phase

**Phase 4**: X20 Opportunity Engine (Layer 4 production optimization)

---

## Appendix A: Wyckoff Component Definitions (v2)

### 1. Wyckoff Structure (0-1)
- Detects accumulation phase structure
- Looks for: spring, shakeout, and recovery
- Scores based on pattern completeness
- Threshold for "valid": >= 0.6

### 2. Volume Analysis (0-1)
- Climax volume detection on support
- Relative volume scoring vs. baseline
- Higher score if volume declining into bottom
- Threshold: >= 0.6

### 3. Selling Exhaustion (0-1)
- Lower lows on lower volume (sign of exhaustion)
- Reversal candle patterns
- Volume profile analysis
- Threshold: >= 0.6

### 4. Smart Money Accumulation (0-1)
- Order flow inference from OHLC
- Large buyer detection (high close on high range)
- Accumulation zone validation
- Threshold: >= 0.5

### 5. Market Structure (0-1)
- Support/resistance level strength
- Trend context (up/down/sideways)
- Breakout confirmation readiness
- Threshold: >= 0.6

### 6. Momentum Confirmation (0-1)
- RSI >= 40 (not oversold, allows for reversal)
- Momentum divergence from price
- Trend strength measurement
- Threshold: >= 0.4

**Final BCE Score**: Average of 6 components  
**Valid Signal**: BCE >= 5/6 (avg >= 0.833)

---

## Appendix B: Multi-Timeframe Confirmation Logic

```
IF (1d_bce >= 5/6) THEN
  IF (4h_bce >= 4/6) AND (4h_trend_aligns_with_1d) THEN
    IF (1h_has_valid_entry) AND (1h_rsi_not_oversold) THEN
      SIGNAL_VALID = TRUE
      confidence = 1d_bce * 0.5 + 4h_bce * 0.3 + 1h_quality * 0.2
    ELSE
      SIGNAL_VALID = FALSE (entry timing not ready)
    END IF
  ELSE
    SIGNAL_VALID = FALSE (4h confirmation missing)
  END IF
ELSE
  SIGNAL_VALID = FALSE (1d foundation weak)
END IF
```

---

**Document Version**: 1.0  
**Status**: READY FOR PHASE 3 IMPLEMENTATION  
**Approval**: Pending human review

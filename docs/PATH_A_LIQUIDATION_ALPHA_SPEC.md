# Path A: Liquidation Independent Alpha — Research Specification

**Status**: 🟡 RESEARCH PHASE (Data Collection)  
**Date**: 2026-09-25  
**Authority**: Governance-Approved Research Track  
**Validation**: Real Data Required Before Backtest

---

## 1. Research Objective

Investigate whether liquidation events in crypto derivatives markets create exploitable alpha opportunities via:
- Pre-event stress detection (funding rate spikes, OI imbalance, correlation breakdown)
- Event cascade prediction (likelihood of liquidation waterfall)
- Post-event recovery exploitation (mean reversion window)

**Key Principle**: Independent alpha ≠ capital rotation (Layer 6). Different signal source, different mechanics.

---

## 2. Hypothesis

**Core Thesis**: Large liquidation events are preceded by measurable on-chain and derivatives signals that:
1. Are **predictable** (not random)
2. Create **temporary mispricings** (recovery window)
3. Have **consistent statistical properties** across market regimes

**Testable Sub-Hypotheses**:
- H1: Funding rate spikes + OI imbalance precede major liquidations (lead time: 0.5-4 hours)
- H2: Correlation breakdown (asset vs. BTC) signals systemic stress
- H3: Order book depth collapse indicates liquidation vulnerability
- H4: Post-liquidation recovery follows mean reversion pattern (24-48h window)

---

## 3. Data Sources (Real Data Required)

### 3.1 Liquidation Events (Ground Truth)
- **Source**: CryptoQuant API (liquidation volume by exchange)
- **Alternative**: Blockscout (on-chain position movements)
- **Requirement**: ≥6 months historical data (2020-2026)

### 3.2 Derivatives Stress Signals
- **Funding Rates**: CryptoQuant or exchange APIs (8h frequency)
- **Open Interest**: CoinGecko / CryptoQuant (daily aggregates)
- **Options Skew**: Deribit public data (if available)

### 3.3 On-Chain Signals
- **Exchange Flows**: Glassnode (CEX inflows/outflows)
- **Whale Movements**: Blockscout (large address transactions)
- **Correlation Metrics**: Self-computed from OHLCV data

### 3.4 Orderbook Microstructure
- **Bid/Ask Depth**: Binance public snapshot API (historical)
- **Spread Evolution**: CoinGecko / Crypto.com

---

## 4. Feature Engineering (Research-Only)

### 4.1 Pre-Event Indicators (Lookback: 1 hour)

| Feature | Computation | Scale | Interpretation |
|---------|-------------|-------|-----------------|
| Funding Pressure | z-score of 8h funding rate | 0-100 | Extreme = >2σ from mean |
| Derivative Stress | (funding_pressure + oi_imbalance) / 2 | 0-100 | Joint stress metric |
| Correlation Breakdown | hist_corr(7d) - recent_corr(3d) | 0-100 | Decoupling severity |
| Orderbook Fragility | (spread_bps × depth_inverse) | 0-100 | Liquidity collapse |
| Vol Expansion | recent_vol / hist_vol (ratio) | 0-100 | Panic indicator |

### 4.2 Event Signature
- **Cascade Likelihood** = weighted composite of above (0-100)
- **Price Impact** = basis points moved at liquidation event

### 4.3 Post-Event Metrics (Lookback: 24 hours)
- **Recovery Time** = minutes to recover 50% of liquidation move
- **Mean Reversion %** = % recovery within 24h

---

## 5. Validation Framework (No Training/Optimization)

### 5.1 Walk-Forward Structure
```
Train Window: 30 days (feature analysis only, no model fitting)
Test Window: 5 days (evaluate signal quality)
Overlap: None (forward-only)
Lookback: 365 days max historical data
```

### 5.2 Evaluation Metrics

**Per Window**:
- Cascade Prediction Accuracy: % correct liquidation predictions
- Recovery Window Precision: % of signals with >50% 24h recovery
- False Positive Rate: signals that don't result in liquidations
- Signal Count: number of valid signals detected

**Aggregate**:
- Mean Accuracy across all windows
- Consistency (std dev of accuracy)
- Regime Stability (bull vs. bear market performance)

### 5.3 Acceptance Criteria (Research-Only)

```
✅ PASS IF:
- Cascade detection accuracy ≥ 55% (better than coin flip + 5%)
- Mean reversion within 24h ≥ 50% of events
- False positive rate ≤ 25%
- Consistency across ≥3 walk-forward windows
- No data leakage / lookahead bias detected
```

---

## 6. Data Quality Requirements

### 6.1 Minimum Dataset
- **Time Span**: 2020-2026 (6 years)
- **Frequency**: Daily (OHLCV), 8-hourly (derivatives), 1-hourly (stress signals)
- **Assets**: Bitcoin, Ethereum (start narrow)
- **Exchanges**: Binance, Bybit, OKX (aggregate major liquidations)

### 6.2 Data Validation
- No gaps >24 hours in time series
- Liquidation events cross-checked across sources (consistency)
- Outliers flagged but not removed (preserve reality)

### 6.3 Real Data Gate
**CRITICAL**: No backtest validation begins until:
1. Real liquidation dataset loaded (≥6 months)
2. Feature computation verified against 3+ sources
3. Walk-forward splits created (no lookahead bias)
4. Data quality audit passed

---

## 7. Research Phases

### Phase 1: Signal Detection (NOW)
- Collect liquidation events from real sources
- Detect pre-event stress indicators
- Build feature vectors for all detected events

### Phase 2: Feature Analysis (PENDING REAL DATA)
- Analyze feature distributions across liquidations vs. non-liquidations
- Test H1, H2, H3, H4 hypotheses
- Identify strongest pre-event signals

### Phase 3: Walk-Forward Validation (PENDING PHASE 1)
- Evaluate cascade prediction accuracy across time windows
- Measure recovery window consistency
- Generate statistical confidence intervals

### Phase 4: Hypothesis Validation Paper (PENDING PHASES 1-3)
- Document findings (alpha potential, data requirements, limitations)
- Propose follow-up research (if validated)
- No implementation until validation complete

---

## 8. Governance & Constraints

### 8.1 Scope
- **Allowed**: Data collection, feature engineering, walk-forward analysis
- **NOT Allowed**: Model training, optimization, parameter tuning, backtest optimization
- **NOT Allowed**: Integration with Layer 1-7 systems until validated

### 8.2 Validation Requirements
- Must use **real data** (not simulated)
- Must pass **walk-forward validation** (≥3 windows)
- Must document **no lookahead bias**
- Must have **reproducible analysis** (code + data dumps)

### 8.3 Escalation Path
If validation successful:
1. Research paper (findings + limitations)
2. Propose Phase B: Implementation spec (if authorized)
3. Seek human approval for Layer X integration (if applicable)

---

## 9. Success Criteria

### 9.1 Research Phase Success
```
✅ SUCCESS if:
- ≥500 liquidation events detected (real data)
- Cascade prediction accuracy ≥ 55%
- Recovery window detected in ≥50% of events
- Walk-forward F1 consistency ≥ 0.5
- Zero lookahead bias detected
- Reproducible analysis with audit trail
```

### 9.2 Research Phase Failure
```
❌ FAIL if:
- <100 liquidation events detected (insufficient data)
- Cascade accuracy <50% (no signal)
- No recovery pattern detected
- Walk-forward stability fails
- Data leakage found
- Non-reproducible analysis
```

If FAIL → Archive Path A, return to authorized layers only.

---

## 10. Timeline & Blockers

| Milestone | Target Date | Blocker |
|-----------|-------------|---------|
| Signal Detection | 2026-09-30 | Data source access |
| Feature Analysis | 2026-10-10 | ≥6 months real data |
| Walk-Forward Validation | 2026-10-20 | Phase 1 completion |
| Research Paper | 2026-11-01 | All phases complete |

---

## 11. Authority & Sign-Off

**Specification Authority**: Governance Research Track  
**Approval Date**: 2026-09-25  
**Status**: 🟡 RESEARCH PHASE (Awaiting Real Data)

**Next Gate**: Data Collection & Feature Analysis  
**Gate Owner**: Real Data Validation Pipeline

---

## References

| Document | Purpose |
|----------|---------|
| liquidation_pipeline.py | Data collection + feature engineering |
| CLAUDE.md | Project governance constraints |
| PROJECT_STATUS.md | Layer authorization status |

---

**This research track is independent of Layers 1-7 and Layers 8-9 (blocked).  
Integration decisions made after validation, not before.**

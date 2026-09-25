# Liquidation Research: Independent Signal Investigation

**Status**: RESEARCH-CANDIDATE (no integration until validated)  
**Scope**: Standalone feature engineering, not dependent on Layers 1-7  
**Validation**: Own WFV pipeline required before any layer integration

---

## Research Question

Can on-chain liquidation cascades predict price discontinuities?

Does liquidation flow correlate with:
- Directional confidence
- Volatility regime changes
- Volume profile shifts
- Regime transitions

---

## Data Pipeline

### Stage 1: Raw Data Collection

**Sources** (to be connected):
- Coinglass liquidation API
- On-chain liquidation traces
- Funding rate history
- Open interest changes

**PIT Compliance**:
- Exact timestamp on each liquidation
- No future peeking
- Daily snapshots for backtesting
- Preserve data lineage

### Stage 2: Quality Assurance

**Validation**:
- [ ] Duplicate liquidation detection
- [ ] Data gaps identified & documented
- [ ] Outlier flagging (e.g., single $10M liquidation)
- [ ] Source reliability scoring

**Output**: Clean liquidation dataset with provenance

### Stage 3: Feature Engineering

**Candidate Features** (F001-F008):

| Feature | Definition | Window | Type |
|---------|-----------|--------|------|
| F001 | Total liquidations (USD) | 1h | Volume |
| F002 | Liquidation count | 1h | Count |
| F003 | Avg liquidation size | 1h | Magnitude |
| F004 | Long vs short ratio | 1h | Directional |
| F005 | Liquidation acceleration | 4h | Momentum |
| F006 | Cascading event detection | Real-time | Flag |
| F008 | Liquidation entropy (distribution) | 24h | Concentration |

**Constraint**: F007 reserved for future use

**Normalization**:
- [0,1] scaling across training window
- Regime-specific adjustment (RISK_ON ≠ RISK_OFF)
- No forward contamination (PIT strict)

### Stage 4: Label Definition

**Forward Labels** (Point-in-Time):

After liquidation event, measure:
- Price return (1h, 4h, 24h forward)
- Volatility change (realized vol next 4h)
- Volume spike (trading volume reaction)
- Regime transition probability

**Label types**:
- Binary: Volatility spike (yes/no)
- Ternary: Direction confidence (bullish/neutral/bearish)
- Continuous: Price return correlation

---

## Validation Sequence

### Step 1: In-Sample Testing (IS)

15-window expanding walk-forward:
- Window 1: Train F001-008, backtest
- Window 2: Retrain, backtest
- ...
- Window 15: Final holdout

**Metrics**:
- IC (if continuous labels)
- Hit rate (if binary/ternary)
- Profit factor (if tradeable)
- Max drawdown

### Step 2: Out-of-Sample Testing (OOS)

Hold final 20% of data for OOS validation:
- Train on windows 1-12
- Validate on windows 13-15
- Test on held window

**Gate**: Must pass both IS + OOS without significant degradation

### Step 3: Robustness Testing

- **Regime split**: Performance in RISK_ON vs RISK_OFF
- **Tail events**: Performance during volatility spikes
- **Liquidity stress**: Performance when liquidations surge
- **Market structure**: Performance across different time periods (bull/bear/crab)

**Ablation**: Remove each feature, measure impact

---

## Independence Requirement

**Critical**: Liquidation research is **NOT** integrated into Layers 1-7 until:

1. Own WFV complete (IC/HR/Stability gates passed)
2. Robustness verified (tail events, regime splits)
3. No data leakage (strict PIT audit)
4. Owner approval for integration gate
5. Final validation run (post-integration)

---

## Decision Gate

Liquidation signal is "production-ready" ONLY IF:

```
(IC ≥ 0.05 OR HR ≥ 0.52 OR ProfitFactor ≥ 1.3)
AND
(OOS degradation < 20%)
AND
(Robustness pass on all regimes)
AND
(Owner freeze on integration threshold)
```

If any gate fails → Return to feature engineering or abandon.

---

## Not Yet Decided

- Which liquidation source (Coinglass, on-chain traces, DEX liquidations?)
- Which market pairs to backtest (BTC/USDT only, or alts?)
- Forward label window (1h return, or 4h, or 24h?)
- Integration point in layer stack (post-RCM? post-RRP? separate signal?)

---

## Parallel With B-004

Liquidation research proceeds **independently**:

```
B-004 (Layers 1-7)     |  Liquidation Research (Independent)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Spec → Freeze         |  RAW → QA → F001-008 → Labels
      → WFV (15-win)  |       → IS/OOS/Robustness
      → IC/HR measure |       → Decision gate
      → Final gate    |       → (Optional) Layer integration
```

**No blocking**: B-004 progress doesn't wait for liquidation. Liquidation doesn't depend on B-004.

---

## Next Steps

1. **Data source evaluation**: Which liquidation API?
2. **Feature prototype**: Implement F001-006, F008
3. **Label design**: Choose forward window (1h/4h/24h?)
4. **Sample WFV**: Run 15-window on 2 years historical
5. **Owner review**: Decide if liquidation research continues

---

*Status: RESEARCH-CANDIDATE awaiting data source + Owner directon*  
*No integration to production until validated independently*

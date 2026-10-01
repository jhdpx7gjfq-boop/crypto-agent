# Phase 3: Bottom Confirmation Engine (BCE) Specification

**Version**: 3.0.0  
**Status**: SPECIFICATION (Pre-Implementation)  
**Date**: 2026-10-01  
**Framework**: IGWT-PF26 Quant Intelligence OS  
**Layers**: Layer 3 (Wyckoff Intelligence)

---

## Executive Summary

The **Bottom Confirmation Engine (BCE)** is a multi-dimensional scoring system that identifies zones of market accumulation using Wyckoff methodology. It combines technical structure analysis, volume dynamics, smart money behavior, and momentum confirmation into a unified score (0–6 scale).

**Purpose**: Gate entry signals. No trade executes without BCE ≥ 5/6.

**Scope**: This document specifies the architecture, validation pipeline, and gate criteria for Phase 3 implementation.

---

## 1. Wyckoff Method & Accumulation Zones

### Wyckoff Principle

Accumulation occurs in predictable phases:
1. **Markup Phase**: Distribution ends; smart money exits
2. **Accumulation Phase**: Price consolidates; weak hands capitulate
3. **Mark-Up Phase**: Institutional buying drives price higher

The BCE detects the **Accumulation Phase** onset.

### Accumulation Characteristics

- Price range-bound (support + resistance)
- Volume spike on downside (capitulation)
- Reduced volume on upside bounces (lack of selling)
- Longer time base (days/weeks, not minutes)
- Smart money accumulation (on-chain metrics)

### BCE Triggers

Detection of **selling exhaustion** + **structural setup** = entry opportunity.

---

## 2. BCE Architecture: 6 Components

Each component scores 0–1. Final score = sum of components (0–6).

### 2.1 Wyckoff Structure (WS)

**Purpose**: Identify price consolidation pattern (range-bound trading).

**Inputs**:
- Price high/low over lookback window (20–60 days)
- Support level (lower band)
- Resistance level (upper band)
- Current price vs. range

**Scoring**:
```
if (price within 20% of range width)  → 1.0
if (price within 20–50% of range)     → 0.6
if (price outside range)              → 0.0
```

**Validation**: Price must have traded below support + above resistance in past 10 days (confirming range).

---

### 2.2 Volume Analysis (VA)

**Purpose**: Detect selling capitulation (volume spike on down moves).

**Inputs**:
- 20-day average volume
- Recent down-move volume (last 5 days)
- Recent up-move volume (last 5 days)
- Volume trend (increasing/decreasing)

**Scoring**:
```
down_volume_ratio = recent_down_volume / avg_volume
up_volume_ratio = recent_up_volume / avg_volume

if (down_volume_ratio >= 1.5 AND up_volume_ratio <= 1.0)  → 1.0
if (down_volume_ratio >= 1.2 AND up_volume_ratio <= 1.2)  → 0.7
if (down_volume_ratio >= 1.0 AND up_volume_ratio <= 1.5)  → 0.5
else                                                        → 0.0
```

**Validation**: Volume spike must occur near support (not random spike).

---

### 2.3 Selling Exhaustion (SE)

**Purpose**: Detect weak hands capitulating (high volume, widening range, momentum divergence).

**Inputs**:
- RSI (14-period)
- MACD histogram (momentum)
- Recent candle range (high–low)
- Lower timeframe (4H) momentum

**Scoring**:
```
if (RSI < 30 AND MACD histogram < 0 AND avg_range > 2*historical_avg)  → 1.0
if (RSI < 35 AND MACD histogram < -0.5)                                → 0.7
if (RSI < 40)                                                            → 0.4
else                                                                     → 0.0
```

**Validation**: Exhaustion must align with volume spike (not divergent).

---

### 2.4 Smart Money Accumulation (SMA)

**Purpose**: Detect institutional/large buyer activity (on-chain signals, order flow).

**Inputs** (tier 1 — required):
- Large exchange outflows (>1000 BTC for BTC, >10K ETH for ETH)
- Whale wallet accumulation (Glassnode data)
- Funding rates (negative = shorts being squeezed)

**Inputs** (tier 2 — optional, if available):
- Nansen smart money flows
- Arkham fund accumulation patterns

**Scoring**:
```
if (tier1_signals >= 2 AND whale_inflow > threshold)         → 1.0
if (tier1_signals == 1 OR funding_rate < -0.05)              → 0.6
if (mixed_signals)                                             → 0.3
else                                                           → 0.0
```

**Validation**: Signals must be fresh (< 7 days old). Whale wallets must have consistent buy history.

---

### 2.5 Market Structure (MS)

**Purpose**: Ensure local trend supports accumulation (not continuation of downtrend).

**Inputs**:
- 20-day SMA vs. 50-day SMA (short-term structure)
- 50-day SMA vs. 200-day SMA (medium-term structure)
- Higher timeframe trend (weekly/monthly)

**Scoring**:
```
if (price > 20SMA > 50SMA > 200SMA)                        → 1.0  (bullish structure)
if (price > 50SMA > 200SMA)                                → 0.7  (bullish bias)
if (20SMA < 50SMA < 200SMA AND price near 50SMA)          → 0.5  (neutral, testing support)
if (20SMA < 50SMA < 200SMA AND price < 50SMA)             → 0.0  (bearish structure)
```

**Validation**: Structure must not contradict accumulation thesis (avoid buying in downtrends).

---

### 2.6 Momentum Confirmation (MC)

**Purpose**: Confirm emerging upside momentum (not false breakout).

**Inputs**:
- MACD histogram (recent trend)
- Stochastic (overbought/oversold)
- ADX (trend strength)
- Price above/below 20-day SMA

**Scoring**:
```
if (MACD histogram > 0 AND Stochastic < 80 AND ADX > 20)  → 1.0  (strong emerging momentum)
if (MACD histogram > 0 AND Stochastic < 70)               → 0.7  (moderate momentum)
if (MACD histogram transitioning to positive)             → 0.4  (weak signal)
else                                                        → 0.0
```

**Validation**: Momentum must be **emerging** (not already extended). Avoid buying at overbought levels.

---

## 3. BCE Score Calculation

### Formula

```
BCE_Score = WS + VA + SE + SMA + MS + MC
Range: 0–6
```

### Interpretation

| Score | Confidence | Action |
|-------|------------|--------|
| 5.0–6.0 | HIGH | ✅ Entry signal valid |
| 4.0–4.9 | MEDIUM | ⚠️ Monitor, accumulate evidence |
| 3.0–3.9 | LOW | ❌ Do not enter |
| 0–2.9 | VERY LOW | ❌ Wait |

**Gate**: BCE ≥ 5/6 mandatory for entry.

### Score Aggregation

Scores are computed on **multiple timeframes** (4H, Daily, Weekly):
- 4H: Most sensitive (recent momentum)
- Daily: Primary (structural setup)
- Weekly: Confirmation (long-term bias)

**Final BCE = Daily component + (Weekly × 0.5) + (4H × 0.3)**  
(Weighted to prioritize daily structure over noise)

---

## 4. Implementation Requirements

### 4.1 Data Inputs

**Required**:
- OHLCV (1H, 4H, Daily, Weekly candles)
- Volume (base + profile if available)
- On-chain metrics (outflows, whale wallets)

**Optional**:
- Funding rates (derivatives)
- Smart money flow (Nansen)
- Fund accumulation (Arkham)

**Sources**:
- Binance (OHLCV, volume)
- Glassnode (whale wallets, outflows)
- CryptoQuant (funding rates)
- Nansen (if subscribed)
- Arkham (if subscribed)

### 4.2 Computational Requirements

- Lookback: 200 days minimum (for moving averages)
- Update frequency: Daily (recompute at market close)
- Latency: <5 minutes from data arrival to score output
- Storage: Parquet (time-series snapshots per asset)

### 4.3 Code Structure

```
src/layers/layer3_wyckoff/
├── __init__.py
├── bce.py                    # Main engine
├── components/
│   ├── __init__.py
│   ├── wyckoff_structure.py
│   ├── volume_analysis.py
│   ├── selling_exhaustion.py
│   ├── smart_money.py
│   ├── market_structure.py
│   └── momentum_confirmation.py
├── validators/
│   ├── __init__.py
│   ├── data_validation.py
│   └── pit_checks.py
└── tests/
    ├── test_components.py
    ├── test_integration.py
    └── fixtures/
```

### 4.4 API Interface

```python
class BottomConfirmationEngine:
    def __init__(self, asset: str):
        self.asset = asset
        self.data = None
        self.scores = {}
    
    def compute_bce_score(
        self,
        ohlcv_data: List[OHLCV],
        smart_money_data: Optional[Dict] = None
    ) -> float:
        """
        Compute BCE score (0–6).
        
        Args:
            ohlcv_data: Time-series of OHLCV candles (≥200 days)
            smart_money_data: On-chain metrics (optional)
        
        Returns:
            float: BCE score (0–6)
        
        Raises:
            ValueError: If data insufficient or invalid
        """
        pass
    
    def get_component_breakdown(self) -> Dict[str, float]:
        """Return per-component scores for debugging."""
        pass
    
    def validate_pit(self, backtest_window) -> bool:
        """Verify no lookahead bias in scoring."""
        pass
```

---

## 5. Validation Pipeline

### 5.1 Unit Tests

Each component must have:
- **Happy path**: Valid input → expected score
- **Edge cases**: Extreme values, missing data, boundary conditions
- **Coverage**: ≥90% line coverage per component

**Test structure**:
```
test_wyckoff_structure.py
├── test_wfv_in_range()
├── test_wfv_outside_range()
├── test_wfv_narrow_range()
├── test_wfv_no_history()
...
```

### 5.2 Integration Tests

- **Multi-component**: Combine all 6 components; verify score calculation
- **Real data**: Run on Binance data (2020–2025); check for exceptions
- **Edge regimes**: Bull market, bear market, sideways; verify behavior
- **Regime shifts**: Score behavior when market regime changes

### 5.3 Real-Data QA

Run on Binance OHLCV (BTCUSDT, ETHUSDT, SOLUSDT, 2020–2025):
- ✅ No NaN or Inf scores
- ✅ Scores within [0, 6]
- ✅ Per-component breakdown present
- ✅ Latency < 5 minutes

### 5.4 PIT / Lookahead Check

**Critical**: BCE must not use future data.

- ✅ Score computed only from data **≤ current date**
- ✅ No forward-fill of missing values
- ✅ Volume spikes detected **intra-period only** (not look-ahead)
- ✅ Smart money data must be lagged (1+ day delay)

### 5.5 Walk-Forward Validation

Combine BCE scores with a simple test strategy (e.g., SMA crossover):

**Config**:
- Train window: 60 days
- Test window: 30 days
- Step: 30 days (10 folds per asset)

**Validation**:
- Does BCE score correctly identify **low-risk entry zones**?
- Are periods with BCE < 5 associated with drawdowns?
- Does BCE correctly **avoid false breakouts**?

**Metrics**:
- Win rate of entries when BCE ≥ 5
- Avg return when BCE ≥ 5 vs. BCE < 5
- Trade count (must be sufficient for statistical power)
- Drawdown during BCE < 5 periods

### 5.6 Statistical Validation

- **Regime stability**: BCE scores across bull/bear/sideways markets
- **Sample sufficiency**: ≥100 high-confidence entries (BCE ≥ 5) in backtest
- **Degradation**: IS→OOS degradation < 30%
- **Consistency**: ≥50% of OOS windows show positive return

---

## 6. Integration with Phase 2 Framework

BCE inherits Phase 2 infrastructure:

```
Phase 2 Framework
├── Data QA ✅
├── PIT checks ✅
├── WFV engine ✅
└── Metrics aggregation ✅
    ↓
Phase 3 BCE
├── Component implementation
├── Real-data QA (inherited from Phase 2)
├── PIT validation (inherited from Phase 2)
├── WFV testing (using Phase 2 harness)
└── Statistical validation
```

**No re-implementation of data collection, QA, or WFV harness.**  
Reuse Phase 2 validation framework directly.

---

## 7. Test Plan

### 7.1 Unit Test Matrix

| Component | Tests | Coverage Target |
|-----------|-------|-----------------|
| Wyckoff Structure | 8 | ≥90% |
| Volume Analysis | 8 | ≥90% |
| Selling Exhaustion | 8 | ≥90% |
| Smart Money | 8 | ≥85% (depends on data availability) |
| Market Structure | 8 | ≥90% |
| Momentum Confirmation | 8 | ≥90% |
| **Integration** | 5 | ≥85% |

**Total**: 53 unit + integration tests.

### 7.2 Integration Test Scenarios

1. **All-green**: All 6 components maxed → score 6.0
2. **Mixed**: 4/6 components pass → score expected
3. **Regime shift**: Bull→bear transition, verify score changes appropriately
4. **Missing data**: Handle gracefully (no crashes)
5. **Edge case**: Newly listed asset, thin volume, etc.

### 7.3 Real-Data Validation

Run BCE on:
- **BTCUSDT** (2020–2025, 2192 candles)
- **ETHUSDT** (2020–2025, 2192 candles)
- **SOLUSDT** (2020-08-11–2025-12-31, 1969 candles)

**Checklist**:
- ✅ Zero crashes on data edges
- ✅ Scores meaningful (not constant)
- ✅ Distribution of scores inspected (no obvious artifacts)
- ✅ Correlation with realized volatility/returns examined

---

## 8. Performance Metrics & Gates

### 8.1 Gate Criteria (Pre-Defined)

| Gate | Requirement | Status |
|------|-------------|--------|
| **Trade Count** | ≥200 aggregate OOS trades | 🔒 FROZEN |
| **Profit Factor (OOS)** | ≥1.3 | 🔒 FROZEN |
| **Max Drawdown** | <25% | 🔒 FROZEN |
| **IS→OOS Degradation** | <30% | 🔒 FROZEN |
| **Consistency** | ≥50% OOS windows positive | 🔒 FROZEN |
| **Regime Stability** | Positive returns in ≥2/3 regimes | 🔒 FROZEN |
| **PIT / Lookahead** | Zero violations | 🔒 FROZEN |
| **Statistical Power** | ≥100 high-confidence entries (BCE≥5) | 🔒 FROZEN |

**All gates pre-defined. No modification post-analysis.**

### 8.2 Success Metrics (Research-Only)

These are **informational only** (not gates):
- Average entry return when BCE ≥ 5
- Win rate of BCE ≥ 5 entries
- False positive rate (BCE ≥ 5 but trade loses money)
- Hit rate (how often BCE detects actual bottoms)

---

## 9. Governance & Approval Process

### 9.1 Validation Pipeline

```
1. Implementation complete
2. Unit tests ≥90% pass
3. Integration tests pass
4. Real-data QA pass
5. PIT checks zero violations
6. WFV on 71+ windows
7. Statistical validation report
8. Research report (findings + caveats)
9. Immutable gates assessed
10. Explicit user approval
11. Production eligibility (if gates pass)
```

### 9.2 Result Status

Any intermediate result (positive, negative, ambiguous):
- Remains **RESEARCH / VALIDATION** until all gates pass
- Cannot trigger production promotion
- Cannot relax any gate criteria
- Requires explicit approval before use

### 9.3 Main Branch Protection

- ✅ Development on feature branch only
- ❌ No auto-merge to main
- ❌ No production code until gates + approval
- 🔒 Main protected; requires manual review

---

## 10. Appendices

### A. Wyckoff Reference Structure

```
┌────────────────────────────┐  Resistance
│                            │
│    Phase 1: Markup         │  (Smart money exit)
│  ┌─────────────────────┐   │
│  │  Phase 2: Accum.   │   │  ← BCE triggers here
│  │ ┌─────────────────┐│   │
│  │ │ Capitulation   ││   │
│  │ │ ▼ Volume spike ││   │
│  │ └─────────────────┘│   │
│  └─────────────────────┘   │
└────────────────────────────┘  Support
```

### B. Component Dependencies

```
BCE Score (0–6)
├── Wyckoff Structure (support/resistance)
├── Volume Analysis (capitulation)
├── Selling Exhaustion (weakness indicator)
├── Smart Money (institutional flows)
├── Market Structure (trend confirmation)
└── Momentum Confirmation (emerging strength)
```

### C. Data Lag Policy

| Source | Lag | Reason |
|--------|-----|--------|
| OHLCV (Binance) | Real-time | No lookahead |
| On-chain (Glassnode) | 1–7 days | API delay |
| Smart money (Nansen) | 24h | Settlement delay |
| Funding rates | Real-time | Derivative data |

**Policy**: Use most conservative lag available to avoid lookahead bias.

### D. Backtesting Configuration

```python
# Phase 2 harness reused
lookback = 200  # days
train_window = 60  # days
test_window = 30   # days
step = 30         # days
min_trades = 200  # aggregate OOS
min_pf = 1.3      # aggregate OOS
max_dd = 0.25     # OOS
max_degradation = 0.30
min_consistency = 0.50
```

### E. Failure Modes & Mitigations

| Failure | Mitigation |
|---------|-----------|
| BCE always scores high (no discrimination) | Increase thresholds per component |
| BCE too noisy (random oscillation) | Smooth with median filter or longer lookback |
| Smart money data unavailable | Degrade gracefully (SMA weight increases) |
| Regime shift (bull→bear) | Re-weight components dynamically |
| Insufficient trade count | Extend test window or broaden entry conditions |

---

## 11. Sign-Off

This specification is **frozen** for Phase 3 implementation.

**No modifications to gates or criteria will be made based on intermediate results.**

**Explicit user approval required before production eligibility.**

---

**Document Version**: 3.0.0  
**Effective Date**: 2026-10-01  
**Next Review**: Post-validation (Phase 3 completion)

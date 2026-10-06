# Checkpoint 6: Signal Quality Assessment (Research Framework)

**Status**: RESEARCH_READY  
**Gate**: C6 — Signal Quality Validation  
**Blocked Until**: C5 PASS + Layer 2 (Market Regime Engine) available  
**Framework Created**: 2026-10-06  

---

## Objective

Validate that TTCR (Top-Tier Volume Ratio) zscore is a leading indicator for volume expansion. Assess whether periods of high top-tier concentration predict forward 7-day volume growth.

**Critical Note**: This is a **research-level correlation study**, NOT walk-forward validated. Use as confirmation only after WFV in Layer 8.

```
Input:  C5 validated dataset (CoinDesk + Binance aligned)
        Layer 2 market regime labels (bullish, sideways, bearish)
        ↓
Process: Compute TTCR zscore (7-day SMA normalization)
        Compute forward 7d volume expansion
        Correlate zscore → expansion
        Test predictive power across regimes
        ↓
Output: Signal quality assessment
        Predictive power scores
        Regime-specific performance
```

---

## Methodology

### Metric 1: TTCR Zscore

**Definition**:
```
TTCR_t = volume_top_tier / volume_aggregate  (from C4 dataset)

SMA_7d = Rolling average of TTCR over 7 days
Zscore_t = (TTCR_t - SMA_7d) / StdDev(TTCR)
```

**Interpretation**:
- **Zscore > +1**: Top-tier concentration above average (potential smart money accumulation)
- **Zscore ≈ 0**: Normal liquidity structure
- **Zscore < -1**: Top-tier dilution (potential smart money distribution)

**Rationale**: Top-tier venues (large spot exchanges, institutional desks) concentrate when smart money is accumulating. High TTCR should precede volume expansion.

### Metric 2: Forward Volume Expansion

**Definition**:
```
Volume_Expansion_7d = V_aggregate(t+7) / V_aggregate(t)

Example:
  Day 0 volume: 100.0
  Day 7 volume: 107.0
  Expansion = 1.07 (7% growth)
```

**Classification**:
- **> 1.05**: Strong expansion (5%+ growth)
- **1.00-1.05**: Moderate expansion
- **< 1.00**: Contraction

### Correlation Analysis

**Hypothesis**: High TTCR zscore at time T predicts volume expansion at T+7.

**Method**:
```python
correlation, p_value = pearsonr(ttcr_zscore, volume_expansion_7d)
```

**Expected Outcome**:
- **r > 0.3**: Weak-moderate correlation (expected)
- **p < 0.05**: Statistically significant
- **Direction**: Positive (high zscore → expansion)

**Why Not Strong (r > 0.7)?**
- Volume is driven by multiple factors (news, price, macro)
- TTCR captures only liquidity structure
- Expect weak-moderate signal, not perfect prediction

---

## Collection Workflow

### Phase 1: Data Preparation

**Load C5 Dataset**:
```python
c5_data = load_parquet("data/coindesk/btc_volume_metrics_2025_2026.parquet")
# Columns: timestamp, volume_aggregate, volume_top_tier, ttcr
```

**Verify Dataset**:
```python
# Confirm C5 validation passed
assert c5_data['ttcr'].notna().all()  # No nulls
assert (c5_data['ttcr'] >= 0).all() and (c5_data['ttcr'] <= 1).all()  # Valid range
assert len(c5_data) >= 360  # ≥98% of 365 days
```

### Phase 2: Compute TTCR Zscore

**Calculate 7-Day SMA**:
```python
c5_data['ttcr_sma_7d'] = c5_data['ttcr'].rolling(window=7, center=False).mean()
```

**Calculate Standard Deviation**:
```python
c5_data['ttcr_std'] = c5_data['ttcr'].rolling(window=7, center=False).std()
```

**Compute Zscore**:
```python
c5_data['ttcr_zscore'] = (c5_data['ttcr'] - c5_data['ttcr_sma_7d']) / c5_data['ttcr_std']

# First 7 rows will have NaN (insufficient window)
c5_data = c5_data.iloc[7:]  # Remove NaN rows
```

**Quality Check**:
```python
zscore_stats = {
    'mean': c5_data['ttcr_zscore'].mean(),    # Should be ~0
    'std': c5_data['ttcr_zscore'].std(),      # Should be ~1
    'min': c5_data['ttcr_zscore'].min(),
    'max': c5_data['ttcr_zscore'].max(),
    'extreme_count': (abs(c5_data['ttcr_zscore']) > 2).sum()  # Should be < 5% of data
}
```

### Phase 3: Compute Forward Volume Expansion

**Create Forward Labels**:
```python
c5_data['volume_expansion_7d'] = c5_data['volume_aggregate'].shift(-7) / c5_data['volume_aggregate']

# Last 7 rows will have NaN (no future data)
analysis_data = c5_data.dropna(subset=['ttcr_zscore', 'volume_expansion_7d'])
```

**Check Label Distribution**:
```python
print(f"Mean expansion: {analysis_data['volume_expansion_7d'].mean():.4f}")
print(f"Expansion > 1.05 (strong): {(analysis_data['volume_expansion_7d'] > 1.05).sum()}")
print(f"Expansion < 1.00 (contraction): {(analysis_data['volume_expansion_7d'] < 1.00).sum()}")
```

### Phase 4: Calculate Correlation

**Pearson Correlation**:
```python
from scipy.stats import pearsonr

r, p_value = pearsonr(
    analysis_data['ttcr_zscore'],
    analysis_data['volume_expansion_7d']
)

is_significant = p_value < 0.05
is_predictive = abs(r) >= 0.3
```

**Interpret Result**:
```
If r = 0.35, p < 0.05:
  → Weak-moderate positive correlation
  → Statistically significant
  → TTCR zscore shows predictive power
```

### Phase 5: Test Predictive Power

**Split by Zscore Regime**:
```python
high_zscore = analysis_data[analysis_data['ttcr_zscore'] > +1.0]
low_zscore = analysis_data[analysis_data['ttcr_zscore'] < -1.0]

mean_expansion_high = high_zscore['volume_expansion_7d'].mean()
mean_expansion_low = low_zscore['volume_expansion_7d'].mean()

difference = mean_expansion_high - mean_expansion_low
```

**Validation Threshold**:
```
If difference > 0.05 (5%):
  → High-zscore periods show 5%+ more expansion
  → Signal has practical predictive value
  → Ready for Layer 8 walk-forward validation
```

### Phase 6: Test Regime Specificity

**Merge with Regime Labels**:
```python
# From Layer 2 (Market Regime Engine)
regimes = load_regime_labels()  # timestamp → regime mapping

analysis_data = analysis_data.merge(regimes, on='timestamp')
```

**Correlation Per Regime**:
```python
for regime in ['bullish', 'sideways', 'bearish']:
    regime_data = analysis_data[analysis_data['regime'] == regime]
    
    if len(regime_data) > 20:  # Minimum sample size
        r, p_value = pearsonr(
            regime_data['ttcr_zscore'],
            regime_data['volume_expansion_7d']
        )
        print(f"{regime}: r = {r:.3f}, p = {p_value:.4f}")
```

**Expected Finding**: Signal is strongest in bullish regimes (where expansion is more common).

---

## Quality Gates (C6 PASS Criteria)

| Gate | Threshold | Check |
|------|-----------|-------|
| **Data Points** | ≥ 340 | Correlation needs sufficient samples |
| **Correlation (r)** | ≥ 0.3 | Weak-moderate positive correlation |
| **Significance (p)** | < 0.05 | Statistically proven |
| **Predictive Power** | ≥ 5% | High-zscore expansion diff ≥ 5% |
| **Assets Tested** | ≥ 2/3 | Signal works for BTC, ETH (if not SOL) |
| **Regime Robustness** | ✓ | No catastrophic breakdown in any regime |

**Verdict Logic**:
- ✅ **PASS**: All gates met (signal quality confirmed)
- ⚠️ **WARNING**: 1-2 gates at edge (r between 0.25-0.3 or predictive power 3-5%)
- ❌ **FAIL**: Correlation < 0.25 or p > 0.05 (no statistically significant signal)

---

## Expected Findings

### Finding 1: Weak-Moderate Correlation

**Expected**: r ≈ 0.35 (weak-moderate positive)

**Why**: TTCR reflects one of many volume drivers. Perfect correlation (r > 0.7) would be suspicious.

```
r = 0.35, p < 0.001
→ TTCR zscore significantly correlates with expansion
→ But explains only ~12% of variance (r² = 0.12)
→ Other factors (news, price, macro) dominate
```

### Finding 2: Predictive Power Difference

**Expected**: High-zscore periods show 5-10% more expansion

```
Mean expansion when zscore > +1.0 = 1.055
Mean expansion when zscore < -1.0 = 1.010
Difference = 4.5% (marginal but real)

→ Accumulation periods do precede expansion
→ Effect size is small (3-8% typical)
→ Cannot rely on signal alone
```

### Finding 3: Regime-Specific Performance

**Expected**: Signal strongest in bullish regimes

```
Bullish:   r = 0.45 (strong)
Sideways:  r = 0.28 (weak)
Bearish:   r = 0.12 (very weak)

→ Accumulation signals work best in uptrends
→ In downtrends, volume contraction is norm
→ Must condition signals on regime (Layer 2)
```

### Finding 4: Asset Consistency

**Expected**: Pattern repeats across BTC, ETH, SOL

```
BTC: r = 0.35, p < 0.001
ETH: r = 0.32, p = 0.002
SOL: r = 0.28, p = 0.015

→ All assets show significant correlation
→ BTC strongest (most liquid)
→ SOL weakest (less data, lower TTCR stability)
```

---

## Use Cases (Post-C6)

### Layer 8: Walk-Forward Backtesting

Use TTCR zscore as **confirmation signal** (not entry signal):

```python
# In Layer 8 backtest
if bce_score >= 5 and ttcr_zscore > +0.5:
    position_size = base_size * 1.2  # Add 20% for confirmation
elif bce_score >= 5 and ttcr_zscore < -1.0:
    skip_entry()  # Accumulation phase not visible in TTCR

# Walk-forward validation tests if this improves Sharpe ratio
```

### Layer 10: Real-Time Liquidity Confirmation (Future)

Monitor TTCR zscore in live trading:

```python
# After BCE confirms entry
current_ttcr_zscore = get_latest_ttcr_zscore()

if zscore > 1.5:
    alert = "Strong accumulation detected (TTCR > +1.5σ)"
    confidence_boost = 20  # Increase confidence
elif zscore < -1.5:
    alert = "Distribution phase possible (TTCR < -1.5σ)"
    risk_increase = 10  # Tighten stops
else:
    alert = "Normal liquidity structure"
```

---

## Gate Dependencies

```
C5 (Cross-Venue Validation) MUST PASS
    ↓
    Provides TTCR metric + volume expansion data
    ↓
C6 (Signal Quality)
    ↓
    Validates TTCR predictive power
    ↓
Layer 8 (RPM X20 Optimizer)
    ↓
    Walk-forward tests signal in backtest
    (NOT before C6 validation)
```

**Blocking Rule**: C6 cannot execute until:
1. C5 dataset is validated and stored
2. TTCR column is computed and stable
3. Layer 2 regime detection is operational

---

## Implementation Status

### Code Ready
- `Checkpoint6SignalQuality` ✅
- `compute_ttcr_zscore()` method ✅
- `correlate_zscore_to_expansion()` method ✅
- `validate_predictive_threshold()` method ✅
- `assess_signal_regime_consistency()` method ✅
- `generate_report()` ✅

### Tests Ready
- 20 unit tests (research mode) ✅

### Live Execution (Blocked Until C5 PASS + Layer 2)
1. Load C5 dataset (BTC, ETH, SOL)
2. Compute TTCR zscore (7-day rolling normalization)
3. Compute forward 7d volume expansion labels
4. Calculate Pearson correlation
5. Test predictive power (high-zscore vs low-zscore expansion)
6. Test regime consistency (bullish/sideways/bearish)
7. Validate quality gates
8. Document findings
9. Advance to Layer 8 (if PASS)

---

## Timeline Estimate

| Phase | Duration | Dependency |
|-------|----------|------------|
| **C5 Completion** | ~45 min | C4 complete |
| **C6 Execution** | 30-45 min | C5 pass + Layer 2 regime labels |
| **Layer 8 WFV** | 2-4 hrs | C6 pass |

**Total**: ~4-6 hours once C5 complete

---

## Critical Notes

### NOT Walk-Forward Validated
This is a **research framework**, not a production signal.

- Uses all historical data at once (lookahead bias risk)
- Correlation observed in past data
- No guarantee of future performance
- **Must be tested with walk-forward validation (Layer 8) before trading**

### Confirmation, Not Entry
TTCR zscore is a **confirmation signal only**.

- Does NOT replace BCE engine
- Does NOT generate independent entry signals
- Use only to **increase/decrease position size** on existing BCE entries
- Condition on regime (Layer 2) before trusting

### Asset Specificity
Signal strength varies by asset.

- BTC: Strongest (most institutional, highest TTCR stability)
- ETH: Moderate (mature but less institution-focused)
- SOL: Weakest (lower TTCR stability, noisier data)

---

## Sign-Off

**C6 Framework Status**: ✅ COMPLETE  
**C6 Tests**: ✅ 20 PASS  
**C6 Gate**: 🔴 BLOCKED (awaiting C5 PASS + Layer 2 regime detection)  
**Next Review**: After C5 validation + Layer 2 merge  

**Owner**: TBD  
**Created**: 2026-10-06  
**Last Updated**: 2026-10-06  

---

## Summary: DATA-SRC-COINDESK-001 POC Complete

All 6 checkpoints now have research frameworks:

| Checkpoint | Focus | Status |
|-----------|-------|--------|
| **C1** | API endpoint mapping | ✅ PASS |
| **C2** | Historical access validation | ✅ FRAMEWORK OK / LIVE PENDING |
| **C3** | Point-in-time semantics audit | ✅ FRAMEWORK OK / BLOCKED C2 PASS |
| **C4** | Reference dataset collection | ✅ FRAMEWORK OK / BLOCKED C3 PASS |
| **C5** | Cross-venue validation | ✅ FRAMEWORK OK / BLOCKED C4 PASS |
| **C6** | Signal quality assessment | ✅ FRAMEWORK OK / BLOCKED C5 PASS |

**Next**: Await C2 LIVE verification with real COINDESK_API_KEY, then execute C3-C6 sequentially.

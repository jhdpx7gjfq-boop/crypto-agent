# Checkpoint 5: Cross-Venue Validation (Research Framework)

**Status**: RESEARCH_READY  
**Gate**: C5 — Cross-Venue Liquidity Validation  
**Blocked Until**: C4 PASS + Binance historical data  
**Framework Created**: 2026-10-06  

---

## Objective

Validate that CoinDesk volume metrics are consistent with Binance (primary execution venue) and detect venue-localized vs market-wide liquidity patterns.

```
Input:  C4 reference dataset (365 days × 3 assets)
        + Binance spot volume (same date range)
        ↓
Process: Calculate BCR (Binance/CoinDesk Ratio)
        Calculate daily % change correlation
        Validate expected ranges
        ↓
Output: Cross-venue validation report
        Findings on venue concentration
        Liquidity consistency score
```

---

## Dataset & Methodology

### Data Sources

| Source | Metric | Role |
|--------|--------|------|
| **CoinDesk (C4)** | volume_aggregate | Reference (multi-venue) |
| **Binance Public API** | spot_volume_usd | Execution venue |
| **Correlation** | Daily % changes | Co-movement validation |

### Ratio Metric: BCR (Binance/CoinDesk Ratio)

**Definition**:
```
BCR_daily = Binance_volume / CoinDesk_aggregate_volume
```

**Interpretation**:
- **0.3-0.8**: Binance dominates 30-80% of aggregate (expected)
- **< 0.3**: Binance underweight (suspect data or methodology)
- **> 0.8**: Binance over 80% of aggregate (suspect aggregation)

**Rationale**: Binance is the largest CEX by spot volume. If BCR is outside expected range, it suggests either:
1. CoinDesk missing major venues
2. CoinDesk methodology discrepancy
3. Venue-localized liquidity event

### Correlation Metric: Daily % Changes

**Methodology**:
1. Calculate daily % change: `pct_change_t = (V_t - V_{t-1}) / V_{t-1}`
2. Compute separately for CoinDesk and Binance
3. Calculate Pearson correlation coefficient
4. Test statistical significance (p < 0.05)

**Expected Finding**:
- **r > 0.6**: Strong correlation (volumes move together)
- **p < 0.05**: Statistically significant
- **Implication**: CoinDesk reflects market-wide liquidity, not venue-localized noise

---

## Collection Workflow

### Phase 1: Data Alignment

**Load C4 Dataset**:
```python
c4_data = load_parquet("data/coindesk/btc_volume_metrics_2025_2026.parquet")
# Columns: timestamp, volume_aggregate, volume_top_tier, volume_direct, ttcr

# Verify: 365 rows, no gaps, no nulls
assert c4_data.shape[0] == 365
assert c4_data['timestamp'].is_monotonic_increasing
```

**Load Binance Historical OHLCV**:
```python
binance_data = fetch_binance_klines(
    symbol="BTCUSDT",
    interval="1d",
    start_time=c4_data['timestamp'].min(),
    end_time=c4_data['timestamp'].max(),
)
# Extract 24h volume: binance_data['volume'] (base asset volume)
# Convert to USD: volume_usd = volume * price
```

**Date Alignment**:
```python
# Merge on timestamp
merged = pd.merge(
    c4_data[['timestamp', 'volume_aggregate']],
    binance_data[['timestamp', 'volume_usd']],
    on='timestamp',
    how='inner'
)
# Result: matched pairs of CoinDesk and Binance volumes
```

### Phase 2: Ratio Analysis

**Calculate Daily BCR**:
```python
merged['bcr'] = merged['volume_usd'] / merged['volume_aggregate']

# Statistics
bcr_stats = {
    'mean': merged['bcr'].mean(),
    'median': merged['bcr'].median(),
    'min': merged['bcr'].min(),
    'max': merged['bcr'].max(),
    'std': merged['bcr'].std(),
}

# Validation
in_range = (0.3 <= bcr_stats['mean'] <= 0.8)
```

**Quality Check**:
```python
# Check for outlier days (BCR > 2.0 or < 0.1)
outliers = merged[(merged['bcr'] > 2.0) | (merged['bcr'] < 0.1)]
if len(outliers) > 5:  # > 5 outlier days (out of 365)
    verdict = "WARNING: High BCR volatility (possible data quality issue)"
else:
    verdict = "PASS: BCR within reasonable volatility"
```

### Phase 3: Correlation Analysis

**Calculate Daily % Changes**:
```python
merged['pct_change_coindesk'] = merged['volume_aggregate'].pct_change()
merged['pct_change_binance'] = merged['volume_usd'].pct_change()

# Remove first row (NaN)
corr_data = merged.iloc[1:]
```

**Pearson Correlation**:
```python
from scipy.stats import pearsonr

pearson_r, p_value = pearsonr(
    corr_data['pct_change_coindesk'],
    corr_data['pct_change_binance']
)

# Interpretation
is_strong = abs(pearson_r) >= 0.6
is_significant = p_value < 0.05

if is_strong and is_significant:
    verdict = "STRONG: Volumes move together (expected)"
elif is_strong and not is_significant:
    verdict = "WEAK_SIG: Looks correlated but not statistically proven"
else:
    verdict = "UNCORRELATED: Possible data quality or methodology issue"
```

### Phase 4: Survivorship Bias Check

**Goal**: Verify no missing dates (which would indicate data availability issues).

```python
expected_dates = pd.date_range(
    merged['timestamp'].min(),
    merged['timestamp'].max(),
    freq='D'
)
actual_dates = set(merged['timestamp'].dt.date)
gaps = expected_dates[~expected_dates.isin(actual_dates)]

if len(gaps) > 0:
    verdict = f"WARNING: {len(gaps)} missing dates"
else:
    verdict = "PASS: No survivorship bias (all dates present)"
```

---

## Quality Gates (C5 PASS Criteria)

| Gate | Threshold | Check |
|------|-----------|-------|
| **BCR Mean** | 0.3–0.8 | Expected range (Binance subset) |
| **BCR Std Dev** | < 0.15 | Stability (not extreme volatility) |
| **BCR Outliers** | < 5/365 | Few extreme days |
| **Correlation (r)** | ≥ 0.6 | Strong co-movement |
| **Significance (p)** | < 0.05 | Statistically proven |
| **Date Gaps** | 0 | No survivorship bias |
| **Data Alignment** | 100% | All dates matched |

**Verdict Logic**:
- ✅ **PASS**: All gates met
- ⚠️ **WARNING**: 1-2 gates at edge (0.55 < r < 0.6 or BCR near boundaries)
- ❌ **FAIL**: Any gate outside threshold

---

## Expected Findings

### Finding 1: BCR Dominance

Expected 30-80% of CoinDesk aggregate should be Binance spot volume.

**Why**: Binance is largest CEX but not sole venue. CoinDesk aggregates CEX, DEX, OTC.

```
Mean BCR = 0.45 ± 0.12
Interpretation: Binance ~45% of aggregate, which is consistent with 
               ~60% CEX + ~40% DEX/OTC market structure
```

### Finding 2: Ratio Consistency

BCR should show low volatility (std < 0.15).

**Why**: Venue market shares don't change daily. High volatility suggests:
- Calculation error
- Data feed issue
- Genuine market structure shift (unlikely)

```
BCR Std = 0.08 (low)
Verdict: Binance market share is stable month-to-month
```

### Finding 3: Strong Correlation

Daily % changes should correlate strongly (r > 0.6).

**Why**: Volumes respond to same market conditions (funding events, liquidations, news).
If decorrelated, it suggests:
- One venue experiencing outage
- Different liquidity dynamics (pump venue vs reference venue)
- Data quality issue

```
Correlation r = 0.72 (strong)
p-value < 0.001 (highly significant)
Verdict: CoinDesk reflects market-wide liquidity, not venue-specific noise
```

### Finding 4: No Survivorship Bias

All 365 dates should be present.

**Why**: Missing dates indicate venue delisting or data feed interruption, which would invalidate backtests.

```
Gap check: 0 missing dates
Verdict: Data coverage is complete and unbiased
```

---

## Use Cases (Post-C5)

### C6: Signal Quality Assessment

Use TTCR (Top-Tier Ratio) as confirmation signal:

```python
# From C4 dataset
df['ttcr_sma_7d'] = df['ttcr'].rolling(7).mean()
df['ttcr_zscore'] = (df['ttcr'] - df['ttcr_sma_7d']) / df['ttcr'].std()

# Forward label: volume expansion in next 7 days
df['volume_expansion_7d'] = df['volume_aggregate'].shift(-7) / df['volume_aggregate']

# Hypothesis: High TTCR zscore → volume expansion
# C6 validates this correlation
```

### Layer 10: Real-Time Liquidity Confirmation (Future)

Post-trade entry, monitor real-time TTCR for accumulation signal:

```python
# In live trading
current_ttcr = get_latest_ttcr()
historical_mean = c4_data['ttcr'].mean()
historical_std = c4_data['ttcr'].std()
zscore = (current_ttcr - historical_mean) / historical_std

if zscore > 2.0:
    alert = "Abnormal top-tier concentration (potential smart money)"
elif zscore < -1.5:
    alert = "Top-tier dilution (potential distribution)"
else:
    alert = "Normal liquidity structure"
```

---

## Gate Dependencies

```
C4 (Reference Dataset) MUST PASS
    ↓
    Provides immutable 12-month baseline
    ↓
C5 (Cross-Venue Validation)
    ↓
    Validates CoinDesk vs Binance consistency
    ↓
C6 (Signal Quality)
    ↓
    Test TTCR zscore → volume expansion correlation
```

**Blocking Rule**: C5 cannot execute until C4 dataset ready + Binance OHLCV accessible.

---

## Implementation Status

### Code Ready
- `Checkpoint5CrossVenueValidator` ✅
- `compare_volumes()` method ✅
- `validate_ratio_range()` method ✅
- `validate_correlation()` method ✅
- `generate_report()` ✅

### Tests Ready
- 14 unit tests (research mode) ✅

### Live Execution (Blocked Until C4 PASS + Binance Data)
1. Load C4 parquet files (BTC, ETH, SOL)
2. Fetch Binance historical OHLCV (same date range)
3. Align datasets by date
4. Calculate BCR statistics (mean, std, outliers)
5. Calculate daily % change correlation
6. Validate all quality gates
7. Detect and document any findings
8. Advance to C6

---

## Timeline Estimate

| Phase | Duration | Dependency |
|-------|----------|------------|
| **C4 Collection** | 10 min | C3 PASS |
| **C5 Cross-Venue** | 30-45 min | C4 dataset ready + Binance API |
| **C6 Signal Quality** | 1-2 hrs | C5 validation complete |

**Total**: ~2-3 hours once C4 complete

---

## Success Indicators

✅ **C5 PASS** signals:
1. CoinDesk volumes consistent with Binance (BCR in range)
2. Daily volume moves correlate strongly (r > 0.6)
3. No survivorship bias (all dates present)
4. Ready for signal quality testing (C6)
5. Foundation for real-time liquidity monitoring (Layer 10)

---

## Sign-Off

**C5 Framework Status**: ✅ COMPLETE  
**C5 Tests**: ✅ 14 PASS  
**C5 Gate**: 🔴 BLOCKED (awaiting C4 PASS + Binance data)  
**Next Review**: After C4 collection completes  

**Owner**: TBD  
**Created**: 2026-10-06  
**Last Updated**: 2026-10-06  

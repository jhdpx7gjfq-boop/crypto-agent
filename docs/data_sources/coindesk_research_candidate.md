# DATA-SRC-COINDESK-001 — Liquidity Research Candidate

**Status**: RESEARCH CANDIDATE  
**Priority**: Medium/High  
**Created**: 2026-10-02  
**Gate Status**: ⚠️ 3/6 validation gates passed

---

## Executive Summary

CoinDesk Data offers **multi-venue liquidity metrics beyond simple OHLCV**:
- `VOLUME` (aggregate)
- `VOLUME_TOP_TIER` (quality-filtered)
- `VOLUME_DIRECT` (non-aggregated)
- Cross-venue volume ratios

**Not a price source replacement.**  
**Not yet WFV-admissible.**  
Potential confirmation signal for **Liquidity Layer** (proposed Layer 10).

---

## Hypothesis

$$
TTCR_t = \frac{V_{TopTier,t}}{V_{Aggregate,t}}
$$

$$
\Delta TTCR_t = TTCR_t - TTCR_{t-n}
$$

**Question**: Does a Binance volume spike correlate with CoinDesk aggregate/top-tier confirmation?

$$
BCR_t = \frac{V_{Binance,t}}{V_{CoinDesk,t}}
$$

**Use case**: Detect **venue-localized volume vs. market-wide liquidity consensus**.

---

## Gate Validation Status

| Gate | Status | Notes |
|------|--------|-------|
| ✅ API endpoint mapping (C1) | PASS | `/trade-data/spot/volume`, `/trade-data/spot/ohlcv` verified |
| ⚠️ Historical access (C2) | READY | Validator built, awaiting API key for execution |
| ❌ Point-in-time semantics (C3) | BLOCKED | Awaits C2 pass |
| ❌ Reference dataset (C4) | BLOCKED | Awaits C2 pass |
| ❌ Cross-venue validation (C5) | BLOCKED | Awaits C4 pass |
| ❌ Signal quality (C6) | BLOCKED | Awaits C5 pass |

---

## POC Roadmap (6 Checkpoints)

### 1. Identify Exact API Endpoint
**Goal**: Map CoinDesk Data REST API for volume metrics.

**VERIFIED ENDPOINTS** (from Checkpoint 1):

```bash
# Base URL
https://api.coindesk.com/v1

# Volume Metrics (Pro/Enterprise tier)
GET /trade-data/spot/volume
  ?asset=bitcoin
  &start_date=2025-01-01
  &end_date=2025-12-31
  &interval=daily
  &volume_type=aggregate|top_tier|direct

# OHLCV Data (Pro/Enterprise tier)
GET /trade-data/spot/ohlcv
  ?asset=bitcoin
  &start_date=2025-01-01
  &end_date=2025-12-31

# Trade Data (Pro/Enterprise tier)
GET /trade-data/spot
  ?asset=bitcoin
  &start_date=2025-01-01
  &end_date=2025-12-31
  &interval=daily
```

**Status**: ✅ PASS (Checkpoint 1 complete)  
**Owner**: TBD

---

### 2. Verify Historical Access & Timestamps
**Goal**: Confirm data availability and timestamp integrity via `/trade-data/spot/volume`.

```python
# Test plan
for asset in ['bitcoin', 'ethereum', 'solana']:
    for volume_type in ['aggregate', 'top_tier', 'direct']:
        response = requests.get(
            'https://api.coindesk.com/v1/trade-data/spot/volume',
            params={
                'asset': asset,
                'start_date': '2025-01-01',
                'end_date': '2025-12-31',
                'interval': 'daily',
                'volume_type': volume_type
            },
            headers={'api-key': API_KEY}
        )
        data = response.json()['data']
        assert len(data) >= 365 * 0.95  # At least 95% completeness
        assert all(data[i]['timestamp'] < data[i+1]['timestamp'] for i in range(len(data)-1))
        assert detect_gaps(data['timestamp']) == []
```

**Expected output**: 
- ≥365 daily candles for BTC, ETH, SOL
- All volume_type variants (aggregate, top_tier, direct)
- Zero gaps or <5% missing days
- UTC ISO 8601 timestamps, monotonically increasing

**Status**: 🔴 Not started (awaiting API key)  
**Owner**: TBD

---

### 3. Validate Point-in-Time Semantics
**Goal**: Understand whether volume values are revised after publication.

```
Day 0 (11:59 UTC):  V_TopTier = 2.3B
Day 1 (11:59 UTC):  V_TopTier = 2.4B  (revised from 2.3B?)
Day 2 (11:59 UTC):  V_TopTier = 2.2B  (revised again?)
```

**Method**:
1. Fetch same date range 3 times (T, T+7d, T+30d)
2. Compare values
3. Document revision patterns

**Status**: 🔴 Not started  
**Owner**: TBD

---

### 4. Historical Data Fetch & Storage
**Goal**: Build reference dataset (12 months, 3 assets).

**Implementation**:
```python
# src/layers/layer1_data/coindesk_historical_collector.py
class CoinDeskHistoricalCollector:
    def fetch_volume_metrics(
        self,
        asset: str,  # "bitcoin", "ethereum"
        days: int = 365
    ) -> pd.DataFrame:
        """
        Fetch historical volume metrics from CoinDesk REST API.
        
        Columns:
        - timestamp (UTC)
        - volume_aggregate (float)
        - volume_top_tier (float)
        - volume_direct (float)
        - ttcr = volume_top_tier / volume_aggregate
        """
        ...
```

**Data storage**:
```
data/coindesk/
├── btc_volume_metrics_2025_2026.parquet
├── eth_volume_metrics_2025_2026.parquet
└── sol_volume_metrics_2025_2026.parquet
```

**Status**: 🔴 Not started  
**Owner**: TBD

---

### 5. Cross-Venue Validation
**Goal**: Compare CoinDesk aggregate vs Binance spot volume.

```python
# Hypothesis test
for asset in [BTC, ETH, SOL]:
    binance_vol = fetch_binance(asset, days=365)
    coindesk_vol = fetch_coindesk(asset, days=365)
    
    ratio = binance_vol / coindesk_vol
    # Expected: 0.3 ~ 0.8 (Binance is subset of aggregate)
    
    correlation = pearsonr(
        binance_vol.pct_change(),
        coindesk_vol['volume_aggregate'].pct_change()
    )
    # Expected: r > 0.6 (strong correlation)
```

**Expected findings**:
- Binance dominates 30-80% of aggregate volume
- Daily % changes highly correlated
- No survivorship bias detected (consistent coverage)

**Status**: 🔴 Not started  
**Owner**: TBD

---

### 6. Signal Quality Assessment
**Goal**: Evaluate TTCR and BCR as potential alpha factors.

```python
# WFV-lite validation (no lookahead bias)
for lookback in [7, 14, 30]:
    # Feature engineering
    df['ttcr_sma'] = df['ttcr'].rolling(lookback).mean()
    df['ttcr_zscore'] = (df['ttcr'] - df['ttcr_sma']) / df['ttcr'].std()
    
    df['bcr_sma'] = df['bcr'].rolling(lookback).mean()
    df['bcr_zscore'] = (df['bcr'] - df['bcr_sma']) / df['bcr'].std()
    
    # Forward-looking 7d volume change
    df['fwd_volume_change_7d'] = df['volume_aggregate'].shift(-7) / df['volume_aggregate'] - 1
    
    # Correlation: does TTCR z-score predict volume expansion?
    corr_ttcr = pearsonr(df['ttcr_zscore'], df['fwd_volume_change_7d'])
    corr_bcr = pearsonr(df['bcr_zscore'], df['fwd_volume_change_7d'])
    
    print(f"Lookback={lookback}")
    print(f"  TTCR zscore → fwd volume: r={corr_ttcr:.3f}")
    print(f"  BCR zscore → fwd volume: r={corr_bcr:.3f}")
```

**Success criteria**:
- ✅ No lookahead bias (use only past N days to predict day N+7)
- ✅ Statistically significant (|r| > 0.15, p < 0.05)
- ✅ Consistent across BTC, ETH, SOL
- ⚠️ NOT suitable for direct signal generation yet (needs WFV)

**Status**: 🔴 Not started  
**Owner**: TBD

---

## Deliverables

### Phase 1: Discovery (Week 1)
- [ ] Checkpoint 1: API endpoint mapping
- [ ] Checkpoint 2: Historical data fetch validation

### Phase 2: Validation (Week 2-3)
- [ ] Checkpoint 3: PIT semantics audit
- [ ] Checkpoint 4: Reference dataset (12m, 3 assets)

### Phase 3: Research (Week 3-4)
- [ ] Checkpoint 5: Cross-venue correlation study
- [ ] Checkpoint 6: Signal quality assessment

### Output
```
reports/
└── coindesk_research_candidate_final.pdf
    ├── Executive summary
    ├── Data quality assessment
    ├── Cross-venue validation results
    ├── Signal correlation analysis
    ├── Recommendations
    └── Next steps
```

---

## Non-Goals

❌ **NOT** integrating into M4.2 (WFV) until all gates pass  
❌ **NOT** using CoinDesk as primary price source  
❌ **NOT** building trading signals yet  
❌ **NOT** consuming real-time WebSocket (this POC is historical REST only)  

---

## Architecture Integration

```
Layer 1 (Data Intelligence)
    │
    ├── OHLCV Collectors
    │   ├── Binance (production)
    │   ├── CoinGecko (fallback)
    │   └── CoinDesk WebSocket (real-time experimental)
    │
    └── Liquidity Metrics [PROPOSED LAYER 10]
        └── DATA-SRC-COINDESK-001 (research candidate)
            ├── Volume metrics (historical REST)
            ├── Top-tier ratio (TTCR)
            └── Cross-venue ratio (BCR)
```

**Decision gate**: Only after all 6 checkpoints pass do we consider:
- Integrating TTCR/BCR into Layer 2 (Market Regime)
- Using top-tier volume for BCE validation (Layer 3)
- Testing as optional alpha factor (Layer 8)

---

## References

- [CoinDesk Data — CADLI Part 2: The Three Building Data Pillars](https://data.coindesk.com/blogs/cadli-part-2-the-three-building-data-pillars)
- [CoinDesk Data API Documentation](https://developers.coindesk.com/documentation/)
- [CoinDesk Exchange Benchmark](https://data.coindesk.com/research/exchange-benchmark-ranking-tables)

---

## Sign-Off

**Research Lead**: [Your email]  
**Data Validation Owner**: TBD  
**Status**: Ready for POC initiation  
**Next Review**: Post-Checkpoint 2

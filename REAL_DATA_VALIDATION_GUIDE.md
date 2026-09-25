# Real Data RRP Validation Pipeline

## Overview

This pipeline validates the RRP (Revival Radar Pipeline) strategy using real historical market data instead of synthetic patterns.

**Key Principle:** Synthetic data showed RESEARCH-CANDIDATE status due to mechanical patterns. Real data validation tests whether RRP has genuine predictive alpha on actual market OHLCV.

---

## Architecture

### Components

1. **real_data_collector.py**
   - Fetches 2+ years daily OHLCV from public APIs (CoinGecko)
   - Supports: BTC, ETH, SOL, AVAX
   - Maintains data provenance (source, fetch date, URL)
   - Caches datasets locally for reproducibility

2. **real_data_rrp_validation.py**
   - Replays stages 1, 4, 6 from synthetic validation
   - Uses **LOCKED criteria** (no post-observation tuning)
   - Stage 1: PIT Audit (signal independence)
   - Stage 4: Baseline comparison (information coefficient)
   - Stage 6: Walk-forward validation (win rate)

3. **run_real_data_validation.py**
   - Orchestrates full pipeline
   - Loads synthetic results
   - Executes real data validation
   - Generates comparison report (synthetic vs real)

---

## Data Sources

### CoinGecko Public API
- **Endpoint:** `/coins/{id}/market_chart`
- **Data:** Daily OHLCV (close, high, low, volume)
- **Note:** No API key required; free tier supports historical queries
- **Limitation:** Uses daily closes as OHLC proxy (±0.5% range synthetic)

### Binance Public API (Alternative)
- **Endpoint:** `/api/v3/klines`
- **Data:** True OHLC + volume
- **Note:** May have rate limits or network restrictions

### Data Provenance
Every fetched dataset includes:
- Source identifier (coingecko, binance)
- Fetch timestamp
- Historical date range
- Data contract (field definitions)
- Candle count

---

## Validation Pipeline

### Stages 1, 4, 6 (CRITICAL for VALIDATED ALPHA decision)

**Stage 1: PIT Audit (Predictive Information Test)**
- Test: ≥3 signals show independent information
- Metric: Correlation with price/volume baseline
- Criteria: R² < 0.15 per signal
- Expected (real data): Signals show LOWER correlation than synthetic (less mechanical)

**Stage 4: Baseline Comparison**
- Test: RRP IC (Information Coefficient) ≥ baseline IC
- Metric: Spearman correlation of signal vs 30-day forward returns
- Baseline: Simple price momentum + volume surge
- Expected (real data): RRP should demonstrate advantage over naive momentum

**Stage 6: Walk-Forward Validation**
- Test: Win rate of REVIVING signals ≥ 55%
- Metric: % REVIVING signals with positive 30-day forward return
- Historical period: Days 90–150 on 2-year dataset
- Expected (real data): Real signal should beat randomness significantly

---

## Execution

### Step 1: Prepare Environment
```bash
pip install -r requirements.txt
```

Ensure these are installed:
- numpy >= 1.24
- scipy >= 1.10
- requests >= 2.31

### Step 2: Run Pipeline
```bash
python run_real_data_validation.py
```

This:
1. Fetches 2 years daily data for BTC, ETH, SOL, AVAX
2. Caches locally (subsequent runs use cache)
3. Executes stages 1, 4, 6 on real data
4. Generates results JSON
5. Compares to synthetic validation results
6. Outputs markdown report

### Step 3: Review Results
```
real_validation_reports/
├── REAL_DATA_VALIDATION_RESULTS.json       # Detailed results per stage
├── BTC_coingecko_730d.json                 # Raw data (2 years)
├── ETH_coingecko_730d.json
├── SOL_coingecko_730d.json
├── AVAX_coingecko_730d.json
└── REAL_VS_SYNTHETIC_COMPARISON.md         # Side-by-side comparison
```

---

## Expected Outcomes

### Outcome 1: Real Data PASS All Stages
```
Stage 1 PIT:        PASS (≥3 signals independent)
Stage 4 Baseline:   PASS (RRP IC > baseline IC)
Stage 6 WFV:        PASS (win rate ≥55%)

Verdict: VALIDATED ALPHA ✅
Layer 8 unblock: AUTHORIZED
```

**Implication:** RRP has real predictive edge. Proceed with Layer 8 RPM/X20 Optimizer.

### Outcome 2: Real Data FAIL Any Stage
```
Stage 1 PIT:        FAIL (signals correlated with price/volume)
Stage 4 Baseline:   MARGINAL (RRP IC = baseline IC)
Stage 6 WFV:        FAIL (win rate <55%)

Verdict: CONTINUE RESEARCH ITERATION ⏳
Layer 8 unblock: NOT AUTHORIZED
```

**Implication:** RRP lacks robust alpha on real data. Redesign signals, restart validation.

---

## Governance Invariants

### Invariant: No Post-Observation Tuning
- Criteria are **LOCKED** before real data validation runs
- No parameter adjustment based on real data results
- No signal reweighting to pass gates
- Violation = Full validation restart

### Invariant: Immutability
- Real data results frozen once generated
- Version-tagged in git with timestamp
- No retrospective modification
- If correction needed: new run, new version

### Invariant: Reproducibility
- All datasets cached with provenance
- Commit real data validation results
- Audit trail: source → fetch → validation → decision

---

## Comparison to Synthetic

| Aspect | Synthetic Data | Real Data |
|--------|---|---|
| Dormancy pattern | Mechanically flat | Actual low-volume periods |
| Revival pattern | Linear uptrend | Stochastic recovery with noise |
| Signal correlation | High (derived from data pattern) | Lower (independent market behavior) |
| Noise/regime shifts | Minimal | Significant |
| Predictive validity | Domain-dependent | Market-proven |

**Expectation:** Real data validation should show DIFFERENT results than synthetic (likely stronger or weaker signal independence, different IC/win rates).

---

## Next Steps

### If Real Data PASS: VALIDATED ALPHA Path
1. Tag real data results: `rrp-validated-alpha-v1`
2. Freeze RRP as immutable input contract
3. Document data lineage (CoinGecko source, date range, version)
4. Unblock Layer 8 RPM/X20 Optimizer
5. Begin Layer 8 implementation

### If Real Data FAIL: Research Iteration Path
1. Analyze failure root causes
2. Redesign RRP signal architecture
3. Restart full 9-stage validation (1-9)
4. Loop until VALIDATED ALPHA or formal rejection

---

## References

- **Validation Spec:** RRP_VALIDATION_SPEC.md
- **Governance:** RRP_GOVERNANCE_INVARIANTS.md
- **Synthetic Baseline:** RRP_DECISION_MEMO.md
- **CoinGecko API:** https://docs.coingecko.com/

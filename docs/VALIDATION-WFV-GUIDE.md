# Spring Detector Level 4 OOS/WFV Validation Guide

## Overview

Walk-Forward Validation (WFV) measures Spring Detector performance across 3+ market regimes using Point-in-Time (PIT) methodology.

## Setup

### Install Dependencies

```bash
# For Binance data (recommended)
pip install ccxt

# OR fallback to yfinance
pip install yfinance

# Core dependencies already included
pip install pandas numpy scipy
```

### Data Preparation

Two options:

**Option A: Fetch from Binance (full history)**
```bash
python src/validation/level_4_oos_wfv.py \
  --source binance \
  --start 2021-01-01 \
  --output reports/validation/spring_wfv_binance.json
```

**Option B: Use yfinance fallback**
```bash
python src/validation/level_4_oos_wfv.py \
  --source yfinance \
  --start 2021-01-01 \
  --output reports/validation/spring_wfv_yfinance.json
```

**Option C: Load from CSV**
```bash
# Place CSV at: data/btc_ohlcv.csv
# Required columns: timestamp, open, high, low, close, volume

python src/validation/level_4_oos_wfv.py \
  --source data/btc_ohlcv.csv \
  --output reports/validation/spring_wfv_csv.json
```

## Validation Pipeline

### Regimes Tested

```
1. Bull 2021 (Jan-Nov)     → Accumulation → ATH ~$69k
2. Bear 2022 (Jan-Dec)     → Correction → Bottom ~$16k
3. Recovery 2023 (Jan-Dec) → Consolidation + bounce
4. Bull 2024 partial (Jan-Sep) → Volatility + setup
```

### WFV Windows

Per regime:
- Train period: 180 days
- Test period: 30 days
- Overlap: 0 days
- Sliding step: 30 days

### Point-in-Time Validation

At each test timestamp `t`:
- Use ONLY data available before `t` (no look-ahead)
- Classify with Spring Detector
- Compare signal to next candle's close
- Measure accuracy and IC (Information Coefficient)

## Output Report

Generated: `reports/validation/spring_detector_level4.json`

### Metrics

| Metric | Target | Notes |
|--------|--------|-------|
| IC (Mean) | > 0.015 | Spearman correlation of signal vs outcome |
| IC (Std Dev) | < 0.05 | Stability across windows |
| Hit Rate | > 52% | % correct predictions |
| Stability | > 0.75 | 1 - (std / mean) → consistency |

### Gate Decision

PASS if ALL:
- `ic_mean > 0.01`
- `hit_rate_mean > 0.52`
- `stability > 0.75`

## Interpreting Results

### Good Signal (SPRING_CANDIDATE)
```
IC: +0.18 (strong positive correlation)
Hit Rate: 64% (decent predictive power)
Stability: 0.82 (consistent across regimes)
→ Signal validates across market types
```

### Weak Signal
```
IC: +0.003 (near random)
Hit Rate: 51% (barely better than flip)
Stability: 0.45 (inconsistent)
→ Refinement needed before Phase B
```

## Troubleshooting

### "No data from Binance"
- Check internet connectivity
- Verify Binance API is accessible
- Try yfinance fallback

### "Not enough test data for window"
- Increase test_period_days
- Or decrease overlap_days

### Low IC / Hit Rate
- Spring Detector may need refinement
- Check for look-ahead bias in test data
- Validate on different timeframe (4h instead of 1d)

## Next Steps (Phase B)

Once Level 4 PASSED:
1. **RPM/RCM Engine**: Capital rotation detection
2. **NARM-P+**: Narrative adoption scoring  
3. **RRP Revival Radar**: Dead token resurrection
4. **Dashboard**: iPhone-optimized monitoring
5. **Agent**: Autonomous research assistant

## References

- [ITWT-PREDICTIVE-INFORMATION-001.md](./ITWT-PREDICTIVE-INFORMATION-001.md) - Full validation spec
- [Spring Detector P0.4](../src/data/spring_detector.py) - Current implementation
- [WFV Pipeline](../src/validation/level_4_oos_wfv.py) - Validation engine

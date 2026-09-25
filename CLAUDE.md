# IGWT-PF26: Crypto Intelligence OS — Project Context

**Version**: 0.1.0  
**Status**: Phase A Validation (Spring Detector Level 4 in progress)  
**Last Updated**: 2026-09-25

## Project Mission

IGWT-PF26 is a quantitative research infrastructure for cryptocurrency investment decision support. **NOT** an automated trading bot.

Architecture: 8 research layers combining market regime detection, Wyckoff analysis, narrative signals, and statistical validation.

## Current Work: Spring Detector P0.4 Validation

### Completed

✅ **Spring Detector P0.4** (40/41 tests passing)
- 5-state classifier: NO_SPRING, RANGE, SWEEP, SPRING_CANDIDATE, BREAKDOWN
- Detects Wyckoff spring patterns (range → sweep → reclaim)
- Handles regime boundaries with smart contamination detection
- PIT-compliant (no look-ahead in normal flow)
- Location: `src/data/spring_detector.py`

⚠️ **Known Issue**: `test_look_ahead_c_sweep_not_confirmed_early` 
- Test checks `df[:54]` (close=93.5, no reclaim) but expects SPRING_CANDIDATE
- Reclaim only appears at `df[:56]` (close=99.0)
- Appears to be test data/assertion mismatch, not detector bug
- Do NOT modify test expectations per user guidance

✅ **Level 4 WFV Pipeline** (runnable, awaiting data)
- Walk-forward validation across 4 market regimes (2021-2024)
- PIT methodology (no look-ahead)
- Metrics: IC (Spearman), hit_rate, stability
- Gate criteria: IC > 0.01 AND HR > 52% AND Stability > 0.75
- Location: `src/validation/level_4_oos_wfv.py`

✅ **Data Layer**
- Binance source (requires `pip install ccxt`)
- yfinance fallback
- CSV loader
- OHLC integrity validation
- Location: `src/validation/data_sourcing.py`

✅ **Documentation**
- VALIDATION-WFV-GUIDE.md: Step-by-step user guide
- ITWT-PREDICTIVE-INFORMATION-001.md: Full validation specification

### Next Steps (Immediate)

1. **Run WFV on Real Data** (blocking Phase B)
   ```bash
   pip install ccxt  # or yfinance
   python src/validation/level_4_oos_wfv.py --source binance --start 2021-01-01
   ```
   Expected runtime: 10-30 minutes
   Output: `reports/validation/spring_detector_level4.json`

2. **Interpret Results**
   - If PASS (IC>0.01, HR>52%, Stability>0.75): Proceed to Phase B
   - If FAIL: Investigate low IC/HR/Stability; refactor Spring Detector P0.5

3. **Phase B (if P0.4 passes WFV)**
   - RPM/RCM: Capital rotation engine
   - NARM-P+: Narrative adoption scoring
   - RRP: Dead token revival detection
   - Dashboard: Market monitoring UI
   - Agent: Autonomous research assistant

### Known Limitations

- **test_look_ahead_c**: May require temporal architecture redesign (P0.5)
- **Data dependencies**: ccxt/yfinance not pre-installed
- **P0.5 (abandoned)**: Temporal model passes 0/3 critical tests; needs rethinking

## Architecture Overview

### Layer 1: Data Intelligence
- CoinGecko, Binance, Glassnode, DefiLlama, Nansen, Arkham, AIXBT, Polymarket

### Layer 2: Market Regime Engine
- Bitcoin regime detection (Bull/Bear/Accumulation)
- Liquidity, risk-on/off, macro conditions

### Layer 3: Wyckoff Intelligence
- **Bottom Confirmation Engine (BCE)**: 6-point range validation
- Requires BCE >= 5/6 before entry signal

### Layer 4: X20 Engine
- Identifies asymmetric opportunities (potential 10x-20x)
- Fundamental + narrative + quantitative scoring

### Layer 5: NARM-P+ 
- Narrative Adoption Rotation Model (100 pts)
- Sector rotation detection

### Layer 6: RPM/RCM
- Capital flow detection
- Rotation confirmation

### Layer 7: RRP Revival Radar
- Dead token resurrection monitoring

### Layer 8: RPM X20 Optimizer
- Strategy optimization
- MFE/MAE analysis
- Overfit detection

## Technical Stack

- **Backend**: Python + FastAPI
- **Data**: Parquet, DuckDB, Turso
- **Streaming**: Kafka, Redis Streams
- **ML**: MLFlow, Optuna
- **Frontend**: Next.js + React (mobile-first)

## Key Files

| File | Purpose | Status |
|------|---------|--------|
| `src/data/spring_detector.py` | P0.4 classifier | ✅ 40/41 tests |
| `src/data/spring_detector_p05_temporal.py` | P0.5 (WIP) | ⚠️ Incomplete |
| `src/validation/level_4_oos_wfv.py` | WFV pipeline | ✅ Runnable |
| `src/validation/data_sourcing.py` | Data layer | ✅ Ready |
| `docs/ITWT-PREDICTIVE-INFORMATION-001.md` | Validation spec | ✅ Complete |
| `docs/VALIDATION-WFV-GUIDE.md` | User guide | ✅ Complete |
| `tests/test_spring_detector.py` | Test suite (41 tests) | ✅ 40/41 passing |

## Development Branch

- **Branch**: `claude/busy-goodall-jmiaq3`
- **Remote**: origin (up to date)
- **Commits**: 2 (Spring Detector + WFV pipeline)

## Token Economy Notes

- Responses: Concise, direct, no fluff
- No verification reads on just-edited files
- Parallel tool calls where independent
- Cache context from previous messages

## Critical Constraints

1. **No automated trading**: Decisions stay human-driven
2. **No heuristics**: Prefer deterministic architecture (temporal causality)
3. **PIT validation**: Never use future data in testing
4. **BCE >= 5/6**: Mandatory gate for entry signals
5. **FOMO circuit breaker**: Prevent emotional entries

## Questions for Next Session

1. Should we run WFV now, or refactor P0.5 first?
2. If WFV shows P0.4 fails: temporal architecture (P0.5) or regime-aware heuristics?
3. test_look_ahead_c: Fix test data or accept as known limitation?
4. Phase B priority: RPM/RCM or NARM-P+ first?

---

**Last Action**: Completed WFV pipeline, awaiting real data validation.  
**Estimated Next**: 30min to run WFV, 2-4h if P0.4 refinement needed.

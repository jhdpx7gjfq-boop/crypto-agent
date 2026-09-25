# IGWT-PF26: Crypto Intelligence OS — Project Context

**Version**: 0.2.0  
**Status**: Phase B-001 (Ablation Study: Spring + Context Validation)  
**Last Updated**: 2026-09-25

## Project Mission

IGWT-PF26 is a quantitative research infrastructure for cryptocurrency investment decision support. **NOT** an automated trading bot.

Architecture: 8 research layers combining market regime detection, Wyckoff analysis, narrative signals, and statistical validation.

## Current Work: Phase B-001 (Incremental Alpha Research)

### Phase A: CLOSED ✅

Spring Detector P0.4 WFV Results:
- IC = 0.000 (target >0.01) ❌ **REJECTED as standalone alpha**
- HR = 87.1% (target >52%) ✅
- Stability = 1.0 (target >0.75) ✅
- Status: **Frozen. Retained as structural feature, NOT modified.**

### Phase B-001: COMPLETED ✅ — GATE FAILED ❌

**Objective**: Spring incremental alpha?

**Results**: Spring redundant (Δ IC = 0.000), Regime weak (+0.020)
- Model A: IC = -0.1208
- Model B (+ Spring): IC = -0.1208 (Δ = 0.000 ❌)
- Model C (+ Regime): IC = -0.1006 (Δ = +0.020)

### Phase B-002: COMPLETED ✅ — GATE FAILED ❌

**Objective**: Capital flow (OI, Funding) incremental alpha?

**Results**: Flow negative (Δ IC = -0.0009), makes predictions worse
- Model A: IC = -0.1208, HR = 43.6%
- Model D (+ Flow): IC = -0.1217 (Δ = -0.0009 ❌, WORSE)
- Model G (Full): IC = -0.1128 (Spring adds only +0.009)

**Verdict**: Micro-structure layers (Spring + Regime + Flow) non-predictive on 1D BTC

### Micro-Structure Investigation: COMPLETE

| Layer | Δ IC | Status | Notes |
|-------|------|--------|-------|
| Spring (B-001) | 0.000 | ❌ | Pattern detector, not predictor |
| Regime (B-001) | +0.020 | ⚠️ | Weakly helpful, insufficient |
| Flow (B-002) | -0.0009 | ❌ | Negative; synthetic data noise likely |
| Full Stack (B-002) | -0.113 | ❌ | No synergy; all components weak |

**Key Finding**: Baseline momentum (IC ≈ -0.12) is contrarian: predicts DOWN when momentum UP.

**Key Files**:
- `docs/SPRING-PHASE-B-002-SPEC.md`, `RESULTS.md`: Flow validation
- `reports/research/phase_b_002_ablation.json`: Raw data

### Constraints (FROZEN)

**No modifications to**:
- Spring Detector P0.4 logic
- BCE/X20/RPM parameters
- Phase A validation results

### Phase B-003 Options (Micro-Structure Complete, Failed)

Micro-structure (Spring + Regime + Flow) proven non-predictive on 1D BTC.

**Option 1: Jump to Macro (Layer 5) — RECOMMENDED**
- Abandon micro-structure entirely
- Test NARM-P+ (Narrative + adoption rotation)
- Then RPM/RCM (Capital rotation on macro scale)
- Assumption: Alpha in narrative/macro, not order flow

**Option 2: Test X20 Standalone (Layer 4)**
- Asymmetric opportunities (10-20x potential tokens)
- Different signal type vs momentum-based layers
- May be independent of 1D return prediction
- Then test X20 + macro (NARM-P+, RPM/RCM)

**Option 3: Horizon Experiment (Branch B-002-ALT)**
- Re-run B-001/B-002 with 5D returns instead of 1D
- Test if Flow/Spring/Regime IC flips positive on longer horizon
- If yes, rebuild stack for 5D; if no, confirm micro is dead
- Risk: Extends validation cycle significantly

**Option 4: Real Flow Data (Contingency)**
- Current Flow used synthetic data (placeholder OI/Funding)
- If had `pip install ccxt` → real Binance Perpetual data
- Re-run D/G with authentic signals
- Risk: Still likely to fail (Flow inherently not lead indicator)

---

**Phase B-003 awaits user directive. Micro-structure validation complete.**

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

## Latest: WFV Validation Complete (2026-09-25)

**Results**: Spring Detector P0.4 passes 2/3 gate criteria
- IC = 0.000 (target >0.01) ❌ **FAILED**
- HR = 87.1% (target >52%) ✅ PASSED
- Stability = 1.0 (target >0.75) ✅ PASSED

**Interpretation**: Detector identifies Wyckoff patterns accurately (87% overall accuracy), but sweep depth alone is not predictive of immediate price moves. Requires integration with other layers.

**Path Forward**:
1. Phase B: Implement RPM/RCM (capital rotation), NARM-P+ (narrative)
2. Re-validate integrated system (layers 2-6 combined)
3. Final IC measurement after full architecture assembly

**Action**: WFV complete. Ready for Phase B implementation.  
**Next Session**: Start RPM/RCM engine (capital flow detection)

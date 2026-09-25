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

### Phase B-001: IN PROGRESS 🔄

**Objective**: Determine if Spring becomes predictive when conditioned on market context.

**Framework**:
- Ablation matrix: 7 models (A=Baseline, B=+Spring, C=+Regime, D=+Flow, E=+Spring+Regime, F=+Spring+Flow, G=Full)
- PIT validation across 4 market regimes (2021-2024), 18 WFV windows
- Metrics: Incremental IC, HR, Expectancy, MFE/MAE per window + per regime

**Gate Criteria**:
- Spring incremental IC: IC(B) - IC(A) > 0.005
- Spring + Regime synergy: IC(E) - IC(C) > 0.003

**Status**: 
- Framework built ✅ (spec + 6 modules)
- WFV running (30-45 min) 🔄
- Output: `reports/research/phase_b_001_ablation.json`

**Key Files**:
- `docs/SPRING-PHASE-B-001-SPEC.md`: Full protocol
- `src/research/market_regime_detector.py`: Trend/Vol classification (PIT-safe)
- `src/research/baseline_predictor.py`: Model A (momentum only)
- `src/research/spring_context_predictor.py`: Models B-G
- `src/research/ablation_framework.py`: IC/HR measurement engine
- `src/research/phase_b_001_runner.py`: WFV orchestration

### Constraints (FROZEN)

**No modifications to**:
- Spring Detector P0.4 logic
- BCE/X20/RPM parameters
- Phase A validation results

### Next Steps (Conditional on Phase B-001 Gate)

**If Phase B-001 PASS**:
1. Phase B-002: Capital Flow layer (OI, funding, liquidations)
2. Re-validate integrated system (Layers 2-6 combined)
3. Final IC measurement after full architecture assembly

**If Phase B-001 FAIL**:
1. Archive Spring P0.4 as non-predictive structural feature
2. Pivot to Regime-only model (C) for Phase B gates
3. Investigate alternative entry signals (X20, NARM-P+)

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

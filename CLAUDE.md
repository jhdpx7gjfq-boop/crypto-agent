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

**Objective**: Determine if Spring becomes predictive when conditioned on market context.

**Results**:
```
Model A (Baseline)           : IC = -0.121
Model B (+ Spring)           : IC = -0.121  [delta = 0.000 ❌ <0.005]
Model C (+ Regime)           : IC = -0.100  [delta = +0.020]
Model E (+ Spring + Regime)  : IC = -0.100  [delta = 0.000 ❌ <0.003]
```

**Key Findings**:
- **Spring is fully redundant** (delta IC = 0.000): No new predictive information
- **Regime adds marginal value** (+0.020 IC): Weak but present
- **Spring + Regime: No synergy** (E = C): Spring doesn't enrich regime context
- **Baseline momentum is contrarian** (IC<0): Predicts DOWN when momentum UP

**Gate Decision**: FAIL
- Spring incremental IC: 0.000 (target >0.005) ❌
- Spring + Regime synergy: 0.000 (target >0.003) ❌

**Interpretation**:
- Spring excels at pattern detection (HR=87% from Phase A)
- But produces signals uncorrelated with short-term returns (IC=0)
- Possible issues: 1D horizon too short, momentum reversion natural in crypto, or Spring simply doesn't predict

**Key Files**:
- `docs/SPRING-PHASE-B-001-SPEC.md`: Protocol
- `docs/SPRING-PHASE-B-001-RESULTS.md`: Full interpretation
- `reports/research/phase_b_001_ablation.json`: Raw results
- `src/research/`: Framework (6 modules, reusable for Phase B-002)

### Constraints (FROZEN)

**No modifications to**:
- Spring Detector P0.4 logic
- BCE/X20/RPM parameters
- Phase A validation results

### Architectural Decision: Phase B-002 Roadmap

Phase B-001 FAILED → Multiple options forward:

**Option 1: Archive Spring (Recommended)**
- Spring retained as structural/risk-mgmt tool (not signal)
- Proceed to Phase B-002: Capital Flow layer (OI, Funding, Liquidations)
- Test: IC(Flow) alone, then IC(Regime + Flow)

**Option 2: Investigate Capital Flow First**
- Test if Flow layer is sufficient for Phase B predictiveness
- Ablation: D, F, G fully implemented (currently placeholder)
- If IC(D-A) >0.010, proceed; else abandon this path

**Option 3: Modify Horizon**
- Test 5D returns instead of 1D (momentum reversion vs trend)
- Re-run B/C/E on longer horizon
- If Spring IC improves on longer term, reconsider architecture

**Option 4: Pivot to Layer 4 (X20 Engine)**
- Skip Flow layer entirely
- Test X20 (asymmetric opportunities) as Phase B core
- Measure IC(X20 alone), then IC(Regime + X20)

**Option 5: Reconsider Entire Stack**
- Accept that micro-structure layers (Spring/Flow) may not be predictive
- Build Phase B on macro layers (Layer 5: NARM-P+, Layer 6: RPM/RCM)
- Wyckoff + narrative rotation + capital rotation as primary signals

---

**Awaiting user directive. CLAUDE.md will freeze here until Phase B-002 scope is chosen.**

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

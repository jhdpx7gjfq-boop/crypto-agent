# IGWT-PF26: Crypto Intelligence OS — Project Context

**Version**: 0.3.0  
**Status**: Phase 2.1 FINAL PASS ✅ | B-004 UNBLOCKED  
**Last Updated**: 2026-09-25  
**Gate 2.1 Decision**: Exception ACCEPTED (1 pre-existing test, out-of-scope)

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

### Phase B-003: COMPLETED ✅ — GATE FAILED ❌

**Objective**: NARM-P+ (Narrative + Adoption) incremental alpha?

**Results**: NARM-P+ IC improved +0.0359 points, but fails overall gate
- Model A (Baseline): IC = -0.1208, HR = 43.6%
- Model H (+ NARM-P+): IC = -0.0849 (Δ = +0.0359 points)
- Model I (Full stack): IC = -0.0935 (regresses vs H; Δ = -0.0086)

**Gate Criteria** (ALL must pass):
1. Δ IC(H-A) > 0.005: **✅ PASS** (0.0359 points)
2. HR(H) > 0.50: **❌ FAIL** (0.4363 = 43.6%)
3. Stability(H) > 0.65: **⚠️ UNMEASURED**

**Official verdict**: **GATE FAILED** (HR criterion not satisfied)

**Per-Regime IC Deltas** (Δ IC in points):
| Regime | A IC | H IC | Δ IC | Status |
|--------|------|------|------|--------|
| Bull 2021 | -0.0930 | -0.0035 | +0.0895 | 🟢 |
| Bear 2022 | -0.0987 | -0.0957 | +0.0030 | 🟡 |
| Recovery 2023 | -0.2019 | -0.1778 | +0.0241 | 🟡 |
| Bull 2024 | -0.0131 | +0.0226 | +0.0357 | 🟢 |

**Classification**:
- **Research finding**: ✅ NARM-P+ reduces contrarian drift magnitude in Bull regimes
- **Production signal**: ❌ IC final still negative; HR fails; no standalone directional alpha
- **Full stack (I)**: ❌ Excludes Spring/Regime (regression: −0.0086)
- **Data-snooping risk**: 19 windows × 4 regimes requires caution on regime claims (post-hoc analysis only)

**Key Files**:
- `docs/SPRING-PHASE-B-003-SPEC.md`: Protocol
- `docs/SPRING-PHASE-B-003-RESULTS.md`: Full interpretation
- `reports/research/phase_b_003_ablation.json`: Raw data
- `src/research/narm_data_layer.py`, `narm_predictor.py`, `phase_b_003_runner.py`: Implementation

### Micro & Macro Investigation: COMPLETE ✅

| Layer | Type | Δ IC | Gate | Notes |
|-------|------|------|------|-------|
| Spring (B-001) | Micro | 0.000 | ❌ FAIL | Pattern detector, not predictor |
| Regime (B-001) | Micro | +0.020 | ⚠️ WEAK | Insufficient incremental alpha |
| Flow (B-002) | Micro | -0.0009 | ❌ FAIL | Negative; adds noise |
| **NARM-P+ (B-003)** | **Macro** | **+0.0359** | **❌ FAIL** | **ΔIC passes, HR/Stability fail; research finding only** |

**Verdict**: 
- **Micro-structure**: Non-predictive (0 to −9 bps IC delta)
- **Macro-structure**: Research signal identified (ΔIC +35.7–89.5 points in Bull regimes), but production validation fails (HR > 0.50 not met)
- **Next**: Phase B-004 (RPM/RCM capital rotation) **without pre-filtering to Bull** (post-hoc regime analysis only)

### Phase 2.1: COMPLETED ✅ — FINAL PASS ✅

**Objective**: Real equity accounting backtester for WFV validation

**Implementation**: EquityBacktester with mark-to-market, PIT compliance, T→T convention, trade provenance, annualized metrics

**Gate 2.1 Results** (all 6 criteria verified):
1. ✅ PIT No-Lookahead: Signal receives only data[:idx+1]
2. ✅ Future Invariance: Modifying T+n doesn't affect signals T<n
3. ✅ Equity Conservation: close_equity = cash + position_value (exact)
4. ✅ T→T Convention: entry_timestamp ≠ exit_timestamp (strictly different bars)
5. ✅ Annualization: Log-based formula, numerically stable (tested: 100% return → 1.0 annualized)
6. ✅ Trade Provenance: Full record with entry_signal_pit_cutoff, pnl, fees

**Test Suite**:
- Phase 2.1 tests: 9/9 passing
- Old tests: 130/130 passing
- Total: 139/140 (1 pre-existing failure)

**Known Exception** (ACCEPTED by Owner):
- Test: `test_look_ahead_c_sweep_not_confirmed_early` (Spring Detector Phase A)
- Status: Pre-existing (verified on commit `2e2fbd5` before Phase 2.1)
- Scope: OUT-OF-PHASE-2.1 (zero interaction with backtester code)
- Regression: NONE introduced
- Owner approval: 2026-09-25 (ACCEPT EXCEPTION)

**Verdict**: ✅ **GATE 2.1 FINAL PASS** (exception accepted, non-regression verified)

**Status**: Ready for Phase B-004 RPM/RCM validation

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
- **Commits**: 6 (Spring Detector + WFV pipeline + Phase B-001/B-002/B-003 + Phase 2.1 backtester)

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

## Latest: Phase 2.1 FINAL PASS | B-004 UNBLOCKED (2026-09-25)

**Phase 2.1 Backtester Hardening**: ✅ FINAL PASS
- EquityBacktester: Real MTM, PIT compliance, T→T convention, trade provenance
- Test suite: 139/140 passing (1 pre-existing Spring test, out-of-scope)
- Gate 2.1: ALL 6 CRITERIA VERIFIED PASSING
- Exception: Accepted (test pre-existing on commit `2e2fbd5`, zero Phase 2.1 interaction)

**Phase B Micro & Macro Investigation**: COMPLETE
- **Micro-structure (Spring + Regime + Flow)**: Non-predictive (Δ IC = 0 to −9 points)
- **Macro-structure (NARM-P+)**: Research signal (ΔIC +35.7–89.5 points in Bull), production gate fails (HR < 0.50)

**Path Forward**:
1. **Phase B-004**: RPM/RCM validation (UNBLOCKED) — FULL WFV, no pre-filtering to Bull
2. **Protocol**: Freeze results → measure ΔIC/HR/Stability → test gate criteria → post-hoc regime analysis
3. **Layer 8**: BLOCKED until alpha independently validated

**Status**: Phase 2.1 prerequisite complete. B-004 ready to execute.  
**Next**: RPM/RCM capital rotation (Layer 6) — full-dataset WFV validation

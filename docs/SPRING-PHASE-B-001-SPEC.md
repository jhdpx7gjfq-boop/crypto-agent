# SPRING-PHASE-B-001: Incremental Alpha / Context Validation

**Status**: Research Protocol  
**Objective**: Determine if Spring becomes predictive when conditioned on market context  
**Frozen**: Spring Detector P0.4 (no modifications; IC=0.000 is canonical)

---

## 1. Protocol

### Freeze P0.4
- Spring Detector locked at current state
- Result: IC=0.000, HR=87.1%, Stability=1.0 (standalone REJECTED)
- Role: Structural feature only

### Baseline Construction
- Universe: BTC/USDT 2021-2024 (same as Phase A WFV)
- Windows: 180d train / 30d test / 30d overlap (PIT validation)
- Regimes: Bull 2021, Bear 2022, Recovery 2023, Bull 2024
- Target: Next-candle return (same as Phase A)

### Ablation Matrix

```
A = Baseline (no Spring, no Regime, no Flow)
B = Baseline + Spring
C = Baseline + Regime
D = Baseline + Flow
E = Baseline + Spring + Regime
F = Baseline + Spring + Flow
G = Baseline + Spring + Regime + Flow (Full)
```

Goal: Measure incremental IC for each component independently and conditionally.

---

## 2. Contextual Variables

### Priority 1: Market Regime
- Trend (Bull / Bear / Sideways)
- Volatility (High / Low)
- Signal: Rolling directional filter; smoothed ATR

### Priority 2: Capital Flow
- Volume (normalized)
- OI (open interest) — if data source PIT-compliant
- Funding rates — if Binance Perpetual data available
- Liquidation cascade — if Glassnode API attached
- **Gate**: Only use if no forward-look bias

### Priority 3: Structure/Liquidity
- Break of Structure (BoS) — higher/lower highs/lows
- FVG / Open Block detection
- Liquidity sweep zones
- **Later phase**: Only if Phase B shows Spring + Regime insufficient

### NOT YET
- X20 Engine
- NARM-P+
- RPM/RCM
- Parameter tuning on Spring
- BCE modifications

---

## 3. Metrics (Per Window + Summary)

### IC (Information Coefficient)
- Spearman rank correlation: signal vs next-candle return
- Report: Mean, Std, Min, Max across windows
- Delta IC: IC(B) - IC(A), IC(E) - IC(C), etc.

### Hit Rate
- Correct state classification (if binary: UP/DOWN)
- Report: %, std
- Note: Class imbalance check (% SPRING_CANDIDATE vs others)

### Expectancy / Return
- Average return on SPRING_CANDIDATE signals
- Average return on non-SPRING signals
- Report: Mean, Std, Sharpe (if applicable)

### Max Adverse Excursion / Favorable Excursion (MFE/MAE)
- From entry to N-candle horizon
- Report: Max MFE, Max MAE, MFE/MAE ratio

### Max Drawdown
- Peak-to-trough during test period
- Per window + aggregate

### Stability
- 1 - (IC_std / |IC_mean|)
- Per regime + aggregate

---

## 4. Validation Gates

### Within-Sample (Train Period)
- No IC reported; fitting only
- Log: window splits, feature states

### Out-of-Sample (Test Period)
- PIT: No future data
- Look-ahead audit: Timestamp <= test_timestamp in feature calc
- Report: OOS IC, HR, Expectancy

### Walk-Forward
- 18 windows across 4 regimes
- Per-regime stability
- Cross-regime generalisation

---

## 5. Gate Decision

**Phase B PASS** requires:
- Incremental IC(B) - IC(A) > 0.005 (Spring adds signal)
- **AND** IC(E) - IC(C) > 0.003 (Spring + Regime synergy)
- **AND** Per-regime stability > 0.70

**If PASS**: Proceed to Priority 2 (Capital Flow)  
**If FAIL**: Archive P0.4 as non-predictive feature; pivot to Regime-only (C) for Phase B gates.

---

## 6. Implementation Files

| File | Purpose |
|------|---------|
| `src/research/ablation_framework.py` | Engine: runs A-G tests |
| `src/research/market_regime_detector.py` | Regime context |
| `src/research/baseline_predictor.py` | Model A baseline |
| `src/research/spring_context_predictor.py` | Models B-G |
| `src/research/phase_b_001_runner.py` | Orchestration + WFV |
| `reports/research/phase_b_001_ablation.json` | Results |

---

## 7. Output Report

```json
{
  "phase": "B-001",
  "frozen": "Spring P0.4 (IC=0.000)",
  "ablation": {
    "A": { "ic_mean": 0.xxx, "ic_std": 0.xxx, "hr_mean": 0.xxx },
    "B": { ... },
    ...
    "G": { ... }
  },
  "deltas": {
    "ic_delta_b_a": 0.xxx,
    "ic_delta_e_c": 0.xxx,
    "ic_delta_f_d": 0.xxx,
    "ic_delta_g_c": 0.xxx
  },
  "per_regime": {
    "bull_2021": { "a": {...}, "b": {...}, ... },
    ...
  },
  "gate": "PASS|FAIL",
  "next": "Phase B-002 (Capital Flow) | Archive P0.4"
}
```

---

## 8. Timeline & Constraints

- **Duration**: ~2-4 hours (WFV × 7 models)
- **Data**: yfinance (PIT-compliant; no ccxt needed)
- **Code**: No modification to Spring P0.4
- **Freeze**: Respect user constraint; do NOT change BCE/X20 thresholds

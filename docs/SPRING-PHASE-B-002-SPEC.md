# SPRING-PHASE-B-002: Capital Flow Layer Validation

**Status**: Research Protocol — Phase B-002  
**Objective**: Measure incremental IC contribution of capital flow signals  
**Frozen**: Spring P0.4, Regime, Baseline momentum (from B-001)

---

## 1. Data Contract: Capital Flow

### Signals Required

| Signal | Source | Granularity | PIT? | Coverage | Priority |
|--------|--------|-------------|------|----------|----------|
| Open Interest (OI) | Binance Perpetual | 1D | ✅ | 2019+ | P0 |
| Funding Rate | Binance Perpetual | 8h→1D | ✅ | 2019+ | P0 |
| Liquidation Cascade | Binance Perpetual | 1h→1D | ✅ | 2020+ | P1 |
| Volume (CVD) | Spot + Perp | 1D | ✅ | 2021+ | P1 |

### Data Availability Audit

**Binance Perpetual (ccxt / HTTP API)**:
- OI: Daily snapshot (end-of-day)
- Funding: Historical rates (8h intervals, aggregatable to 1D)
- Liquidations: Event stream (realtime, can backfill via Glassnode if needed)

**Constraints**:
- OI backward-available from 2019
- Funding rates from first futures listing
- Liquidations depend on Glassnode access (optional; fallback: Nansen/OnChain Labs)

### PIT Protocol (CRITICAL)

At each test timestamp `t`:
1. **OI as-of-t**: Use only OI snapshot <= t (not future OI)
2. **Funding rate avg**: Use only rates from periods ending before t
3. **Liquidation cascade**: Count only liquidations timestamp < t
4. **Volume**: Daily close as-of t (known by EOD t)

**NO forward-looking**:
- Don't use tomorrow's OI to predict today's return
- Don't use intraday liquidations if testing at EOD

---

## 2. Flow Signals: Definitions

### OI Signal
```
oi_change_pct = (OI_today - OI_yesterday) / OI_yesterday
- Positive: Longs accumulating, risk appetite
- Negative: Longs liquidating, risk off
```

### Funding Rate Signal
```
funding_rate_7d_avg = mean(rates over last 7 days)
- Positive & high: Longs paying shorts, euphoric
- Negative & low: Shorts paying longs, bearish
```

### Liquidation Signal
```
liquidation_cascade = liquidation_volume_1d / ADV
- > 0.5%: Significant cascade, potential washout
- < 0.1%: Normal
```

### Volume Signal (if available)
```
adv_vs_sma = ADV / SMA(ADV, 20)
- > 1.2: High volume momentum
- < 0.8: Low volume, weak move
```

---

## 3. Ablation Models (B-002 Scope)

```
A = Baseline momentum (from B-001)
D = Baseline + Flow (all signals above)
G = Baseline + Spring + Regime + Flow (full stack)
```

### Model Definitions

**Model A (Frozen from B-001)**:
- Input: 5D momentum slope
- Output: Direction score [-1, +1]

**Model D (NEW)**:
- Input: Baseline + OI change + Funding avg + Liquidation cascade
- Blend: 50% baseline, 30% OI, 15% Funding, 5% Liquidations
- Output: Direction score [-1, +1]

**Model G (NEW)**:
- Input: Baseline + Spring state + Regime + Flow
- Blend: 30% baseline, 20% OI, 10% Funding, 3% Liquidations, 25% Spring, 12% Regime
- Output: Direction score [-1, +1]

---

## 4. Validation Pipeline

### Phase 1: Data Collection & Audit
```
1. Fetch OI historical (Binance, ccxt)
2. Fetch Funding rates (Binance, ccxt)
3. Fetch Liquidations (if Glassnode available, else placeholder)
4. Align timestamps with OHLCV
5. Check: NaN, duplicates, gaps, forward-look bias
```

### Phase 2: PIT Audit
```
- At each test t, verify: all flow data uses only info before t
- Simulate strict PIT environment
- Log any violations
```

### Phase 3: Look-Ahead Audit
```
- Run detector at t with data < t
- Run detector at t+1 with data < t+1
- Verify: signals different (not hardcoded)
- Verify: using fresh info, not stale
```

### Phase 4: WFV
```
- Same 19 windows as B-001
- Same regimes: bull_2021, bear_2022, recovery_2023, bull_2024
- Metrics: IC, HR, Expectancy per window + per regime
```

### Phase 5: Ablation & Decision
```
- Compute deltas: D-A, G-D, G-A
- Per-regime stability
- Cross-regime generalization
- Gate decision
```

---

## 5. Gate Criteria

### Flow Contribution (D vs A)

**PASS if ALL**:
- `IC(D) - IC(A) > 0.003` (Flow adds info)
- `HR(D) > 0.48` (Better than random)
- `Stability(D) > 0.70` (Consistent across regimes)

**FAIL if ANY**:
- `IC(D) ≤ IC(A)` (Flow subtracts or adds nothing)
- Flow data unavailable / unvalidated

### Spring in Flow Context (G-D)

**If Flow PASS**:
- If `IC(G) > IC(D)` by >0.001: Spring has marginal value in flow context
- If `IC(G) ≈ IC(D)`: Spring remains structural only
- If `IC(G) < IC(D)`: Spring is noise in flow context

---

## 6. Expected Outcomes & Branches

### Scenario A: Flow Succeeds (IC Δ > 0.003)
→ **Proceed to B-003**: Add X20 layer (asymmetric signal)
→ Combine: Baseline + Flow + X20

### Scenario B: Flow ≈ Baseline (Δ ≈ 0)
→ **Archive Flow**: Non-predictive micro-structure signal
→ **Pivot to B-003 Alt**: Test X20 standalone
→ Or: Jump to Layer 5 (NARM-P+ macro)

### Scenario C: Flow Fails (IC < Baseline)
→ **Reject Flow**: Negative information
→ **Halt micro-structure investigation**
→ **Jump to Layer 4-5 (macro signals)**

---

## 7. Implementation Files

| File | Purpose |
|------|---------|
| `src/research/flow_data_layer.py` | OI/Funding/Liquidation fetcher |
| `src/research/flow_predictor.py` | Models D + G |
| `src/research/phase_b_002_runner.py` | WFV orchestration |
| `docs/SPRING-PHASE-B-002-RESULTS.md` | Interpretation |

---

## 8. Timeline & Constraints

- **Data fetch**: ~10 min (Binance API)
- **PIT audit**: ~5 min
- **WFV execution**: ~20-30 min (19 windows × 2 models)
- **Total**: ~45 min
- **Constraints**: No modification to A (Baseline) or Spring
- **Freeze**: All decisions await full B-002 completion + gate evaluation

---

## 9. Success Criteria for Proceeding to B-003

✅ Flow data validated (PIT, look-ahead audits pass)
✅ Flow IC Δ > 0.003 (statistically meaningful improvement)
✅ Flow stability > 0.70 (generalizable across regimes)
✅ No artifacts or data leakage detected

If all ✅ → **Phase B-003: X20 + Ablation (D+X20, G+X20)**

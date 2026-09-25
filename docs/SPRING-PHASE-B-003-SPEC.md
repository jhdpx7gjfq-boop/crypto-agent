# SPRING-PHASE-B-003: Macro Layer (NARM-P+) Validation

**Status**: Research Protocol — Phase B-003  
**Objective**: Test Narrative + Adoption layer for incremental IC  
**Frozen**: Spring P0.4, Regime, Baseline, Flow (from B-001/B-002)

---

## 1. Data Contract: Narrative Signals

### Signals Required (Macro, NOT micro-structure)

| Signal | Source | Type | PIT? | Coverage | Priority |
|--------|--------|------|------|----------|----------|
| Social Sentiment | LunarCrush, Santiment | Score 0-100 | ✅ | 2021+ | P0 |
| Dev Activity | GitHub, Glassnode | Commits/activity | ✅ | 2020+ | P0 |
| On-Chain Adoption | Glassnode, Nansen | Active addresses | ✅ | 2019+ | P1 |
| Sector Narrative | CoinGecko categories, news | Category dominance | ✅ | 2021+ | P1 |
| Funding/Investor | CrunchBase, on-chain | Recent rounds | ✅ | 2020+ | P2 |

### Data Availability

**Free/Public Sources** (no auth required):
- CoinGecko: Categories, trending, market cap, dominance
- LunarCrush: 30D free trial (historical data available)
- GitHub: Public commits, repo activity
- Social: Twitter Trends API (free tier limited)

**Paid/Restricted** (skip if unavailable):
- Glassnode: On-chain metrics (requires API key — skip if not available)
- Santiment: Sentiment (API key required)

**Fallback**: Use synthetic NARM-P+ scores from LunarCrush directly (if available as historical data).

### PIT Protocol

At each test timestamp `t`:
1. **Social sentiment as-of-t**: Use sentiment snapshot <= t (not future sentiment)
2. **Dev activity**: Commits/activity that occurred before t
3. **On-chain**: Active address counts as-of t
4. **Sector narrative**: Dominant category as-of t (known by market consensus)

**NO forward-looking**: Don't use tomorrow's news/sentiment to predict today's return.

---

## 2. NARM-P+ Signal Definition

**Narrative Adoption Rotation Model Plus** (100-point scale):

```
NARM-P+ Score = 100 × [
    0.25 × sentiment_score +        # Social narrative strength (0-1)
    0.25 × adoption_score +         # On-chain + dev activity (0-1)
    0.20 × rotation_signal +        # Capital rotation indicator (0-1)
    0.20 × fundamentals_score +     # Funding, team, roadmap (0-1)
    0.10 × momentum_confirmation    # Price momentum alignment (0-1)
]
```

### Components

**Sentiment Score (0-1)**:
- LunarCrush sentiment (convert 0-100 scale to 0-1)
- Social spike detection (% increase in mentions)
- Weighted avg: 70% LunarCrush, 30% trend acceleration

**Adoption Score (0-1)**:
- On-chain active addresses (vs 30D avg): (current / avg_30d - 1) capped
- GitHub activity (commits/PR vs avg): similar
- Dev + adoption equal weight (0.5 each)

**Rotation Signal (0-1)**:
- Sector dominance change: (sector_mcap_share_today / sector_mcap_share_1w_ago) - 1
- +1 if sector is gaining narratively (new ATH, media attention)
- -1 if sector losing share

**Fundamentals Score (0-1)**:
- Recent funding rounds (1 = fresh funding, 0.5 = old, 0 = none)
- Team changes (0.7 = new major hire, 0.3 = stable, 0 = departures)
- Roadmap milestones (0.8 = major milestone achieved, 0 = delays)
- Simplified: Use 0.5 as default (neutral) unless explicit event

**Momentum Confirmation (0-1)**:
- Price momentum (5D return): +0.1 if positive, -0.1 if negative
- Volume trend: +0.1 if volume spike, 0 otherwise
- Combined: 0.5 baseline, ±0.2 range based on above

---

## 3. Ablation Models (Phase B-003)

```
A = Baseline momentum (frozen from B-001)
H = Baseline + NARM-P+
I = Baseline + NARM-P+ + Regime + Spring (full stack v2)
```

### Model Definitions

**Model A**: Frozen from B-001
- Input: 5D momentum slope
- Output: Direction score [-1, +1]

**Model H (NEW)**: Baseline + Macro Narrative
- Input: Baseline (50%) + NARM-P+ score (50%)
- Blend: If NARM-P+ > 60 → bias +0.3, if < 40 → bias -0.3
- Output: Direction score [-1, +1]

**Model I (NEW)**: Full Stack v2
- Input: Baseline + NARM-P+ + Regime + Spring
- Blend: 30% baseline, 40% NARM-P+, 15% regime, 15% spring
- Output: Direction score [-1, +1]

---

## 4. Validation Pipeline

### Phase 1: Data Collection & Validation
```
1. Fetch NARM-P+ components (sentiment, adoption, rotation, fundamentals)
2. Validate: NaN, duplicates, forward-look bias
3. Align timestamps with OHLCV (daily)
4. Audit: Can compute score at each timestamp without future data
```

### Phase 2: PIT Audit
```
- At each test t, verify all NARM data uses info before t
- Simulate: Would a real trader have this info at t?
- Flag any violations (e.g., using today's news for today's trade)
```

### Phase 3: WFV
```
- Same 19 windows as B-001/B-002
- Same regimes: bull_2021, bear_2022, recovery_2023, bull_2024
- Metrics: IC, HR, Expectancy per window + per regime
```

### Phase 4: Ablation & Gate
```
- Compute deltas: H-A, I-H, I-A
- Per-regime stability
- Cross-regime generalization
- Gate decision
```

---

## 5. Gate Criteria

### NARM-P+ Contribution (H vs A)

**PASS if ALL**:
- `IC(H) - IC(A) > 0.005` (Macro adds meaningful signal)
- `HR(H) > 0.50` (Better than ~random)
- `Stability(H) > 0.65` (Generalizable)

**FAIL if ANY**:
- `IC(H) ≤ IC(A)` (No improvement)
- Data unavailable / unvalidated

### Full Stack Synergy (I vs H)

**If NARM-P+ PASS**:
- If `IC(I) > IC(H)` by >0.003: Spring + Regime add value (unlikely)
- If `IC(I) ≈ IC(H)`: Keep H only; discard Spring/Regime
- If `IC(I) < IC(H)`: Discard Spring/Regime entirely

---

## 6. Expected Outcomes

### Scenario A: NARM-P+ Succeeds (Δ IC > 0.005)
→ **Macro layer is alpha source**
→ Proceed to Phase B-004: RPM/RCM (capital rotation at macro scale)
→ Combine: Baseline + NARM-P+ + RPM/RCM

### Scenario B: NARM-P+ Weak (Δ IC ≈ 0.002)
→ **Narrative weak but not negative** (unlike Flow)
→ Investigate: Better narrative sources? Or inherently weak?
→ Contingency: Test X20 (Layer 4) in parallel

### Scenario C: NARM-P+ Fails (Δ IC ≤ 0 or no data)
→ **Narrative/adoption not predictive either**
→ Conclude: Crypto alpha not in micro (Spring/Flow) or macro (Narrative)
→ **Last resort**: Test X20 (Layer 4 fundamental-driven opportunities)

---

## 7. Implementation Files

| File | Purpose |
|------|---------|
| `src/research/narm_data_layer.py` | Fetch sentiment, adoption, rotation |
| `src/research/narm_predictor.py` | NARM-P+ scoring + models H/I |
| `src/research/phase_b_003_runner.py` | WFV orchestration |
| `docs/SPRING-PHASE-B-003-RESULTS.md` | Interpretation |

---

## 8. Timeline & Constraints

- **Data fetch**: ~15 min (LunarCrush, GitHub, CoinGecko)
- **PIT audit**: ~5 min
- **WFV execution**: ~15 min (19 windows × 2 models)
- **Total**: ~35 min
- **Constraints**: No modifications to A, Spring, Regime, Flow
- **Fallback**: If LunarCrush/GitHub unavailable → synthetic NARM-P+ (deterministic)

---

## 9. Success Criteria for Phase B-004

✅ NARM-P+ data validated (PIT, look-ahead audits pass)
✅ NARM-P+ IC Δ > 0.005 (meaningful improvement)
✅ NARM-P+ stability > 0.65 (generalizable)
✅ Full stack (I) better than macro alone (H)

If all ✅ → **Phase B-004: RPM/RCM + Re-validation**

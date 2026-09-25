# LAYER 7 SPECIFICATION — RRP (Revival Radar Pipeline)

**Version**: 1.0 (FROZEN)  
**Date**: 2026-09-25  
**Status**: FROZEN (Owner approval required before implementation)  
**Scope**: Layer 7 — Dead token resurrection detection

---

## Executive Summary

Layer 7 tests **Revival Radar Pipeline (RRP)** as opportunity detection layer for tokens transitioning from dormancy → resurrection state. Objective: Identify "dead" tokens showing early-stage recovery (on-chain activity spike, holder concentration shift, narrative emergence).

**Key constraint**: RRP is **independent opportunity class**, not gated by Layer 8 constraint (alpha validation). Tests new signal paradigm: resurrection detection vs. return prediction.

**Output**: Revival candidates ranked by revival confidence (0-100) with entry timing recommendations.

---

## 1. RRP Architecture

### 1.1 Signal Class

RRP detects **state transition**, not price prediction:
- **Input**: On-chain inactivity metrics, holder data, sentiment
- **Output**: Revival probability + timing window
- **Target**: Binary (revival vs. non-revival) within 30/60/90 day window

### 1.2 Core Metrics

| Metric | Source | Interpretation | Weight |
|--------|--------|-----------------|--------|
| Dormancy Index | CryptoQuant | Days since last on-chain activity | 0.20 |
| Activity Acceleration | On-chain (diff²) | d²(transactions)/dt² > threshold | 0.25 |
| Whale Accumulation | Glassnode/Nansen | Large holder entry patterns | 0.15 |
| Developer Activity | GitHub (via Arkham) | Code commits, repo activity spike | 0.15 |
| Narrative Momentum | LunarCrush | Mentions acceleration, sentiment shift | 0.15 |
| Liquidity Rebound | CryptoQuant | DEX trading volume spike | 0.10 |

### 1.3 Dormancy Classification

**Active**: Daily transactions > 100, last activity < 7 days → **Not candidate**

**Dormant**: Last activity 30–365 days → **Monitor for revival**

**Dead**: Last activity > 365 days → **High priority for revival detection**

### 1.4 Revival Detection Threshold

Revival confirmed when **ALL** (AND logic):
1. Activity Acceleration > +2σ (above recent mean) for ≥3 consecutive days
2. Whale Accumulation detected (>$100k inflow, <30 day hold)
3. Narrative Momentum > baseline (2x mention rate spike)

**OR** (alternative trigger, lower bar):
- Developer Activity spike + Dormancy > 90 days

---

## 2. Revival Scoring Model

### 2.1 Dormancy Score (D)

```
D = (days_since_activity - 30) / (365 - 30)  # Normalized [0, 1]
D = clip(D, 0, 1)
```

**Interpretation**: D close to 1 = strong dormancy

### 2.2 Activity Acceleration (A)

```
accel_raw = (activity[t] - activity[t-1]) - (activity[t-1] - activity[t-2])
A_normalized = accel_raw / std(recent_acceleration)
A = tanh(A_normalized / 2)  # Clipped [-1, +1]
```

**Interpretation**: A > 0.5 = strong acceleration signal

### 2.3 Whale Entry (W)

```
whale_inflow = sum(wallets > $100k, recent 30 days)
W = min(whale_inflow / baseline_whale_activity, 2.0)  # Capped at 2.0
```

**Interpretation**: W > 1.0 = above-average whale interest

### 2.4 Developer Activity (DE)

```
dev_activity = (commits[t] + issues[t] + PRs[t]) - avg(30-day)
DE = dev_activity / std(30-day)  # Standardized
DE = tanh(DE / 3)  # Clipped [-1, +1]
```

**Interpretation**: DE > 0.3 = measurable dev engagement

### 2.5 Narrative Momentum (N)

```
N_mentions = mentions[t] / avg(30-day mentions)
N_sentiment = (positive - negative) / total_mentions
N = (N_mentions * 0.7 + N_sentiment * 0.3) - 1  # Normalized
N = clip(N, -1, +1)
```

**Interpretation**: N > 0.5 = strong narrative acceleration

### 2.6 Revival Confidence Score

```
Revival_Score = (
    0.20 * D +           # Dormancy component
    0.25 * A +           # Acceleration (highest weight)
    0.15 * W +           # Whale entry
    0.15 * DE +          # Developer engagement
    0.15 * N +           # Narrative shift
    0.10 * L             # Liquidity rebound (L = volume_ratio - 1)
)

Revival_Confidence = sigmoid(Revival_Score) * 100  # [0, 100]
```

**Thresholds**:
- Revival_Confidence > 70: **High candidate** (likely revival)
- Revival_Confidence 50–70: **Medium candidate** (monitor)
- Revival_Confidence < 50: **Low probability** (skip)

---

## 3. Detection Pipeline

### 3.1 Candidate Screening

**Entry criteria** (ALL must be true):
1. Dormancy Index > 30 days
2. Currently listed on ≥2 major exchanges
3. Market cap > $1M (liquidity minimum)
4. Not delisted/deprecated project
5. Tradeable on Binance or top CEX

**Output**: Watchlist of dormant tokens (baseline pool)

### 3.2 Daily Monitoring

For each token in watchlist:
1. Fetch latest on-chain metrics (24h, 7d, 30d)
2. Calculate Revival_Confidence score
3. If > 70: **Alert** (high revival probability)
4. If 50–70: **Log** (candidate, monitor daily)
5. If < 50: **Hold** (insufficient signal)

### 3.3 Confirmation Window

**Once alert triggered**:
- **Next 3 days**: Validate acceleration persistence (must maintain >50% of day-0 acceleration)
- **Days 4–14**: Monitor whale accumulation (if reversed, confidence drops)
- **Days 15–30**: Track narrative momentum (must sustain mention rate)

**Confirmed Revival**: All three validations pass → **Entry Window Opens**

---

## 4. Entry Timing & Risk Management

### 4.1 Entry Window

Recommended entry: **Days 7–14 after confirmation** (early whale accumulation phase)

**Rationale**:
- Day 0–3: Noise risk high (false accelerations)
- Day 7–14: Trend confirmed, whale participation visible
- Day 21+: Price may have recovered (entry timing deteriorates)

### 4.2 Position Sizing

Based on Revival_Confidence:
- **80–100**: 3% of portfolio (high conviction)
- **70–80**: 2% (moderate conviction)
- **50–70**: 1% (exploratory)

### 4.3 Risk Limits

**Stop conditions** (exit if triggered):
1. Revival_Confidence drops below 40 (signal degradation)
2. Whale inflow reverses (large > $500k outflow in 24h)
3. Developer activity halts again (3+ days without updates)
4. Market-wide risk-off (BTC dominance > 50%, overall trend down)

**Position hold duration**: Max 60–90 days if entry confirmed

---

## 5. Historical Validation (WFV)

### 5.1 Backtesting Protocol

**Data period**: 2021-01-01 to 2024-09-25 (same as B-004 for consistency)

**Target definition** (different from B-004):

```python
revival_target = 1 if (
    price[t+30] > price[t] * 1.3  # 30% gain within 30 days
) else 0
```

**Prediction window**: Identify revival candidates → forecast 30-day return

### 5.2 Win Rate & Validation Metrics

**Primary metric**: Win Rate (WR)
```
WR = (number of revivals correctly predicted) / (total candidates)
```

**Gate criterion**: WR > 0.50 (better than random)

**Secondary metrics**:
- Average return on winners: > 50%
- Average loss on losers: < 20%
- Sharpe ratio: > 0.5

### 5.3 Walk-Forward Windows

Same as B-004: **19 expanding windows** (180D train, 30D test, 30D slide)

**Difference**: Target is binary (revival vs non-revival), not continuous return

### 5.4 Out-of-Sample Validation

Split final validation:
- 70% in-sample (19 windows)
- 30% OOS (recent 109 days, untouched during WFV)

**OOS gate criterion**: WR_OOS ≥ WR_IS (no overfitting)

---

## 6. Gate Criteria

### 6.1 Requirements (ALL must pass)

| Criterion | Metric | Target | Rationale |
|-----------|--------|--------|-----------|
| **1. Win Rate** | WR > 0.50 | > 50% | Better than random binary prediction |
| **2. Precision** | TP / (TP + FP) > 0.60 | > 60% | False positive tolerance (avoid whipsaws) |
| **3. Stability** | Std(WR across windows) / Mean(WR) < 0.5 | < 0.5 | Consistent performance across periods |
| **4. OOS Validation** | WR_OOS ≥ WR_IS − 0.05 | ≥ IS−5% | Avoid overfitting (max 5% degradation) |

**Pass decision**: ALL FOUR must be TRUE  
**Fail decision**: ANY ONE is FALSE

### 6.2 Interpretation

| Outcome | Decision | Next Action |
|---------|----------|------------|
| ✅ All pass | **GATE PASS** | Integrate into Layer 7; proceed to Layer 8 research |
| ❌ Any fail | **GATE FAIL** | Document findings; consider alternative metrics or data sources |

---

## 7. Implementation Notes

### 7.1 Code Structure

**Expected modules**:
- `src/data/rrp_data_layer.py` — On-chain + NLP data fetching
- `src/research/rrp_layer.py` — Revival scoring logic
- `src/research/layer_7_runner.py` — WFV orchestration
- `tests/test_rrp.py` — PIT compliance, scoring validation

### 7.2 Data Sources

| Metric | Source | API/Method | Frequency |
|--------|--------|-----------|-----------|
| Dormancy | CryptoQuant | REST API | Daily |
| Activity | CryptoQuant | REST API | Daily |
| Whales | Glassnode / Nansen | REST API | Daily |
| Developer | Arkham / GitHub | REST API | Daily |
| Narrative | LunarCrush | REST API | Real-time |
| Price/OHLCV | Binance | CCXT / REST | 1D candles |

### 7.3 Testing Requirements

```
✓ test_dormancy_classification — Correct binning (Active/Dormant/Dead)
✓ test_revival_score_bounds — Score ∈ [0, 100]
✓ test_acceleration_calculation — d² math correct
✓ test_wfv_windows — 19 windows, correct boundaries
✓ test_win_rate_calculation — Binary target evaluation
✓ test_oos_validation — Train/test split enforced
✓ test_pit_compliance — No future data access
```

---

## 8. Status & Governance

### 8.1 Specification Status

**Current**: 🔴 DRAFT (awaiting owner review)  
**Target**: FROZEN after owner approval  
**Authority**: dvdlgustin@gmail.com  
**Immutability**: LOCKED once frozen (no modifications without new version)

### 8.2 Pre-Implementation Checklist

- [ ] Owner reviews and approves specification
- [ ] Data source access confirmed (CryptoQuant, Glassnode, Nansen, LunarCrush)
- [ ] Historical data availability verified (2021-01-01 to 2024-09-25)
- [ ] Implementation timeline confirmed
- [ ] Gate criteria acceptance confirmed

### 8.3 Freeze Conditions

**Ready to freeze when**:
1. Owner approval given
2. All data sources accessible
3. No material scope changes requested

**After freeze**:
- Specification immutable
- Implementation must conform exactly
- No post-hoc tuning of weights
- Results frozen before analysis

---

## 9. Rationale & Differentiation

### Why Layer 7 Now?

1. **Independent of Layer 8**: No alpha-validation gate required (different signal class)
2. **Different paradigm**: Detection (state transition) vs. Prediction (return forecast)
3. **Lower correlation**: Previous layers (momentum, narrative, flows) all non-predictive; resurrection may succeed
4. **Strategic value**: Complements existing detection layers (Spring, BCE)
5. **Feasible timeline**: Core logic straightforward, data available

### Why RRP Matters

- **Niche opportunity**: Most traders ignore dormant tokens (less competition)
- **Information asymmetry**: Revival signals often missed by momentum-only strategies
- **Testable hypothesis**: Binary outcome (revival vs. non-revival) easier to validate than directional returns
- **Risk management**: Entry window clear, exit rules explicit

---

## 10. Related Documents

- `CLAUDE.md` — Project status and governance
- `SPRING-PHASE-B-004-SPEC.md` — Capital Rotation layer (predecessor)
- `SPRING-PHASE-B-003-SPEC.md` — Macro layer (NARM-P+)
- `ITWT-PREDICTIVE-INFORMATION-001.md` — Validation framework

---

**LAYER 7 SPECIFICATION v1.0**  
**Status**: DRAFT → Awaiting owner approval → FROZEN  
**Date**: 2026-09-25


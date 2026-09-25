# B-004: Rotation & Capital Rotation Model Specification

**Status:** 🟢 SPEC FREEZE (Locked & Immutable)  
**Date:** 2026-09-25  
**Specification ID:** b_004_spec_2026_09_25  
**Authority:** Phase 0 Spec Freeze Gate (Human-Approved)  
**Validation:** Implementation commits frozen against this spec

---

## Executive Summary

B-004 defines the technical specification for RPM (Rotation Prediction Model) and RCM (Rotation Confirmation Model), two capital rotation detection engines for identifying sector/narrative capital flows in crypto markets.

### Specification Purpose
- Freeze technical requirements **before** implementation validation
- Prevent post-hoc definition changes (lookahead bias protection)
- Establish acceptance criteria for backtesting validation
- Create audit trail linking implementation to frozen spec

### Key Principle
**Spec Freeze First, Then Validate** — This order prevents lookahead bias.

---

## 1. Components

### 1.1 RPM — Rotation Prediction Model

**Purpose:** Identify upcoming capital rotation opportunities based on momentum and narrative convergence.

**Input Data:**
- Price momentum (3x, 5x, 10x acceleration detection)
- Trading volume change (>2x surge threshold)
- Developer activity (commit frequency, protocol adoption)
- Smart money accumulation (whale addresses, CEX inflows)
- Narrative signals (media mentions, social sentiment)
- Sector rotation timing (historical seasonal patterns)

**Output:**
- Rotation probability score (0-100)
- Expected duration (days/weeks)
- Confidence level (low/medium/high)
- Key catalysts (funding, launch, regulation)

**Acceptance Criteria:**
- Precision ≥ 60% (true positive rate on detected rotations)
- Recall ≥ 55% (don't miss major rotations)
- F1 score ≥ 0.57 (balanced precision/recall)
- Walk-forward F1 ≥ 0.55 (no overfitting to recent data)

---

### 1.2 RCM — Rotation Confirmation Model

**Purpose:** Confirm a predicted rotation is actually happening (reduce false positives).

**Input Data:**
1. **Capital Flow (25% weight)**
   - CEX inflows to sector coins
   - DEX trading volume concentration
   - Liquidity pool deposits (Uniswap, etc.)

2. **Relative Strength (25% weight)**
   - Sector performance vs. BTC
   - Sector correlation matrix change
   - Price action confirmation (higher highs)

3. **Narrative Acceleration (20% weight)**
   - Mention spike in crypto news
   - GitHub activity acceleration
   - Developer ecosystem metrics

4. **Fundamental Confirmation (20% weight)**
   - Token unlock schedules aligned
   - Partnership announcements
   - Regulatory progress

5. **Derivatives Structure (10% weight)**
   - Options skew (upside bias = demand)
   - Funding rates (positive = bullish sentiment)
   - Open Interest growth

**Output:**
- Confirmation score (0-100)
- Rotation strength (weak/moderate/strong)
- Counterarguments (reasons rotation may fail)
- Risk assessment (drawdown potential)

**Acceptance Criteria:**
- Precision ≥ 70% (high-confidence confirmations only)
- Recall ≥ 50% (catch most real rotations)
- F1 score ≥ 0.58 (prioritize precision over recall)
- Walk-forward F1 ≥ 0.56 (stable out-of-sample)

---

## 2. Definitions (Frozen)

### 2.1 Rotation (Canonical Definition)

**Crypto Market Rotation:** A measurable shift in capital flows from one sector/narrative to another, characterized by:

1. **Volume Concentration Change**
   - ≥2x increase in trading volume for sector
   - >50% of volume in "new" narrative assets
   - Sustained >1 week (not one-day spike)

2. **Price Action**
   - Sector outperformance vs. BTC (>500 bps over 14 days)
   - New higher highs (not just recovery)
   - Breakout from historical price range

3. **Smart Money Accumulation**
   - Whale addresses holding sector tokens increase
   - CEX inflows > outflows for sector (net positive)
   - Liquidation protection (long positions hold)

**NOT Considered Rotation:**
- Single-day spike (requires >7 days sustained)
- Inverse correlation to BTC crash (correlation breakdown ≠ rotation)
- Small-cap pumps without volume confirmation
- Liquidation events (false demand)

---

### 2.2 Capital Flow (25% RCM Weight)

**Measurement Method:**
```
Capital_Flow = (CEX_Inflow - CEX_Outflow) / 7d_Average_Volume

Threshold:
- Positive: CF > 0.05 (net inflows >5% of volume)
- Strong: CF > 0.15 (net inflows >15% of volume)
- Weak: 0 < CF < 0.05

Score (0-100):
- 0-20: Net outflows (negative signal)
- 20-50: Flat (neutral)
- 50-70: Moderate inflow (bullish)
- 70-100: Strong inflow (very bullish)
```

**Data Sources:**
- Glassnode (CEX inflow/outflow API)
- CryptoQuant (exchange flow tracking)
- DEX aggregators (Uniswap, Curve TVL changes)

---

### 2.3 Relative Strength (25% RCM Weight)

**Measurement Method:**
```
RS = (Sector_Return - BTC_Return) / Sector_Volatility

Benchmark:
- RS > 1.0: Outperformance (positive signal)
- RS > 1.5: Strong outperformance (very positive)
- RS < 0.5: Underperformance (negative signal)

Score (0-100):
Based on RS rank vs. historical distribution:
- <10th percentile: Score 0-20 (bearish)
- 10-30th: Score 20-40 (weak)
- 30-70th: Score 40-60 (neutral)
- 70-90th: Score 60-80 (bullish)
- >90th: Score 80-100 (very bullish)
```

**Lookback Windows:**
- 3-day RS (short-term momentum)
- 14-day RS (medium-term trend)
- 90-day RS (long-term relative strength)
- Weighted: 20% short + 50% medium + 30% long

---

### 2.4 Narrative Acceleration (20% RCM Weight)

**Measurement Method:**
```
Narrative_Acceleration = ln(Current_Mentions / 7d_Avg) + ln(Current_Dev_Activity / 30d_Avg)

Threshold:
- Positive: NA > 0.3 (>35% above average)
- Strong: NA > 0.8 (>120% above average)
- Weak: 0 < NA < 0.3

Score (0-100):
- 0-25: Declining narrative (bearish)
- 25-40: Below average (weak)
- 40-60: Average (neutral)
- 60-75: Above average (bullish)
- 75-100: Strong acceleration (very bullish)
```

**Data Sources:**
- LunarCrush (social mentions, sentiment)
- GitHub (developer activity)
- Crypto news aggregators (news volume)
- Twitter API (trending topics)

---

### 2.5 Fundamental Confirmation (20% RCM Weight)

**Measurement Method (Qualitative):**

Point-based scoring:
- +20 pts: Major token unlock scheduled (upcoming 2-4 weeks)
- +15 pts: Partnership/integration announcement
- +15 pts: Regulatory clarity (positive)
- +10 pts: User growth metrics (DAU, TVL increase)
- +10 pts: Mainnet launch or major upgrade
- -20 pts: Negative regulatory news
- -15 pts: Team departure or controversy
- -10 pts: Lock-up expiration (sell pressure)

**Score (0-100):**
- Sum points, cap at 100
- Normalize to 0-100 scale

---

### 2.6 Derivatives Structure (10% RCM Weight)

**Measurement Method:**
```
Derivatives_Signal = (Funding_Rate + Options_Skew + OI_Growth) / 3

Components:
- Funding_Rate: 8h average (positive = bullish)
  Score: -100 at -0.05%, 0 at 0%, +100 at +0.05%
  
- Options_Skew: Call/Put ratio (>1.0 = bullish)
  Score: 0 at 0.5, 50 at 1.0, 100 at 1.5
  
- OI_Growth: 7d OI change %
  Score: 0 if declining, 50 at 5% growth, 100 at 25%+ growth

Final Score (0-100):
Average of 3 components
```

---

## 3. Temporal Constraints (Frozen)

### 3.1 Minimum Duration
**Rotation must persist ≥7 days** to be counted as valid.
- Daily/intraday moves: Not rotations
- Measure: Volume sustained >1 week
- Cutoff: If reverses before 7 days, mark as "false signal"

### 3.2 Lookback Windows
- **Short-term (3d):** For immediate signals
- **Medium-term (14d):** For main analysis
- **Long-term (90d):** For trend confirmation

### 3.3 Historical Range
- **Data Source:** 2020-2026 (6 years)
- **Excluded:** 2017-2019 (ICO era, different dynamics)
- **Rationale:** Recent market structure more predictive

---

## 4. Validation & Walk-Forward Testing (Frozen)

### 4.1 In-Sample Testing (PIT)
- **Train on:** 80% of data (2020-2025)
- **Target:** F1 ≥ 0.57
- **Gate:** Must pass before OOS testing

### 4.2 Out-of-Sample Testing (OOS)
- **Test on:** 20% holdout (Q1-Q3 2026)
- **Target:** F1 ≥ 0.55
- **Criterion:** No lookahead bias

### 4.3 Walk-Forward Validation (WFV)
- **Windows:** 6 rolling 6-month periods
- **Refit:** Monthly (no lookahead)
- **Target:** F1 ≥ 0.55 on each window
- **Criterion:** Consistency across market regimes

### 4.4 Robustness Testing (7 Dimensions)
1. **Bull market** (sustained >20% gain)
2. **Bear market** (sustained >20% loss)
3. **High volatility** (>60-day realized vol)
4. **Low volatility** (<20-day realized vol)
5. **Rising correlation** (all coins track BTC)
6. **Falling correlation** (breakdown of structure)
7. **Liquidation events** (extreme volume spikes)

**Gate:** >75% F1 pass rate across all 7 dimensions

---

## 5. Output Definitions (Frozen)

### 5.1 RPM Output
```json
{
  "rotation_id": "rot_2026_09_25_001",
  "sector": "DeFi Tokens",
  "predicted_probability": 0.68,
  "confidence": "high",
  "duration_days": 21,
  "key_catalysts": [
    "Governance vote (2 weeks)",
    "Protocol upgrade (3 weeks)"
  ],
  "timestamp": "2026-09-25T10:00:00Z",
  "lookback_window": "14d"
}
```

### 5.2 RCM Output
```json
{
  "rotation_id": "rot_2026_09_25_001",
  "confirmation_score": 72,
  "rotation_strength": "strong",
  "component_scores": {
    "capital_flow": 75,
    "relative_strength": 68,
    "narrative_acceleration": 70,
    "fundamental_confirmation": 75,
    "derivatives_structure": 65
  },
  "counterarguments": [
    "Liquidation risk if BTC drops >5%",
    "Narrative may shift if news negative"
  ],
  "risk_drawdown_potential": "15-20%",
  "timestamp": "2026-09-25T10:30:00Z"
}
```

---

## 6. Immutability & Audit Trail

### 6.1 Spec Freeze Date
**2026-09-25** (Today) — This spec is locked.

### 6.2 Change Control
**No modifications allowed after this date** without:
1. New spec version (B-004_v2)
2. Human approval required
3. Lookahead bias assessment
4. Documentation of changes

### 6.3 Implementation Commits
**Locked against this spec:**
- Commit: `a116674` (Phase 5: NARM-P+)
- Commit: `7f377aa` (Phase 6: RCM/RPM)

**Validation chain:**
1. Spec frozen (B-004_SPEC.md) ✅
2. Implementation frozen (commits a116674, 7f377aa)
3. Backtesting against spec (Phases 3-5 validation)
4. Walk-forward validation (6 windows)
5. Robustness testing (7 dimensions)

---

## 7. Acceptance Criteria (Frozen)

### 7.1 RPM Acceptance Gate
```
✅ PASS if ALL:
- F1_PIT ≥ 0.57
- F1_OOS ≥ 0.55
- F1_WFV_avg ≥ 0.55
- Robustness_pass_rate ≥ 75%
- No lookahead bias detected
```

### 7.2 RCM Acceptance Gate
```
✅ PASS if ALL:
- F1_PIT ≥ 0.58
- F1_OOS ≥ 0.56
- F1_WFV_avg ≥ 0.56
- Robustness_pass_rate ≥ 75%
- Precision ≥ 70% (high-quality confirmations)
```

### 7.3 Combined Acceptance (RPM + RCM)
```
✅ VALIDATED_ALPHA if:
- Both RPM and RCM gates PASS
- Walk-forward F1 stable (no degradation >10%)
- No data leakage / lookahead bias
- Audit trail complete
```

---

## 8. Authority & Governance

**Specification Authority:** Phase 0 Spec Freeze Gate  
**Approval Date:** 2026-09-25  
**Approval Method:** Human-gated validation requirement  
**Status:** 🟢 LOCKED & IMMUTABLE

**Implementation Validation:**
- Authority: RRP_VALIDATION_SPEC.md
- Gate Status: Phase 0 Unlocked → Sequential validation (Phases 1-7)
- Next Check: Phase 3 Walk-Forward Validation

---

## 9. References

| Document | Purpose | Status |
|----------|---------|--------|
| RRP_VALIDATION_SPEC.md | Validation framework | ✅ Phase 0 Freeze |
| PHASE_5_ROBUSTNESS_SPEC.md | Robustness testing | ✅ Linked |
| PHASE_6_FINAL_GATE_SPEC.md | Final approval gate | ✅ Linked |
| DASHBOARD_GOVERNANCE_AUDIT.md | Dashboard governance | ✅ Linked |

---

## 10. Sign-Off

```
SPECIFICATION FREEZE CERTIFICATION

Specification ID:  b_004_spec_2026_09_25
Spec Name:         Rotation & Capital Rotation Model (RPM/RCM)
Freeze Date:       2026-09-25
Authority:         Phase 0 Spec Freeze Gate (Human-Approved)
Status:            🟢 LOCKED & IMMUTABLE

Implementation Commits:
  - a116674: Phase 5 NARM-P+ (Narrative Adoption Rotation)
  - 7f377aa: Phase 6 RCM/RPM (Rotation Confirmation Model)

Validation Path:
  Phase 1 → Phase 2 → Phase 3 (WFV) → Phase 4 (Ablation) 
  → Phase 5 (Robustness) → Phase 6 (Final Gate)

Next Gate: Phase 3 Walk-Forward Validation
Gate Criteria: F1_WFV_avg ≥ 0.55, Robustness ≥ 75%, No lookahead bias

Sign-Off: Governance Protocol
Date: 2026-09-25
Authority: RRP_VALIDATION_SPEC.md (Phase 0 Spec Freeze Locked)
```

---

**This specification is LOCKED as of 2026-09-25 and may not be modified without a new version and human approval.**

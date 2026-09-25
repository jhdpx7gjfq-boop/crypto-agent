# Phase 2: Ground Truth Labeling Guide

**Phase:** 2 Ground Truth Labeling  
**Timeline:** Oct 16-23, 2026  
**Gate:** Ground Truth Freeze (Oct 23)  
**Status:** Classification of dormant (Q1) vs resurrection (Q2) tokens

---

## Q1 Definition: DORMANT TOKEN

A token is classified as **Q1** if it exhibits sustained inactivity across multiple metrics:

**Market Metrics:**
- Market cap: < $50M
- 24-hour volume: < $1M
- Active addresses: < 100K

**Activity Criteria:**
- Dormancy period: ≥ 90 days (no significant activity)
- Status: Listed on CoinGecko but effectively inactive
- Price: Minimal trading activity, near zero volume

**Rationale:** Q1 tokens represent the baseline dormant state. These are listed cryptoassets with essentially zero market activity and neglected by traders/developers.

---

## Q2 Definition: RESURRECTION (Token Revival)

A token is classified as **Q2** if it shows clear evidence of revival from dormancy:

**Activity Surge (all relative to dormant baseline):**
- Volume increase: ≥ 3x from dormant baseline
- Active addresses: ≥ 2x from dormant baseline
- Price increase: ≥ 50% from dormant low

**Validation Rules:**
- At least 2 of 3 conditions must be TRUE
- Observation window: Last 6 months (rolling lookback)
- Trigger must be sustained (not flash spike)

**Examples:**
- Token dormant at $0.01 with 1K daily volume
- Suddenly trades $50K volume and hits $0.015 (+50%)
- Active addresses go from 500 to 1,200 (+140%)
- → Q2 (meets price + addresses condition)

---

## Confidence Levels

Assign confidence 1-5 reflecting your certainty in the label:

| Level | Label | Criteria |
|-------|-------|----------|
| **1** | Very Low | Ambiguous signals, conflicting data, insufficient evidence |
| **2** | Low | Some evidence but mixed signals, borderline cases |
| **3** | Medium | Clear signals but minor uncertainty, reasonable case for Q1 or Q2 |
| **4** | High | Strong evidence, clear classification, high confidence |
| **5** | Very High | Definitive, unambiguous classification, no doubt |

**Scoring Guidance:**
- **Q1 confidence 5:** Token has 0 volume, no activity, clearly dead
- **Q1 confidence 2:** Borderline low activity, could be dormant or ignored small-cap
- **Q2 confidence 5:** 10x volume spike, 5x addresses, 100% price gain
- **Q2 confidence 2:** Just barely meets 2/3 conditions with thin data

---

## Labeling Workflow

### 1. Interactive Labeling (CLI)

```bash
python3 src/phase_2_ground_truth/labeling_interface.py --interactive
```

For each coin:
1. View OHLCV data from Phase 1 (last 6 months)
2. Review Q1 and Q2 definitions (printed)
3. Enter label: `Q1` or `Q2`
4. Enter confidence: `1` to `5`
5. System logs with timestamp and labeler name

### 2. CSV Template (Offline Labeling)

Create template:
```bash
python3 src/phase_2_ground_truth/labeling_interface.py --template templates/phase2_labeling.csv
```

Fill offline with columns:
- `coin_id`: Coin identifier
- `symbol`: Trading symbol
- `label`: Q1, Q2, or SKIP
- `confidence`: 1-5
- `notes`: Optional reasoning

Import completed CSV:
```bash
python3 src/phase_2_ground_truth/labeling_interface.py --import templates/phase2_labeling_filled.csv
```

### 3. Validation & Freeze

Run validation:
```bash
python3 src/phase_2_ground_truth/validate_ground_truth.py data/ground_truth/phase_2/labels.csv
```

Validation checks:
- **Completeness:** ≥95% coverage vs Phase 1 coins
- **Confidence:** Average confidence ≥3.0
- **Distribution:** Both Q1 and Q2 labeled (no empty categories)
- **Consistency:** No missing fields, valid labels/confidence values

On **PASS**: Creates immutable snapshot (read-only, SHA256 verified)

---

## Quality Expectations

### Labeler Requirements

1. **Domain knowledge** of token market dynamics
2. **Attention to detail** for data verification
3. **Consistency** in applying Q1/Q2 definitions
4. **Documentation** of edge cases

### Output Quality

- All Phase 1 coins must be labeled or explicitly SKIP
- Confidence distribution should peak at 3-4 (not all 5s or all 1s)
- Q1/Q2 ratio balanced (avoid extreme skew)
- No missing symbols or invalid confidence scores

### Validation Gate

Must PASS all checks before freeze:
```
✓ Completeness ≥95%
✓ Average Confidence ≥3.0
✓ Both Q1 and Q2 present
✓ No consistency errors
```

**If FAIL:** Review failed category, correct data, re-validate

---

## Timeline & Ownership

| Date | Owner | Milestone |
|------|-------|-----------|
| Oct 16 | Labeling Team | Labeling begins |
| Oct 20 | Labeling Team | 80% coverage checkpoint |
| Oct 22 | Labeling Team | 100% labels complete |
| Oct 23 | QA Lead | Validation PASS/FAIL decision |
| Oct 24 | DevOps | Immutable snapshot finalized |

---

## Post-Labeling

After freeze:
- Ground truth locked (read-only, immutable)
- CSV snapshot stored in `/data/ground_truth/phase_2/frozen_snapshots/`
- Freeze certificate generated with SHA256 hash
- No modifications allowed until Phase 6 gate closes (Dec 20)

Next phase: **Phase 3 Walk-Forward Validation** (Oct 24 launch)

---

**Questions?** Contact Phase 2 Lead for labeling disputes or edge cases.

# Phase 2: Ground Truth Construction & Freeze Specification
**IGWT-PF26 RRP Alpha Validation**

**Phase:** 2 of 7  
**Timeline:** Oct 16-23, 2026 (overlaps Phase 1, completes before Phase 3a)  
**Predecessor:** Phase 1 Data Audit ✅ PASS REQUIRED  
**Successor:** Phase 3a PIT Backtest  
**Input:** Immutable data snapshot from Phase 1  
**Output:** Frozen ground truth labels (dormant/resurrected)  
**Authority:** Human approval required at gate completion  

---

## Executive Summary

Phase 2 formally labels every coin as **dormant** or **resurrected** using the locked Q1-Q2 definitions from Phase 0 Spec Freeze. This ground truth is **immutable** — no post-hoc modifications allowed.

**Core Principle:** Ground truth is defined BEFORE validation, preventing lookahead bias.

---

## Locked Definitions (From Phase 0)

### Q1: Dormant Token Definition (LOCKED)
```
Dormant Token (RRP-specific):
  - Market cap:      < $50M
  - Daily volume:    < $1M
  - Active addresses: < 100K
  - Duration:        ≥ 90 days continuously in dormant state
```

### Q2: Resurrection Event Definition (LOCKED)
```
Resurrection Event (RRP-specific):
  - Criteria:        All three MUST satisfy 2/3 checks below
  - Volume surge:    ≥ 3x sustained over 7 days
  - Address growth:  ≥ 2x increase over 30 days
  - Price gain:      ≥ 50% from dormant floor
  - Time window:     6 months from snapshot date T0
  - Confirmation:    2/3 checks must pass (matches RRP 3-check framework)
```

---

## Objectives

| Objective | Metric | Owner |
|-----------|--------|-------|
| Apply Q1 definition | Label all coins dormant/not | Labeling Team |
| Apply Q2 definition | Check resurrection within +6mo | Labeling Team |
| Resolve ambiguities | Manual review + decision | Human Reviewer |
| Freeze ground truth | Lock labels, create immutable snapshot | Data Team |
| Document all decisions | Labeling report with rationale | Labeling Team |
| Obtain human approval | Sign-off on ground truth | Human Authority |

---

## 1. Ground Truth Construction Process

### 1.1 Step 1: Identify Dormant Coins (Q1 Application)

**Input:** Phase 1 immutable data snapshot (OHLCV + metrics)

**Process:**
```python
for coin_id in all_coins:
    for year in [2020, 2021, 2022, 2023, 2024]:
        # Find periods where coin meets dormancy criteria
        periods = []
        for date in year_dates:
            mcap = market_cap(coin_id, date)
            volume = daily_volume(coin_id, date)
            addresses = active_addresses(coin_id, date)
            
            if mcap < 50e6 and volume < 1e6 and addresses < 100e3:
                periods.append(date)
        
        # Find continuous 90-day periods
        for period in find_continuous_periods(periods, min_duration=90):
            dormant_coins.append({
                'coin_id': coin_id,
                'start_date': period.start,
                'end_date': period.end,
                'duration_days': period.duration,
                'reason': 'Below dormancy thresholds'
            })
```

**Output:** Set of (coin_id, T0_start, T0_end) tuples for all dormant periods

**Example Output:**
```
coin_id    | dormant_start | dormant_end | duration_days | mcap_min | vol_min | addr_min
───────────┼───────────────┼─────────────┼───────────────┼──────────┼─────────┼──────────
Bitcoin    | 2014-01-01    | —           | Still dormant | $0.1M    | $1K     | <1K
Ethereum   | 2017-01-01    | 2018-01-15  | 380           | $100M    | $500K   | $10K
Solana     | 2020-02-01    | 2021-07-15  | 530           | $5M      | $100K   | $50K
```

**Validation Checkpoints:**
- [ ] All coins reviewed (no missing coins)
- [ ] Dormancy periods non-overlapping for same coin
- [ ] Duration >= 90 days for all periods
- [ ] Thresholds applied consistently

---

### 1.2 Step 2: Check Resurrection (Q2 Application)

**Input:** Dormant coins from Step 1, Phase 1 data snapshot

**Process:**
```python
for dormant_coin in dormant_coins:
    coin_id = dormant_coin.coin_id
    T0 = dormant_coin.dormant_start  # Snapshot date
    T_end = T0 + 180_days  # 6-month observation window
    
    # Get dormant baseline metrics
    dormant_baseline = {
        'price': price(coin_id, T0),
        'volume': daily_volume(coin_id, T0 to T0-30),
        'addresses': active_addresses(coin_id, T0)
    }
    
    # Check each resurrection criterion
    checks = {
        'volume_3x': False,
        'address_2x': False,
        'price_50pct': False
    }
    
    for date in T0+1 to T_end:
        volume_7d_avg = moving_avg(daily_volume, date-7, date)
        if volume_7d_avg >= dormant_baseline.volume * 3:
            checks['volume_3x'] = True
        
        addresses_30d = active_addresses(coin_id, date)
        if addresses_30d >= dormant_baseline.addresses * 2:
            checks['address_2x'] = True
        
        price = price(coin_id, date)
        if price >= dormant_baseline.price * 1.50:
            checks['price_50pct'] = True
    
    # Count passes
    passes = sum([checks.volume_3x, checks.address_2x, checks.price_50pct])
    
    if passes >= 2:
        resurrected = True
        resurrection_date = first_date_meeting_2_checks(T0, T_end)
    else:
        resurrected = False
        resurrection_date = None
        confidence = DEFINITE
```

**Output:** Ground truth labels with confidence

```
coin_id | T0_date    | resurrected | resurrection_date | confidence | notes
────────┼────────────┼─────────────┼───────────────────┼────────────┼──────────
Bitcoin | 2014-01-01 | No          | —                 | DEFINITE   | Never left dormancy
Solana  | 2020-02-01 | Yes         | 2021-07-15        | DEFINITE   | 3/3 checks passed
Shib    | 2020-08-01 | Yes         | 2021-05-11        | PROBABLE   | 2/3 checks, 1 borderline
```

---

### 1.3 Step 3: Manual Review of Ambiguous Cases

**Criteria for "Ambiguous":**
- Exactly 1 check passed (not 0, not 2)
- Borderline metric values (e.g., 1.9x vs 2.0x addresses)
- Data gaps during critical period
- Significant exchange delisting during observation window

**Manual Review Process:**
```
For each ambiguous case:
  1. Pull raw data (OHLCV + metrics + events)
  2. Review for external events (listings, burns, airdrops, etc.)
  3. Assign confidence: DEFINITE | PROBABLE | AMBIGUOUS | EXCLUDE
  4. Document rationale
  5. Update label if necessary
```

**Review Template:**
```yaml
case_id: "SHIB_20200801_AMBIGUOUS"
coin_id: "shib"
T0_date: "2020-08-01"
T0_end: "2021-02-01"

checks:
  volume_3x: true  # Passed: vol went 1K → 3.2K USD
  address_2x: false  # Failed: 8K → 15K (1.875x, not 2x)
  price_50pct: true  # Passed: $0.00000001 → $0.00005 (500,000x!)

evidence:
  - Large airdrop on 2021-05-11 (Uniswap distribution)
  - Viral social media (Twitter 500K new followers)
  - Celebrity endorsement spike
  - Address count inflated by bot activity (estimated 20%)

decision: PROBABLE  # 2/3 checks BUT address count unreliable
rationale: "Resurrection is likely real (price + volume legitimate), but address count inflated by bot activity. Classification as PROBABLE rather than DEFINITE due to metric reliability."

reviewer: "Human Analyst #1"
review_date: "2026-10-19"
```

**Ambiguity Resolution:**
- If < 5% cases ambiguous: All resolved manually, proceed with ground truth freeze
- If ≥ 5% cases ambiguous: Flag for methodology review (may indicate definition issues)

---

## 2. Ground Truth Data Structure

### 2.1 Frozen Ground Truth Format

```python
ground_truth = {
  coin_id: {
    # Dormancy specification
    dormant_start_date: str,        # T0 (ISO format)
    dormant_end_date: str | None,   # When dormancy ended (if ever)
    dormant_duration_days: int,     # ≥90
    
    # Dormancy verification (matched against Q1)
    dormant_mcap_max: float,        # Max market cap during dormancy (<$50M)
    dormant_volume_max: float,      # Max daily volume during dormancy (<$1M)
    dormant_addresses_max: int,     # Max active addresses (<100K)
    
    # Resurrection outcome
    resurrected: bool,               # True/False
    resurrection_date: str | None,   # When 2/3 checks passed (if resurrected)
    
    # Resurrection verification (matched against Q2)
    resurrection_checks: {
      volume_3x: bool,              # ≥3x sustained over 7 days?
      address_2x: bool,             # ≥2x increase over 30 days?
      price_50pct: bool,            # ≥50% price gain?
      checks_passed: int             # 0-3
    },
    
    # Confidence level
    confidence: str,                # DEFINITE | PROBABLE | AMBIGUOUS
    
    # Human review notes
    human_reviewed: bool,
    human_reviewer: str | None,
    review_date: str | None,
    notes: str,
    
    # Immutability timestamp
    frozen_date: str,               # When ground truth was locked
    frozen_version: str             # Hash of this record
  }
}
```

### 2.2 Immutable Snapshot

```json
{
  "ground_truth_id": "rrp_alpha_p2_gt_2026-10-23",
  "created": "2026-10-23T18:00:00Z",
  "immutable": true,
  "sha256_hash": "xyz789abc...",
  
  "statistics": {
    "total_coins_labeled": 3421,
    "dormant_coins": 847,
    "resurrected_coins": 312,
    "not_resurrected": 535,
    "resurrection_rate": "36.8%",
    "ambiguous_cases": 23,
    "ambiguous_resolution_rate": "100%"
  },
  
  "validation": {
    "all_coins_labeled": true,
    "dormancy_criteria_applied": true,
    "resurrection_criteria_applied": true,
    "ambiguous_cases_reviewed": true,
    "human_approval_required": true,
    "human_approval_date": null,
    "human_approver": null
  },
  
  "storage": {
    "location": "s3://crypto-agent-data/rrp_alpha/phase2_gt",
    "format": "parquet",
    "file": "ground_truth_2026-10-23.parquet",
    "backup": "local://backups/phase2_gt_2026-10-23.tar.gz"
  }
}
```

---

## 3. Phase 2 Labeling Report

```
PHASE 2 GROUND TRUTH CONSTRUCTION REPORT
Generated: 2026-10-23
Labeling Period: Oct 16-23, 2026
Team: Ground Truth Labeling + Human Review

═══════════════════════════════════════════════════════════════

EXECUTIVE SUMMARY
─────────────────
Coins Labeled: 3,421 (100%)
Dormant Coins: 847 (24.8%)
Resurrected: 312/847 (36.8%)
Ambiguous Cases: 23 (2.7% of dormant coins)
Ambiguity Resolution: 23/23 (100%)
Status: READY FOR PHASE 3 PIT BACKTEST

═══════════════════════════════════════════════════════════════

1. LABELING SUMMARY

Stage                    | Coins    | Status
─────────────────────────┼──────────┼─────────────────────
Dormancy Q1 Applied      | 3,421    | ✅ 100% labeled
Resurrection Q2 Applied  | 847      | ✅ 100% labeled
Ambiguous Cases ID'd     | 23       | ✅ For manual review
Manual Review Complete   | 23       | ✅ All resolved
Human Review Approval    | 3,421    | ⏳ Awaiting sign-off

═══════════════════════════════════════════════════════════════

2. DORMANCY DISTRIBUTION

Dormant Coins: 847 total

Dormancy Duration:
  90-180 days:    145 coins (17.1%)
  180-365 days:   287 coins (33.9%)
  365-730 days:   298 coins (35.2%)
  > 730 days:     117 coins (13.8%)

Example Dormant Coins:
  - Bitcoin (2014-01-01, never exited dormancy)
  - Ethereum (2016-07-30, duration 380 days)
  - Litecoin (2017-02-15, duration 520 days)
  - Ripple (2015-08-01, duration 890 days)

═══════════════════════════════════════════════════════════════

3. RESURRECTION DISTRIBUTION

Resurrected Coins: 312/847 (36.8%)

By Check Combination:
  ✅ All 3 checks passed:  98 coins (31.4%)
  ✅ 2 of 3 checks passed: 214 coins (68.6%)
  ❌ 0-1 checks passed:    535 coins (not resurrected)

Examples (DEFINITE):
  - Solana: 3/3 checks (volume ✅, addresses ✅, price ✅)
  - Dogecoin: 3/3 checks (all metrics exceeded 2x)
  - Ripple: 2/3 checks (volume ✅, price ✅)

Examples (PROBABLE):
  - Shiba Inu: 2/3 checks (volume ✅, price ✅, addr ~1.9x)
  - SafeMoon: 2/3 checks (addr ✅, price ✅, vol borderline)

═══════════════════════════════════════════════════════════════

4. AMBIGUOUS CASES RESOLUTION

Total Ambiguous: 23 (2.7% of dormant coins)

Resolution Summary:
  Resolved as PROBABLE:  16 cases (69.6%)
  Resolved as AMBIGUOUS: 7 cases (30.4%)
  Excluded from GT:      0 cases

Example Case #1: SHIB_20200801
  Checks: volume ✅, address ❌ (1.9x), price ✅
  Issue: Address count inflated by bot activity
  Resolution: PROBABLE (2/3 legitimate, address unreliable)

Example Case #2: SafeMoon_20200908
  Checks: address ✅, price ✅, volume ❌ (2.9x)
  Issue: Volume spike coincided with exchange delisting
  Resolution: PROBABLE (legitimate fundamentals, volume data issue)

═══════════════════════════════════════════════════════════════

5. GROUND TRUTH VALIDATION

Consistency Checks:
  [✅] All 3,421 coins labeled
  [✅] No missing labels or NULLs
  [✅] Dormancy dates chronologically valid
  [✅] Resurrection dates within +180 days of dormancy start
  [✅] No resurrection before dormancy start
  [✅] Confidence levels assigned to all ambiguous cases
  [✅] Human review trail complete

Quality Metrics:
  [✅] Dormancy definition applied consistently
  [✅] Resurrection definition applied consistently
  [✅] Ambiguous cases reviewed by humans
  [✅] No post-hoc modifications after freeze date
  [✅] Immutable snapshot created with hash verification

═══════════════════════════════════════════════════════════════

6. FROZEN GROUND TRUTH SPECIFICATION

Immutable Snapshot:
  ID: rrp_alpha_p2_gt_2026-10-23
  Hash: abc123def... (SHA256, verified)
  Size: 45 MB (parquet format)
  Records: 3,421 coins × 2 attributes = 6,842 ground truth labels
  Status: LOCKED (no modifications allowed)

Phase 3 Backtest will reference this snapshot.
All historical analysis will use these fixed labels.
No retraining or relabeling after this date.

═══════════════════════════════════════════════════════════════

7. GATE APPROVAL

Phase 2 Gate Requirements (ALL REQUIRED):
  [✅] All coins labeled (3,421/3,421)
  [✅] Ambiguous cases < 5% (2.7% achieved)
  [✅] Ambiguous cases resolved (23/23)
  [✅] Human verification sample reviewed (random 10% spot-checked)
  [✅] Ground truth frozen (immutable snapshot created)
  [✅] Labeling report approved: AWAITING HUMAN SIGN-OFF

═══════════════════════════════════════════════════════════════

HUMAN SIGN-OFF

Approved By: ____________________
Title: Human Authority
Date: ____________________
Comments: ____________________

═══════════════════════════════════════════════════════════════

GATE DECISION: [ ] PASS → Phase 3a PIT | [ ] FAIL → Remediate Phase 2
```

---

## 4. Phase 2 Roles & Responsibilities

| Role | Tasks | Authority |
|------|-------|-----------|
| **Labeling Team** | Apply Q1/Q2 definitions, identify ambiguous cases | Execute |
| **Human Reviewer** | Manually review ambiguous cases, assign confidence | Approve |
| **QA Lead** | Validate consistency, approve labeling report | Approve |
| **Human Authority** | Final sign-off on ground truth, unlock Phase 3 | Gate |

---

## 5. Phase 2 Success Criteria (Gate to Phase 3)

All of the following must be TRUE:

✅ **All Coins Labeled** 3,421/3,421 dormant/resurrected  
✅ **Dormancy Q1 Applied** Consistently to all coins  
✅ **Resurrection Q2 Applied** Consistently to all dormant coins  
✅ **Ambiguous < 5%** (2.7% achieved, target met)  
✅ **Ambiguous Resolved** Manual review complete, confidence assigned  
✅ **Ground Truth Frozen** Immutable snapshot created, hash verified  
✅ **Human Approval** QA Lead + Human Authority sign off  

**If any criterion fails:** Return to Phase 2, remediate, re-label, re-approve, re-submit.

---

## 6. Timeline & Milestones

```
Oct 16 | Phase 2 kickoff (data from Phase 1 arrives)
Oct 18 | Q1 dormancy labeling complete
Oct 19 | Q2 resurrection labeling complete
Oct 20 | Ambiguous cases identified (23 cases found)
Oct 22 | Manual review + ambiguity resolution complete
Oct 23 | Ground truth frozen + labeling report approved
```

**Note:** Phase 1 and Phase 2 overlap. Phase 2 begins on Oct 16 as Phase 1 data arrives. Phase 2 completes by Oct 23, unblocking Phase 3a PIT backtest.

---

## 7. Risk Mitigation

### Risk: Definition Ambiguity Creates Inconsistent Labels

**Mitigation:**
- Lock Q1/Q2 definitions in Phase 0 (prevents post-hoc changes)
- Apply definitions to subset first (validate consistency)
- Document all edge cases + resolution approach
- Human review for ambiguous cases (no auto-decisions)

### Risk: Ambiguous Cases Exceed 5% Threshold

**Mitigation:**
- Flag in Phase 1 if data quality issues (e.g., missing on-chain data)
- Increase threshold to 10% if justified (but requires human rationale)
- Exclude problematic coins if necessary (with documentation)
- Re-evaluate definition in Phase 4 robustness analysis

### Risk: Ground Truth Modified After Freeze

**Mitigation:**
- Create immutable snapshot with SHA256 hash
- Store backup in read-only location
- Version control locks ground truth
- Audit trail tracks any access attempts

---

## Deliverables (Phase 2 Completion)

1. **Labeled Ground Truth Dataset** (3,421 coins × dormant/resurrected labels)
2. **Confidence Classifications** (DEFINITE/PROBABLE/AMBIGUOUS)
3. **Ambiguity Resolution Report** (23 cases reviewed + decided)
4. **Human Review Trail** (spot-check sample + sign-off)
5. **Frozen Ground Truth Snapshot** (immutable, SHA256 hash verified)
6. **Labeling Report** (PASS/FAIL gate decision)
7. **Phase 3 Ready Confirmation** (unlock PIT backtest)

---

**Built:** 2026-09-25  
**Phase:** 2 of 7  
**Status:** Ready for Oct 16 Execution  
**Authority:** Human approval required at gate completion  
**Downstream:** Phase 3a PIT Backtest (begins upon Phase 2 PASS)

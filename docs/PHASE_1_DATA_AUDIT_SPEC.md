# Phase 1: Data Audit & Collection Specification
**IGWT-PF26 RRP Alpha Validation**

**Phase:** 1 of 7  
**Timeline:** Oct 9-23, 2026 (2 weeks)  
**Predecessor:** Phase 0 Spec Freeze ✅ LOCKED (Q1-Q9)  
**Successor:** Phase 2 Ground Truth Construction  
**Authority:** Human approval required at gate completion  

---

## Executive Summary

Phase 1 verifies that all required data for RRP validation is:
- **Complete** (≥95% coverage across all sources)
- **Clean** (documented gaps, explained misalignments)
- **Traceable** (provenance chain for audit)
- **Immutable snapshot** (frozen before ground truth labeling)

**NO LABELING OCCURS IN PHASE 1.** Only data collection and quality audit.

---

## Objectives

| Objective | Metric | Owner |
|-----------|--------|-------|
| Collect historical OHLCV | All coins 2020-present | Data Team |
| Verify data completeness | ≥95% overall, ≥90% per-source | QA |
| Document all gaps | Gap report with root cause | Data Team |
| Create immutable snapshot | Versioned dataset with hash | Data Team |
| Produce audit report | Pass/Fail for each source | QA |
| Obtain human approval | Sign-off on audit report | Human Authority |

---

## 1. Data Collection Strategy

### 1.1 Primary Data Sources (Ranked by Priority)

#### Source A: CoinGecko API (PRIMARY)
**What:** OHLCV, market cap, volume, address count  
**Coverage:** All coins with CoinGecko ID (est. 3,000+ coins)  
**History:** 2014-present (daily candlesticks)  
**Reliability:** High (well-maintained, documented)  
**Rate Limits:** 10-50 calls/min free tier  

**Collection Method:**
```python
# Pseudocode
for coin_id in coin_list:
    ohlcv_data = coingecko.get_historical_price_data(
        id=coin_id,
        vs_currency="usd",
        days="max",  # All available history
        interval="daily"
    )
    save_with_timestamp(coin_id, ohlcv_data, source="coingecko")
```

**Data Quality Checks:**
- [ ] No missing dates (detect weekends/holidays)
- [ ] OHLC ordering: open ≤ high, close ≤ high, low ≤ all
- [ ] Volume ≥ 0 (no negative volumes)
- [ ] Price > 0 (no $0 or negative prices)

---

#### Source B: On-Chain Metrics (SECONDARY)
**What:** Active addresses, transaction counts, holder distribution  
**Services:**
- Glassnode (on-chain analytics)
- Nansen (smart money tracking)
- CryptoQuant (exchange flows, funding rates)

**Coverage:** Major coins (BTC, ETH, SOL, etc.) + subset of alts  
**History:** Variable (BTC: 2011+, Alts: 2017+)  
**Reliability:** Medium (requires API key, rate limits)  

**Data Quality Checks:**
- [ ] Address count >= 0
- [ ] Address count monotonically non-decreasing (addresses don't disappear)
- [ ] Transaction count >= 0
- [ ] Holder distribution sums to 100% or documents missing slices

---

#### Source C: Exchange Data (TERTIARY)
**What:** Order book depth, liquidation data, funding rates  
**Services:**
- Binance public API (free tier)
- Crypto.com public endpoints

**Coverage:** Traded coins only  
**History:** Limited (recent data only, 1-5 years typical)  
**Reliability:** Medium (API stability varies by exchange)  

**Note:** Exchange data NOT required for RRP dormancy detection, but useful for resurrection confirmation.

---

### 1.2 Data Collection Timeline

| Week | Task | Owner | Deliverable |
|------|------|-------|-------------|
| **Oct 9** | Prepare collection scripts | Data Team | Scripts + configs |
| **Oct 10-12** | Collect CoinGecko data (all coins) | Data Team | Raw OHLCV dataset |
| **Oct 13-15** | Collect on-chain data (major coins) | Data Team | On-chain metrics |
| **Oct 16-17** | Audit for gaps & quality issues | QA | Gap report |
| **Oct 18-20** | Document provenance trail | Data Team | Provenance manifest |
| **Oct 21-22** | Final QA + human review | QA + Human | Audit report |
| **Oct 23** | Gate approval | Human Authority | PASS/FAIL decision |

---

## 2. Data Quality Standards

### 2.1 Completeness Requirements

**Overall Target:** ≥95% of required data collected

**Definition:**
```
completeness = (total_coin_records_collected / expected_total_coin_records) * 100%

Expected total = (# coins in universe) × (# days per time period) × (# metrics)
```

**Acceptance Thresholds:**

| Metric | Threshold | Justification |
|--------|-----------|---------------|
| CoinGecko OHLCV | ≥95% coins, ≥99% dates | Primary source, must be near-complete |
| On-chain data | ≥80% of major coins | Secondary, OK if sparse |
| Exchange data | ≥70% if collected, NA if skipped | Tertiary, optional |
| **Overall** | **≥95%** | Spec requirement (Q5) |

**Per-Coin Minimum:** ≥90% (no individual coin below this)

**Per-Source Minimum:** ≥85% (each source ≥85% of its target coins)

---

### 2.2 Data Quality Checks

#### Structural Checks
- [ ] All OHLC values present (no nulls in price data)
- [ ] No negative prices, volumes, or addresses
- [ ] OHLC ordering valid: O ≤ H, C ≤ H, L ≤ O, L ≤ C
- [ ] Timestamps in chronological order, no duplicates
- [ ] Expected frequency (daily = 365±3 days/year, no 2-day gaps)

#### Domain Checks
- [ ] Volume > 0 on trading days (zeros acceptable on off days)
- [ ] Address count non-decreasing (monotonic increase allowed)
- [ ] Market cap = price × circulating_supply (within 5% tolerance)
- [ ] No price spikes >1000x in single day (flag for manual review)
- [ ] Price decimals consistent with historical norms

#### Temporal Checks
- [ ] Data starts before or at 2020-01-01
- [ ] Data goes through 2024-12-31 (required for PIT)
- [ ] No gaps >30 days in continuous series (document any gaps found)
- [ ] Weekend/holiday handling consistent

---

### 2.3 Gap Policy

**Acceptable Gaps:**
- < 7 days: Mark as "temporary gap", proceed
- 7-30 days: Mark as "extended gap", investigate root cause, document
- > 30 days: Flag as "data quality issue", may exclude coin if critical period

**Gap Documentation Template:**
```yaml
gap_id: "BTC_20210715_20210730"
coin_id: "bitcoin"
source: "coingecko"
gap_start: "2021-07-15"
gap_end: "2021-07-30"
duration_days: 15
reason: "CoinGecko data maintenance window (internal)"
severity: "low"  # low | medium | high | critical
impact: "Dormancy detection: None (gap predates dormancy period)"
resolution: "Interpolate using secondary source (Binance)"
verified_by: "Human QA"
```

---

## 3. Data Provenance & Audit Trail

### 3.1 Provenance Manifest

Every dataset must include a manifest documenting:

```json
{
  "dataset_id": "rrp_alpha_p1_audit_2026-09-23",
  "created": "2026-09-23T14:30:00Z",
  "version": "1.0",
  "immutable": true,
  "sha256_hash": "abc123def456...",
  
  "sources": [
    {
      "name": "coingecko",
      "api_endpoint": "https://api.coingecko.com/api/v3",
      "data_type": "OHLCV",
      "coins_collected": 3421,
      "date_range": ["2014-01-01", "2026-09-23"],
      "records": 1247633,
      "collection_date": "2026-10-12",
      "collection_time_hours": 4.5,
      "rate_limit_hits": 0,
      "errors": []
    },
    {
      "name": "glassnode",
      "api_endpoint": "https://api.glassnode.com/v1/metrics",
      "data_type": "on-chain",
      "coins_collected": 187,
      "date_range": ["2018-01-01", "2026-09-23"],
      "records": 287451,
      "collection_date": "2026-10-15",
      "collection_time_hours": 6.2,
      "errors": ["BTC: timeout on 2023-04-15", "ETH: partial sync 2021-02-03"]
    }
  ],
  
  "quality_metrics": {
    "overall_completeness": 96.3,
    "coingecko_completeness": 99.2,
    "glassnode_completeness": 81.5,
    "gap_count": 12,
    "max_gap_days": 14,
    "data_errors_found": 3,
    "data_errors_resolved": 3
  },
  
  "storage": {
    "location": "s3://crypto-agent-data/rrp_alpha/phase1_audit",
    "format": "parquet",
    "files": ["ohlcv_2020_2026.parquet", "onchain_2018_2026.parquet"],
    "total_size_gb": 2.3,
    "backup_location": "local://backups/phase1_audit_2026-09-23.tar.gz"
  },
  
  "validation": {
    "structural_checks_passed": true,
    "domain_checks_passed": true,
    "temporal_checks_passed": true,
    "human_review_approved": false,
    "human_reviewer": null,
    "human_review_date": null
  }
}
```

### 3.2 Audit Trail Recording

Every data modification is logged:

```
2026-10-12 14:30:00 | DATA_COLLECTION_START | CoinGecko | 3421 coins
2026-10-12 18:45:00 | DATA_COLLECTION_END | CoinGecko | 1247633 records
2026-10-13 08:00:00 | STRUCTURAL_CHECK_START | All sources
2026-10-13 12:30:00 | STRUCTURAL_CHECK_END | PASSED (0 errors)
2026-10-13 13:00:00 | DOMAIN_CHECK_START | All sources
2026-10-13 16:45:00 | DOMAIN_CHECK_END | PASSED (3 warnings logged)
2026-10-14 09:00:00 | GAP_ANALYSIS_START | All sources
2026-10-14 15:20:00 | GAP_ANALYSIS_END | 12 gaps identified
2026-10-15 10:00:00 | PROVENANCE_MANIFEST_CREATED | rrp_alpha_p1_audit_2026-09-23
2026-10-22 14:00:00 | HUMAN_REVIEW_START | QA Lead
2026-10-22 16:30:00 | HUMAN_REVIEW_APPROVED | PASS
```

---

## 4. Phase 1 Audit Report Template

**PHASE 1 DATA AUDIT REPORT**
```
Generated: 2026-10-23
Audit Period: Oct 9-23, 2026
Auditor: QA Team
Authority: Human Review

═══════════════════════════════════════════════════════════════

EXECUTIVE SUMMARY
─────────────────
Data Completeness: 96.3% (✅ Target: ≥95%)
Data Quality: PASSED all structural & domain checks
Gaps Documented: 12 (all ≤14 days, acceptable)
Provenance: Complete audit trail recorded
Status: READY FOR PHASE 2 GROUND TRUTH CONSTRUCTION

═══════════════════════════════════════════════════════════════

1. DATA COLLECTION SUMMARY

Source          | Coins    | Records  | Coverage | Quality
────────────────┼──────────┼──────────┼──────────┼─────────
CoinGecko       | 3,421    | 1,247,633| 99.2%    | ✅ PASS
Glassnode       | 187      | 287,451  | 81.5%    | ✅ PASS
Crypto.com      | 892      | 156,230  | 85.0%    | ✅ PASS
────────────────┼──────────┼──────────┼──────────┼─────────
TOTAL           | —        | 1,691,314| 96.3%    | ✅ PASS

═══════════════════════════════════════════════════════════════

2. DATA QUALITY CHECKS

Structural Validation
  [✅] OHLC ordering valid (all 1,247,633 records checked)
  [✅] No negative prices/volumes
  [✅] No null values in critical fields
  [✅] Timestamps chronological, no duplicates

Domain Validation
  [✅] Price decimals consistent with historical
  [✅] Volume > 0 on trading days
  [✅] Address counts monotonic (non-decreasing)
  [⚠️]  3 price spike warnings (>500x in 1 day)
     - SHIB: 2021-05-11 ($0.000001 → $0.00004, valid event)
     - DOGE: 2021-01-28 ($0.008 → $0.08, valid event)
     - SafeMoon: 2021-05-12 (contract bug, documented)
  [✅] Market cap = price × supply (within 5%)

Temporal Validation
  [✅] Data starts 2014 (before 2020 requirement)
  [✅] Data includes 2024-12-31 (PIT requirement)
  [✅] Frequency: 365±3 days/year (valid with weekends)
  [✅] No unexplained multi-day gaps

═══════════════════════════════════════════════════════════════

3. GAP ANALYSIS

Total Gaps Identified: 12
  - 0-7 days:    9 gaps (acceptable, market data normal)
  - 7-30 days:   3 gaps (investigated, documented below)
  - >30 days:    0 gaps

Documented Gaps:
  Gap ID               | Coin  | Dates          | Cause
  ─────────────────────┼───────┼────────────────┼──────────────
  BTC_20210710_20210714| BTC   | Jul 10-14 2021 | Glassnode maintenance
  ETH_20200315_20200318| ETH   | Mar 15-18 2020 | Exchange API outage
  USDC_20210101_20210107| USDC | Jan 1-7 2021   | Stablecoin data lag
  [etc. 9 more gaps documented]

Resolution: All gaps ≤14 days, no coins excluded. Interpolation
approved for ground truth construction (Phase 2).

═══════════════════════════════════════════════════════════════

4. PROVENANCE AUDIT

Dataset Manifest: ✅ Complete
  - Source fingerprints: ✅ All recorded
  - Collection timestamps: ✅ All logged
  - Data hashes: ✅ SHA256 verified
  - Storage location: s3://crypto-agent-data/rrp_alpha/phase1_audit
  - Backup: ✅ Stored locally

Audit Trail: ✅ Complete
  - Collection logs: ✅ 147 events recorded
  - Validation logs: ✅ 38 events recorded
  - Quality checks: ✅ All signed off
  - Human review trail: ✅ To be signed

═══════════════════════════════════════════════════════════════

5. FROZEN DATASET SPECIFICATION

Immutable Snapshot:
  ID: rrp_alpha_p1_audit_2026-09-23
  Hash: 7a3c91... (SHA256, verified)
  Size: 2.3 GB (parquet format)
  Records: 1,691,314
  Coins: 3,421
  Date Range: 2014-01-01 to 2026-09-23
  Status: LOCKED (no modifications allowed)

Ground Truth Construction (Phase 2) will use this snapshot.
Historical backtesting (Phase 3) will reference this snapshot.

═══════════════════════════════════════════════════════════════

6. GATE APPROVAL

Phase 1 Gate Requirements (ALL REQUIRED):
  [✅] Data completeness ≥95%: ACHIEVED 96.3%
  [✅] No unexplained gaps: All gaps documented
  [✅] Provenance trail intact: Complete audit trail
  [✅] Audit report approved: AWAITING HUMAN SIGN-OFF
  [✅] Dataset immutable: Snapshot frozen

═══════════════════════════════════════════════════════════════

HUMAN SIGN-OFF

Approved By: ____________________
Title: QA Lead / Human Authority
Date: ____________________
Comments: ____________________

═══════════════════════════════════════════════════════════════

GATE DECISION: [ ] PASS → Phase 2 | [ ] FAIL → Remediate Phase 1
```

---

## 5. Phase 1 Roles & Responsibilities

| Role | Tasks | Authority |
|------|-------|-----------|
| **Data Team** | Collect OHLCV, document provenance, manage audit trail | Execute |
| **QA Lead** | Validate data quality, approve audit report, gate decision | Approve |
| **Human Authority** | Final sign-off on Phase 1 completion, unlock Phase 2 | Gate |

---

## 6. Risk Mitigation

### Risk: Incomplete Data Coverage

**Mitigation:**
- Collect from 3+ sources (primary, secondary, tertiary)
- Set ≥95% threshold (allows 5% acceptable gaps)
- Document all gaps (transparency)
- Use interpolation for isolated gaps (Phase 2)

### Risk: Data Quality Issues Discovered Late

**Mitigation:**
- Run quality checks DURING collection (not after)
- Flag anomalies immediately for investigation
- Document all issues in gap report
- Set 2-week timeline with buffer

### Risk: Immutability Violated (Data Modified)

**Mitigation:**
- Create cryptographic hash of final snapshot (SHA256)
- Store backup in read-only location
- Lock dataset in version control
- Audit trail prevents accidental modification

---

## 7. Success Criteria (Gate to Phase 2)

All of the following must be TRUE:

✅ **Data Completeness** ≥95% (overall), ≥90% (per-coin)  
✅ **Data Quality** Structural/domain/temporal checks PASSED  
✅ **Gaps Documented** Gap report complete, all >7 day gaps explained  
✅ **Provenance Complete** Manifest signed, audit trail recorded  
✅ **Dataset Frozen** Immutable snapshot created, hash verified  
✅ **Human Approval** QA Lead + Human Authority sign off  

**If any criterion fails:** Return to Phase 1, remediate, re-audit, re-submit.

---

## 8. Timeline & Milestones

```
Oct 9  | Phase 1 kickoff (scripts ready)
Oct 12 | CoinGecko collection complete
Oct 15 | On-chain data collection complete
Oct 17 | Quality audit complete, gaps documented
Oct 20 | Provenance manifest finalized
Oct 22 | Human review + approval
Oct 23 | GATE DECISION: PASS → Phase 2 | FAIL → Remediate
```

---

## Deliverables (Phase 1 Completion)

1. **Immutable Data Snapshot** (parquet files, locked)
2. **Provenance Manifest** (JSON, with hashes)
3. **Gap Analysis Report** (all gaps ≤14 days documented)
4. **Data Quality Audit Report** (PASS/FAIL decision)
5. **Human Approval Sign-Off** (QA Lead + Authority)
6. **Audit Trail Log** (all events timestamped)
7. **Phase 2 Ready Confirmation** (unlock ground truth construction)

---

**Built:** 2026-09-25  
**Phase:** 1 of 7  
**Status:** Ready for Oct 9 Execution  
**Authority:** Human approval required at gate completion

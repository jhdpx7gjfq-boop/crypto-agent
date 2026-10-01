# IGWT-PF26: Quant Intelligence Operating System

## Project Status: Layer 1 (Data Intelligence) — Infrastructure Complete

**Current State:** Step 1-5 complete on canonical branch `claude/gracious-pascal-mcg5bl`

### Layer 1 Completion Summary

| Step | Component | Commit | Tests | Status |
| --- | --- | --- | --- | --- |
| 1 | ADR-035 (Control Separation) | d1a1399 | N/A | ✅ Approved |
| 2 | Snapshot Manifest | a3e1681 | 22/22 | ✅ PASS |
| 3 | Revision Audit (C1.4-IGWT) | 57a59c4 | 19/19 | ✅ PASS |
| 4 | Snapshot Freezing (C1.5-IGWT) | dc0bdd9 | 24/24 | ✅ PASS |
| 5 | PIT Validation (C1.5-PIT engine) | e810e78 | 42/42 | ✅ PASS |
| **Total** | — | — | **107/107** | **✅ Infrastructure Ready** |

---

## Critical Distinction: What Layer 1 Does & Does Not Prove

### ✅ Layer 1 Proves (Complete)

```
C1.5-IGWT: Snapshot Reproducibility
- We can capture data at timestamp T
- We can freeze it immutably
- We can reconstruct it deterministically
- Hash verification detects tampering
107/107 unit tests PASS
```

### ⏳ Layer 1 Does NOT Prove (Pending Empirical Validation)

```
C1.5-PIT: Temporal Availability (Provider-Level)
- Binance/CoinGecko had data available at historical time T
- availability_time ≤ decision_time for actual data
PITValidator engine exists and is correct
BUT: Provider compliance is empirically unverified
```

### 🔴 Layer 1 Cannot Prove (Out of Scope)

```
Alpha / Predictive Performance
- No statistical validation
- No walk-forward backtesting
- No ablation studies
Layer 1 is infrastructure only
```

---

## Canonical Development Branch

**Single authorized branch for Layer 1 work:**
```
claude/gracious-pascal-mcg5bl
```

**Rules:**
- All five steps committed to this branch only
- Zero merges to other branches
- Zero promotion to production until empirical validation complete
- Zero WFV until C1.5-PIT empirical proof

---

## Architecture Overview

### Layer 1: Data Intelligence Controls

| Control | Implementation | Gate | Status |
| --- | --- | --- | --- |
| **C1.1** | Historical Availability | — | ⏳ Pending |
| **C1.2** | Timestamp Precision | SnapshotManifest | ✅ |
| **C1.3** | Forecast Availability | — | ⏳ Pending |
| **C1.4-SOURCE** | Provider Revision History | — | UNVERIFIED |
| **C1.4-IGWT** | Capture Revision Audit | RevisionAuditEngine | ✅ |
| **C1.5-SOURCE** | Provider PIT API | — | UNVERIFIED |
| **C1.5-IGWT** | Snapshot Freezing | SnapshotFreezer | ✅ |
| **C1.5-PIT** | Temporal Availability (Independent) | PITValidator | Engine ✅; Empirical ⏳ |
| **C1.6** | BTC/ETH Intraday Alignment ≥15m | — | ⏳ Pending |
| **C1.7** | Event Inventory Coverage | — | ⏳ Pending |

---

## Key Classes & Modules

### `src/layers/layer1_data/`

#### snapshot_manifest.py (269 lines)
- **SnapshotManifest**: Immutable provenance record with SHA256 hash, frozen timestamp, source metadata
- **SourceMetadata**: Source endpoint, fetch_timestamp, date_range, checksums
- **Checksum**: File-level SHA256 verification
- **Method**: `get_data_as_of(asset, query_date)` — reproducible query with `pit_status="UNVERIFIED"`

#### revision_audit.py (317 lines)
- **RevisionAuditEngine**: Detects changes between snapshot T and T+1
- **Change**: Individual correction/addition/deletion entry
- **RevisionAuditLog**: Immutable audit record with disclaimer: "C1.4-IGWT (our capture), NOT C1.4-SOURCE (upstream)"
- **Invariant**: `pit_status="UNVERIFIED"` always (does not prove upstream revision history)

#### snapshot_freezing.py (269 lines)
- **FrozenSnapshot**: Immutable capture with `frozen_at` timestamp, `data_hash` (SHA256)
- **SnapshotFreezer**: Static methods for freezing, reconstruction, tampering detection
- **Method**: `get_data_as_of()` — includes explicit warning: "C1.5-IGWT (reproducibility), NOT C1.5-PIT (availability)"
- **Invariant**: `pit_status="UNVERIFIED"` always

#### pit_validator.py (280 lines)
- **PITValidator**: Temporal availability validation engine
- **AvailabilityProofLevel**: Hierarchy A-E (PASS / PASS_CONDITIONAL / FAIL)
- **Key Separation**:
  - `event_time`: When event occurred
  - `availability_time`: When we obtained the observation
  - `decision_time`: When decision was made
- **Core Rule**: `availability_time ≤ decision_time` (NOT event_time ≤ decision_time)

---

## Test Coverage

### tests/unit/layer1_data/

| File | Tests | Coverage | Status |
| --- | --- | --- | --- |
| test_snapshot_manifest.py | 22 | Manifest schema, hash verification, immutability, PIT_STATUS invariant | ✅ 22/22 PASS |
| test_revision_audit.py | 19 | Diff detection, audit log, disclaimer, no upstream claims | ✅ 19/19 PASS |
| test_snapshot_freezing.py | 24 | Freezing, hash computation, reconstruction, tampering detection | ✅ 24/24 PASS |
| test_pit_validation.py | 42 | Temporal ordering, future rejection, late rejection, proof hierarchy | ✅ 42/42 PASS |

**Total: 107/107 PASS**

Run all tests:
```bash
python -m pytest tests/unit/layer1_data/ -v
```

---

## Mandatory Invariants

### PIT_STATUS = "UNVERIFIED" (Always, Until C1.5-PIT Empirical Proof)

Every artifact carries `pit_status`:
```python
{
  "snapshot_id": "20260929_150000",
  "pit_status": "UNVERIFIED",  # Hardcoded default
  "data": {...}
}
```

**Rules:**
- Never created as `VERIFIED` in code
- Only set to `VERIFIED` after PITValidator passes AND provider empirical proof obtained
- If empirical proof fails: remains `UNVERIFIED`, WFV blocked
- If empirical proof is CONDITIONAL: remains `UNVERIFIED`, WFV blocked

### No Future Data (100% Rejection)

PITValidator rejects any observation where:
```
availability_time > decision_time
```

Tests verify 100% rejection rate.

### No Late-Arriving Data (100% Rejection)

Late observations (available after decision) rejected at query time.

### Retroactive Revisions Explicitly Handled

RevisionAuditEngine detects snapshot changes. Revisions must be:
- Logged immutably
- Explicitly marked `"handled": True`
- Never silently tolerated

### Aggregation Cutoffs Enforced

PITValidator blocks premature aggregates:
- Daily: requires next-day 00:00 UTC
- Weekly: requires next-Monday 00:00 UTC
- Monthly: requires next-month 00:00 UTC

---

## Next Phase: Empirical Validation (Not Code)

**Do not proceed to Step 6 until:**

1. **Binance/CoinGecko Audit**: For BTC/ETH/SOL, document:
   - Actual `availability_time` for each historical candle
   - Archive/versioning method
   - Proof level (A/B/C/D/E)

2. **PITValidator Injection**: Run real data through engine, obtain:
   - PASS / PASS_CONDITIONAL / FAIL verdict per source
   - Violation report (if any)

3. **Gate Decision**:
   - PASS → Proceed to WFV
   - PASS_CONDITIONAL → WFV conditional on documentation
   - FAIL → Block WFV, investigate

4. **No Forcing**: If Binance cannot prove availability_time:
   - Result = PASS_CONDITIONAL (not PASS)
   - WFV remains BLOCKED
   - This is scientifically correct

---

## Development Conventions

### Branching
- **Canonical branch**: `claude/gracious-pascal-mcg5bl` (production work only)
- **Experimental**: Create temp branches only with explicit permission
- **Merging**: Zero merges to canonical until empirical validation complete

### Commit Attribution
Every commit includes:
```
Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01Vh9TodeasSRHHrxPfYSHiK
```

### Code Style
- Dataclasses for immutable structures
- Static methods for functional operations
- Type hints mandatory
- No hardcoded assumptions about provider behavior
- Explicitly document when something is UNVERIFIED

### Testing Discipline
- TDD: tests first, then implementation
- No test without clear acceptance criteria
- All tests must pass before commit
- Integration tests document full workflows

---

## ADR-035: Control Separation & Integrity Model

**Location:** `docs/ADR-035_DATA_SOURCE_ARCHITECTURE.md`

**Key Sections:**
- §5.1: C1.4-SOURCE / C1.5-SOURCE marked UNVERIFIED (upstream capabilities)
- §5.2: C1.4-IGWT / C1.5-IGWT marked AUTHORIZED (capture layer, this project)
- §5.3: C1.5-PIT marked BLOCKED pending independent proof
- §5.4: Gate 3 decision record (when PIT validation occurs)
- §5.5: Governance rule enforcing PIT_STATUS = "UNVERIFIED" invariant

---

## Status Summary

### What's Done
✅ Snapshot capture & immutability (C1.5-IGWT)
✅ Revision tracking (C1.4-IGWT)
✅ Hash verification & tampering detection
✅ Temporal validation engine (PITValidator)
✅ 107 comprehensive unit tests

### What's Pending
⏳ Empirical provider audit (BTC/ETH/SOL)
⏳ Availability proof (A/B/C/D/E hierarchy)
⏳ WFV approval (blocked until C1.5-PIT PASS)

### What's Out of Scope (Layer 1)
🔴 Alpha validation
🔴 Statistical backtesting
🔴 Performance metrics
🔴 Production trading

---

## For Future Developers

**Read these first:**
1. ADR-035 (governance foundation)
2. This CLAUDE.md (status & architecture)
3. test_pit_validation.py (temporal validation logic)

**Before touching code:**
- Understand the C1.5-IGWT vs C1.5-PIT distinction
- Do not modify PIT_STATUS validation logic
- Do not remove any of the 107 tests
- Document every new assumption about provider behavior

**When stuck:**
- Check if the issue is infrastructure (Layer 1) or empirical (Phase 2)
- Layer 1 infrastructure is locked until empirical validation
- Empirical validation happens outside this codebase

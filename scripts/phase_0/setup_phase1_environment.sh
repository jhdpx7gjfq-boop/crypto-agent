#!/bin/bash
# Phase 1 Environment Setup Script
# Prepares system for Phase 1 data collection
# Run before Oct 9, 2026

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "=========================================="
echo "PHASE 1 ENVIRONMENT SETUP"
echo "=========================================="
echo "Project Directory: ${PROJECT_DIR}"

# 1. Create directory structure
echo -e "\n1. Creating directory structure..."
mkdir -p "${PROJECT_DIR}/data/raw/phase_1"
mkdir -p "${PROJECT_DIR}/data/qa/phase_1"
mkdir -p "${PROJECT_DIR}/data/immutable_snapshots/phase_1"
mkdir -p "${PROJECT_DIR}/data/manifests"
mkdir -p "${PROJECT_DIR}/logs/phase_0"
mkdir -p "${PROJECT_DIR}/logs/phase_1"
mkdir -p "${PROJECT_DIR}/logs/phase_2"
mkdir -p "${PROJECT_DIR}/backups/phase_1"
echo "✓ Directory structure created"

# 2. Setup Python virtual environment (optional)
echo -e "\n2. Setting up Python virtual environment..."
if [ ! -d "${PROJECT_DIR}/venv" ]; then
    python3 -m venv "${PROJECT_DIR}/venv"
    echo "✓ Virtual environment created"

    # Activate and install dependencies
    source "${PROJECT_DIR}/venv/bin/activate"
else
    source "${PROJECT_DIR}/venv/bin/activate"
    echo "✓ Using existing virtual environment"
fi

# 3. Install Python dependencies
echo -e "\n3. Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r "${PROJECT_DIR}/requirements-phase1.txt"
echo "✓ Dependencies installed"

# 4. Create .env file template
echo -e "\n4. Creating environment configuration..."
ENV_FILE="${PROJECT_DIR}/.env.phase1"

if [ ! -f "${ENV_FILE}" ]; then
    cat > "${ENV_FILE}" << 'EOF'
# Phase 1 Data Collection Environment Variables
# Copy values here before running collection scripts

# CoinGecko (public API, no key required)
COINGECKO_API_URL=https://api.coingecko.com/api/v3

# Glassnode (requires API key)
GLASSNODE_API_KEY=your_glassnode_api_key_here

# AWS S3 Backup (optional)
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
AWS_REGION=us-east-1

# Google Cloud Storage Backup (optional)
GCS_PROJECT_ID=your_gcs_project_id_here
GOOGLE_APPLICATION_CREDENTIALS=/path/to/gcs/credentials.json

# Phase 1 Configuration
PHASE1_MAX_COINS=3421
PHASE1_START_DATE=2020-01-01
PHASE1_END_DATE=2026-12-31
PHASE1_TARGET_COMPLETENESS=0.95
PHASE1_MAX_GAP_DAYS=14

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
EOF
    echo "✓ Environment template created: ${ENV_FILE}"
    echo "  → Edit ${ENV_FILE} with your API keys before Phase 1"
else
    echo "✓ Environment file already exists: ${ENV_FILE}"
fi

# 5. Create data collection schedule
echo -e "\n5. Creating Phase 1 execution schedule..."
SCHEDULE_FILE="${PROJECT_DIR}/docs/PHASE_1_EXECUTION_SCHEDULE.md"

if [ ! -f "${SCHEDULE_FILE}" ]; then
    cat > "${SCHEDULE_FILE}" << 'EOF'
# Phase 1 Execution Schedule
## October 9-23, 2026 (14 days)

### Week 1: Data Collection

**Oct 9-10 (Days 1-2): Pre-Flight**
- 6:00 AM: Pre-flight checklist (launch_day_preflight.sh)
- 7:00 AM: Go/No-Go decision
- 8:00 AM: Launch briefing

**Oct 10-12 (Days 2-4): CoinGecko Collection**
```bash
python3 src/phase_1_data_collection/collect_coingecko.py
```
- Target: 3,421 coins
- Rate limit: 100 req/min
- Expected: 3,400+ coins collected
- Output: Parquet files + manifest

**Oct 13-14 (Days 5-6): Glassnode On-Chain**
```bash
python3 src/phase_1_data_collection/collect_glassnode.py
```
- Requires: GLASSNODE_API_KEY set
- Target: 10+ major coins
- Metrics: active_addresses, transaction_count, exchange_flow

**Oct 15-16 (Days 7-8): Data Consolidation**
- Merge OHLCV and on-chain data
- DuckDB schema creation
- Parquet format validation

### Week 2: Quality Assurance

**Oct 17-19 (Days 9-11): Quality Audit**
```bash
python3 src/phase_1_qa/audit_completeness.py
```
- Completeness check: ≥95% data points
- Gap analysis: <14 days max
- Outlier detection
- Gate decision: PASS/FAIL

**Oct 20-21 (Days 12-13): Immutable Snapshot**
```bash
python3 src/phase_1_qa/create_immutable_snapshot.py
```
- SHA256 hashing
- Multi-location backup
- Read-only enforcement
- Immutability certificate

### Oct 23: Phase 1 Completion Gate

**QA Lead Approval:**
- [ ] Completeness audit PASS
- [ ] All files SHA256 verified
- [ ] Immutable snapshot created
- [ ] Backup verified
- [ ] Gate decision: PASS

**Decision:**
- ✓ PASS → Proceed to Phase 2 (Oct 24)
- ✗ FAIL → Remediation required

---

## Daily Standup Template

**Date:** Oct X, 2026
**Lead:** _______________

### Yesterday
- [ ] Task 1 complete
- [ ] Task 2 complete

### Today
- [ ] Task 1 in progress
- [ ] Task 2 planned

### Blockers
- None
- (List any blockers here)

### Metrics
- Coins collected: X/3421
- Data completeness: X%
- API calls: X/X rate limit
- Storage used: X GB
EOF
    echo "✓ Execution schedule created: ${SCHEDULE_FILE}"
fi

# 6. Create monitoring dashboard
echo -e "\n6. Creating monitoring configuration..."
MONITORING_FILE="${PROJECT_DIR}/scripts/phase_1/monitor_collection.py"

if [ ! -f "${MONITORING_FILE}" ]; then
    cat > "${MONITORING_FILE}" << 'EOF'
#!/usr/bin/env python3
"""
Phase 1 Data Collection Monitoring Dashboard
Real-time monitoring of collection progress
"""

import json
import sys
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw" / "phase_1"

def get_progress():
    """Get current collection progress"""
    parquet_files = list(DATA_DIR.glob("*.parquet"))

    total_size = sum(f.stat().st_size for f in parquet_files)

    return {
        "timestamp": datetime.now().isoformat(),
        "coins_collected": len(parquet_files),
        "total_size_gb": round(total_size / (1024**3), 2),
        "target_coins": 3421,
        "progress_percent": round(100 * len(parquet_files) / 3421, 1)
    }

if __name__ == "__main__":
    progress = get_progress()
    print(json.dumps(progress, indent=2))
EOF
    chmod +x "${MONITORING_FILE}"
    echo "✓ Monitoring dashboard created"
fi

# 7. Git pre-commit hook for data integrity
echo -e "\n7. Setting up Git hooks..."
GIT_HOOKS_DIR="${PROJECT_DIR}/.git/hooks"

if [ -d "${GIT_HOOKS_DIR}" ]; then
    cat > "${GIT_HOOKS_DIR}/pre-commit" << 'EOF'
#!/bin/bash
# Pre-commit hook: Ensure no data files are committed

STAGED_DATA=$(git diff --cached --name-only | grep -E "data/raw|data/immutable|backups" || true)

if [ ! -z "$STAGED_DATA" ]; then
    echo "ERROR: Data files should not be committed to Git"
    echo "Staged data files:"
    echo "$STAGED_DATA"
    exit 1
fi

exit 0
EOF
    chmod +x "${GIT_HOOKS_DIR}/pre-commit"
    echo "✓ Pre-commit hook configured"
fi

# 8. Summary
echo -e "\n=========================================="
echo "SETUP COMPLETE"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env.phase1 with your API keys"
echo "2. Run pre-flight check:"
echo "   ./scripts/phase_0/launch_day_preflight.sh"
echo "3. Schedule daily standups"
echo "4. Review Phase 1 execution schedule"
echo ""
echo "Ready for Phase 1 launch: Oct 9, 2026"
echo ""

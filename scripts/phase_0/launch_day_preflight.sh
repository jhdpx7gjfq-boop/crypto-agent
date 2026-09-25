#!/bin/bash
# Phase 1 Launch Day Pre-Flight Checklist
# October 9, 2026 @ 6:00 AM
# Verify all systems ready before Phase 1 execution begins

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOGS_DIR="${PROJECT_DIR}/logs/phase_0"
mkdir -p "${LOGS_DIR}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PREFLIGHT_LOG="${LOGS_DIR}/preflight_${TIMESTAMP}.log"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "${PREFLIGHT_LOG}"
}

# Test function
test_component() {
    local name=$1
    local command=$2

    echo -n "Testing $name... " | tee -a "${PREFLIGHT_LOG}"
    if eval "$command" &>> "${PREFLIGHT_LOG}"; then
        echo "✓ PASS" | tee -a "${PREFLIGHT_LOG}"
        return 0
    else
        echo "✗ FAIL" | tee -a "${PREFLIGHT_LOG}"
        return 1
    fi
}

log "=========================================="
log "PHASE 1 LAUNCH DAY PRE-FLIGHT CHECK"
log "=========================================="
log "Start Time: $(date)"
log "Environment: ${PROJECT_DIR}"

# Initialize results
PASSED=0
FAILED=0

# 1. Directory structure verification
log "\n1. DIRECTORY STRUCTURE VERIFICATION"
log "========================================"

if test_component "Project root" "test -d ${PROJECT_DIR}"; then
    ((PASSED++))
else
    ((FAILED++))
fi

if test_component "Source code" "test -d ${PROJECT_DIR}/src"; then
    ((PASSED++))
else
    ((FAILED++))
fi

if test_component "Data directories" "test -d ${PROJECT_DIR}/data"; then
    ((PASSED++))
else
    ((FAILED++))
fi

if test_component "Scripts directory" "test -d ${PROJECT_DIR}/scripts"; then
    ((PASSED++))
else
    ((FAILED++))
fi

# 2. Python environment
log "\n2. PYTHON ENVIRONMENT VERIFICATION"
log "========================================"

if test_component "Python installed" "python3 --version"; then
    ((PASSED++))
else
    ((FAILED++))
fi

if test_component "Pip installed" "pip --version"; then
    ((PASSED++))
else
    ((FAILED++))
fi

if test_component "virtualenv available" "python3 -m venv --help &> /dev/null"; then
    ((PASSED++))
else
    ((FAILED++))
fi

# 3. Required Python packages
log "\n3. REQUIRED PYTHON PACKAGES"
log "========================================"

REQUIRED_PACKAGES=("pandas" "numpy" "requests" "pyarrow" "tenacity")

for pkg in "${REQUIRED_PACKAGES[@]}"; do
    if test_component "Package: $pkg" "python3 -c 'import ${pkg}' 2>/dev/null"; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
done

# 4. API connectivity
log "\n4. API CONNECTIVITY TESTS"
log "========================================"

if test_component "CoinGecko API" "curl -s https://api.coingecko.com/api/v3/ping -o /dev/null && echo 'ok'"; then
    ((PASSED++))
else
    ((FAILED++))
fi

if test_component "Internet connectivity" "ping -c 1 8.8.8.8 &> /dev/null"; then
    ((PASSED++))
else
    ((FAILED++))
fi

# 5. Database setup
log "\n5. DATABASE SETUP VERIFICATION"
log "========================================"

if test_component "DuckDB installed" "python3 -c 'import duckdb' 2>/dev/null"; then
    ((PASSED++))
else
    ((FAILED++))
fi

# 6. Data directory setup
log "\n6. DATA DIRECTORY STRUCTURE"
log "========================================"

DATA_DIRS=("raw/phase_1" "qa/phase_1" "immutable_snapshots/phase_1" "manifests")
for dir in "${DATA_DIRS[@]}"; do
    data_path="${PROJECT_DIR}/data/${dir}"
    if mkdir -p "${data_path}"; then
        echo "✓ Created/verified: ${dir}" | tee -a "${PREFLIGHT_LOG}"
        ((PASSED++))
    else
        echo "✗ Failed: ${dir}" | tee -a "${PREFLIGHT_LOG}"
        ((FAILED++))
    fi
done

# 7. Log directory setup
log "\n7. LOG DIRECTORY STRUCTURE"
log "========================================"

LOG_DIRS=("phase_0" "phase_1" "phase_2" "phase_3" "phase_4" "phase_5")
for dir in "${LOG_DIRS[@]}"; do
    log_path="${PROJECT_DIR}/logs/${dir}"
    if mkdir -p "${log_path}"; then
        echo "✓ Created/verified: logs/${dir}" | tee -a "${PREFLIGHT_LOG}"
        ((PASSED++))
    else
        echo "✗ Failed: logs/${dir}" | tee -a "${PREFLIGHT_LOG}"
        ((FAILED++))
    fi
done

# 8. Git repository status
log "\n8. GIT REPOSITORY STATUS"
log "========================================"

if test_component "Git repository" "cd ${PROJECT_DIR} && git status &> /dev/null"; then
    ((PASSED++))
    # Check branch
    BRANCH=$(cd "${PROJECT_DIR}" && git rev-parse --abbrev-ref HEAD)
    log "Current branch: ${BRANCH}"

    # Check for uncommitted changes
    CHANGES=$(cd "${PROJECT_DIR}" && git status --porcelain | wc -l)
    if [ "${CHANGES}" -eq 0 ]; then
        echo "✓ No uncommitted changes" | tee -a "${PREFLIGHT_LOG}"
        ((PASSED++))
    else
        echo "⚠ Warning: ${CHANGES} uncommitted changes" | tee -a "${PREFLIGHT_LOG}"
    fi
else
    ((FAILED++))
fi

# 9. Key files verification
log "\n9. KEY FILES VERIFICATION"
log "========================================"

KEY_FILES=(
    "docs/PHASE_0_EXECUTION_CHECKLIST.md"
    "docs/PHASE_0_APPROVAL_FORM.md"
    "docs/PHASE_1_IMPLEMENTATION_GUIDE.md"
    "src/phase_1_data_collection/collect_coingecko.py"
    "src/phase_1_qa/audit_completeness.py"
    "scripts/phase_1/orchestrate_phase1.py"
    "requirements-phase1.txt"
)

for file in "${KEY_FILES[@]}"; do
    if test_component "File: $file" "test -f ${PROJECT_DIR}/${file}"; then
        ((PASSED++))
    else
        ((FAILED++))
    fi
done

# 10. Environment variables
log "\n10. ENVIRONMENT VARIABLES"
log "========================================"

# Optional but recommended
if [ -n "$GLASSNODE_API_KEY" ]; then
    echo "✓ GLASSNODE_API_KEY is set" | tee -a "${PREFLIGHT_LOG}"
    ((PASSED++))
else
    echo "⚠ GLASSNODE_API_KEY not set (Glassnode collection may fail)" | tee -a "${PREFLIGHT_LOG}"
fi

if [ -n "$AWS_ACCESS_KEY_ID" ]; then
    echo "✓ AWS credentials available (S3 backup enabled)" | tee -a "${PREFLIGHT_LOG}"
    ((PASSED++))
else
    echo "⚠ AWS credentials not set (S3 backup disabled)" | tee -a "${PREFLIGHT_LOG}"
fi

# Summary
log "\n=========================================="
log "PRE-FLIGHT CHECK COMPLETE"
log "=========================================="
log "Tests Passed: ${PASSED}"
log "Tests Failed: ${FAILED}"
log "Total Tests: $((PASSED + FAILED))"

if [ ${FAILED} -eq 0 ]; then
    log "✓ ALL SYSTEMS GO - Ready for Phase 1 launch"
    exit 0
else
    log "✗ FAILURES DETECTED - Address issues before launch"
    exit 1
fi

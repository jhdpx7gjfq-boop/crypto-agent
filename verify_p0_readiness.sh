#!/bin/bash
# P0 Readiness Verification Script
# Checks: 1) Directory structure, 2) Synthetic data archived, 3) Real-data readiness
# Usage: ./verify_p0_readiness.sh

set -e

echo "=========================================="
echo "P0 READINESS VERIFICATION"
echo "=========================================="
echo ""

# Check 1: Directory structure
echo "[1/4] Checking directory structure..."
required_dirs=(
    "data/raw/synthetic_invalid"
    "data/real_binance/BTCUSDT"
    "data/real_binance/ETHUSDT"
    "data/real_binance/SOLUSDT"
    "data/processed"
    "data/validation_reports"
)

all_exist=true
for dir in "${required_dirs[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✓ $dir"
    else
        echo "  ✗ $dir (MISSING)"
        all_exist=false
    fi
done

if [ "$all_exist" = true ]; then
    echo "  → Directory structure: ✅ PASS"
else
    echo "  → Directory structure: ❌ FAIL"
    exit 1
fi
echo ""

# Check 2: Synthetic data archived
echo "[2/4] Checking synthetic data archive..."
synthetic_files=(
    "data/raw/synthetic_invalid/BTCUSDT_2020-2025.json"
    "data/raw/synthetic_invalid/ETHUSDT_2020-2025.json"
    "data/raw/synthetic_invalid/SOLUSDT_2020-2025.json"
)

synthetic_ok=true
for file in "${synthetic_files[@]}"; do
    if [ -f "$file" ]; then
        size=$(wc -c < "$file")
        echo "  ✓ $file ($size bytes)"
    else
        echo "  ✗ $file (NOT ARCHIVED)"
        synthetic_ok=false
    fi
done

if [ "$synthetic_ok" = true ]; then
    echo "  → Synthetic archive: ✅ PASS"
else
    echo "  → Synthetic archive: ❌ FAIL (synthetic data not found in archive)"
    exit 1
fi
echo ""

# Check 3: Real-data status
echo "[3/4] Checking real-data provision status..."
real_files=(
    "data/real_binance/BTCUSDT/BTCUSDT_1d.json"
    "data/real_binance/ETHUSDT/ETHUSDT_1d.json"
    "data/real_binance/SOLUSDT/SOLUSDT_1d.json"
)

real_count=0
for file in "${real_files[@]}"; do
    if [ -f "$file" ]; then
        size=$(wc -c < "$file")
        rows=$(python -c "import json; f=open('$file'); data=json.load(f); print(len(data))" 2>/dev/null || echo "?")
        echo "  ✓ $file ($rows candles)"
        ((real_count++))
    else
        echo "  ⏸ $file (awaiting user download)"
    fi
done

if [ $real_count -eq 3 ]; then
    echo "  → Real data: ✅ READY (3/3 files)"
elif [ $real_count -gt 0 ]; then
    echo "  → Real data: ⚠️ PARTIAL ($real_count/3 files)"
else
    echo "  → Real data: ⏸️ AWAITING USER DATA (0/3 files)"
fi
echo ""

# Check 4: Pipeline availability
echo "[4/4] Checking pipeline code..."
pipeline_files=(
    "src/layers/layer3_wyckoff/data_provenance_audit.py"
    "src/layers/layer3_wyckoff/real_data_wfv_pipeline.py"
    "docs/P0_REAL_DATA_INGESTION.md"
)

pipeline_ok=true
for file in "${pipeline_files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (MISSING)"
        pipeline_ok=false
    fi
done

if [ "$pipeline_ok" = true ]; then
    echo "  → Pipeline: ✅ READY"
else
    echo "  → Pipeline: ❌ FAIL"
    exit 1
fi
echo ""

# Summary
echo "=========================================="
echo "SUMMARY"
echo "=========================================="

if [ $real_count -eq 3 ]; then
    echo "✅ P0 COMPLETE: All real data provided"
    echo ""
    echo "Next step: Run audit and WFV pipeline"
    echo "  python -m src.layers.layer3_wyckoff.data_provenance_audit"
    echo "  python -m src.layers.layer3_wyckoff.real_data_wfv_pipeline"
    exit 0
elif [ $real_count -gt 0 ]; then
    echo "⚠️  P0 PARTIAL: $real_count/3 files provided"
    echo ""
    echo "Missing data:"
    for file in "${real_files[@]}"; do
        if [ ! -f "$file" ]; then
            echo "  - $(basename $file)"
        fi
    done
    exit 1
else
    echo "⏸️  P0 AWAITING DATA: User must download real Binance OHLCV"
    echo ""
    echo "Download instructions:"
    echo "  1. Visit https://www.binance.vision/"
    echo "  2. Download Daily (1d) OHLCV for:"
    echo "     - BTCUSDT (2020-01-01 onwards)"
    echo "     - ETHUSDT (2020-01-01 onwards)"
    echo "     - SOLUSDT (2020-03-20 onwards, NO pre-launch)"
    echo "  3. Place files in:"
    echo "     - data/real_binance/BTCUSDT/BTCUSDT_1d.json"
    echo "     - data/real_binance/ETHUSDT/ETHUSDT_1d.json"
    echo "     - data/real_binance/SOLUSDT/SOLUSDT_1d.json"
    echo "  4. Re-run this script to verify"
    exit 0
fi

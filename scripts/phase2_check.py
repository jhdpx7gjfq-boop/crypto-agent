#!/usr/bin/env python3
"""Phase 2 Integration Readiness Check."""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from research.phase2_credentials import Phase2CredentialManager


def main():
    """Run Phase 2 readiness check."""
    print("\n" + "="*70)
    print("PHASE 2 INTEGRATION READINESS CHECK")
    print("="*70 + "\n")

    # Check environment
    print("1. Environment Check")
    print("-" * 70)
    env_file = Path(".env")
    if env_file.exists():
        print("   ✓ .env file found")
    else:
        print("   ℹ .env file not found (use .env.example as template)")
    print()

    # Check credentials
    print("2. Credential Status")
    print("-" * 70)
    manager = Phase2CredentialManager()
    print(manager.report())

    # Check Phase 2 files
    print("3. Phase 2 Framework Files")
    print("-" * 70)
    files_to_check = [
        "src/research/phase2_credentials.py",
        "src/research/phase2_integration.py",
        "docs/PATH_A_PHASE2_SETUP.md",
        "tests/integration/test_phase2_integration.py",
    ]

    for fpath in files_to_check:
        exists = Path(fpath).exists()
        symbol = "✓" if exists else "✗"
        print(f"   {symbol} {fpath}")
    print()

    # Next steps
    print("4. Next Steps")
    print("-" * 70)

    if manager.all_available():
        print("   ✓ All credentials available!")
        print("   → Ready to run Phase 2 integration")
        print("   → Execute: python -m src.research.phase2_integration")
        return 0
    else:
        missing = manager.missing_credentials()
        if "CRYPTOQUANT_API_KEY" in missing:
            print("   1. Request CryptoQuant API key:")
            print("      → Visit: https://www.cryptoquant.com")
            print("      → Sign up and request liquidation events API access")

        if "GLASSNODE_API_KEY" in missing:
            print("   2. Request Glassnode API key:")
            print("      → Visit: https://glassnode.com")
            print("      → Sign up and request on-chain metrics API access")

        print()
        print("   3. Configure environment:")
        print("      → Copy: cp .env.example .env")
        print("      → Edit: export CRYPTOQUANT_API_KEY='<your_key>'")
        print("      → Edit: export GLASSNODE_API_KEY='<your_key>'")
        print()
        print("   4. Verify:")
        print("      → python scripts/phase2_check.py")
        print()

        return 1

    print("="*70 + "\n")


if __name__ == "__main__":
    sys.exit(main())

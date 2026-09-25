#!/usr/bin/env python3
"""Phase 2 Integration Execution Script.

Runs Phase 2 data collection with real API credentials or mock data.
Usage:
  python scripts/run_phase2.py --mock        # Test with mock data
  python scripts/run_phase2.py --real        # Run with real API keys
  python scripts/run_phase2.py --help        # Show options
"""

import sys
import os
import argparse
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from research.phase2_credentials import Phase2CredentialManager
from research.phase2_mock_test import run_phase2_mock_test


def main():
    """Execute Phase 2 integration."""
    parser = argparse.ArgumentParser(
        description="Phase 2: Liquidation Ground Truth Integration"
    )
    parser.add_argument(
        "--mode",
        choices=["mock", "real", "check"],
        default="check",
        help="Execution mode (default: check)",
    )
    parser.add_argument(
        "--assets",
        nargs="+",
        default=["BTC", "ETH"],
        help="Assets to collect (default: BTC ETH)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=180,
        help="Lookback window in days (default: 180)",
    )

    args = parser.parse_args()

    print("\n" + "="*70)
    print("PHASE 2: LIQUIDATION GROUND TRUTH INTEGRATION")
    print("="*70 + "\n")

    # Check credentials
    manager = Phase2CredentialManager()
    print(manager.report())

    if args.mode == "check":
        return 0

    elif args.mode == "mock":
        print("\n" + "="*70)
        print("RUNNING WITH MOCK DATA (No API calls)")
        print("="*70)
        results = run_phase2_mock_test()

        if results["status"] == "PASS":
            print("\n✓ Mock test passed. Framework is ready for real API credentials.\n")
            return 0
        else:
            print("\n✗ Mock test failed.\n")
            return 1

    elif args.mode == "real":
        if not manager.all_available():
            print("\n✗ Cannot run real integration: credentials missing")
            print("\nSet environment variables:")
            for key, svc in manager.REQUIRED_KEYS.items():
                print(f"  export {key}='<your_key>'")
            return 1

        print("\n" + "="*70)
        print("RUNNING WITH REAL API DATA")
        print("="*70)
        print("\nAssets:", ", ".join(args.assets))
        print("Lookback:", args.days, "days")
        print("\nNOTE: This would call CryptoQuant and Glassnode APIs")
        print("Full implementation pending API integration\n")

        # TODO: Call Phase2IntegrationPipeline with real credentials
        # from src.research.phase2_integration import Phase2IntegrationPipeline
        # pipeline = Phase2IntegrationPipeline(
        #     cryptoquant_key=manager.get("CRYPTOQUANT_API_KEY"),
        #     glassnode_key=manager.get("GLASSNODE_API_KEY"),
        # )
        # results = pipeline.run_full_integration(
        #     assets=args.assets,
        #     days=args.days,
        # )

        return 0


if __name__ == "__main__":
    sys.exit(main())

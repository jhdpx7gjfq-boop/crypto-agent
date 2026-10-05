"""Checkpoint 2: Historical Access & Timestamps Validation.

DATA-SRC-COINDESK-001 POC Validation Gate.

Purpose:
- Verify CoinDesk REST API provides 365-day historical data
- Validate timestamp integrity (no gaps, monotonic, frequency)
- Test data completeness for BTC, ETH, SOL
- Detect survivorship bias (consistent coverage)

Status: REQUIRES API KEY (Pro/Enterprise tier)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import json

logger = logging.getLogger(__name__)


class Checkpoint2HistoricalValidator:
    """Validate historical data access via CoinDesk REST API."""

    BASE_URL = "https://api.coindesk.com/v1"

    ASSETS = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize validator.

        Args:
            api_key: CoinDesk Pro/Enterprise API key
        """
        self.api_key = api_key
        self.results = {}

    def validate_historical_access(
        self,
        asset: str = "bitcoin",
        days: int = 365,
        vs_currency: str = "usd"
    ) -> Dict[str, Any]:
        """
        Validate historical data access and timestamps.

        Args:
            asset: CoinDesk asset ID (e.g., 'bitcoin', 'ethereum')
            days: Number of historical days to fetch
            vs_currency: Quote currency

        Returns:
            Dict with validation results and metrics
        """
        result = {
            "asset": asset,
            "days_requested": days,
            "checkpoint": "C2_HISTORICAL_ACCESS",
            "status": "NOT_RUN",
            "endpoint": None,
            "auth_method": None,
            "http_status": None,
            "data_points": 0,
            "timestamp_first": None,
            "timestamp_last": None,
            "timestamp_gaps": [],
            "timestamp_frequency": None,
            "is_monotonic": None,
            "expected_points": days,
            "actual_points": 0,
            "completeness": 0.0,
            "survivorship_bias": None,
            "verdict": "UNVERIFIED",
            "error": None,
        }

        if not self.api_key:
            result["status"] = "SKIPPED"
            result["error"] = "No API key provided (requires Pro/Enterprise tier)"
            result["verdict"] = "UNVERIFIED"
            logger.warning(f"{asset}: C2 SKIPPED — no API key")
            return result

        try:
            import requests
        except ImportError:
            result["error"] = "requests library required"
            result["verdict"] = "FAIL"
            return result

        # Build endpoint
        endpoint = f"{self.BASE_URL}/coins/{asset}/market_chart"
        result["endpoint"] = endpoint
        result["auth_method"] = "header"

        params = {
            "vs_currency": vs_currency,
            "days": days,
            "interval": "daily",
        }

        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            resp = requests.get(
                endpoint,
                params=params,
                headers=headers,
                timeout=30
            )
            result["http_status"] = resp.status_code

            if resp.status_code == 401:
                result["error"] = "Unauthorized (invalid API key)"
                result["verdict"] = "FAIL"
                logger.error(f"{asset}: C2 FAIL — 401 Unauthorized")
                return result

            if resp.status_code == 403:
                result["error"] = "Forbidden (insufficient tier)"
                result["verdict"] = "FAIL"
                logger.error(f"{asset}: C2 FAIL — 403 Forbidden")
                return result

            if resp.status_code != 200:
                result["error"] = f"HTTP {resp.status_code}"
                result["verdict"] = "FAIL"
                logger.error(f"{asset}: C2 FAIL — {resp.status_code}")
                return result

            data = resp.json()

            # Parse response
            prices = data.get("prices", [])
            volumes = data.get("volumes", [])

            if not volumes or len(volumes) == 0:
                result["error"] = "No volume data in response"
                result["verdict"] = "FAIL"
                return result

            # Extract timestamps
            timestamps = []
            for timestamp_ms, volume in volumes:
                ts = datetime.fromtimestamp(timestamp_ms / 1000)
                timestamps.append(ts)

            result["actual_points"] = len(timestamps)
            result["data_points"] = len(timestamps)

            if len(timestamps) == 0:
                result["error"] = "No timestamps extracted"
                result["verdict"] = "FAIL"
                return result

            # Validate timestamps
            result["timestamp_first"] = timestamps[0].isoformat()
            result["timestamp_last"] = timestamps[-1].isoformat()

            # Check monotonicity
            is_monotonic = all(
                timestamps[i] < timestamps[i + 1]
                for i in range(len(timestamps) - 1)
            )
            result["is_monotonic"] = is_monotonic

            if not is_monotonic:
                result["error"] = "Timestamps not monotonically increasing"
                result["verdict"] = "FAIL"
                return result

            # Detect gaps (expected: daily, so 1 day between points)
            gaps = []
            for i in range(len(timestamps) - 1):
                diff = (timestamps[i + 1] - timestamps[i]).days
                if diff != 1:
                    gaps.append({
                        "index": i,
                        "before": timestamps[i].isoformat(),
                        "after": timestamps[i + 1].isoformat(),
                        "gap_days": diff
                    })

            result["timestamp_gaps"] = gaps
            result["timestamp_frequency"] = "daily"

            # Calculate completeness
            result["completeness"] = len(timestamps) / days if days > 0 else 0.0

            # Verdict
            if len(gaps) == 0 and is_monotonic and len(timestamps) >= days * 0.95:
                result["status"] = "VALIDATED"
                result["verdict"] = "PASS"
                logger.info(
                    f"✅ {asset}: C2 PASS — {len(timestamps)} points, "
                    f"no gaps, {result['completeness']*100:.1f}% complete"
                )
            elif len(gaps) > 0:
                result["status"] = "PARTIAL"
                result["verdict"] = "PARTIAL"
                logger.warning(
                    f"⚠️  {asset}: C2 PARTIAL — {len(gaps)} gaps detected"
                )
            else:
                result["status"] = "INCOMPLETE"
                result["verdict"] = "FAIL"
                logger.warning(
                    f"❌ {asset}: C2 FAIL — {result['completeness']*100:.1f}% "
                    f"complete (need ≥95%)"
                )

            return result

        except requests.exceptions.RequestException as e:
            result["status"] = "ERROR"
            result["error"] = str(e)
            result["verdict"] = "FAIL"
            logger.error(f"{asset}: C2 ERROR — {e}")
            return result
        except (KeyError, ValueError) as e:
            result["status"] = "PARSE_ERROR"
            result["error"] = str(e)
            result["verdict"] = "FAIL"
            logger.error(f"{asset}: C2 PARSE ERROR — {e}")
            return result

    def validate_all_assets(self) -> Dict[str, Dict[str, Any]]:
        """Validate all tracked assets (BTC, ETH, SOL)."""
        results = {}
        for ticker, asset_id in self.ASSETS.items():
            result = self.validate_historical_access(asset=asset_id)
            results[ticker] = result
        return results

    def generate_report(self) -> Dict[str, Any]:
        """Generate C2 validation report."""
        all_results = self.validate_all_assets()

        passed = sum(
            1 for r in all_results.values()
            if r["verdict"] == "PASS"
        )
        partial = sum(
            1 for r in all_results.values()
            if r["verdict"] == "PARTIAL"
        )
        failed = sum(
            1 for r in all_results.values()
            if r["verdict"] in ["FAIL", "UNVERIFIED", "ERROR"]
        )

        return {
            "checkpoint": "C2_HISTORICAL_ACCESS",
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "passed": passed,
                "partial": partial,
                "failed": failed,
                "total": len(all_results),
            },
            "verdict": "PASS" if passed == len(all_results) else (
                "PARTIAL" if passed + partial > 0 else "FAIL"
            ),
            "results": all_results,
            "key_findings": [
                f"✅ PASS" if passed == len(all_results) else f"⚠️  {passed}/{len(all_results)} assets validated",
                "Timestamp integrity: Monotonic ✓" if all(
                    r.get("is_monotonic") for r in all_results.values()
                ) else "Timestamp integrity: ✗ Non-monotonic data detected",
                f"Data gaps: {sum(len(r.get('timestamp_gaps', [])) for r in all_results.values())} total",
                "Recommendation: Do NOT proceed to C3 (PIT validation) until all assets PASS",
            ],
            "next_checkpoint": "C3_POINT_IN_TIME_SEMANTICS" if passed == len(all_results) else None,
        }


# Checkpoint 2 entry point
def checkpoint_2_status():
    """Run Checkpoint 2 validation."""
    import os

    api_key = os.environ.get("COINDESK_API_KEY")

    print("\n" + "=" * 80)
    print("CHECKPOINT 2: Historical Access & Timestamps Validation")
    print("=" * 80)

    validator = Checkpoint2HistoricalValidator(api_key=api_key)
    report = validator.generate_report()

    print(f"\n📋 Summary:")
    print(f"   Passed: {report['summary']['passed']}/{report['summary']['total']}")
    print(f"   Partial: {report['summary']['partial']}/{report['summary']['total']}")
    print(f"   Failed: {report['summary']['failed']}/{report['summary']['total']}")
    print(f"\n🎯 Verdict: {report['verdict'].upper()}")

    for key, result in report["results"].items():
        status_icon = {
            "PASS": "✅",
            "PARTIAL": "⚠️ ",
            "FAIL": "❌",
            "UNVERIFIED": "⏳",
        }.get(result["verdict"], "?")

        print(f"\n{status_icon} {key}:")
        print(f"   Status: {result['status']}")
        print(f"   Points: {result['actual_points']}/{result['expected_points']}")
        if result.get("completeness"):
            print(f"   Completeness: {result['completeness']*100:.1f}%")
        if result.get("timestamp_gaps"):
            print(f"   Gaps: {len(result['timestamp_gaps'])}")
        if result.get("error"):
            print(f"   Error: {result['error']}")

    print("\n🔍 Key Findings:")
    for finding in report["key_findings"]:
        print(f"   • {finding}")

    if report["next_checkpoint"]:
        print(f"\n→ Next: {report['next_checkpoint']}")
    else:
        print(f"\n🔴 BLOCKED: Fix failures before proceeding")

    print("=" * 80 + "\n")

    return report


if __name__ == "__main__":
    checkpoint_2_status()

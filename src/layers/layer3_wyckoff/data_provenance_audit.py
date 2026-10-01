"""
Phase 3 Data Provenance Audit
Validates real Binance OHLCV data before PIT/WFV pipeline.

Per governance directive: strict provenance validation required.
No synthetic, interpolated, or pre-launch data allowed.
"""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class DataProvenanceAudit:
    """Audits real Binance OHLCV data for governance compliance."""

    def __init__(self, asset_symbol: str, data_path: str):
        self.symbol = asset_symbol
        self.data_path = Path(data_path)
        self.results = {}

    def compute_sha256(self) -> str:
        """Compute file SHA-256 hash."""
        sha256 = hashlib.sha256()
        with open(self.data_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def audit_file_metadata(self) -> Dict[str, Any]:
        """Audit file size, modification time, existence."""
        if not self.data_path.exists():
            return {"exists": False, "error": f"File not found: {self.data_path}"}

        stat = self.data_path.stat()
        return {
            "exists": True,
            "file_size_bytes": stat.st_size,
            "file_mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "sha256": self.compute_sha256(),
        }

    def audit_ohlcv_content(self) -> Dict[str, Any]:
        """Audit OHLCV content: row count, candle times, duplicates, gaps."""
        try:
            with open(self.data_path, "r") as f:
                data = json.load(f)

            if not isinstance(data, list) or len(data) == 0:
                return {"error": "Invalid OHLCV format (expected non-empty list)"}

            # Validate candle structure
            first_candle = data[0]
            required_keys = {"timestamp", "open", "high", "low", "close", "volume"}
            if not all(k in first_candle for k in required_keys):
                return {
                    "error": f"Missing keys in candle. Expected {required_keys}, got {first_candle.keys()}"
                }

            timestamps = []
            for i, candle in enumerate(data):
                if "timestamp" not in candle:
                    return {"error": f"Candle {i} missing timestamp"}
                timestamps.append(candle["timestamp"])

            # Detect duplicates
            unique_timestamps = set(timestamps)
            duplicate_count = len(timestamps) - len(unique_timestamps)

            # Detect gaps (assuming daily data, gaps should be ~86400 seconds)
            gaps = []
            for i in range(1, len(timestamps)):
                expected_gap = 86400  # 1 day
                actual_gap = timestamps[i] - timestamps[i - 1]
                if actual_gap != expected_gap:
                    gaps.append(
                        {
                            "position": i,
                            "expected_gap_seconds": expected_gap,
                            "actual_gap_seconds": actual_gap,
                            "previous_timestamp": timestamps[i - 1],
                            "current_timestamp": timestamps[i],
                        }
                    )

            first_dt = datetime.utcfromtimestamp(timestamps[0]).isoformat()
            last_dt = datetime.utcfromtimestamp(timestamps[-1]).isoformat()

            return {
                "row_count": len(data),
                "first_candle_timestamp": timestamps[0],
                "first_candle_datetime": first_dt,
                "last_candle_timestamp": timestamps[-1],
                "last_candle_datetime": last_dt,
                "unique_timestamp_count": len(unique_timestamps),
                "duplicate_count": duplicate_count,
                "gap_count": len(gaps),
                "gaps": gaps[:10],  # Report first 10 gaps
                "timespan_days": (timestamps[-1] - timestamps[0]) / 86400,
            }

        except json.JSONDecodeError as e:
            return {"error": f"JSON parse error: {e}"}
        except Exception as e:
            return {"error": f"Unexpected error: {e}"}

    def audit_asset_coverage(self) -> Dict[str, Any]:
        """Audit asset-specific coverage constraints."""
        launch_dates = {
            "BTC": None,  # Bitcoin from genesis (2009)
            "ETH": datetime(2015, 7, 30).timestamp(),  # Ethereum ICO
            "SOL": datetime(2020, 3, 20).timestamp(),  # Solana mainnet launch
        }

        audit = self.audit_ohlcv_content()
        if "error" in audit:
            return audit

        first_ts = audit.get("first_candle_timestamp")
        launch_ts = launch_dates.get(self.symbol)

        if launch_ts and first_ts < launch_ts:
            return {
                "error": f"{self.symbol} data backdated before launch. Launch: {datetime.utcfromtimestamp(launch_ts).isoformat()}, Data starts: {datetime.utcfromtimestamp(first_ts).isoformat()}"
            }

        return {"coverage_valid": True, "symbol": self.symbol}

    def run_full_audit(self) -> Dict[str, Any]:
        """Execute complete provenance audit."""
        return {
            "symbol": self.symbol,
            "data_path": str(self.data_path),
            "audit_timestamp": datetime.utcnow().isoformat(),
            "metadata": self.audit_file_metadata(),
            "content": self.audit_ohlcv_content(),
            "coverage": self.audit_asset_coverage(),
        }


def audit_all_real_binance_data(base_path: str = "data/real_binance") -> Dict[str, Any]:
    """Run complete audit on all real Binance datasets."""
    results = {}
    base = Path(base_path)

    for symbol in ["BTCUSDT", "ETHUSDT", "SOLUSDT"]:
        symbol_short = symbol.replace("USDT", "")
        data_path = base / symbol / f"{symbol}_1d.json"

        auditor = DataProvenanceAudit(symbol_short, str(data_path))
        results[symbol] = auditor.run_full_audit()

    return results


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        results = audit_all_real_binance_data(sys.argv[1])
    else:
        results = audit_all_real_binance_data()

    print(json.dumps(results, indent=2))

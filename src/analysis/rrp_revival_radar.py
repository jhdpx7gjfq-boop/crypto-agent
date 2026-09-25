"""
RRP - Revival Radar Pipeline
Version: 1.0.0

Detects dead tokens showing signs of resurrection.
6-stage pipeline: Collector → Validator → Immutable Store → Feature Enrichment
→ Performance Tracker → Statistical Validation
"""

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

VERSION = "1.0.0"


@dataclass
class DeadTokenSnapshot:
    """Immutable raw data snapshot of a potentially dead token."""

    timestamp: str
    coin_id: str
    price: float
    market_cap: float
    volume_24h: float
    active_addresses: int
    transaction_volume: float
    velocity: float  # (volume / market_cap)

    def to_dict(self) -> Dict:
        return asdict(self)


class RRPRevivalRadar:
    """Revival Radar Pipeline: Detect dead token resurrections."""

    # Dead token thresholds
    DEAD_TOKEN_THRESHOLDS = {
        "max_market_cap": 50e6,          # < $50M market cap
        "max_volume_24h": 1e6,           # < $1M daily volume
        "max_active_addresses": 100e3,   # < 100k active addresses
        "min_velocity": 0.01,            # Very low velocity
    }

    REVIVAL_THRESHOLDS = {
        "volume_increase_pct": 3.0,       # 3x volume increase
        "address_increase_pct": 2.0,      # 2x address increase
        "price_increase_pct": 0.50,       # 50% price increase
        "min_snapshot_count": 5,          # Need 5+ snapshots to confirm
    }

    def __init__(self):
        logger.info(f"RRP Revival Radar initialized (v{VERSION})")
        self.snapshots: Dict[str, List[DeadTokenSnapshot]] = {}
        self.revival_scores: Dict[str, float] = {}

    # Stage 1: Collector
    def collect_snapshot(self, coin_data: Dict) -> Optional[DeadTokenSnapshot]:
        """
        Collect raw data snapshot of a token.

        Args:
            coin_data: {
                "id": "token_id",
                "price": float,
                "market_cap": float,
                "volume_24h": float,
                "active_addresses": int,
                "transaction_volume": float,
            }

        Returns:
            DeadTokenSnapshot if valid, None otherwise
        """
        coin_id = coin_data.get("id")
        if not coin_id:
            return None

        timestamp = datetime.utcnow().isoformat()
        velocity = coin_data.get("volume_24h", 0) / max(coin_data.get("market_cap", 1), 1)

        snapshot = DeadTokenSnapshot(
            timestamp=timestamp,
            coin_id=coin_id,
            price=coin_data.get("price", 0),
            market_cap=coin_data.get("market_cap", 0),
            volume_24h=coin_data.get("volume_24h", 0),
            active_addresses=coin_data.get("active_addresses", 0),
            transaction_volume=coin_data.get("transaction_volume", 0),
            velocity=velocity,
        )

        return snapshot

    # Stage 2: Snapshot Validator
    def validate_snapshot(self, snapshot: DeadTokenSnapshot) -> bool:
        """Validate snapshot data quality."""
        if not snapshot:
            return False

        # Check for missing/invalid data
        if snapshot.price <= 0 or snapshot.market_cap < 0 or snapshot.volume_24h < 0:
            return False

        if snapshot.active_addresses < 0 or snapshot.transaction_volume < 0:
            return False

        return True

    # Stage 3: Immutable Raw Store
    def store_snapshot(self, snapshot: DeadTokenSnapshot) -> bool:
        """
        Store snapshot immutably (append-only).

        Returns True if stored, False if validation failed.
        """
        if not self.validate_snapshot(snapshot):
            logger.warning(f"Failed to validate snapshot for {snapshot.coin_id}")
            return False

        coin_id = snapshot.coin_id
        if coin_id not in self.snapshots:
            self.snapshots[coin_id] = []

        self.snapshots[coin_id].append(snapshot)
        logger.info(f"Stored snapshot for {coin_id} (total: {len(self.snapshots[coin_id])})")
        return True

    # Stage 4: Feature Enrichment
    def enrich_features(self, coin_id: str) -> Dict:
        """
        Enrich stored snapshots with calculated features.

        Returns feature dict with growth metrics and indicators.
        """
        if coin_id not in self.snapshots or len(self.snapshots[coin_id]) < 2:
            return {}

        snapshots = self.snapshots[coin_id]
        df = pd.DataFrame([s.to_dict() for s in snapshots])
        df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Calculate growth rates
        features = {
            "coin_id": coin_id,
            "snapshot_count": len(snapshots),
            "timespan_days": (df["timestamp"].iloc[-1] - df["timestamp"].iloc[0]).days,
        }

        # Price change
        if len(df) >= 2:
            features["price_change"] = (df["price"].iloc[-1] - df["price"].iloc[0]) / df["price"].iloc[0]
            features["price_change_7d"] = None
            if len(df) >= 7:
                features["price_change_7d"] = (df["price"].iloc[-1] - df["price"].iloc[-7]) / df["price"].iloc[-7]

        # Volume growth
        if len(df) >= 2:
            features["volume_change"] = (df["volume_24h"].iloc[-1] - df["volume_24h"].iloc[0]) / max(df["volume_24h"].iloc[0], 1)
            features["volume_change_7d"] = None
            if len(df) >= 7:
                features["volume_change_7d"] = (df["volume_24h"].iloc[-1] - df["volume_24h"].iloc[-7]) / max(df["volume_24h"].iloc[-7], 1)

        # Address growth
        if len(df) >= 2:
            features["address_change"] = (df["active_addresses"].iloc[-1] - df["active_addresses"].iloc[0]) / max(df["active_addresses"].iloc[0], 1)
            features["address_change_7d"] = None
            if len(df) >= 7:
                features["address_change_7d"] = (df["active_addresses"].iloc[-1] - df["active_addresses"].iloc[-7]) / max(df["active_addresses"].iloc[-7], 1)

        # Volatility
        if len(df) > 1:
            price_returns = df["price"].pct_change().dropna()
            features["price_volatility"] = price_returns.std() if len(price_returns) > 0 else 0

        # Recent momentum
        if len(df) >= 3:
            recent_prices = df["price"].iloc[-3:]
            features["recent_uptrend"] = (recent_prices.iloc[-1] > recent_prices.iloc[0])

        features["latest_price"] = df["price"].iloc[-1]
        features["latest_market_cap"] = df["market_cap"].iloc[-1]
        features["latest_volume"] = df["volume_24h"].iloc[-1]
        features["latest_addresses"] = df["active_addresses"].iloc[-1]

        return features

    # Stage 5: Performance Tracker
    def track_performance(self, coin_id: str) -> Dict:
        """Track performance relative to baseline (earliest snapshot)."""
        if coin_id not in self.snapshots or len(self.snapshots[coin_id]) < 2:
            return {}

        snapshots = self.snapshots[coin_id]
        baseline = snapshots[0]  # First snapshot
        latest = snapshots[-1]   # Latest snapshot

        performance = {
            "coin_id": coin_id,
            "baseline_timestamp": baseline.timestamp,
            "latest_timestamp": latest.timestamp,
            "baseline_price": baseline.price,
            "latest_price": latest.price,
            "price_multiple": latest.price / max(baseline.price, 0.0001),
            "baseline_volume": baseline.volume_24h,
            "latest_volume": latest.volume_24h,
            "volume_multiple": latest.volume_24h / max(baseline.volume_24h, 1),
            "baseline_addresses": baseline.active_addresses,
            "latest_addresses": latest.active_addresses,
            "address_multiple": latest.active_addresses / max(baseline.active_addresses, 1),
            "velocity_change": latest.velocity - baseline.velocity,
        }

        return performance

    # Stage 6: Statistical Validation
    def validate_revival(self, coin_id: str) -> Tuple[bool, Dict]:
        """
        Statistical validation of revival signal.

        Returns (is_revival, validation_details)
        """
        if coin_id not in self.snapshots:
            return False, {}

        snapshots = self.snapshots[coin_id]

        # Need minimum snapshots to confirm
        if len(snapshots) < self.REVIVAL_THRESHOLDS["min_snapshot_count"]:
            return False, {"reason": "insufficient_snapshots"}

        features = self.enrich_features(coin_id)
        performance = self.track_performance(coin_id)

        validation = {
            "coin_id": coin_id,
            "snapshot_count": len(snapshots),
            "checks": {},
            "passed_checks": 0,
            "total_checks": 3,
        }

        # Check 1: Volume surge
        volume_increase = features.get("volume_change", 0)
        volume_check = volume_increase >= self.REVIVAL_THRESHOLDS["volume_increase_pct"]
        validation["checks"]["volume_surge"] = volume_check
        if volume_check:
            validation["passed_checks"] += 1

        # Check 2: Address growth
        address_increase = features.get("address_change", 0)
        address_check = address_increase >= self.REVIVAL_THRESHOLDS["address_increase_pct"]
        validation["checks"]["address_growth"] = address_check
        if address_check:
            validation["passed_checks"] += 1

        # Check 3: Price appreciation
        price_increase = (performance.get("price_multiple", 1) - 1.0) * 100
        price_check = price_increase >= self.REVIVAL_THRESHOLDS["price_increase_pct"] * 100
        validation["checks"]["price_appreciation"] = price_check
        if price_check:
            validation["passed_checks"] += 1

        # Revival = at least 2/3 checks pass
        is_revival = validation["passed_checks"] >= 2

        validation["is_revival"] = is_revival
        validation["confidence"] = validation["passed_checks"] / validation["total_checks"]

        return is_revival, validation

    def score_revival_candidate(self, coin_id: str) -> Dict:
        """
        Comprehensive revival scoring (0-100).

        Combines growth metrics, momentum, and statistical validation.
        """
        if coin_id not in self.snapshots or len(self.snapshots[coin_id]) < 2:
            return {"coin_id": coin_id, "score": 0, "status": "insufficient_data"}

        features = self.enrich_features(coin_id)
        performance = self.track_performance(coin_id)
        is_revival, validation = self.validate_revival(coin_id)

        score = 0.0

        # Volume growth component (30 pts)
        volume_change = features.get("volume_change", 0)
        if volume_change >= 5.0:  # 5x+
            score += 30
        elif volume_change >= 3.0:  # 3x+
            score += 25
        elif volume_change >= 1.0:  # 2x+
            score += 15
        elif volume_change > 0:
            score += 8

        # Address growth component (30 pts)
        address_change = features.get("address_change", 0)
        if address_change >= 3.0:  # 3x+
            score += 30
        elif address_change >= 2.0:  # 2x+
            score += 25
        elif address_change >= 1.0:  # 2x+
            score += 15
        elif address_change > 0:
            score += 8

        # Price appreciation component (20 pts)
        price_multiple = performance.get("price_multiple", 1)
        if price_multiple >= 2.0:  # 2x+
            score += 20
        elif price_multiple >= 1.5:  # 50%+
            score += 15
        elif price_multiple >= 1.1:  # 10%+
            score += 8

        # Velocity improvement component (10 pts)
        velocity_change = features.get("velocity_change", 0)  # Will be filled if we have it
        latest_velocity = self.snapshots[coin_id][-1].velocity if self.snapshots[coin_id] else 0
        if latest_velocity > 0.05:
            score += 10
        elif latest_velocity > 0.02:
            score += 5

        # Statistical validation bonus (10 pts)
        if is_revival:
            score += 10

        score = min(100.0, score)

        return {
            "coin_id": coin_id,
            "score": score,
            "status": "revival_candidate" if score >= 50 else "monitoring",
            "snapshot_count": len(self.snapshots[coin_id]),
            "volume_growth": volume_change,
            "address_growth": address_change,
            "price_multiple": price_multiple,
            "validation": validation,
            "features": {k: v for k, v in features.items() if k != "coin_id"},
        }

    def detect_resurrections(self, coins_data: List[Dict]) -> pd.DataFrame:
        """Detect multiple dead tokens showing revival signs."""
        results = []

        for coin in coins_data:
            # Collect and store
            snapshot = self.collect_snapshot(coin)
            if snapshot:
                self.store_snapshot(snapshot)

            # Score
            score_result = self.score_revival_candidate(coin.get("id", "unknown"))
            results.append({
                "coin_id": score_result.get("coin_id"),
                "score": score_result.get("score", 0),
                "status": score_result.get("status", "unknown"),
                "volume_growth": score_result.get("volume_growth", 0),
                "address_growth": score_result.get("address_growth", 0),
                "price_multiple": score_result.get("price_multiple", 1),
            })

        df = pd.DataFrame(results)
        return df.sort_values("score", ascending=False) if len(df) > 0 else df


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    radar = RRPRevivalRadar()

    # Simulate collecting snapshots over time
    test_coin = {
        "id": "dead_token",
        "price": 0.001,
        "market_cap": 10e6,
        "volume_24h": 100e3,
        "active_addresses": 5000,
        "transaction_volume": 50e3,
    }

    print("=== RRP Revival Radar Test ===\n")

    # Day 1
    print("Day 1 - Collecting baseline...")
    snapshot1 = radar.collect_snapshot(test_coin)
    radar.store_snapshot(snapshot1)

    # Day 2 - Small increase
    test_coin["price"] = 0.0015
    test_coin["volume_24h"] = 200e3
    test_coin["active_addresses"] = 7000
    snapshot2 = radar.collect_snapshot(test_coin)
    radar.store_snapshot(snapshot2)

    # Day 3 - Bigger increase
    test_coin["price"] = 0.003
    test_coin["volume_24h"] = 500e3
    test_coin["active_addresses"] = 12000
    snapshot3 = radar.collect_snapshot(test_coin)
    radar.store_snapshot(snapshot3)

    # Day 4-5 - Continued growth
    for _ in range(2):
        test_coin["price"] *= 1.3
        test_coin["volume_24h"] *= 1.4
        test_coin["active_addresses"] = int(test_coin["active_addresses"] * 1.2)
        snapshot = radar.collect_snapshot(test_coin)
        radar.store_snapshot(snapshot)

    # Score and validate
    score_result = radar.score_revival_candidate("dead_token")
    is_revival, validation = radar.validate_revival("dead_token")

    print(f"\nCoin: {score_result['coin_id']}")
    print(f"Revival Score: {score_result['score']:.1f}/100")
    print(f"Status: {score_result['status']}")
    print(f"Snapshots: {score_result['snapshot_count']}")
    print(f"\nGrowth Metrics:")
    print(f"  Volume Growth: {score_result['volume_growth']:.2f}x")
    print(f"  Address Growth: {score_result['address_growth']:.2f}x")
    print(f"  Price Multiple: {score_result['price_multiple']:.2f}x")
    print(f"\nStatistical Validation: {is_revival}")
    print(f"  Checks Passed: {validation.get('passed_checks', 0)}/3")

    print("\n✓ RRP Revival Radar test complete")

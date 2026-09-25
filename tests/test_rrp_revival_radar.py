import pytest
import pandas as pd
from datetime import datetime, timedelta
from src.analysis.rrp_revival_radar import RRPRevivalRadar, DeadTokenSnapshot


@pytest.fixture
def radar():
    return RRPRevivalRadar()


@pytest.fixture
def dead_token_data():
    return {
        "id": "dead_token",
        "price": 0.001,
        "market_cap": 10e6,
        "volume_24h": 100e3,
        "active_addresses": 5000,
        "transaction_volume": 50e3,
    }


@pytest.fixture
def reviving_token_data():
    return {
        "id": "reviving_token",
        "price": 0.005,
        "market_cap": 30e6,
        "volume_24h": 500e3,
        "active_addresses": 15000,
        "transaction_volume": 200e3,
    }


def test_radar_init(radar):
    assert radar is not None
    assert hasattr(radar, "snapshots")
    assert hasattr(radar, "DEAD_TOKEN_THRESHOLDS")
    assert hasattr(radar, "REVIVAL_THRESHOLDS")


def test_collect_snapshot(radar, dead_token_data):
    snapshot = radar.collect_snapshot(dead_token_data)

    assert snapshot is not None
    assert snapshot.coin_id == "dead_token"
    assert snapshot.price == 0.001
    assert snapshot.market_cap == 10e6
    assert snapshot.velocity > 0


def test_snapshot_without_id(radar):
    invalid_data = {
        "price": 0.001,
        "market_cap": 10e6,
    }
    snapshot = radar.collect_snapshot(invalid_data)
    assert snapshot is None


def test_validate_snapshot(radar, dead_token_data):
    snapshot = radar.collect_snapshot(dead_token_data)
    assert radar.validate_snapshot(snapshot) is True


def test_validate_snapshot_invalid_price(radar, dead_token_data):
    snapshot = radar.collect_snapshot(dead_token_data)
    snapshot.price = -1
    assert radar.validate_snapshot(snapshot) is False


def test_store_snapshot(radar, dead_token_data):
    snapshot = radar.collect_snapshot(dead_token_data)
    result = radar.store_snapshot(snapshot)

    assert result is True
    assert "dead_token" in radar.snapshots
    assert len(radar.snapshots["dead_token"]) == 1


def test_store_invalid_snapshot(radar):
    snapshot = DeadTokenSnapshot(
        timestamp=datetime.utcnow().isoformat(),
        coin_id="test",
        price=-1,  # Invalid
        market_cap=100,
        volume_24h=10,
        active_addresses=100,
        transaction_volume=50,
        velocity=0.1,
    )
    result = radar.store_snapshot(snapshot)
    assert result is False


def test_enrich_features_insufficient_data(radar, dead_token_data):
    # Only one snapshot, need at least 2
    snapshot = radar.collect_snapshot(dead_token_data)
    radar.store_snapshot(snapshot)

    features = radar.enrich_features("dead_token")
    assert len(features) == 0


def test_enrich_features_with_data(radar, dead_token_data):
    # Add multiple snapshots
    snapshot1 = radar.collect_snapshot(dead_token_data)
    radar.store_snapshot(snapshot1)

    # Simulate price increase
    dead_token_data["price"] = 0.002
    dead_token_data["volume_24h"] = 300e3
    dead_token_data["active_addresses"] = 10000

    snapshot2 = radar.collect_snapshot(dead_token_data)
    radar.store_snapshot(snapshot2)

    features = radar.enrich_features("dead_token")

    assert "coin_id" in features
    assert "price_change" in features
    assert "volume_change" in features
    assert "address_change" in features
    assert features["price_change"] > 0
    assert features["volume_change"] > 0


def test_track_performance(radar, dead_token_data):
    # Add baseline
    snapshot1 = radar.collect_snapshot(dead_token_data)
    radar.store_snapshot(snapshot1)

    # Add improved snapshot
    dead_token_data["price"] = 0.003  # 3x
    dead_token_data["volume_24h"] = 500e3  # 5x
    dead_token_data["active_addresses"] = 15000  # 3x

    snapshot2 = radar.collect_snapshot(dead_token_data)
    radar.store_snapshot(snapshot2)

    performance = radar.track_performance("dead_token")

    assert "price_multiple" in performance
    assert "volume_multiple" in performance
    assert "address_multiple" in performance
    assert performance["price_multiple"] == pytest.approx(3.0)
    assert performance["volume_multiple"] == pytest.approx(5.0)


def test_validate_revival_insufficient_snapshots(radar, dead_token_data):
    snapshot = radar.collect_snapshot(dead_token_data)
    radar.store_snapshot(snapshot)

    is_revival, validation = radar.validate_revival("dead_token")
    assert is_revival is False
    assert validation.get("reason") == "insufficient_snapshots"


def test_validate_revival_positive(radar, dead_token_data):
    # Add multiple snapshots with strong growth
    for i in range(6):
        dead_token_data["price"] *= 1.2
        dead_token_data["volume_24h"] *= 1.5
        dead_token_data["active_addresses"] = int(dead_token_data["active_addresses"] * 1.3)

        snapshot = radar.collect_snapshot(dead_token_data)
        radar.store_snapshot(snapshot)

    is_revival, validation = radar.validate_revival("dead_token")

    assert isinstance(validation, dict)
    assert "checks" in validation
    assert "passed_checks" in validation
    assert "confidence" in validation


def test_score_revival_candidate(radar, dead_token_data):
    # Single snapshot
    snapshot = radar.collect_snapshot(dead_token_data)
    radar.store_snapshot(snapshot)

    result = radar.score_revival_candidate("dead_token")

    assert result["coin_id"] == "dead_token"
    assert result["score"] == 0
    assert result["status"] == "insufficient_data"


def test_score_revival_candidate_with_growth(radar, dead_token_data):
    # Add growth over time
    for i in range(5):
        dead_token_data["price"] *= 1.4
        dead_token_data["volume_24h"] *= 1.6
        dead_token_data["active_addresses"] = int(dead_token_data["active_addresses"] * 1.5)

        snapshot = radar.collect_snapshot(dead_token_data)
        radar.store_snapshot(snapshot)

    result = radar.score_revival_candidate("dead_token")

    assert result["score"] > 0
    assert result["status"] in ["revival_candidate", "monitoring"]
    assert "volume_growth" in result
    assert "address_growth" in result
    assert "price_multiple" in result


def test_score_range(radar, dead_token_data):
    # Add multiple snapshots
    for i in range(5):
        snapshot = radar.collect_snapshot(dead_token_data)
        radar.store_snapshot(snapshot)

    result = radar.score_revival_candidate("dead_token")
    assert 0 <= result["score"] <= 100


def test_detect_resurrections_empty(radar):
    results_df = radar.detect_resurrections([])
    assert len(results_df) == 0


def test_detect_resurrections_single_coin(radar, dead_token_data):
    results_df = radar.detect_resurrections([dead_token_data])

    assert len(results_df) >= 1
    assert "coin_id" in results_df.columns
    assert "score" in results_df.columns
    assert "status" in results_df.columns


def test_detect_resurrections_multiple_coins(radar):
    coins = [
        {
            "id": "coin1",
            "price": 0.001,
            "market_cap": 10e6,
            "volume_24h": 100e3,
            "active_addresses": 5000,
            "transaction_volume": 50e3,
        },
        {
            "id": "coin2",
            "price": 0.002,
            "market_cap": 20e6,
            "volume_24h": 200e3,
            "active_addresses": 10000,
            "transaction_volume": 100e3,
        },
    ]

    results_df = radar.detect_resurrections(coins)

    assert len(results_df) == 2
    assert results_df["score"].iloc[0] >= results_df["score"].iloc[1]  # Sorted by score


def test_immutability_of_snapshots(radar, dead_token_data):
    # Store snapshot
    snapshot1 = radar.collect_snapshot(dead_token_data)
    radar.store_snapshot(snapshot1)

    # Store another
    dead_token_data["price"] = 0.002
    snapshot2 = radar.collect_snapshot(dead_token_data)
    radar.store_snapshot(snapshot2)

    # Verify both are stored (immutable store)
    assert len(radar.snapshots["dead_token"]) == 2
    assert radar.snapshots["dead_token"][0].price == 0.001
    assert radar.snapshots["dead_token"][1].price == 0.002


def test_dead_token_criteria(radar):
    # Token meeting dead token criteria
    dead_data = {
        "id": "very_dead",
        "price": 0.00001,
        "market_cap": 1e6,  # < 50M
        "volume_24h": 50e3,  # < 1M
        "active_addresses": 1000,  # < 100k
        "transaction_volume": 10e3,
    }

    snapshot = radar.collect_snapshot(dead_data)
    assert snapshot is not None

    # Check if it fits dead token profile
    market_cap_ok = snapshot.market_cap <= radar.DEAD_TOKEN_THRESHOLDS["max_market_cap"]
    volume_ok = snapshot.volume_24h <= radar.DEAD_TOKEN_THRESHOLDS["max_volume_24h"]
    addresses_ok = snapshot.active_addresses <= radar.DEAD_TOKEN_THRESHOLDS["max_active_addresses"]

    assert market_cap_ok or volume_ok or addresses_ok  # At least one criterion


def test_revival_validation_checks(radar, dead_token_data):
    # Build up growth to trigger revival checks
    for i in range(6):
        dead_token_data["price"] *= 1.3  # Price increase
        dead_token_data["volume_24h"] *= 1.5  # Volume surge
        dead_token_data["active_addresses"] = int(dead_token_data["active_addresses"] * 1.4)  # Address growth

        snapshot = radar.collect_snapshot(dead_token_data)
        radar.store_snapshot(snapshot)

    is_revival, validation = radar.validate_revival("dead_token")

    # Should have checks
    assert "checks" in validation
    assert "volume_surge" in validation["checks"]
    assert "address_growth" in validation["checks"]
    assert "price_appreciation" in validation["checks"]

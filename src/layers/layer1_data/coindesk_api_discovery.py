"""CoinDesk Data API endpoint discovery.

Checkpoint 1 of DATA-SRC-COINDESK-001 POC.

Reference: https://data.coindesk.com/data-catalogue
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CoinDeskEndpoint:
    """Discovered API endpoint."""
    name: str
    path: str
    method: str = "GET"
    description: str = ""
    params: List[str] = None
    authentication: str = "api_key"
    tier: str = "basic"  # basic, pro, enterprise
    rate_limit: str = ""

    def __post_init__(self):
        if self.params is None:
            self.params = []


class CoinDeskAPIDiscovery:
    """
    Discover and catalog CoinDesk Data API endpoints.

    From CoinDesk Data Catalogue:
    https://data.coindesk.com/data-catalogue
    """

    BASE_URL = "https://api.coindesk.com/v1"

    # Discovered endpoints (from public documentation)
    ENDPOINTS = {
        # Reference Rates (CADLI)
        "cadli_latest": CoinDeskEndpoint(
            name="CADLI Latest Tick",
            path="/indices/cadli/{pair}",
            description="Latest CADLI reference rate tick",
            params=["pair"],  # e.g., "BTC-USD", "ETH-USD"
            tier="basic",
        ),

        "cadli_historical": CoinDeskEndpoint(
            name="CADLI Historical",
            path="/indices/cadli/{pair}/history",
            description="Historical CADLI reference rates",
            params=["pair", "start_date", "end_date", "interval"],
            tier="pro",
        ),

        # Trade Data (Spot)
        "spot_trade_data": CoinDeskEndpoint(
            name="Spot Trade Data",
            path="/trade-data/spot",
            description="Aggregated spot trade data across venues",
            params=["asset", "start_date", "end_date", "interval"],
            tier="pro",
        ),

        "spot_ohlcv": CoinDeskEndpoint(
            name="Spot OHLCV",
            path="/trade-data/spot/ohlcv",
            description="OHLCV candles (all venues aggregated)",
            params=["asset", "vs_currency", "start_date", "end_date"],
            tier="pro",
        ),

        "spot_volume_metrics": CoinDeskEndpoint(
            name="Spot Volume Metrics",
            path="/trade-data/spot/volume",
            description="Volume breakdown: aggregate, top-tier, direct",
            params=[
                "asset",
                "start_date",
                "end_date",
                "interval",
                "volume_type",  # aggregate, top_tier, direct
            ],
            tier="pro",
        ),

        # Derivatives
        "derivatives_ohlcv": CoinDeskEndpoint(
            name="Derivatives OHLCV",
            path="/derivatives/ohlcv",
            description="Futures/perpetuals OHLCV across venues",
            params=["asset", "instrument", "start_date", "end_date"],
            tier="pro",
        ),

        "derivatives_funding_rate": CoinDeskEndpoint(
            name="Funding Rate",
            path="/derivatives/funding-rate",
            description="Perpetual funding rates by venue",
            params=["asset", "venue", "start_date", "end_date"],
            tier="pro",
        ),

        "derivatives_open_interest": CoinDeskEndpoint(
            name="Open Interest",
            path="/derivatives/open-interest",
            description="Open interest aggregated and by venue",
            params=["asset", "start_date", "end_date", "venue"],
            tier="pro",
        ),

        # Order Book
        "orderbook_snapshot": CoinDeskEndpoint(
            name="Order Book Snapshot",
            path="/order-book/snapshot",
            description="Current order book (L1, L2, or L3)",
            params=["asset", "venue", "depth"],
            tier="pro",
        ),

        "orderbook_historical": CoinDeskEndpoint(
            name="Order Book Historical",
            path="/order-book/historical",
            description="Historical order book snapshots",
            params=["asset", "venue", "start_date", "end_date", "interval"],
            tier="enterprise",
        ),

        # On-Chain Data
        "onchain_bitcoin": CoinDeskEndpoint(
            name="Bitcoin On-Chain",
            path="/on-chain/bitcoin",
            description="BTC transaction count, active addresses, flows",
            params=["metric", "start_date", "end_date"],
            tier="pro",
        ),

        "onchain_ethereum": CoinDeskEndpoint(
            name="Ethereum On-Chain",
            path="/on-chain/ethereum",
            description="ETH transaction count, active addresses, gas",
            params=["metric", "start_date", "end_date"],
            tier="pro",
        ),
    }

    @classmethod
    def get_endpoint(cls, name: str) -> Optional[CoinDeskEndpoint]:
        """Get endpoint by name."""
        return cls.ENDPOINTS.get(name)

    @classmethod
    def list_endpoints(cls, tier: str = None) -> List[CoinDeskEndpoint]:
        """List all endpoints, optionally filtered by tier."""
        if tier:
            return [ep for ep in cls.ENDPOINTS.values() if ep.tier == tier]
        return list(cls.ENDPOINTS.values())

    @classmethod
    def list_volume_endpoints(cls) -> List[CoinDeskEndpoint]:
        """List endpoints relevant to volume metrics."""
        keywords = ["volume", "spot_trade"]
        return [
            ep for ep in cls.ENDPOINTS.values()
            if any(kw in ep.name.lower() or kw in ep.description.lower()
                   for kw in keywords)
        ]

    @classmethod
    def build_url(cls, endpoint_name: str, **params) -> Optional[str]:
        """Build full URL for endpoint with parameters."""
        ep = cls.get_endpoint(endpoint_name)
        if not ep:
            return None

        url = f"{cls.BASE_URL}{ep.path}"

        # Replace path parameters
        for param in ep.params:
            if param in params:
                url = url.replace(f"{{{param}}}", str(params[param]))

        # Add query parameters
        query_params = {k: v for k, v in params.items() if k not in ep.params}
        if query_params:
            query_str = "&".join(f"{k}={v}" for k, v in query_params.items())
            url = f"{url}?{query_str}"

        return url

    @classmethod
    def print_discovery_report(cls):
        """Print API discovery report."""
        print("\n" + "=" * 80)
        print("CoinDesk API Discovery Report")
        print("=" * 80)

        for tier in ["basic", "pro", "enterprise"]:
            endpoints = cls.list_endpoints(tier)
            print(f"\n### {tier.upper()} Tier ({len(endpoints)} endpoints)")
            for ep in endpoints:
                print(f"\n  📍 {ep.name}")
                print(f"     Path: {ep.path}")
                print(f"     Method: {ep.method}")
                print(f"     Params: {', '.join(ep.params) if ep.params else 'none'}")
                print(f"     Desc: {ep.description}")

        print("\n" + "=" * 80)
        print("Volume Metrics Endpoints (for DATA-SRC-COINDESK-001)")
        print("=" * 80)
        for ep in cls.list_volume_endpoints():
            print(f"\n  📊 {ep.name}")
            print(f"     Path: {ep.path}")
            print(f"     Tier: {ep.tier}")
            print(f"     Params: {', '.join(ep.params) if ep.params else 'none'}")


# Checkpoint 1 status
def checkpoint_1_status():
    """Checkpoint 1: API Endpoint Mapping."""
    print("\n" + "=" * 80)
    print("CHECKPOINT 1: API Endpoint Mapping")
    print("=" * 80)

    endpoints = CoinDeskAPIDiscovery.list_endpoints()
    volume_eps = CoinDeskAPIDiscovery.list_volume_endpoints()

    print(f"\n✅ Total endpoints discovered: {len(endpoints)}")
    print(f"✅ Volume-related endpoints: {len(volume_eps)}")

    print("\n📋 Key endpoints for DATA-SRC-COINDESK-001:")
    print("  1. spot_volume_metrics: volume breakdown (aggregate, top-tier, direct)")
    print("  2. spot_ohlcv: basic OHLCV data")
    print("  3. derivatives_funding_rate: funding rates")
    print("  4. derivatives_open_interest: open interest")

    print("\n⚠️  Requirements:")
    print("  - Pro or Enterprise API key (basic tier insufficient)")
    print("  - Rate limits: check documentation for your tier")
    print("  - Authentication: API key in header or URL parameter")

    print("\n🔄 Next: Checkpoint 2 (Historical Access Validation)")
    print("=" * 80 + "\n")

    return True


if __name__ == "__main__":
    # Print discovery report
    CoinDeskAPIDiscovery.print_discovery_report()

    # Check checkpoint 1 status
    checkpoint_1_status()

    # Example: Build URL for volume metrics
    print("\n📌 Example URL construction:")
    url = CoinDeskAPIDiscovery.build_url(
        "spot_volume_metrics",
        asset="bitcoin",
        start_date="2025-01-01",
        end_date="2025-01-31",
        volume_type="aggregate"
    )
    print(f"   {url}")

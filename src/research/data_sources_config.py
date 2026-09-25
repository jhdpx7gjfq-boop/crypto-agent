"""Path A: Data Sources Configuration & Availability Check."""

import logging
from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DataSourceStatus(Enum):
    """Data source availability status."""
    AVAILABLE = "available"
    REQUIRES_API_KEY = "requires_api_key"
    NOT_AVAILABLE = "not_available"
    PARTIAL_ACCESS = "partial_access"


@dataclass
class DataSourceInfo:
    """Metadata for each data source."""
    name: str
    purpose: str
    status: DataSourceStatus
    api_type: str  # "rest", "websocket", "public", "none"
    rate_limit: str
    data_latency: str  # "real-time", "1h delayed", "daily", etc.
    historical_depth: str  # how far back data goes
    requirements: List[str]
    priority: int  # 1=critical, 2=important, 3=nice-to-have


class DataSourceRegistry:
    """Registry of all available data sources for Path A research."""

    sources: Dict[str, DataSourceInfo] = {
        # === LIQUIDATION EVENTS (Ground Truth) ===
        "cryptoquant": DataSourceInfo(
            name="CryptoQuant",
            purpose="Liquidation volume by exchange + derivatives metrics",
            status=DataSourceStatus.REQUIRES_API_KEY,
            api_type="rest",
            rate_limit="20 req/min (free tier)",
            data_latency="1h delayed",
            historical_depth="2020-present",
            requirements=["API_KEY"],
            priority=1,
        ),

        "blockscout": DataSourceInfo(
            name="Blockscout",
            purpose="On-chain transaction analysis + whale movements",
            status=DataSourceStatus.AVAILABLE,
            api_type="rest",
            rate_limit="100 req/min",
            data_latency="1-5 min delayed",
            historical_depth="2015-present (blockchain)",
            requirements=[],
            priority=2,
        ),

        # === DERIVATIVES STRESS SIGNALS ===
        "coingecko_derivatives": DataSourceInfo(
            name="CoinGecko (Derivatives)",
            purpose="Funding rates, OI, options data aggregation",
            status=DataSourceStatus.PARTIAL_ACCESS,
            api_type="rest",
            rate_limit="10-50 calls/min (free)",
            data_latency="1h delayed",
            historical_depth="2020-present",
            requirements=[],
            priority=1,
        ),

        "deribit": DataSourceInfo(
            name="Deribit",
            purpose="BTC/ETH options skew + funding rates",
            status=DataSourceStatus.AVAILABLE,
            api_type="websocket",
            rate_limit="Unlimited (public endpoints)",
            data_latency="real-time",
            historical_depth="2015-present",
            requirements=[],
            priority=2,
        ),

        # === ON-CHAIN METRICS ===
        "glassnode": DataSourceInfo(
            name="Glassnode",
            purpose="Exchange flows + on-chain metrics + smart money",
            status=DataSourceStatus.REQUIRES_API_KEY,
            api_type="rest",
            rate_limit="1000 requests/month (free tier)",
            data_latency="1-2h delayed",
            historical_depth="2009-present",
            requirements=["API_KEY"],
            priority=1,
        ),

        # === PRICE & VOLUME DATA ===
        "binance_public": DataSourceInfo(
            name="Binance (Public APIs)",
            purpose="OHLCV, order book snapshots, trades",
            status=DataSourceStatus.AVAILABLE,
            api_type="rest + websocket",
            rate_limit="1200 req/min",
            data_latency="real-time",
            historical_depth="2017-present",
            requirements=[],
            priority=1,
        ),

        "coingecko_public": DataSourceInfo(
            name="CoinGecko (Public)",
            purpose="Price history, market cap, volume aggregates",
            status=DataSourceStatus.AVAILABLE,
            api_type="rest",
            rate_limit="10-50 calls/min",
            data_latency="1h delayed",
            historical_depth="2015-present",
            requirements=[],
            priority=2,
        ),

        # === SENTIMENT & NARRATIVE ===
        "lunarcrush": DataSourceInfo(
            name="LunarCrush",
            purpose="Social mentions, sentiment, developer activity",
            status=DataSourceStatus.REQUIRES_API_KEY,
            api_type="rest",
            rate_limit="100 req/month (free)",
            data_latency="1h delayed",
            historical_depth="2019-present",
            requirements=["API_KEY"],
            priority=3,
        ),
    }

    @classmethod
    def get_source(cls, name: str) -> DataSourceInfo:
        """Retrieve source info by name."""
        return cls.sources.get(name)

    @classmethod
    def get_critical_sources(cls) -> List[str]:
        """Get critical (priority 1) data sources."""
        return [name for name, info in cls.sources.items() if info.priority == 1]

    @classmethod
    def get_available_sources(cls) -> List[str]:
        """Get immediately available sources (no API key required)."""
        return [
            name for name, info in cls.sources.items()
            if info.status in [DataSourceStatus.AVAILABLE, DataSourceStatus.PARTIAL_ACCESS]
        ]

    @classmethod
    def get_missing_api_keys(cls) -> List[str]:
        """Get sources that require API keys."""
        return [
            name for name, info in cls.sources.items()
            if info.status == DataSourceStatus.REQUIRES_API_KEY
        ]

    @classmethod
    def print_registry(cls) -> str:
        """Print formatted registry."""
        lines = [
            "\n" + "="*80,
            "PATH A: LIQUIDATION ALPHA — DATA SOURCE REGISTRY",
            "="*80,
            "",
        ]

        # Group by priority
        for priority in [1, 2, 3]:
            priority_sources = [
                (name, info) for name, info in cls.sources.items()
                if info.priority == priority
            ]
            if not priority_sources:
                continue

            priority_label = {
                1: "🔴 CRITICAL",
                2: "🟡 IMPORTANT",
                3: "🟢 OPTIONAL",
            }[priority]

            lines.append(f"\n{priority_label} — Priority {priority}")
            lines.append("-" * 80)

            for name, info in priority_sources:
                status_icon = {
                    DataSourceStatus.AVAILABLE: "✅",
                    DataSourceStatus.PARTIAL_ACCESS: "🟡",
                    DataSourceStatus.REQUIRES_API_KEY: "🔑",
                    DataSourceStatus.NOT_AVAILABLE: "❌",
                }[info.status]

                lines.append(f"\n{status_icon} {name.upper()}")
                lines.append(f"   Purpose: {info.purpose}")
                lines.append(f"   API Type: {info.api_type}")
                lines.append(f"   Latency: {info.data_latency}")
                lines.append(f"   Historical: {info.historical_depth}")
                lines.append(f"   Rate Limit: {info.rate_limit}")
                if info.requirements:
                    lines.append(f"   Requires: {', '.join(info.requirements)}")

        lines.append("\n" + "="*80)
        lines.append("\nACTION ITEMS:")
        lines.append(f"  - Critical sources: {len(DataSourceRegistry.get_critical_sources())}")
        lines.append(f"  - Immediately available: {len(DataSourceRegistry.get_available_sources())}")
        lines.append(f"  - Requires API keys: {len(DataSourceRegistry.get_missing_api_keys())}")
        lines.append("="*80 + "\n")

        return "\n".join(lines)


class DataCollectionPlan:
    """Phased data collection plan for Path A research."""

    @staticmethod
    def phase_1_immediate() -> Dict[str, Any]:
        """Phase 1: Collect immediately available data (no API keys)."""
        return {
            "phase": "Phase 1 — Immediate Collection",
            "timeline": "Week 1",
            "sources": [
                "binance_public",
                "coingecko_public",
                "blockscout",
                "deribit",
            ],
            "deliverables": [
                "6 months OHLCV data (BTC/ETH)",
                "Order book snapshots (Binance historical)",
                "Deribit funding rates + options data",
                "Blockscout whale transaction logs",
            ],
            "status": "🟢 READY TO START",
        }

    @staticmethod
    def phase_2_api_keys() -> Dict[str, Any]:
        """Phase 2: Integrate API key sources (requires setup)."""
        return {
            "phase": "Phase 2 — API Key Integration",
            "timeline": "Week 2-3",
            "sources": [
                "cryptoquant",  # Primary: liquidation events
                "glassnode",  # Secondary: on-chain flows
            ],
            "deliverables": [
                "Liquidation event timeline (ground truth)",
                "CEX inflow/outflow vectors",
                "Exchange flow stress metrics",
            ],
            "blockers": [
                "CryptoQuant API key (request via website)",
                "Glassnode API key (request via website)",
            ],
            "status": "⏳ BLOCKED (Awaiting credentials)",
        }

    @staticmethod
    def phase_3_secondary() -> Dict[str, Any]:
        """Phase 3: Secondary data sources (nice-to-have)."""
        return {
            "phase": "Phase 3 — Secondary Integration",
            "timeline": "Week 4+",
            "sources": [
                "lunarcrush",  # Sentiment (optional for Phase A)
            ],
            "deliverables": [
                "Social mention correlation with liquidations",
            ],
            "blockers": [
                "LunarCrush API key",
            ],
            "status": "🟢 OPTIONAL",
        }

    @staticmethod
    def print_plan() -> str:
        """Print formatted data collection plan."""
        lines = [
            "\n" + "="*80,
            "PATH A: LIQUIDATION ALPHA — DATA COLLECTION PLAN",
            "="*80,
        ]

        for phase_fn in [
            DataCollectionPlan.phase_1_immediate,
            DataCollectionPlan.phase_2_api_keys,
            DataCollectionPlan.phase_3_secondary,
        ]:
            plan = phase_fn()
            lines.append(f"\n{plan['phase']}")
            lines.append(f"Timeline: {plan['timeline']}")
            lines.append(f"Status: {plan['status']}")
            lines.append(f"Sources: {', '.join(plan['sources'])}")
            lines.append("Deliverables:")
            for deliverable in plan['deliverables']:
                lines.append(f"  ✓ {deliverable}")
            if 'blockers' in plan and plan['blockers']:
                lines.append("Blockers:")
                for blocker in plan['blockers']:
                    lines.append(f"  ⚠️  {blocker}")

        lines.append("\n" + "="*80 + "\n")
        return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Print registry
    print(DataSourceRegistry.print_registry())

    # Print collection plan
    print(DataCollectionPlan.print_plan())

    # Summary
    logger.info("Data sources registered. Ready for Phase 1 collection.")

"""Agent IA — Autonomous Research Assistant.

Market surveillance, report generation, hypothesis testing.
"""

from .orchestrator import (
    SignalType,
    Signal,
    AgentDecision,
    MarketContext,
    AgentOrchestrator,
)
from .report_generator import (
    MarketReport,
    AssetReport,
    ScenarioReport,
    ReportGenerator,
)

__all__ = [
    "SignalType",
    "Signal",
    "AgentDecision",
    "MarketContext",
    "AgentOrchestrator",
    "MarketReport",
    "AssetReport",
    "ScenarioReport",
    "ReportGenerator",
]

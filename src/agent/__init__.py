"""
IGWT-PF26 Phase 9: AI Research Agent Layer
============================================

Read-only research copilot for hypothesis generation and anomaly detection.
Human-gated validation pipeline.

Constraints:
✅ Read data
✅ Analyze
✅ Propose hypotheses
✅ Report findings
❌ Modify parameters
❌ Execute trades
❌ Bypass validation

Version: 1.0.0
"""

from .ai_research_copilot import (
    AIResearchCopilot,
    ResearchProposal,
    AnomalyReport,
    ComparisonScenario,
    ApprovalGate,
    AnalysisScope,
)

__all__ = [
    "AIResearchCopilot",
    "ResearchProposal",
    "AnomalyReport",
    "ComparisonScenario",
    "ApprovalGate",
    "AnalysisScope",
]

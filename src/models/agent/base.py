"""Research IA Assistant Agent data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ResearchQuery(BaseModel):
    """User research query for the agent."""

    query: str
    context: str | None = None
    focus_assets: list[str] | None = None
    analysis_type: Literal[
        "market_analysis",
        "anomaly_detection",
        "scenario_comparison",
        "hypothesis_challenge",
        "opportunity_scan",
        "risk_assessment",
    ] = "market_analysis"
    depth: Literal["quick", "standard", "deep"] = "standard"
    lookback_days: int = Field(default=30, ge=1, le=365)

    model_config = {"use_enum_values": True}


@dataclass
class AnalysisContext:
    """Context from all layers for analysis."""

    timestamp: datetime
    market_regime: str  # RISK_ON/RISK_OFF/TRANSITIONAL
    regime_confidence: float
    bce_score: float  # 0-6
    x20_opportunities: list[dict[str, Any]]
    narm_rotation_phase: str  # EMERGING/ACCELERATING/MATURE/DECLINING
    rcm_confirmation: bool
    rcm_score: float
    rrp_revival_signals: list[dict[str, Any]]


@dataclass
class AnomalyDetection:
    """Detected market anomalies."""

    timestamp: datetime
    anomaly_type: str  # volume_spike, price_discontinuity, holder_shift, etc.
    asset_id: str | None
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    data_points: dict[str, Any]
    recommendation: str


@dataclass
class ScenarioComparison:
    """Scenario comparison analysis."""

    scenario_name: str
    probability: float  # [0, 1]
    impact_bullish: float  # [-1, 1]
    impact_bearish: float  # [-1, 1]
    key_indicators: list[str]
    timeline_days: int
    assumptions: list[str]


@dataclass
class ResearchReport:
    """Generated research report."""

    query_id: str
    query: str
    timestamp: datetime
    analysis_type: str
    executive_summary: str
    detailed_analysis: str
    anomalies_detected: list[AnomalyDetection] = field(default_factory=list)
    scenarios: list[ScenarioComparison] = field(default_factory=list)
    key_findings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    confidence_score: float = 0.0  # [0, 1]
    data_quality: float = 0.0  # [0, 1]: How complete/reliable the analysis
    reasoning_chain: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_markdown(self) -> str:
        """Convert report to markdown format."""
        lines = [
            "# Research Report",
            "",
            f"**Query**: {self.query}",
            f"**Type**: {self.analysis_type}",
            f"**Generated**: {self.timestamp.isoformat()}",
            "",
            "## Executive Summary",
            "",
            self.executive_summary,
            "",
            "## Detailed Analysis",
            "",
            self.detailed_analysis,
        ]

        if self.key_findings:
            lines.extend(
                [
                    "",
                    "## Key Findings",
                    "",
                ]
            )
            for i, finding in enumerate(self.key_findings, 1):
                lines.append(f"{i}. {finding}")

        if self.anomalies_detected:
            lines.extend(
                [
                    "",
                    "## Anomalies Detected",
                    "",
                ]
            )
            for anom in self.anomalies_detected:
                lines.append(f"- **{anom.anomaly_type}** ({anom.severity})")
                lines.append(f"  {anom.description}")
                lines.append(f"  Recommendation: {anom.recommendation}")

        if self.scenarios:
            lines.extend(
                [
                    "",
                    "## Scenarios",
                    "",
                ]
            )
            for scenario in self.scenarios:
                lines.append(f"### {scenario.scenario_name}")
                lines.append(
                    f"Probability: {scenario.probability:.0%} | "
                    f"Bullish Impact: {scenario.impact_bullish:+.2f} | "
                    f"Bearish Impact: {scenario.impact_bearish:+.2f}"
                )
                lines.append(f"Timeline: {scenario.timeline_days} days")

        if self.recommendations:
            lines.extend(
                [
                    "",
                    "## Recommendations",
                    "",
                ]
            )
            for i, rec in enumerate(self.recommendations, 1):
                lines.append(f"{i}. {rec}")

        lines.extend(
            [
                "",
                "---",
                f"Confidence: {self.confidence_score:.0%} | "
                f"Data Quality: {self.data_quality:.0%}",
            ]
        )

        return "\n".join(lines)

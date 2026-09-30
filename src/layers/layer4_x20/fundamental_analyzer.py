"""
Fundamental Analyzer for Phase 4 X20 Engine.

Analyzes team quality, investor backing, tokenomics, adoption metrics,
and competitive positioning to identify fundamentally strong opportunities.

Author: Claude Haiku 4.5
Version: 1.0
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum


class VCTier(Enum):
    """Venture capital tier classification."""
    TIER_1 = "Tier 1 (Sequoia, a16z, Pantera, Paradigm)"
    TIER_2 = "Tier 2 (Strong regional/specialized)"
    TIER_3 = "Tier 3 (Emerging, micro-cap focused)"
    STRATEGIC = "Strategic (Corporate, trade investors)"
    ANGEL = "Angel (Individual investors)"
    NONE = "None"


class TokenomicsHealth(Enum):
    """Tokenomics health assessment."""
    EXCELLENT = "Excellent (low unlock risk, good distribution)"
    GOOD = "Good (manageable unlocks, reasonable distribution)"
    FAIR = "Fair (notable unlock risk, concentrated distribution)"
    POOR = "Poor (high unlock risk, concerning distribution)"
    CRITICAL = "Critical (severe issues, major red flags)"


@dataclass
class TeamMember:
    """Information about a team member."""
    name: str
    role: str  # CEO, CTO, advisor, etc.
    prior_experience: str  # Previous companies/projects
    github_activity: Optional[float] = None  # Commits per month (if applicable)
    social_presence: Optional[float] = None  # Twitter followers, credibility
    expertise_relevance: float = 0.0  # 0-1, how relevant to project
    is_founder: bool = False


@dataclass
class FundamentalScore:
    """Fundamental analysis score."""
    asset: str
    timestamp: str

    # Component scores (0-100)
    team_quality: float
    investor_quality: float
    tokenomics_health: float
    adoption_metrics: float
    competitive_advantage: float

    # Details
    team_members: List[TeamMember] = field(default_factory=list)
    vc_backers: List[str] = field(default_factory=list)
    vc_tier: VCTier = VCTier.NONE
    tokenomics_issues: List[str] = field(default_factory=list)
    adoption_signals: List[str] = field(default_factory=list)
    competitive_advantages: List[str] = field(default_factory=list)

    # Composite score
    overall_fundamental_score: float = 0.0

    # Red flags
    red_flags: List[str] = field(default_factory=list)

    def is_red_flagged(self) -> bool:
        """Check if significant red flags exist."""
        return len(self.red_flags) > 2 or any(
            'critical' in flag.lower() for flag in self.red_flags
        )


class FundamentalAnalyzer:
    """
    Analyzes fundamental strength of crypto projects.

    Evaluates:
    - Team quality and experience
    - Investor backing (tier, quality)
    - Tokenomics (supply, vesting, distribution)
    - Adoption metrics (users, adoption rate)
    - Competitive positioning
    """

    # Scoring thresholds
    STRONG_TEAM_MIN = 70.0
    TIER_1_VC_BONUS = 20.0  # Bonus points for Tier-1 VC backing

    # Tokenomics red flags
    TOKENOMICS_THRESHOLDS = {
        'max_unlock_per_month': 0.10,  # Max 10% per month
        'founder_concentration': 0.25,  # Max 25% for founders
        'team_concentration': 0.30,  # Max 30% for team
        'vc_concentration': 0.20,  # Max 20% for early investors
    }

    def __init__(self):
        """Initialize fundamental analyzer."""
        self.results: Dict[str, FundamentalScore] = {}

    def analyze_asset(
        self,
        asset: str,
        team_members: List[TeamMember],
        vc_backers: List[str],
        tokenomics: Dict,
        adoption_metrics: Dict,
        competitive_context: Dict,
    ) -> FundamentalScore:
        """
        Analyze fundamental strength of an asset.

        Args:
            asset: Asset symbol (e.g., 'TOKEN')
            team_members: List of team member info
            vc_backers: List of known VC backers
            tokenomics: Dict with 'total_supply', 'circulating', 'vesting_schedule', 'distribution'
            adoption_metrics: Dict with 'users', 'tvl', 'transaction_volume', 'growth_rate'
            competitive_context: Dict with market position, alternatives, differentiation

        Returns:
            FundamentalScore with detailed analysis
        """

        score = FundamentalScore(
            asset=asset,
            timestamp=str(__import__('datetime').datetime.now()),
            team_quality=self._score_team(team_members),
            investor_quality=self._score_investors(vc_backers),
            tokenomics_health=self._score_tokenomics(tokenomics),
            adoption_metrics=self._score_adoption(adoption_metrics),
            competitive_advantage=self._score_competition(competitive_context),
            team_members=team_members,
            vc_backers=vc_backers,
            vc_tier=self._classify_vc_tier(vc_backers),
        )

        # Populate details
        score.tokenomics_issues = self._identify_tokenomics_issues(tokenomics)
        score.adoption_signals = self._identify_adoption_signals(adoption_metrics)
        score.competitive_advantages = self._identify_competitive_advantages(competitive_context)

        # Calculate composite score
        score.overall_fundamental_score = self._calculate_composite_score(score)

        # Identify red flags
        score.red_flags = self._identify_red_flags(score)

        # Store result
        self.results[asset] = score

        return score

    def _score_team(self, team_members: List[TeamMember]) -> float:
        """
        Score team quality 0-100.

        Considers:
        - Team size and diversity
        - Prior successful exits
        - Relevant expertise
        - GitHub activity (for technical projects)
        """
        if not team_members:
            return 0.0

        # Founder score
        founders = [m for m in team_members if m.is_founder]
        founder_score = min(100, len(founders) * 15 + sum(
            m.expertise_relevance * 20 for m in founders
        ) / max(1, len(founders)))

        # Team experience (prior successful projects)
        experience_score = min(100, sum(
            m.expertise_relevance * 20 for m in team_members
        ) / max(1, len(team_members)))

        # Team diversity (roles)
        roles = set(m.role for m in team_members)
        diversity_score = min(100, len(roles) * 15)

        # Developer activity (for technical projects)
        dev_members = [m for m in team_members if 'dev' in m.role.lower() or 'cto' in m.role.lower()]
        dev_score = min(100, sum(
            (m.github_activity or 0) / 100 * 50 for m in dev_members
        )) if dev_members else 50.0

        # Composite team score
        team_score = (
            founder_score * 0.35 +
            experience_score * 0.30 +
            diversity_score * 0.20 +
            dev_score * 0.15
        )

        return min(100, team_score)

    def _score_investors(self, vc_backers: List[str]) -> float:
        """
        Score investor quality 0-100.

        Tier-1 VCs: Sequoia, a16z, Pantera, Paradigm, Polychain
        Tier-2: Strong regional or specialized VCs
        Tier-3: Emerging, micro-cap VCs
        """
        if not vc_backers:
            return 30.0  # No VC backing is concerning

        tier_1_vcs = {
            'Sequoia', 'a16z', 'Andreessen Horowitz',
            'Pantera', 'Paradigm', 'Polychain',
            'Benchmark', 'Lightspeed Venture',
            'Khosla Ventures', 'Galaxy Digital'
        }

        tier_2_vcs = {
            'Coinbase Ventures', 'Crypto.com Capital',
            'Electric Capital', 'Dragonfly Capital',
            'Lerer Hippeau', 'Greycroft'
        }

        tier_1_count = sum(1 for backer in vc_backers if backer in tier_1_vcs)
        tier_2_count = sum(1 for backer in vc_backers if backer in tier_2_vcs)
        other_count = len(vc_backers) - tier_1_count - tier_2_count

        investor_score = (
            tier_1_count * 25 +
            tier_2_count * 15 +
            other_count * 5
        )

        # Diversity bonus (multiple investors)
        diversity_bonus = min(20, len(vc_backers) * 2)

        return min(100, investor_score + diversity_bonus)

    def _score_tokenomics(self, tokenomics: Dict) -> float:
        """
        Score tokenomics health 0-100.

        Red flags:
        - High monthly unlock rate
        - Concentrated distribution
        - Founder token lock-up concerns
        """
        score = 75.0  # Start at reasonable baseline

        # Check vesting schedule (should be smooth, not cliff-based)
        vesting = tokenomics.get('vesting_schedule', {})
        cliff_months = vesting.get('cliff_months', 0)
        if cliff_months > 6:
            score -= 15  # Cliff-based vesting is risky

        max_unlock_rate = vesting.get('max_monthly_unlock', 0)
        if max_unlock_rate > self.TOKENOMICS_THRESHOLDS['max_unlock_per_month']:
            score -= min(20, (max_unlock_rate - 0.10) / 0.10 * 20)

        # Check distribution
        distribution = tokenomics.get('distribution', {})
        founder_pct = distribution.get('founder_team', 0)
        if founder_pct > self.TOKENOMICS_THRESHOLDS['founder_concentration']:
            score -= min(15, (founder_pct - 0.25) * 100)

        # Circulating supply ratio
        total = tokenomics.get('total_supply', 1)
        circulating = tokenomics.get('circulating_supply', total)
        if total > 0:
            circ_ratio = circulating / total
            if circ_ratio < 0.10:
                score -= 20  # Very low circulation is concerning

        return max(0, min(100, score))

    def _score_adoption(self, adoption_metrics: Dict) -> float:
        """
        Score adoption metrics 0-100.

        Considers:
        - User growth rate
        - Total active users
        - TVL (for DeFi)
        - Transaction volume
        - Adoption velocity
        """
        score = 50.0  # Start at neutral

        # User growth
        users = adoption_metrics.get('users', 0)
        if users > 1000000:
            score += 20
        elif users > 100000:
            score += 15
        elif users > 10000:
            score += 10
        elif users > 1000:
            score += 5

        # Growth rate (month-over-month)
        growth_rate = adoption_metrics.get('growth_rate', 0)
        if growth_rate > 0.50:
            score += min(20, growth_rate * 20)  # 50%+ growth is very strong
        elif growth_rate > 0.20:
            score += 10
        elif growth_rate > 0.10:
            score += 5
        elif growth_rate < 0:
            score -= 10  # Negative growth is bad

        # TVL for DeFi projects
        tvl = adoption_metrics.get('tvl', 0)
        if tvl > 1000000000:  # > $1B
            score += 15
        elif tvl > 100000000:  # > $100M
            score += 10
        elif tvl > 10000000:  # > $10M
            score += 5

        # Transaction volume
        volume = adoption_metrics.get('transaction_volume', 0)
        if volume > 100000000:  # > $100M daily
            score += 10
        elif volume > 10000000:  # > $10M daily
            score += 5

        return min(100, score)

    def _score_competition(self, competitive_context: Dict) -> float:
        """
        Score competitive advantage 0-100.

        Evaluates:
        - Market differentiation
        - Unique technology/approach
        - Market share in category
        - Barriers to entry
        """
        score = 50.0

        # Differentiation
        differentiation = competitive_context.get('differentiation', 0)
        score += differentiation * 30  # 0-30 points

        # Market leadership
        market_position = competitive_context.get('market_position', 0)
        if market_position > 0.30:  # Top 3 in category
            score += 20
        elif market_position > 0.10:  # Top 10
            score += 10
        elif market_position > 0:
            score += 5

        # Technology moat
        has_moat = competitive_context.get('has_technology_moat', False)
        if has_moat:
            score += 15

        # Adoption advantage
        adoption_lead = competitive_context.get('adoption_lead_months', 0)
        if adoption_lead > 12:
            score += 10
        elif adoption_lead > 6:
            score += 5

        return min(100, score)

    def _calculate_composite_score(self, score: FundamentalScore) -> float:
        """
        Calculate overall fundamental score.

        Weighting:
        - Team Quality: 30%
        - Investor Quality: 25%
        - Tokenomics: 20%
        - Adoption: 15%
        - Competition: 10%
        """
        composite = (
            score.team_quality * 0.30 +
            score.investor_quality * 0.25 +
            score.tokenomics_health * 0.20 +
            score.adoption_metrics * 0.15 +
            score.competitive_advantage * 0.10
        )

        return min(100, composite)

    def _classify_vc_tier(self, vc_backers: List[str]) -> VCTier:
        """Classify VC backing tier."""
        tier_1 = {'Sequoia', 'a16z', 'Pantera', 'Paradigm', 'Polychain'}
        if any(backer in tier_1 for backer in vc_backers):
            return VCTier.TIER_1
        elif len(vc_backers) > 2:
            return VCTier.TIER_2
        elif len(vc_backers) > 0:
            return VCTier.TIER_3
        else:
            return VCTier.NONE

    def _identify_tokenomics_issues(self, tokenomics: Dict) -> List[str]:
        """Identify tokenomics red flags."""
        issues = []

        max_unlock = tokenomics.get('vesting_schedule', {}).get('max_monthly_unlock', 0)
        if max_unlock > 0.20:
            issues.append(f"High monthly unlock rate: {max_unlock:.1%}")

        founder_pct = tokenomics.get('distribution', {}).get('founder_team', 0)
        if founder_pct > 0.30:
            issues.append(f"High founder concentration: {founder_pct:.1%}")

        cliff = tokenomics.get('vesting_schedule', {}).get('cliff_months', 0)
        if cliff > 12:
            issues.append(f"Long vesting cliff: {cliff} months")

        return issues

    def _identify_adoption_signals(self, adoption_metrics: Dict) -> List[str]:
        """Identify positive adoption signals."""
        signals = []

        growth = adoption_metrics.get('growth_rate', 0)
        if growth > 0.50:
            signals.append(f"Strong adoption growth: {growth:.0%} MoM")

        users = adoption_metrics.get('users', 0)
        if users > 1000000:
            signals.append(f"Large user base: {users:,.0f} users")

        tvl = adoption_metrics.get('tvl', 0)
        if tvl > 100000000:
            signals.append(f"Significant TVL: ${tvl/1e9:.1f}B")

        return signals

    def _identify_competitive_advantages(self, competitive_context: Dict) -> List[str]:
        """Identify competitive strengths."""
        advantages = []

        diff = competitive_context.get('differentiation', 0)
        if diff > 0.6:
            advantages.append("Clear technical differentiation")

        if competitive_context.get('has_technology_moat', False):
            advantages.append("Strong technology moat")

        position = competitive_context.get('market_position', 0)
        if position > 0.20:
            advantages.append(f"Strong market position: {position:.0%} of category")

        return advantages

    def _identify_red_flags(self, score: FundamentalScore) -> List[str]:
        """Identify critical red flags."""
        flags = []

        if score.team_quality < 40:
            flags.append("Weak team quality or unknown founders")

        if score.investor_quality < 30 and score.vc_tier == VCTier.NONE:
            flags.append("No known VC backing")

        if score.tokenomics_health < 40:
            flags.append("Critical tokenomics issues")

        if score.adoption_metrics < 30:
            flags.append("Very low adoption metrics")

        flags.extend(score.tokenomics_issues)

        return flags

    def get_report(self, asset: str) -> Optional[str]:
        """Generate human-readable fundamental analysis report."""
        if asset not in self.results:
            return None

        score = self.results[asset]

        report = f"""
╔════════════════════════════════════════════════════════════╗
║         FUNDAMENTAL ANALYSIS REPORT                        ║
║         Asset: {asset}
╚════════════════════════════════════════════════════════════╝

OVERALL FUNDAMENTAL SCORE: {score.overall_fundamental_score:.1f}/100
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Component Scores:
  • Team Quality: {score.team_quality:.1f}/100
  • Investor Quality: {score.investor_quality:.1f}/100
  • Tokenomics Health: {score.tokenomics_health:.1f}/100
  • Adoption Metrics: {score.adoption_metrics:.1f}/100
  • Competitive Advantage: {score.competitive_advantage:.1f}/100

VC Backing Tier: {score.vc_tier.value}

Team ({len(score.team_members)} members):
"""
        for member in score.team_members:
            report += f"  • {member.name} ({member.role})\n"

        if score.tokenomics_issues:
            report += f"\nTokenomics Concerns:\n"
            for issue in score.tokenomics_issues:
                report += f"  ⚠ {issue}\n"

        if score.adoption_signals:
            report += f"\nAdoption Signals:\n"
            for signal in score.adoption_signals:
                report += f"  ✓ {signal}\n"

        if score.competitive_advantages:
            report += f"\nCompetitive Advantages:\n"
            for adv in score.competitive_advantages:
                report += f"  ★ {adv}\n"

        if score.red_flags:
            report += f"\nRed Flags:\n"
            for flag in score.red_flags:
                report += f"  ✗ {flag}\n"

        return report

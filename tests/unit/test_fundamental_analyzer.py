"""
Unit tests for Fundamental Analyzer (Phase 4 Component 1).
"""

import pytest
from src.layers.layer4_x20.fundamental_analyzer import (
    FundamentalAnalyzer,
    FundamentalScore,
    TeamMember,
    VCTier,
    TokenomicsHealth,
)


class TestFundamentalAnalyzer:
    """Tests for FundamentalAnalyzer class."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return FundamentalAnalyzer()

    @pytest.fixture
    def strong_team(self):
        """Create a strong team."""
        return [
            TeamMember(
                name="Alice Smith",
                role="CEO",
                prior_experience="Founded 2 successful startups",
                expertise_relevance=0.95,
                is_founder=True,
            ),
            TeamMember(
                name="Bob Johnson",
                role="CTO",
                prior_experience="Ex-Google engineer, 8 years experience",
                github_activity=50.0,
                expertise_relevance=0.9,
                is_founder=True,
            ),
            TeamMember(
                name="Carol White",
                role="Head of Product",
                prior_experience="Ex-Facebook product manager",
                expertise_relevance=0.85,
            ),
        ]

    def test_analyzer_creation(self, analyzer):
        """Test analyzer instantiation."""
        assert analyzer is not None
        assert len(analyzer.results) == 0

    def test_team_scoring(self, analyzer, strong_team):
        """Test team quality scoring."""
        team_score = analyzer._score_team(strong_team)

        assert 0 <= team_score <= 100
        assert team_score > 30  # Strong team should score reasonably

    def test_empty_team_scoring(self, analyzer):
        """Test scoring with no team."""
        score = analyzer._score_team([])
        assert score == 0.0

    def test_investor_scoring_tier1(self, analyzer):
        """Test investor scoring with Tier-1 VCs."""
        vc_backers = ['Sequoia', 'a16z', 'Pantera']
        score = analyzer._score_investors(vc_backers)

        assert score > 70

    def test_investor_scoring_no_vc(self, analyzer):
        """Test scoring with no VC backing."""
        score = analyzer._score_investors([])
        assert score == 30.0  # Baseline for no backing

    def test_tokenomics_scoring_healthy(self, analyzer):
        """Test tokenomics scoring for healthy structure."""
        tokenomics = {
            'total_supply': 1000000000,
            'circulating_supply': 400000000,
            'vesting_schedule': {
                'cliff_months': 3,
                'max_monthly_unlock': 0.05,
            },
            'distribution': {
                'founder_team': 0.20,
                'vc': 0.15,
                'public': 0.65,
            },
        }

        score = analyzer._score_tokenomics(tokenomics)
        assert score > 60  # Should be reasonable

    def test_tokenomics_scoring_poor(self, analyzer):
        """Test tokenomics scoring for poor structure."""
        tokenomics = {
            'total_supply': 1000000000,
            'circulating_supply': 50000000,  # Only 5% circulating
            'vesting_schedule': {
                'cliff_months': 24,
                'max_monthly_unlock': 0.30,  # 30% per month
            },
            'distribution': {
                'founder_team': 0.50,  # High founder concentration
                'vc': 0.30,
                'public': 0.20,
            },
        }

        score = analyzer._score_tokenomics(tokenomics)
        assert score < 50  # Should be concerning

    def test_adoption_scoring_strong(self, analyzer):
        """Test adoption scoring for strong metrics."""
        adoption = {
            'users': 5000000,
            'growth_rate': 0.75,  # 75% MoM
            'tvl': 500000000,  # $500M
            'transaction_volume': 200000000,  # $200M daily
        }

        score = analyzer._score_adoption(adoption)
        assert score > 75

    def test_adoption_scoring_weak(self, analyzer):
        """Test adoption scoring for weak metrics."""
        adoption = {
            'users': 100,
            'growth_rate': -0.10,  # Negative growth
            'tvl': 0,
            'transaction_volume': 0,
        }

        score = analyzer._score_adoption(adoption)
        assert score < 50

    def test_competition_scoring(self, analyzer):
        """Test competitive advantage scoring."""
        context = {
            'differentiation': 0.8,
            'market_position': 0.25,
            'has_technology_moat': True,
            'adoption_lead_months': 18,
        }

        score = analyzer._score_competition(context)
        assert score > 70

    def test_vc_tier_classification(self, analyzer):
        """Test VC tier classification."""
        tier1 = analyzer._classify_vc_tier(['Sequoia'])
        assert tier1 == VCTier.TIER_1

        tier2 = analyzer._classify_vc_tier(['UnknownVC1', 'UnknownVC2', 'UnknownVC3'])
        assert tier2 == VCTier.TIER_2

        none_tier = analyzer._classify_vc_tier([])
        assert none_tier == VCTier.NONE

    def test_tokenomics_issues_detection(self, analyzer):
        """Test tokenomics red flag detection."""
        tokenomics = {
            'vesting_schedule': {
                'cliff_months': 15,
                'max_monthly_unlock': 0.25,
            },
            'distribution': {
                'founder_team': 0.35,
            },
        }

        issues = analyzer._identify_tokenomics_issues(tokenomics)
        assert len(issues) > 0
        assert any('unlock' in issue.lower() for issue in issues)

    def test_adoption_signals_detection(self, analyzer):
        """Test adoption signal detection."""
        adoption = {
            'growth_rate': 0.75,
            'users': 2000000,
            'tvl': 250000000,
        }

        signals = analyzer._identify_adoption_signals(adoption)
        assert len(signals) > 0
        assert any('adoption' in signal.lower() for signal in signals)

    def test_red_flag_identification(self, analyzer, strong_team):
        """Test red flag identification."""
        score = FundamentalScore(
            asset='TEST',
            timestamp='2026-09-30',
            team_quality=35.0,  # Low
            investor_quality=20.0,  # Very low
            tokenomics_health=30.0,  # Poor
            adoption_metrics=20.0,  # Very weak
            competitive_advantage=40.0,
        )

        flags = analyzer._identify_red_flags(score)
        assert len(flags) > 0

    def test_full_analysis(self, analyzer, strong_team):
        """Test complete asset analysis."""
        result = analyzer.analyze_asset(
            asset='STRONG_TOKEN',
            team_members=strong_team,
            vc_backers=['Sequoia', 'a16z'],
            tokenomics={
                'total_supply': 1000000000,
                'circulating_supply': 400000000,
                'vesting_schedule': {
                    'cliff_months': 3,
                    'max_monthly_unlock': 0.05,
                },
                'distribution': {
                    'founder_team': 0.20,
                    'vc': 0.15,
                    'public': 0.65,
                },
            },
            adoption_metrics={
                'users': 1000000,
                'growth_rate': 0.50,
                'tvl': 100000000,
                'transaction_volume': 50000000,
            },
            competitive_context={
                'differentiation': 0.75,
                'market_position': 0.20,
                'has_technology_moat': True,
                'adoption_lead_months': 12,
            },
        )

        assert result is not None
        assert result.asset == 'STRONG_TOKEN'
        assert result.overall_fundamental_score > 60
        assert not result.is_red_flagged()
        assert 'STRONG_TOKEN' in analyzer.results

    def test_weak_asset_analysis(self, analyzer):
        """Test analysis of weak asset."""
        result = analyzer.analyze_asset(
            asset='WEAK_TOKEN',
            team_members=[
                TeamMember(
                    name='Unknown Dev',
                    role='Developer',
                    prior_experience='Unknown',
                    expertise_relevance=0.1,
                ),
            ],
            vc_backers=[],
            tokenomics={
                'total_supply': 1000000000,
                'circulating_supply': 10000000,  # Only 1% circulating
                'vesting_schedule': {
                    'cliff_months': 12,
                    'max_monthly_unlock': 0.20,
                },
                'distribution': {
                    'founder_team': 0.50,
                    'vc': 0.30,
                    'public': 0.20,
                },
            },
            adoption_metrics={
                'users': 100,
                'growth_rate': -0.10,
                'tvl': 0,
                'transaction_volume': 0,
            },
            competitive_context={
                'differentiation': 0.1,
                'market_position': 0.01,
                'has_technology_moat': False,
                'adoption_lead_months': 0,
            },
        )

        assert result.overall_fundamental_score < 40
        assert result.is_red_flagged()

    def test_report_generation(self, analyzer, strong_team):
        """Test report generation."""
        analyzer.analyze_asset(
            asset='REPORT_TEST',
            team_members=strong_team,
            vc_backers=['Sequoia'],
            tokenomics={
                'total_supply': 1000000000,
                'circulating_supply': 400000000,
                'vesting_schedule': {
                    'cliff_months': 3,
                    'max_monthly_unlock': 0.05,
                },
                'distribution': {
                    'founder_team': 0.20,
                    'vc': 0.15,
                    'public': 0.65,
                },
            },
            adoption_metrics={
                'users': 500000,
                'growth_rate': 0.40,
                'tvl': 50000000,
                'transaction_volume': 25000000,
            },
            competitive_context={
                'differentiation': 0.60,
                'market_position': 0.15,
                'has_technology_moat': True,
                'adoption_lead_months': 10,
            },
        )

        report = analyzer.get_report('REPORT_TEST')
        assert report is not None
        assert 'REPORT_TEST' in report
        assert 'FUNDAMENTAL ANALYSIS' in report
        assert 'Team Quality' in report

    def test_no_report_for_unknown_asset(self, analyzer):
        """Test that report returns None for unknown asset."""
        report = analyzer.get_report('UNKNOWN')
        assert report is None

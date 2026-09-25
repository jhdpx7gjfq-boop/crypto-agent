"""Tests for IGWT-PF26 Dashboard module."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_dashboard_module_exists():
    """Verify dashboard module structure."""
    from src.dashboard import __init__ as dashboard_init
    assert dashboard_init is not None


def test_dashboard_imports():
    """Test that dashboard can import required modules."""
    # Test basic imports without running Streamlit
    try:
        from src.data.coingecko_collector import CoinGeckoCollector
        from src.data.feature_store import FeatureStore
        from src.analysis.wyckoff_bce import WyckoffBCE
        from src.analysis.x20_engine import X20Engine
        from src.analysis.narm_p_plus import NARMPPlus
        from src.analysis.rcm_rpm_engine import RCMRPMEngine
        from src.analysis.rrp_revival_radar import RRPRevivalRadar

        # Verify modules can be instantiated
        assert CoinGeckoCollector() is not None
        assert WyckoffBCE() is not None
        assert X20Engine() is not None
        assert NARMPPlus() is not None
        assert RCMRPMEngine() is not None
        assert RRPRevivalRadar() is not None

    except ImportError as e:
        assert False, f"Failed to import dashboard dependencies: {e}"


def test_dashboard_file_structure():
    """Verify dashboard file exists and is properly structured."""
    dashboard_path = Path(__file__).parent.parent / "src" / "dashboard" / "app.py"
    assert dashboard_path.exists(), "Dashboard app.py not found"

    # Read and verify basic content
    content = dashboard_path.read_text()
    assert "streamlit" in content.lower()
    assert "IGWT-PF26" in content
    assert "version" in content.lower() or "VERSION" in content


def test_dashboard_analysis_modes():
    """Verify dashboard supports all required analysis modes."""
    dashboard_path = Path(__file__).parent.parent / "src" / "dashboard" / "app.py"
    content = dashboard_path.read_text()

    required_modes = [
        "Multi-Coin Overview",
        "Single Coin Deep Dive",
        "Revival Radar",
        "Rotation Tracker",
    ]

    for mode in required_modes:
        assert mode in content, f"Missing analysis mode: {mode}"


def test_requirements_updated():
    """Verify requirements.txt includes dashboard dependencies."""
    requirements_path = Path(__file__).parent.parent / "requirements.txt"
    content = requirements_path.read_text()

    assert "streamlit" in content.lower()


if __name__ == "__main__":
    test_dashboard_module_exists()
    test_dashboard_imports()
    test_dashboard_file_structure()
    test_dashboard_analysis_modes()
    test_requirements_updated()
    print("✓ All dashboard tests passed")

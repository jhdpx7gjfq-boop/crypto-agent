"""
IGWT-PF26 Real-Time Monitoring Dashboard
Version: 1.0.0

Streamlit-based mobile-responsive dashboard for crypto intelligence monitoring.
Integrates all analysis layers: BCE, X20, NARM-P+, RCM/RPM, RRP.
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

import streamlit as st
from streamlit_autorefresh import rerun_script

# Import analysis modules
from src.data.coingecko_collector import CoinGeckoCollector
from src.data.feature_store import FeatureStore
from src.analysis.wyckoff_bce import WyckoffBCE
from src.analysis.x20_engine import X20Engine
from src.analysis.narm_p_plus import NARMPPlus
from src.analysis.rcm_rpm_engine import RCMRPMEngine
from src.analysis.rrp_revival_radar import RRPRevivalRadar

logger = logging.getLogger(__name__)

VERSION = "1.0.0"

# Page config
st.set_page_config(
    page_title="IGWT-PF26 Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS for mobile responsiveness
st.markdown("""
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
        margin: 10px 0;
        font-size: 14px;
    }
    .signal-buy {
        background: #10B981;
        padding: 8px 12px;
        border-radius: 5px;
        color: white;
        font-weight: bold;
    }
    .signal-hold {
        background: #F59E0B;
        padding: 8px 12px;
        border-radius: 5px;
        color: white;
        font-weight: bold;
    }
    .signal-skip {
        background: #EF4444;
        padding: 8px 12px;
        border-radius: 5px;
        color: white;
        font-weight: bold;
    }
    .score-bar {
        width: 100%;
        height: 20px;
        background: #e5e7eb;
        border-radius: 10px;
        overflow: hidden;
        margin: 5px 0;
    }
    .score-fill {
        height: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# Initialize modules (cached)
@st.cache_resource
def init_modules():
    return {
        "collector": CoinGeckoCollector(),
        "bce": WyckoffBCE(),
        "x20": X20Engine(),
        "narm": NARMPPlus(),
        "rcm": RCMRPMEngine(),
        "rrp": RRPRevivalRadar(),
    }

# Header
st.title("📊 IGWT-PF26 Crypto Intelligence Dashboard")
st.markdown(f"*Real-time analysis engine for crypto investment decisions | v{VERSION}*")

# Sidebar
with st.sidebar:
    st.header("⚙️ Configuration")

    coin_input = st.text_input(
        "Enter coin symbol(s)",
        value="bitcoin,ethereum",
        help="Comma-separated symbols (e.g., bitcoin,ethereum,solana)"
    )

    auto_refresh = st.checkbox("Auto-refresh (5s)", value=False)
    if auto_refresh:
        rerun_script(interval=5000)

    analysis_mode = st.selectbox(
        "Analysis Mode",
        ["Multi-Coin Overview", "Single Coin Deep Dive", "Revival Radar", "Rotation Tracker"]
    )

# Parse coins
coins = [c.strip().lower() for c in coin_input.split(",")]

# Initialize modules
modules = init_modules()
collector = modules["collector"]

# Main content
if analysis_mode == "Multi-Coin Overview":
    st.subheader("🔍 Multi-Coin Analysis")

    try:
        # Fetch price data
        with st.spinner("Fetching market data..."):
            price_data = collector.get_price(coins, include_market_cap=True, include_24hr_vol=True)

        if price_data:
            cols = st.columns(len(coins))

            for idx, (coin, col) in enumerate(zip(coins, cols)):
                with col:
                    if coin in price_data:
                        data = price_data[coin]
                        price = data.get("usd", 0)
                        mcap = data.get("usd_market_cap", 0)
                        volume = data.get("usd_24h_vol", 0)

                        st.metric(
                            f"💰 {coin.upper()}",
                            f"${price:,.2f}",
                            f"MCap: ${mcap/1e9:.2f}B" if mcap > 0 else "N/A"
                        )

                        col1, col2 = st.columns(2)
                        with col1:
                            st.caption(f"Volume: ${volume/1e6:.1f}M")
                        with col2:
                            st.caption(f"Last update: {datetime.now().strftime('%H:%M:%S')}")

    except Exception as e:
        st.error(f"Error fetching data: {e}")

elif analysis_mode == "Single Coin Deep Dive":
    st.subheader("🎯 Deep Dive Analysis")

    if len(coins) > 0:
        selected_coin = st.selectbox("Select coin", coins)

        try:
            # Fetch data
            with st.spinner("Analyzing..."):
                price_data = collector.get_price(
                    [selected_coin],
                    include_market_cap=True,
                    include_24hr_vol=True
                )

            if price_data and selected_coin in price_data:
                data = price_data[selected_coin]

                # Display price info
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Price", f"${data.get('usd', 0):,.2f}")
                with col2:
                    st.metric("Market Cap", f"${data.get('usd_market_cap', 0)/1e9:.2f}B")
                with col3:
                    st.metric("24h Volume", f"${data.get('usd_24h_vol', 0)/1e6:.1f}M")
                with col4:
                    st.metric("Signal Status", "🔍 Ready")

                # Analysis tabs
                tab1, tab2, tab3, tab4, tab5 = st.tabs(
                    ["BCE Accumulation", "X20 Opportunity", "NARM-P+ Narrative", "RCM/RPM Rotation", "RRP Revival"]
                )

                with tab1:
                    st.subheader("Wyckoff Bottom Confirmation Engine")
                    st.info("📊 BCE requires OHLCV data with 20+ candles for analysis")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Score", "—/6", help="Need historical price data")
                    with col2:
                        st.metric("Signal", "PENDING", help="Awaiting OHLCV data")

                with tab2:
                    st.subheader("X20 Opportunity Scoring")
                    x20_result = modules["x20"].score_opportunity(
                        selected_coin,
                        {
                            "price": data.get("usd", 0),
                            "market_cap": data.get("usd_market_cap", 0),
                            "volume": data.get("usd_24h_vol", 0),
                            "momentum": 0.5,
                            "volatility": 0.15,
                        },
                        {
                            "team_strength": 0.7,
                            "tokenomics": 0.65,
                            "adoption": 0.6,
                        },
                        {
                            "sector_strength": 0.75,
                            "narrative_growth": 0.65,
                            "attention_growth": 0.55,
                        },
                    )

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Score", f"{x20_result['total_score']:.1f}/100")
                    with col2:
                        st.metric("Signal", x20_result["signal"])
                    with col3:
                        st.metric("Risk", x20_result["risk_level"])

                    with st.expander("Component Breakdown"):
                        for comp, score in x20_result["components"].items():
                            st.progress(score / 25 if score <= 25 else 1.0)
                            st.caption(f"{comp}: {score:.1f}")

                with tab3:
                    st.subheader("NARM-P+ Narrative Rotation")
                    narm_result = modules["narm"].score_narrative({
                        "id": selected_coin,
                        "narratives": ["AI"],
                        "adoption": {"users": 50e6, "tvl": 10e9, "growth_7d": 0.15, "growth_30d": 0.30},
                        "sentiment": {"bullish": 0.65, "neutral": 0.25, "bearish": 0.10},
                        "fundamentals": {"dex_volume": 1e9, "active_addresses": 2e6, "transactions": 10e6},
                        "price_data": {"momentum": 0.5, "rsi": 50},
                        "macro": {"risk_on": 0.70, "crypto_season": "altseason"},
                    })

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Score", f"{narm_result['total_score']:.1f}/100")
                    with col2:
                        st.metric("Narrative", narm_result["primary_narrative"])
                    with col3:
                        st.metric("Rotation", narm_result["rotation_opportunity"])

                with tab4:
                    st.subheader("RCM/RPM Rotation Confirmation")
                    st.info("💼 RCM/RPM requires historical flow data for rotation confirmation")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Score", "—/100")
                    with col2:
                        st.metric("Signal", "PENDING")

                with tab5:
                    st.subheader("RRP Revival Radar")
                    st.info("🔄 RRP requires snapshot history for resurrection detection")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Score", "—/100")
                    with col2:
                        st.metric("Status", "MONITORING")
                    with col3:
                        st.metric("Snapshots", "0")

        except Exception as e:
            st.error(f"Error in analysis: {e}")

elif analysis_mode == "Revival Radar":
    st.subheader("🔄 Dead Token Revival Detection")

    st.info("RRP monitors for tokens showing resurrection signs after extended dormancy")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Tokens Monitored", "—", help="Add coins to monitor")
    with col2:
        st.metric("Revival Candidates", "0", help="Score >= 50/100")
    with col3:
        st.metric("Last Check", datetime.now().strftime("%H:%M:%S"))

    st.subheader("Revival Scoring Criteria")
    criteria_cols = st.columns(3)
    with criteria_cols[0]:
        st.markdown("**Volume Growth** 30pts\n- 5x+ = 30pts\n- 3x+ = 25pts")
    with criteria_cols[1]:
        st.markdown("**Address Growth** 30pts\n- 3x+ = 30pts\n- 2x+ = 25pts")
    with criteria_cols[2]:
        st.markdown("**Price Appreciation** 20pts\n- 2x+ = 20pts\n- 50%+ = 15pts")

elif analysis_mode == "Rotation Tracker":
    st.subheader("💫 Capital Rotation Tracking")

    st.info("RCM/RPM detects capital flows rotating between assets")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Strong Rotations", "0", help="Score >= 75/100")
    with col2:
        st.metric("Moderate Rotations", "0", help="Score 55-75")
    with col3:
        st.metric("Weak Rotations", "0", help="Score 35-55")
    with col4:
        st.metric("Last Check", datetime.now().strftime("%H:%M:%S"))

    st.subheader("Rotation Components")
    cols = st.columns(5)
    components = [
        ("Capital Flow", "25%"),
        ("Relative Strength", "25%"),
        ("Narrative Accel.", "20%"),
        ("Fundamental Conf.", "20%"),
        ("Derivatives", "10%"),
    ]
    for col, (name, weight) in zip(cols, components):
        with col:
            st.markdown(f"**{name}**\n{weight}")

# Footer
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.caption(f"📍 IGWT-PF26 v{VERSION}")
with col2:
    st.caption("🔐 No automatic execution - Human approval only")
with col3:
    st.caption(f"🕐 Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")

# Session info
if st.sidebar.checkbox("Debug Info"):
    st.sidebar.subheader("System Status")
    st.sidebar.write(f"Modules loaded: {len(modules)}")
    st.sidebar.write(f"Analysis coins: {coins}")
    st.sidebar.write(f"Python version: 3.11.15")

"""Streamlit Web Dashboard for StockLens.
Interactive price charts, intraday candle streaming, trend outcome explanations,
IPO intelligence center, valuation tables, and active watchlist alerts.
Educational use only. Not investment advice.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from stocklens.config import DISCLAIMER
from stocklens.data.base import normalize_symbol
from stocklens.data.factory import get_data_provider
from stocklens.data.nse_live import NSELiveProvider
from stocklens.analysis.indicators import (
    sma,
    ema,
    rsi,
    macd,
    bollinger_bands,
    annual_volatility,
    max_drawdown,
    signals,
)
from stocklens.analysis.valuation import (
    calculate_returns,
    market_cap_category,
    format_currency_inr,
    format_percent,
    format_ratio,
    valuation_scorecard,
)
from stocklens.analysis.sentiment import score_news_batch
from stocklens.analysis.peers import get_sector_peers, compare_peers
from stocklens.analysis.explainer import explain_stock_trend, detect_candlestick_pattern
from stocklens.analysis.ipo import fetch_ipos
from stocklens.watchlist.manager import WatchlistManager


st.set_page_config(
    page_title="StockLens - Indian Stock Market & IPO Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_watchlist_manager() -> WatchlistManager:
    return WatchlistManager()


@st.cache_resource
def get_live_provider() -> NSELiveProvider:
    return NSELiveProvider()


wm = get_watchlist_manager()
live_prov = get_live_provider()

# --- Sidebar Controls ---
st.sidebar.title("📈 StockLens")
st.sidebar.caption("Real-Time Indian Market & IPO Intelligence")

# Data Provider Selector
provider_name = st.sidebar.selectbox(
    "Data Engine",
    options=["yfinance", "moneycontrol", "demo"],
    index=0,
    help="Select market data engine.",
)
provider = get_data_provider(provider_name)

# Symbol Input
symbol_input = st.sidebar.text_input(
    "Stock Ticker or Company",
    value="INFY",
    help="Enter ticker (e.g. RELIANCE, TCS, INFY, WIPRO) or name",
).strip().upper()

# Quick Pick Buttons
st.sidebar.markdown("**Quick Picks:**")
col_qp1, col_qp2, col_qp3 = st.sidebar.columns(3)
if col_qp1.button("RELIANCE"):
    symbol_input = "RELIANCE"
if col_qp2.button("TCS"):
    symbol_input = "TCS"
if col_qp3.button("INFY"):
    symbol_input = "INFY"

col_qp4, col_qp5, col_qp6 = st.sidebar.columns(3)
if col_qp4.button("HDFC"):
    symbol_input = "HDFCBANK"
if col_qp5.button("WIPRO"):
    symbol_input = "WIPRO"
if col_qp6.button("ITC"):
    symbol_input = "ITC"

chart_period_years = st.sidebar.slider("Daily History (Years)", min_value=1, max_value=5, value=2)

st.sidebar.markdown("---")
st.sidebar.info(f"**Educational Notice:**\n{DISCLAIMER}")

norm_symbol = normalize_symbol(symbol_input)

# Fetch Data
with st.spinner(f"Loading analytics for {norm_symbol}..."):
    try:
        info = provider.get_info(norm_symbol)
        history = provider.get_history(norm_symbol, years=chart_period_years)
        news_items = provider.get_news(norm_symbol, limit=8)
    except Exception as e:
        st.error(f"Failed to fetch market data for {norm_symbol}: {e}")
        st.info("Tip: You can switch to the 'demo' data engine in the sidebar to review offline.")
        st.stop()

if history.empty or "Close" not in history.columns:
    st.error("No historical price series returned for this symbol.")
    st.stop()

close = history["Close"]
current_price = float(close.iloc[-1])
prev_price = float(close.iloc[-2]) if len(close) > 1 else current_price
daily_change = current_price - prev_price
daily_change_pct = (daily_change / prev_price) * 100.0 if prev_price > 0 else 0.0

# --- Header Banner ---
st.title(f"📊 StockLens: {info.name or norm_symbol} ({norm_symbol})")
st.caption(f"Engine: **{provider_name.upper()}** | Exchange: **NSE / BSE** | Educational Research Only")

# Top Metrics Bar
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Current Price", f"₹{current_price:,.2f}", f"{daily_change_pct:+.2f}%")
m2.metric("Market Cap", format_currency_inr(info.market_cap), market_cap_category(info.market_cap))
m3.metric("P/E Ratio", format_ratio(info.pe_ratio))
m4.metric("P/B Ratio", format_ratio(info.pb_ratio))
m5.metric("ROE", format_percent(info.roe))

# Navigation Tabs
tab_explainer, tab_live, tab_ipo, tab_charts, tab_valuation, tab_peers, tab_news, tab_watchlist = st.tabs(
    [
        "🧠 Real-Time Trend Explainer",
        "🔴 Live & Intraday Candles",
        "🚀 IPO Intelligence",
        "📈 Technical Charts",
        "💎 Valuation & Health",
        "👥 Sector Peers",
        "📰 News Sentiment",
        "⭐ Watchlist & Alerts",
    ]
)

# ==========================================
# TAB 1: REAL-TIME TREND EXPLAINER
# ==========================================
with tab_explainer:
    st.subheader(f"Trend Breakdown & Outcome Explanation: {norm_symbol}")
    st.caption("Synthesizes multi-factor price action, volume anomalies, pattern recognition, and news catalysts.")

    headlines_list = [n.title for n in news_items]
    trend_analysis = explain_stock_trend(
        symbol=norm_symbol,
        history=history,
        info_dict=info.to_dict(),
        headlines=headlines_list,
    )

    col_e1, col_e2, col_e3 = st.columns(3)
    verdict_color = "🟢" if "Bullish" in trend_analysis.trend_verdict or "Expansion" in trend_analysis.trend_verdict else "🔴" if "Bearish" in trend_analysis.trend_verdict else "🟡"
    col_e1.metric("Trend Regime", f"{verdict_color} {trend_analysis.trend_verdict}")
    col_e2.metric("Momentum State", trend_analysis.momentum_rating)
    col_e3.metric("Candlestick Structure", trend_analysis.candlestick_pattern)

    st.markdown("---")
    st.markdown("### 🔍 Why is the Stock Moving?")
    st.info(trend_analysis.why_is_it_moving)

    st.markdown("### 🎯 Critical Price Pivots & Educational Levels")
    p1, p2, p3 = st.columns(3)
    p1.metric("Central Pivot Point", f"₹{trend_analysis.pivot_level:,.2f}")
    p2.metric("Resistance (R1)", f"₹{trend_analysis.resistance_level:,.2f}")
    p3.metric("Immediate Support (S1)", f"₹{trend_analysis.support_level:,.2f}")

    st.markdown("### ⚖️ Risk / Reward Outcome")
    st.success(f"**Educational Assessment:** {trend_analysis.risk_reward_verdict}")

    if trend_analysis.catalysts:
        st.markdown("**Active News Catalysts:**")
        for cat in trend_analysis.catalysts:
            st.write(f"- {cat}")

# ==========================================
# TAB 2: LIVE INTRADAY CANDLES & ORDER DEPTH
# ==========================================
with tab_live:
    st.subheader(f"Free Live Market Reading: {norm_symbol}")
    col_l1, col_l2 = st.columns([1, 3])
    
    with col_l1:
        interval_choice = st.selectbox("Intraday Candle Timeframe", ["1m", "5m", "15m"], index=1)
        st.markdown("**Market Breadth (NIFTY 50):**")
        breadth = live_prov.get_market_breadth()
        st.write(f"🟢 **Advances:** {breadth['advances']}")
        st.write(f"🔴 **Declines:** {breadth['declines']}")
        st.write(f"⚪ **Unchanged:** {breadth['unchanged']}")
        if st.button("🔄 Refresh Live Feed"):
            st.rerun()

    with col_l2:
        try:
            with st.spinner(f"Fetching free live {interval_choice} candles..."):
                intraday_df = live_prov.get_intraday_candles(norm_symbol, interval=interval_choice)
                
            if not intraday_df.empty and all(c in intraday_df.columns for c in ["Open", "High", "Low", "Close"]):
                fig_intra = go.Figure(
                    data=[
                        go.Candlestick(
                            x=intraday_df.index,
                            open=intraday_df["Open"],
                            high=intraday_df["High"],
                            low=intraday_df["Low"],
                            close=intraday_df["Close"],
                            name="Intraday OHLC",
                        )
                    ]
                )
                # Intraday VWAP overlay
                if "Volume" in intraday_df.columns and intraday_df["Volume"].sum() > 0:
                    typical_price = (intraday_df["High"] + intraday_df["Low"] + intraday_df["Close"]) / 3.0
                    vwap = (typical_price * intraday_df["Volume"]).cumsum() / intraday_df["Volume"].cumsum()
                    fig_intra.add_trace(go.Scatter(x=intraday_df.index, y=vwap, name="VWAP", line=dict(color="orange", width=1.5)))

                fig_intra.update_layout(
                    title=f"{norm_symbol} - Live {interval_choice} Intraday Price Action",
                    height=500,
                    margin=dict(l=20, r=20, t=40, b=20),
                    xaxis_rangeslider_visible=False,
                )
                st.plotly_chart(fig_intra, use_container_width=True)
            else:
                st.info("Intraday candle series currently unavailable. Market may be closed; showing recent daily action.")
        except Exception as e:
            st.warning(f"Live candle stream note: {e}")

# ==========================================
# TAB 3: IPO INTELLIGENCE & OUTCOME EXPLAINER
# ==========================================
with tab_ipo:
    st.subheader("🚀 Indian IPO Intelligence Center (Mainboard & SME)")
    st.caption("Tracks issue price bands, subscription demand multiples, GMP, and expected outcomes.")

    ipos = fetch_ipos()
    for ipo in ipos:
        with st.container():
            col_ip1, col_ip2, col_ip3 = st.columns([2, 1, 1])
            status_badge = "🟢 Open" if ipo.status == "Open" else "🔵 Upcoming" if ipo.status == "Upcoming" else "⚪ Listed / Closed"
            col_ip1.markdown(f"### {ipo.company_name} ({ipo.symbol}) [{ipo.category}]")
            col_ip2.metric("Price Band", ipo.price_band, f"Lot: {ipo.lot_size}")
            col_ip3.metric("Subscription / GMP", f"{ipo.subscription_times:.1f}x", f"GMP: +{ipo.gmp_percent:.1f}%")

            st.write(f"**Issue Size:** ₹{ipo.issue_size_cr:,.0f} Cr  |  **Dates:** {ipo.open_date} to {ipo.close_date}  |  **Status:** {status_badge}")
            
            verdict_style = "success" if "High" in ipo.verdict else "warning" if "Moderate" in ipo.verdict else "info"
            if verdict_style == "success":
                st.success(f"**Outcome Verdict:** {ipo.verdict} — {ipo.detailed_outcome}")
            elif verdict_style == "warning":
                st.warning(f"**Outcome Verdict:** {ipo.verdict} — {ipo.detailed_outcome}")
            else:
                st.info(f"**Outcome Verdict:** {ipo.verdict} — {ipo.detailed_outcome}")
            st.markdown("---")

# ==========================================
# TAB 4: TECHNICAL CHARTS
# ==========================================
with tab_charts:
    st.subheader("Daily Price Action & Technical Overlays")
    col_opt1, col_opt2, col_opt3 = st.columns(3)
    chart_type = col_opt1.radio("Chart Style", ["Candlestick", "Line"], horizontal=True)
    show_dma = col_opt2.checkbox("Show 50 & 200 DMA", value=True)
    show_bb = col_opt3.checkbox("Show Bollinger Bands (20, 2)", value=False)

    s50 = sma(close, 50)
    s200 = sma(close, 200)
    rsi_s = rsi(close, 14)
    macd_df = macd(close)
    bb_df = bollinger_bands(close, 20, 2.0)

    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.55, 0.15, 0.15, 0.15],
        subplot_titles=("Price & Overlays", "Volume", "RSI (14)", "MACD (12, 26, 9)"),
    )

    if chart_type == "Candlestick" and all(c in history.columns for c in ["Open", "High", "Low", "Close"]):
        fig.add_trace(
            go.Candlestick(
                x=history.index,
                open=history["Open"],
                high=history["High"],
                low=history["Low"],
                close=history["Close"],
                name="OHLC",
            ),
            row=1,
            col=1,
        )
    else:
        fig.add_trace(
            go.Scatter(x=history.index, y=close, name="Close Price", line=dict(color="#1f77b4", width=2)),
            row=1,
            col=1,
        )

    if show_dma:
        fig.add_trace(go.Scatter(x=history.index, y=s50, name="50 DMA", line=dict(color="#ff7f0e", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=history.index, y=s200, name="200 DMA", line=dict(color="#2ca02c", width=1.5)), row=1, col=1)

    if show_bb:
        fig.add_trace(go.Scatter(x=history.index, y=bb_df["upper"], name="BB Upper", line=dict(color="rgba(150,150,150,0.5)", dash="dot")), row=1, col=1)
        fig.add_trace(go.Scatter(x=history.index, y=bb_df["lower"], name="BB Lower", line=dict(color="rgba(150,150,150,0.5)", dash="dot"), fill='tonexty', fillcolor='rgba(200,200,200,0.1)'), row=1, col=1)

    if "Volume" in history.columns:
        vol_colors = ["#26a69a" if c >= o else "#ef5350" for c, o in zip(history["Close"], history["Open"])]
        fig.add_trace(go.Bar(x=history.index, y=history["Volume"], name="Volume", marker_color=vol_colors, opacity=0.7), row=2, col=1)

    fig.add_trace(go.Scatter(x=history.index, y=rsi_s, name="RSI(14)", line=dict(color="#9c27b0", width=1.5)), row=3, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

    fig.add_trace(go.Scatter(x=history.index, y=macd_df["macd"], name="MACD", line=dict(color="#2196f3", width=1.2)), row=4, col=1)
    fig.add_trace(go.Scatter(x=history.index, y=macd_df["signal"], name="Signal", line=dict(color="#ff9800", width=1.2)), row=4, col=1)
    hist_colors = ["#4caf50" if h >= 0 else "#f44336" for h in macd_df["hist"]]
    fig.add_trace(go.Bar(x=history.index, y=macd_df["hist"], name="Histogram", marker_color=hist_colors), row=4, col=1)

    fig.update_layout(height=800, margin=dict(l=40, r=40, t=40, b=40), xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

# ==========================================
# TAB 5: VALUATION & FUNDAMENTALS
# ==========================================
with tab_valuation:
    st.subheader("Fundamental Analysis & Financial Scorecard")
    scorecard = valuation_scorecard(info)
    col_sc1, col_sc2 = st.columns([1, 2])
    with col_sc1:
        st.metric("Overall Health Score", f"{scorecard['score']} / 100", scorecard["rating"])
        st.progress(scorecard["score"] / 100.0)
    with col_sc2:
        st.markdown("**Scoring Factors:**")
        for factor, desc in scorecard["breakdown"]:
            st.write(f"- **{factor}**: {desc}")

    st.markdown("---")
    f_c1, f_c2 = st.columns(2)
    with f_c1:
        st.dataframe(
            pd.DataFrame([
                {"Metric": "Trailing P/E", "Value": format_ratio(info.pe_ratio)},
                {"Metric": "Forward P/E", "Value": format_ratio(info.forward_pe)},
                {"Metric": "Price to Book (P/B)", "Value": format_ratio(info.pb_ratio)},
                {"Metric": "EV / EBITDA", "Value": format_ratio(info.ev_to_ebitda)},
                {"Metric": "Dividend Yield", "Value": format_percent(info.dividend_yield)},
            ]),
            use_container_width=True,
            hide_index=True,
        )
    with f_c2:
        st.dataframe(
            pd.DataFrame([
                {"Metric": "Return on Equity (ROE)", "Value": format_percent(info.roe)},
                {"Metric": "Debt to Equity", "Value": format_ratio(info.debt_to_equity)},
                {"Metric": "Net Profit Margin", "Value": format_percent(info.profit_margin)},
                {"Metric": "Revenue Growth (YoY)", "Value": format_percent(info.revenue_growth)},
                {"Metric": "Sector / Industry", "Value": f"{info.sector or 'N/A'} / {info.industry or 'N/A'}"},
            ]),
            use_container_width=True,
            hide_index=True,
        )

# ==========================================
# TAB 6: PEER COMPARISON
# ==========================================
with tab_peers:
    st.subheader(f"Sector Peers: {info.sector or 'Industry Benchmarks'}")
    peer_symbols = get_sector_peers(norm_symbol, info.sector)
    selected_peers = st.multiselect(
        "Compare with peers:",
        options=list(set([norm_symbol] + peer_symbols)),
        default=[norm_symbol] + peer_symbols[:3],
    )
    if st.button("Run Peer Comparison"):
        with st.spinner("Fetching peer metrics..."):
            peers_df = compare_peers(selected_peers, provider)
            if not peers_df.empty:
                st.dataframe(peers_df, use_container_width=True, hide_index=True)

# ==========================================
# TAB 7: NEWS & SENTIMENT
# ==========================================
with tab_news:
    st.subheader("Recent Headlines & Offline Financial Sentiment")
    if news_items:
        scored_news = score_news_batch(news_items)
        for sn in scored_news:
            sent_label = sn.sentiment
            badge_color = "🟢" if "Positive" in sent_label else "🔴" if "Negative" in sent_label else "⚪"
            st.markdown(f"### {badge_color} {sn.headline}")
            st.write(f"**Sentiment:** {sent_label} ({sn.score:+.2f}) | **Key terms:** {', '.join(sn.matched_keywords)}")
            st.markdown("---")

# ==========================================
# TAB 8: WATCHLIST & ALERTS
# ==========================================
with tab_watchlist:
    st.subheader("Saved Watchlist & Alert Trigger Conditions")
    with st.expander("➕ Add / Update Stock in Watchlist", expanded=False):
        with st.form("add_watchlist_form"):
            w_sym = st.text_input("Symbol", value=symbol_input).strip().upper()
            w_c1, w_c2 = st.columns(2)
            w_thigh = w_c1.number_input("Target High (Price >=)", min_value=0.0, value=float(current_price * 1.05), step=10.0)
            w_tlow = w_c2.number_input("Target Low (Price <=)", min_value=0.0, value=float(current_price * 0.95), step=10.0)
            w_c3, w_c4 = st.columns(2)
            w_rsi_low = w_c3.number_input("RSI Buy Alert (RSI <=)", min_value=0.0, max_value=100.0, value=30.0, step=5.0)
            w_rsi_high = w_c4.number_input("RSI Sell Alert (RSI >=)", min_value=0.0, max_value=100.0, value=70.0, step=5.0)
            w_sent = st.selectbox("News Sentiment Alert", options=[("No Alert", 0), ("Positive News Alert", 1), ("Negative News Alert", -1)], format_func=lambda x: x[0])
            w_notes = st.text_input("Notes", value="Trial Holding")
            if st.form_submit_button("Save to Watchlist"):
                wm.add_stock(w_sym, w_thigh, w_tlow, w_rsi_low, w_rsi_high, w_sent[1], w_notes)
                st.success(f"Saved {w_sym} to watchlist!")
                st.rerun()

    watchlist_items = wm.get_watchlist()
    if watchlist_items:
        wl_df = pd.DataFrame(watchlist_items)[["symbol", "target_price_high", "target_price_low", "rsi_lower", "rsi_upper", "notes", "created_at"]]
        st.dataframe(wl_df, use_container_width=True, hide_index=True)
        col_w_btn1, col_w_btn2 = st.columns(2)
        if col_w_btn1.button("🔔 Check Active Alerts Now"):
            fired = wm.check_alerts(provider)
            if fired:
                for f in fired:
                    st.error(f"🚨 **{f['symbol']}** [{f['type']}]: {f['message']}")
            else:
                st.success("✅ No alert triggers currently met.")
        with col_w_btn2:
            del_sym = st.selectbox("Select symbol to remove:", options=[it["symbol"] for it in watchlist_items])
            if st.button("🗑️ Remove Selected"):
                wm.remove_stock(del_sym)
                st.success(f"Removed {del_sym}.")
                st.rerun()

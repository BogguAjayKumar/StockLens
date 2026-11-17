"""Real-Time Trend & Outcome Explainer Engine.
Translates price action, volume surges, candlestick patterns, RSI/MACD signals,
and news sentiment into clear, institutional-grade explanations of every stock's move.
Educational use only. Not financial advice.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import pandas as pd

from stocklens.analysis.indicators import sma, rsi, macd, bollinger_bands, annual_volatility
from stocklens.analysis.sentiment import score_headline


@dataclass
class StockTrendExplanation:
    symbol: str
    last_price: float
    change_pct: float
    trend_verdict: str
    momentum_rating: str
    candlestick_pattern: str
    why_is_it_moving: str
    support_level: float
    resistance_level: float
    pivot_level: float
    risk_reward_verdict: str
    catalysts: List[str] = field(default_factory=list)


def detect_candlestick_pattern(df: pd.DataFrame) -> str:
    """Identify key price action candlestick patterns on the latest candles."""
    if len(df) < 2 or not all(c in df.columns for c in ["Open", "High", "Low", "Close"]):
        return "Standard Candle"

    last = df.iloc[-1]
    prev = df.iloc[-2]

    o, h, l, c = last["Open"], last["High"], last["Low"], last["Close"]
    po, ph, pl, pc = prev["Open"], prev["High"], prev["Low"], prev["Close"]

    body = abs(c - o)
    candle_range = h - l
    if candle_range <= 0:
        return "Flat Candle"

    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l

    # Bullish Engulfing (Prev red candle engulfed by current larger green candle)
    if pc < po and c > o and c >= po and o <= pc:
        return "Bullish Engulfing (Strong Buying Wave Overwhelming Prior Sellers)"

    # Bearish Engulfing (Prev green candle engulfed by current larger red candle)
    if pc > po and c < o and c <= po and o >= pc:
        return "Bearish Engulfing (Strong Selling Wave Overwhelming Prior Buyers)"

    # Hammer (Body near upper end, lower shadow >= 2x body, upper shadow small)
    if lower_wick >= (2.0 * body) and upper_wick <= (0.35 * candle_range):
        return "Bullish Hammer (Dip Rejection & Buyers Stepping In)"

    # Shooting Star / Inverted Hammer (Body near lower end, upper shadow >= 2x body, lower shadow small)
    if upper_wick >= (2.0 * body) and lower_wick <= (0.35 * candle_range):
        return "Shooting Star (High Rejection & Sellers Capping Price)"

    # Doji (Extremely tiny body <= 6% of range)
    if body <= (0.06 * candle_range):
        return "Doji (Market Indecision / Potential Pivot)"

    if c > o and body >= (0.7 * candle_range):
        return "Marubozu / Strong Bullish Expansion Candle"
    elif c < o and body >= (0.7 * candle_range):
        return "Marubozu / Strong Bearish Breakdown Candle"

    return "Neutral Trading Candle"


def explain_stock_trend(
    symbol: str,
    history: pd.DataFrame,
    info_dict: Optional[Dict[str, Any]] = None,
    headlines: Optional[List[str]] = None,
) -> StockTrendExplanation:
    """Analyze all signals and produce an institutional-grade explanation of the outcome."""
    info = info_dict or {}
    close = history["Close"]
    volume = history["Volume"] if "Volume" in history.columns else pd.Series([1.0] * len(close))

    last_price = float(close.iloc[-1])
    prev_price = float(close.iloc[-2]) if len(close) > 1 else last_price
    change_pct = ((last_price - prev_price) / prev_price) * 100.0 if prev_price > 0 else 0.0

    # Indicators
    s50 = float(sma(close, 50).iloc[-1]) if len(close) >= 50 else last_price
    s200 = float(sma(close, 200).iloc[-1]) if len(close) >= 200 else last_price
    r_val = float(rsi(close, 14).iloc[-1]) if len(close) >= 15 else 50.0
    m_df = macd(close)
    macd_hist = float(m_df["hist"].iloc[-1]) if len(m_df) > 0 else 0.0

    # Volume anomaly (Relative Volume RVOL)
    avg_vol = float(volume.iloc[-20:].mean()) if len(volume) >= 20 else float(volume.mean())
    current_vol = float(volume.iloc[-1]) if len(volume) > 0 else avg_vol
    rvol = (current_vol / avg_vol) if avg_vol > 0 else 1.0

    # Pivots (Classical Support and Resistance)
    high_last = float(history["High"].iloc[-1]) if "High" in history.columns else last_price * 1.01
    low_last = float(history["Low"].iloc[-1]) if "Low" in history.columns else last_price * 0.99
    pivot = (high_last + low_last + last_price) / 3.0
    r1 = (2 * pivot) - low_last
    s1 = (2 * pivot) - high_last

    # Candlestick pattern
    pattern = detect_candlestick_pattern(history)

    # Catalyst & News
    catalysts = []
    sentiment_bias = 0.0
    if headlines:
        for hl in headlines[:3]:
            sr = score_headline(hl)
            sentiment_bias += sr.score
            if sr.score != 0.0:
                catalysts.append(f"[{sr.sentiment}] {hl}")

    # Determine Trend Verdict & Momentum
    reasons = []

    # 1. Price vs Moving Averages
    if last_price > s50 > s200:
        verdict = "Strong Bullish Expansion"
        reasons.append(f"Trading comfortably above both 50-DMA (₹{s50:,.2f}) and 200-DMA (₹{s200:,.2f}) in a confirmed golden-cross regime.")
    elif last_price > s50 and s50 < s200:
        verdict = "Recovery / Counter-Trend Bounce"
        reasons.append(f"Rebounding above the 50-DMA (₹{s50:,.2f}), but the broader 200-DMA (₹{s200:,.2f}) remains overhead resistance.")
    elif last_price < s50 < s200:
        verdict = "Bearish Downtrend / Distribution"
        reasons.append(f"Depressed below both 50-DMA (₹{s50:,.2f}) and 200-DMA (₹{s200:,.2f}), signaling prevailing institutional selling.")
    else:
        verdict = "Consolidation / Rangebound"
        reasons.append(f"Oscillating between the 50-DMA (₹{s50:,.2f}) and 200-DMA (₹{s200:,.2f}) without definitive directional conviction.")

    # 2. Volume & Momentum Reading
    if rvol > 1.5 and change_pct > 0:
        reasons.append(f"Accumulation confirmed by elevated volume ({rvol:.1f}x of 20-day average), indicating institutional buying pressure.")
    elif rvol > 1.5 and change_pct < 0:
        reasons.append(f"Heavy volume selloff ({rvol:.1f}x of 20-day average), warning of active institutional liquidation.")
    else:
        reasons.append(f"Volume remains within normal parameters ({rvol:.1f}x average).")

    # 3. RSI & MACD Overbought/Oversold
    if r_val >= 70:
        momentum_rating = "Overheated / Stretched"
        reasons.append(f"RSI(14) is overbought at {r_val:.1f}, indicating strong momentum but cautioning of potential near-term consolidation or pullback.")
    elif r_val <= 30:
        momentum_rating = "Severely Oversold"
        reasons.append(f"RSI(14) is oversold at {r_val:.1f}, reflecting high pessimism and setting up potential mean-reversion bounce.")
    else:
        momentum_rating = "Balanced Momentum"
        reasons.append(f"RSI(14) sits at {r_val:.1f} in healthy neutral-bullish territory.")

    if macd_hist > 0:
        reasons.append("MACD histogram is positive, favoring upside continuation.")
    else:
        reasons.append("MACD histogram is negative, suggesting prevailing downward pressure.")

    # 4. Pattern & News Catalysts
    if "Bullish" in pattern or "Hammer" in pattern:
        reasons.append(f"Candlestick structure shows {pattern}.")
    elif "Bearish" in pattern or "Shooting" in pattern:
        reasons.append(f"Price action alerts: {pattern}.")

    if sentiment_bias > 0.3:
        reasons.append("Media headlines reflect positive news sentiment providing external tailwinds.")
    elif sentiment_bias < -0.3:
        reasons.append("News flow is negative, creating headline overhang.")

    why_text = " ".join(reasons)

    # Risk-Reward Assessment
    if verdict.startswith("Strong") and r_val < 68:
        rr_verdict = f"Favorable Bullish: Look for continuation towards R1 (₹{r1:,.2f}) with support at S1 (₹{s1:,.2f})."
    elif r_val >= 70:
        rr_verdict = f"Caution / Profit Booking Zone: Risk/reward less favorable for fresh entries near highs; trailing stop suggested."
    elif verdict.startswith("Bearish"):
        rr_verdict = f"High Risk: Better to await basing pattern or RSI divergence before considering long positions."
    else:
        rr_verdict = f"Range Play: Buy near S1 support (₹{s1:,.2f}), book near R1 resistance (₹{r1:,.2f})."

    return StockTrendExplanation(
        symbol=symbol,
        last_price=last_price,
        change_pct=change_pct,
        trend_verdict=verdict,
        momentum_rating=momentum_rating,
        candlestick_pattern=pattern,
        why_is_it_moving=why_text,
        support_level=round(s1, 2),
        resistance_level=round(r1, 2),
        pivot_level=round(pivot, 2),
        risk_reward_verdict=rr_verdict,
        catalysts=catalysts,
    )

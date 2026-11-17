"""Technical indicators calculation and interpretation.
Pure pandas/numpy calculations without network dependencies.
"""
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    """Simple Moving Average (SMA)."""
    return s.rolling(n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    """Exponential Moving Average (EMA)."""
    return s.ewm(span=n, adjust=False).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    """Wilder's Relative Strength Index (RSI)."""
    d = s.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    
    # Wilder's smoothing uses alpha = 1 / n
    au = up.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    ad = dn.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    
    # Handle zero division safely
    rs = au / ad
    out = 100.0 - (100.0 / (1.0 + rs))
    return out.where(ad != 0, 100.0).where(au.notna())


def macd(
    s: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> pd.DataFrame:
    """Moving Average Convergence Divergence (MACD).
    Returns DataFrame with columns ['macd', 'signal', 'hist'].
    """
    line = ema(s, fast) - ema(s, slow)
    sig = ema(line, signal)
    hist = line - sig
    return pd.DataFrame({"macd": line, "signal": sig, "hist": hist}, index=s.index)


def bollinger_bands(s: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    """Bollinger Bands (Middle, Upper, Lower)."""
    mid = sma(s, n)
    std = s.rolling(n).std()
    upper = mid + (k * std)
    lower = mid - (k * std)
    return pd.DataFrame({"mid": mid, "upper": upper, "lower": lower}, index=s.index)


def annual_volatility(s: pd.Series, trading_days: int = 252) -> float:
    """Annualized volatility based on daily percentage returns."""
    returns = s.pct_change().dropna()
    if len(returns) < 2 or returns.std() == 0:
        return 0.0
    return float(returns.std() * np.sqrt(trading_days))


def drawdown_series(s: pd.Series) -> pd.Series:
    """Percentage drawdown series from all-time or peak cumulative high."""
    cummax = s.cummax()
    return (s / cummax) - 1.0


def max_drawdown(s: pd.Series) -> float:
    """Maximum peak-to-trough decline over the period."""
    dd = drawdown_series(s)
    val = float(dd.min())
    return 0.0 if np.isnan(val) else val


def signals(close: pd.Series) -> Dict[str, Any]:
    """Plain-language reading of the latest technical indicator values.
    Educational interpretation only, not trading advice.
    """
    if len(close) == 0:
        return {}

    last = float(close.iloc[-1])
    out: Dict[str, Any] = {
        "last_price": last,
    }

    # 50 & 200 DMA
    s50_series = sma(close, 50)
    s200_series = sma(close, 200)
    
    s50 = float(s50_series.iloc[-1]) if len(s50_series) >= 50 and not np.isnan(s50_series.iloc[-1]) else None
    s200 = float(s200_series.iloc[-1]) if len(s200_series) >= 200 and not np.isnan(s200_series.iloc[-1]) else None

    if s50 is not None:
        out["50_dma"] = s50
        out["vs 50-DMA"] = "above" if last > s50 else "below"
    
    if s200 is not None:
        out["200_dma"] = s200
        out["vs 200-DMA"] = "above" if last > s200 else "below"

    if s50 is not None and s200 is not None:
        out["50/200 trend"] = (
            "golden-cross zone (50 > 200)" if s50 > s200 else "death-cross zone (50 < 200)"
        )

    # RSI
    rsi_series = rsi(close)
    if len(rsi_series) > 0 and not np.isnan(rsi_series.iloc[-1]):
        r_val = float(rsi_series.iloc[-1])
        status = "overbought (>70)" if r_val >= 70 else "oversold (<30)" if r_val <= 30 else "neutral"
        out["rsi_14"] = r_val
        out["RSI(14)"] = f"{r_val:.1f} ({status})"

    # MACD
    m_df = macd(close)
    if len(m_df) > 0:
        latest_m = float(m_df["macd"].iloc[-1])
        latest_sig = float(m_df["signal"].iloc[-1])
        latest_hist = float(m_df["hist"].iloc[-1])
        out["macd_val"] = latest_m
        out["macd_sig"] = latest_sig
        out["macd_hist"] = latest_hist
        out["MACD"] = (
            "bullish (MACD above signal)" if latest_hist > 0 else "bearish (MACD below signal)"
        )

    # Volatility & Drawdown
    vol = annual_volatility(close)
    mdd = max_drawdown(close)
    out["annual_volatility"] = vol
    out["max_drawdown"] = mdd
    out["volatility_rating"] = "low (<15%)" if vol < 0.15 else "moderate (15-30%)" if vol <= 0.30 else "high (>30%)"

    return out

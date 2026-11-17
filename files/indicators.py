"""Technical indicators. Pure pandas/numpy, no network."""
import numpy as np
import pandas as pd


def sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n).mean()


def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def rsi(s: pd.Series, n: int = 14) -> pd.Series:
    """Wilder's RSI."""
    d = s.diff()
    up, dn = d.clip(lower=0), -d.clip(upper=0)
    au = up.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    ad = dn.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    out = 100 - 100 / (1 + au / ad)
    return out.where(ad != 0, 100.0).where(au.notna())


def macd(s: pd.Series, fast=12, slow=26, signal=9) -> pd.DataFrame:
    line = ema(s, fast) - ema(s, slow)
    sig = ema(line, signal)
    return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})


def annual_volatility(s: pd.Series) -> float:
    return float(s.pct_change().std() * np.sqrt(252))


def max_drawdown(s: pd.Series) -> float:
    return float((s / s.cummax() - 1).min())


def signals(close: pd.Series) -> dict:
    """Plain-language reading of the latest values. Not trading advice."""
    last = close.iloc[-1]
    out = {}
    s50, s200 = sma(close, 50).iloc[-1], sma(close, 200).iloc[-1]
    if not np.isnan(s50):
        out["vs 50-DMA"] = "above" if last > s50 else "below"
    if not np.isnan(s200):
        out["vs 200-DMA"] = "above" if last > s200 else "below"
        out["50/200 trend"] = "golden-cross zone (50 > 200)" if s50 > s200 else "death-cross zone (50 < 200)"
    r = rsi(close).iloc[-1]
    if not np.isnan(r):
        out["RSI(14)"] = f"{r:.1f} " + ("(overbought)" if r >= 70 else "(oversold)" if r <= 30 else "(neutral)")
    m = macd(close)
    out["MACD"] = "bullish (MACD above signal)" if m["hist"].iloc[-1] > 0 else "bearish (MACD below signal)"
    return out

import numpy as np, pandas as pd
import indicators as ix


def test_sma():
    assert ix.sma(pd.Series([1, 2, 3, 4, 5]), 3).iloc[-1] == 4

def test_ema_starts_at_first_value():
    assert ix.ema(pd.Series([10, 20, 30]), 3).iloc[0] == 10

def test_rsi_extremes():
    assert ix.rsi(pd.Series(range(1, 60))).iloc[-1] == 100
    assert ix.rsi(pd.Series(range(60, 1, -1))).iloc[-1] < 1

def test_rsi_alternating_near_50():
    s = pd.Series([100, 101] * 40)
    assert 45 < ix.rsi(s).iloc[-1] < 55

def test_macd_hist_is_difference():
    m = ix.macd(pd.Series(np.linspace(100, 150, 80)))
    assert np.allclose(m["hist"], m["macd"] - m["signal"])

def test_max_drawdown():
    assert abs(ix.max_drawdown(pd.Series([100, 120, 60, 90])) - (-0.5)) < 1e-9

def test_volatility_constant_is_zero():
    assert ix.annual_volatility(pd.Series([100.0] * 30)) == 0

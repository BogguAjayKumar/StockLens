"""Unit tests for every technical indicator with known-value checks."""
import numpy as np
import pandas as pd
import pytest

from stocklens.analysis.indicators import (
    sma,
    ema,
    rsi,
    macd,
    bollinger_bands,
    annual_volatility,
    drawdown_series,
    max_drawdown,
    signals,
)


def test_sma_known_values():
    """Verify SMA calculation against known manual calculations."""
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    res = sma(s, 3)
    # At index 2: (1 + 2 + 3) / 3 = 2.0
    assert np.isnan(res.iloc[0])
    assert np.isnan(res.iloc[1])
    assert pytest.approx(res.iloc[2], 1e-9) == 2.0
    # At index 3: (2 + 3 + 4) / 3 = 3.0
    assert pytest.approx(res.iloc[3], 1e-9) == 3.0
    # At index 4: (3 + 4 + 5) / 3 = 4.0
    assert pytest.approx(res.iloc[4], 1e-9) == 4.0


def test_sma_constant_series():
    """SMA of a constant series must equal the constant value."""
    s = pd.Series([42.0] * 10)
    res = sma(s, 5)
    assert np.allclose(res.dropna(), 42.0)


def test_ema_known_values():
    """Verify EMA exact step-by-step alpha weighting.
    Formula: alpha = 2 / (span + 1). For span=3, alpha = 2/4 = 0.5.
    y0 = 10.0
    y1 = 0.5 * 20 + 0.5 * 10 = 15.0
    y2 = 0.5 * 30 + 0.5 * 15 = 22.5
    """
    s = pd.Series([10.0, 20.0, 30.0])
    res = ema(s, 3)
    assert pytest.approx(res.iloc[0], 1e-9) == 10.0
    assert pytest.approx(res.iloc[1], 1e-9) == 15.0
    assert pytest.approx(res.iloc[2], 1e-9) == 22.5


def test_rsi_strictly_increasing_is_100():
    """Wilder's RSI for strictly rising prices must be exactly 100."""
    s = pd.Series(range(1, 60), dtype=float)
    res = rsi(s, 14)
    assert pytest.approx(res.iloc[-1], 1e-9) == 100.0


def test_rsi_strictly_decreasing_is_near_zero():
    """Wilder's RSI for strictly falling prices must approach 0."""
    s = pd.Series(range(60, 1, -1), dtype=float)
    res = rsi(s, 14)
    assert res.iloc[-1] < 1.0


def test_rsi_alternating_near_50():
    """Wilder's RSI for an alternating series [100, 101] should center around 50."""
    s = pd.Series([100.0, 101.0] * 40)
    res = rsi(s, 14)
    assert 45.0 < res.iloc[-1] < 55.0


def test_macd_difference_property():
    """MACD histogram must exactly equal macd line minus signal line."""
    s = pd.Series(np.linspace(100, 150, 80))
    m = macd(s)
    diff = m["macd"] - m["signal"]
    assert np.allclose(m["hist"], diff, atol=1e-9)


def test_macd_constant_is_zero():
    """MACD for a constant series must be exactly zero after warmup."""
    s = pd.Series([100.0] * 50)
    m = macd(s)
    assert pytest.approx(m["macd"].iloc[-1], abs=1e-7) == 0.0
    assert pytest.approx(m["signal"].iloc[-1], abs=1e-7) == 0.0
    assert pytest.approx(m["hist"].iloc[-1], abs=1e-7) == 0.0


def test_bollinger_bands_known_values():
    """Verify middle is SMA, and width is exactly k * std."""
    s = pd.Series([10.0, 12.0, 14.0, 16.0, 18.0])
    bb = bollinger_bands(s, n=3, k=2.0)
    mid_expected = (14.0 + 16.0 + 18.0) / 3.0  # 16.0
    std_expected = pd.Series([14.0, 16.0, 18.0]).std()
    
    assert pytest.approx(bb["mid"].iloc[-1], 1e-9) == mid_expected
    assert pytest.approx(bb["upper"].iloc[-1], 1e-9) == mid_expected + 2.0 * std_expected
    assert pytest.approx(bb["lower"].iloc[-1], 1e-9) == mid_expected - 2.0 * std_expected


def test_annual_volatility_constant_is_zero():
    """Constant price series has zero daily returns and 0% annual volatility."""
    s = pd.Series([100.0] * 30)
    assert annual_volatility(s) == 0.0


def test_annual_volatility_known_calculation():
    """Verify annual volatility formula: std(returns) * sqrt(252)."""
    # Create simple series with known daily returns
    prices = [100.0, 101.0, 100.0, 101.0, 100.0]
    s = pd.Series(prices)
    returns = s.pct_change().dropna()
    expected_vol = float(returns.std() * np.sqrt(252))
    assert pytest.approx(annual_volatility(s), 1e-9) == expected_vol


def test_max_drawdown_known_value():
    """Verify max drawdown for known peak and trough.
    Peak = 120, Trough = 60 => Drawdown = (60 - 120) / 120 = -0.5 (-50%).
    """
    s = pd.Series([100.0, 120.0, 60.0, 90.0])
    assert pytest.approx(max_drawdown(s), 1e-9) == -0.5
    
    dds = drawdown_series(s)
    assert pytest.approx(dds.iloc[1], 1e-9) == 0.0   # At 120 peak
    assert pytest.approx(dds.iloc[2], 1e-9) == -0.5  # At 60 trough


def test_max_drawdown_strictly_increasing_is_zero():
    """Monotonically rising price series has 0% maximum drawdown."""
    s = pd.Series([100.0, 110.0, 120.0, 130.0])
    assert pytest.approx(max_drawdown(s), 1e-9) == 0.0


def test_signals_golden_and_death_cross():
    """Test golden-cross and death-cross detection in signals()."""
    # Create 250 days where last 50 days are higher than first 200 days => Golden cross zone
    rising_data = pd.Series(np.linspace(100, 200, 250))
    sig_rising = signals(rising_data)
    assert "golden-cross" in sig_rising["50/200 trend"]
    assert sig_rising["vs 50-DMA"] == "above"
    assert sig_rising["vs 200-DMA"] == "above"

    # Create falling series => Death cross zone
    falling_data = pd.Series(np.linspace(200, 100, 250))
    sig_falling = signals(falling_data)
    assert "death-cross" in sig_falling["50/200 trend"]
    assert sig_falling["vs 50-DMA"] == "below"
    assert sig_falling["vs 200-DMA"] == "below"


def test_signals_rsi_thresholds():
    """Test overbought and oversold readings in signals()."""
    overbought = pd.Series(range(1, 100), dtype=float)
    sig_ob = signals(overbought)
    assert "overbought" in sig_ob["RSI(14)"]

    oversold = pd.Series(range(100, 1, -1), dtype=float)
    sig_os = signals(oversold)
    assert "oversold" in sig_os["RSI(14)"]

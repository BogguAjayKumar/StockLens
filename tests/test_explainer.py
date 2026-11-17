"""Unit tests for Trend Explainer and Candlestick Pattern Recognition."""
import pytest
import pandas as pd
from stocklens.analysis.explainer import detect_candlestick_pattern, explain_stock_trend


def test_doji_detection():
    """Verify Doji candlestick pattern when body is tiny compared to range."""
    df = pd.DataFrame(
        {
            "Open": [100.0, 100.0],
            "High": [105.0, 110.0],
            "Low": [95.0, 90.0],
            "Close": [102.0, 100.4],  # Range = 20, body = 0.4 (2% of range <= 6%)
        }
    )
    pattern = detect_candlestick_pattern(df)
    assert "Doji" in pattern


def test_hammer_detection():
    """Verify Bullish Hammer candlestick pattern (long lower shadow, small upper body)."""
    df = pd.DataFrame(
        {
            "Open": [100.0, 98.5],
            "High": [101.0, 100.0],
            "Low": [98.0, 90.0],
            "Close": [99.0, 99.5],  # Body = 1.0, lower wick = 8.5 (> 2*body), upper wick = 0.5
        }
    )
    pattern = detect_candlestick_pattern(df)
    assert "Hammer" in pattern


def test_bullish_engulfing_detection():
    """Verify Bullish Engulfing pattern."""
    df = pd.DataFrame(
        {
            "Open": [100.0, 95.0],
            "High": [101.0, 103.0],
            "Low": [96.0, 94.0],
            "Close": [97.0, 102.0],  # Prev red (100->97), current green (95->102) engulfing
        }
    )
    pattern = detect_candlestick_pattern(df)
    assert "Bullish Engulfing" in pattern


def test_explain_stock_trend_output():
    """Verify outcome engine produces all required analytical attributes."""
    prices = [100.0 + i for i in range(60)]
    df = pd.DataFrame(
        {
            "Open": prices,
            "High": [p + 2.0 for p in prices],
            "Low": [p - 1.0 for p in prices],
            "Close": prices,
            "Volume": [1000000] * 60,
        }
    )
    explanation = explain_stock_trend(
        symbol="INFY.NS",
        history=df,
        headlines=["Company wins record digital deal with major financial enterprise"],
    )

    assert explanation.symbol == "INFY.NS"
    assert explanation.last_price > 0
    assert explanation.pivot_level > 0
    assert explanation.resistance_level >= explanation.pivot_level
    assert explanation.support_level <= explanation.pivot_level
    assert len(explanation.why_is_it_moving) > 20
    assert len(explanation.catalysts) > 0

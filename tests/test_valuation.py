"""Unit tests for valuation metrics, currency formatting, and health scorecard."""
import pytest
import pandas as pd
from stocklens.analysis.valuation import (
    format_currency_inr,
    format_percent,
    format_ratio,
    market_cap_category,
    calculate_returns,
    valuation_scorecard,
)
from stocklens.data.base import StockInfo


def test_format_currency_inr():
    """Verify Indian currency crore formatting."""
    assert format_currency_inr(None) == "N/A"
    # 10,000,000 INR = 1 Cr
    assert "₹1.0 Cr" in format_currency_inr(1e7)
    # 20,000 Cr = 2e11 INR
    assert "₹20,000.0 Cr" in format_currency_inr(2e11)
    # 2 Lakh Cr = 2e12 INR
    assert "₹2.00 Lakh Cr" in format_currency_inr(2e12)


def test_market_cap_category():
    """Verify market cap category tiers: Large (>20k Cr), Mid (5k-20k Cr), Small (<5k Cr)."""
    assert market_cap_category(None) == "Unknown"
    # 25,000 Cr = 2.5e11 => Large Cap
    assert market_cap_category(2.5e11) == "Large Cap"
    # 10,000 Cr = 1e11 => Mid Cap
    assert market_cap_category(1e11) == "Mid Cap"
    # 2,000 Cr = 2e10 => Small Cap
    assert market_cap_category(2e10) == "Small Cap"


def test_calculate_returns_known_values():
    """Verify percentage return calculations over 1W, 1M, 1Y."""
    # Series of 300 days: 100 on day 0, 110 on day 294 (1W ago), 120 on day 278 (1M ago), 150 on day 299 (today)
    prices = [100.0] * 300
    prices[-6] = 120.0  # 5 periods ago
    prices[-1] = 150.0  # today
    s = pd.Series(prices)
    
    rets = calculate_returns(s)
    # 1W return: (150 / 120 - 1) * 100 = 25%
    assert pytest.approx(rets["1W"], 1e-9) == 25.0


def test_valuation_scorecard_strong():
    """Verify health score for high-quality balance sheet and profitability."""
    info = StockInfo(
        symbol="STRONG.NS",
        name="Strong Corp",
        roe=0.25,             # >20% (+20)
        profit_margin=0.18,   # >15% (+10)
        debt_to_equity=0.05,  # <0.2 (+25)
        pe_ratio=18.0,        # 15-30 (+18)
        revenue_growth=0.16,  # >15% (+20)
    )
    scorecard = valuation_scorecard(info)
    assert scorecard["score"] >= 80
    assert scorecard["rating"] == "Strong Fundamentals"


def test_valuation_scorecard_distressed():
    """Verify health score for low-margin, high-debt company."""
    info = StockInfo(
        symbol="WEAK.NS",
        name="Weak Corp",
        roe=-0.05,            # negative (0)
        profit_margin=0.01,   # <5% (0)
        debt_to_equity=2.5,   # >1.5 (0)
        pe_ratio=75.0,        # >50 (0)
        revenue_growth=-0.08, # negative (0)
    )
    scorecard = valuation_scorecard(info)
    assert scorecard["score"] <= 30
    assert scorecard["rating"] == "Caution / Stretched"

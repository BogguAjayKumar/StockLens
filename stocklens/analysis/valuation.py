"""Valuation ratios, financial health scorecards, and returns analysis."""
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd
from stocklens.data.base import StockInfo


def format_currency_inr(val: Optional[float], in_crores: bool = True) -> str:
    """Format currency in Indian Rupee format (Lakhs and Crores)."""
    if val is None or np.isnan(val):
        return "N/A"
    if in_crores:
        # 1 Crore = 10,000,000 (1e7)
        crores = val / 1e7
        if crores >= 100_000:
            return f"₹{crores / 100_000:,.2f} Lakh Cr"
        return f"₹{crores:,.1f} Cr"
    return f"₹{val:,.2f}"


def format_percent(val: Optional[float]) -> str:
    """Format decimal percentage to string."""
    if val is None or np.isnan(val):
        return "N/A"
    return f"{val * 100:+.2f}%" if val != 0 else "0.00%"


def format_ratio(val: Optional[float], decimals: int = 2) -> str:
    """Format numeric ratio."""
    if val is None or np.isnan(val):
        return "N/A"
    return f"{val:.{decimals}f}"


def market_cap_category(mcap_inr: Optional[float]) -> str:
    """Categorize stock by market capitalization according to Indian standards.
    Large Cap: > ₹20,000 Crore (~2e11 INR)
    Mid Cap: ₹5,000 to ₹20,000 Crore (~5e10 to 2e11 INR)
    Small Cap: < ₹5,000 Crore (< 5e10 INR)
    """
    if mcap_inr is None or np.isnan(mcap_inr):
        return "Unknown"
    crores = mcap_inr / 1e7
    if crores >= 20_000:
        return "Large Cap"
    elif crores >= 5_000:
        return "Mid Cap"
    return "Small Cap"


def calculate_returns(close: pd.Series) -> Dict[str, Optional[float]]:
    """Calculate returns over standard trading windows (1W, 1M, 3M, 6M, 1Y)."""
    if len(close) < 2:
        return {"1W": None, "1M": None, "3M": None, "6M": None, "1Y": None}

    last_val = close.iloc[-1]
    windows = {
        "1W": 5,
        "1M": 21,
        "3M": 63,
        "6M": 126,
        "1Y": 252,
    }
    
    returns = {}
    for label, periods in windows.items():
        if len(close) > periods:
            past_val = close.iloc[-periods - 1]
            returns[label] = (last_val / past_val - 1.0) * 100.0
        else:
            returns[label] = None
    return returns


def valuation_scorecard(info: StockInfo) -> Dict[str, Any]:
    """Computes a multi-factor fundamental health score (0 to 100).
    Educational framework evaluating:
    1. Profitability (ROE, profit margin)
    2. Leverage / Solvency (Debt to equity)
    3. Valuation pricing (P/E ratio, P/B ratio)
    4. Growth (Revenue growth)
    """
    score = 0
    max_score = 100
    breakdown = []

    # 1. Profitability (up to 30 pts)
    if info.roe is not None:
        if info.roe >= 0.20:
            score += 20
            breakdown.append(("ROE", "+20 (Exceptional: >20%)"))
        elif info.roe >= 0.12:
            score += 15
            breakdown.append(("ROE", "+15 (Healthy: 12-20%)"))
        elif info.roe > 0:
            score += 5
            breakdown.append(("ROE", "+5 (Positive: <12%)"))
        else:
            breakdown.append(("ROE", "0 (Negative ROE)"))

    if info.profit_margin is not None:
        if info.profit_margin >= 0.15:
            score += 10
            breakdown.append(("Margin", "+10 (High net margin >15%)"))
        elif info.profit_margin > 0.05:
            score += 5
            breakdown.append(("Margin", "+5 (Decent margin 5-15%)"))

    # 2. Leverage / Debt (up to 25 pts)
    if info.debt_to_equity is not None:
        if info.debt_to_equity < 0.2:
            score += 25
            breakdown.append(("Debt/Equity", "+25 (Virtually debt-free: <0.2)"))
        elif info.debt_to_equity <= 0.8:
            score += 20
            breakdown.append(("Debt/Equity", "+20 (Conservative leverage: 0.2-0.8)"))
        elif info.debt_to_equity <= 1.5:
            score += 10
            breakdown.append(("Debt/Equity", "+10 (Moderate leverage: 0.8-1.5)"))
        else:
            breakdown.append(("Debt/Equity", "0 (High debt: >1.5)"))
    else:
        # Default neutral credit
        score += 15
        breakdown.append(("Debt/Equity", "+15 (Not reported / financial sector)"))

    # 3. Valuation (up to 25 pts)
    if info.pe_ratio is not None and info.pe_ratio > 0:
        if info.pe_ratio < 15:
            score += 25
            breakdown.append(("P/E Ratio", "+25 (Attractive value: <15)"))
        elif info.pe_ratio <= 30:
            score += 18
            breakdown.append(("P/E Ratio", "+18 (Reasonable valuation: 15-30)"))
        elif info.pe_ratio <= 50:
            score += 10
            breakdown.append(("P/E Ratio", "+10 (Premium / growth multiple: 30-50)"))
        else:
            breakdown.append(("P/E Ratio", "0 (Elevated valuation: >50)"))
    else:
        score += 10

    # 4. Growth (up to 20 pts)
    if info.revenue_growth is not None:
        if info.revenue_growth >= 0.15:
            score += 20
            breakdown.append(("Growth", "+20 (Strong growth: >15%)"))
        elif info.revenue_growth > 0:
            score += 12
            breakdown.append(("Growth", "+12 (Moderate growth: 0-15%)"))
        else:
            breakdown.append(("Growth", "0 (Declining revenues)"))
    else:
        score += 10

    # Final verdict
    rating = (
        "Strong Fundamentals" if score >= 75
        else "Moderate / Balanced" if score >= 50
        else "Caution / Stretched"
    )

    return {
        "score": score,
        "max_score": max_score,
        "rating": rating,
        "breakdown": breakdown,
    }

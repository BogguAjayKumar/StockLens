"""Offline demo data provider generating synthetic yet realistic stock data."""
import datetime
from typing import List, Dict, Any
import numpy as np
import pandas as pd

from stocklens.data.base import BaseDataProvider, StockInfo, NewsItem, normalize_symbol


DEMO_PROFILES: Dict[str, Dict[str, Any]] = {
    "INFY.NS": {
        "name": "Infosys Limited",
        "sector": "Information Technology",
        "industry": "IT Services & Consulting",
        "base_price": 1850.0,
        "market_cap": 7.7e11,
        "pe": 28.5,
        "pb": 8.2,
        "ev_ebitda": 19.4,
        "roe": 0.315,
        "debt_to_equity": 0.09,
        "profit_margin": 0.175,
        "revenue_growth": 0.085,
        "dividend_yield": 0.024,
        "news": [
            ("Infosys wins multi-year digital transformation deal with global bank", "positive"),
            ("Infosys Q3 net profit jumps 7% YoY, beats market estimates", "positive"),
            ("Infosys raises full-year constant currency revenue growth guidance", "positive"),
            ("Attrition rate stabilizes at Infosys as hiring momentum picks up", "neutral"),
            ("IT sector faces client spending moderation in European markets", "negative"),
        ],
    },
    "TCS.NS": {
        "name": "Tata Consultancy Services Limited",
        "sector": "Information Technology",
        "industry": "IT Services & Consulting",
        "base_price": 4120.0,
        "market_cap": 1.48e12,
        "pe": 31.2,
        "pb": 13.5,
        "ev_ebitda": 22.1,
        "roe": 0.495,
        "debt_to_equity": 0.05,
        "profit_margin": 0.198,
        "revenue_growth": 0.072,
        "dividend_yield": 0.018,
        "news": [
            ("TCS bags $1 billion strategic cloud transformation contract", "positive"),
            ("Tata Consultancy Services announces record dividend payout", "positive"),
            ("TCS expands AI Centers of Excellence across North America", "positive"),
            ("Management commentary remains cautious on BFSI vertical recovery", "negative"),
        ],
    },
    "RELIANCE.NS": {
        "name": "Reliance Industries Limited",
        "sector": "Energy & Conglomerate",
        "industry": "Oil, Gas & Consumable Fuels / Retail / Telecom",
        "base_price": 2980.0,
        "market_cap": 2.01e12,
        "pe": 26.8,
        "pb": 2.4,
        "ev_ebitda": 14.8,
        "roe": 0.098,
        "debt_to_equity": 0.42,
        "profit_margin": 0.082,
        "revenue_growth": 0.114,
        "dividend_yield": 0.004,
        "news": [
            ("Reliance Jio adds 3.5 million 5G subscribers in record monthly surge", "positive"),
            ("Reliance Retail expands footprint with 150 new store openings", "positive"),
            ("Oil-to-chemicals refining margins show strong quarterly rebound", "positive"),
            ("Crude volatility and petchem margins put minor pressure on cash flow", "negative"),
            ("Reliance green energy gigafactory project progressing as scheduled", "positive"),
        ],
    },
}


class DemoDataProvider(BaseDataProvider):
    """Provides synthetic offline data without external internet access."""

    def __init__(self, seed: int = 42):
        self.seed = seed

    def get_history(self, symbol: str, years: int = 2) -> pd.DataFrame:
        sym = normalize_symbol(symbol)
        profile = DEMO_PROFILES.get(sym, {
            "name": f"{sym} Demo Corp",
            "sector": "General Diversified",
            "industry": "Diversified Industries",
            "base_price": 1000.0,
        })
        base = profile["base_price"]
        
        # Determine number of business days (approx 252 days/year)
        n_days = int(years * 252)
        rng = np.random.default_rng(self.seed + sum(ord(c) for c in sym))
        
        # Geometric brownian motion with slight drift
        daily_returns = rng.normal(0.0005, 0.015, n_days)
        prices = base * np.exp(np.cumsum(daily_returns))
        
        # High, Low, Open relative to Close
        highs = prices * (1 + rng.uniform(0.002, 0.018, n_days))
        lows = prices * (1 - rng.uniform(0.002, 0.018, n_days))
        opens = prices * (1 + rng.normal(0.0, 0.006, n_days))
        volumes = rng.integers(500_000, 5_000_000, n_days)

        end_date = pd.Timestamp.today().normalize()
        dates = pd.bdate_range(end=end_date, periods=n_days)

        df = pd.DataFrame(
            {
                "Open": opens,
                "High": highs,
                "Low": lows,
                "Close": prices,
                "Volume": volumes,
            },
            index=dates,
        )
        return df

    def get_info(self, symbol: str) -> StockInfo:
        sym = normalize_symbol(symbol)
        profile = DEMO_PROFILES.get(sym, {
            "name": f"{sym} Corporation (Demo)",
            "sector": "Diversified",
            "industry": "General Business",
            "base_price": 1250.0,
            "market_cap": 5e11,
            "pe": 24.0,
            "pb": 3.5,
            "ev_ebitda": 15.0,
            "roe": 0.16,
            "debt_to_equity": 0.35,
            "profit_margin": 0.12,
            "revenue_growth": 0.10,
            "dividend_yield": 0.015,
            "news": [],
        })
        base = profile.get("base_price", 1000.0)
        return StockInfo(
            symbol=sym,
            name=profile.get("name", sym),
            sector=profile.get("sector", "Conglomerate"),
            industry=profile.get("industry", "Diversified"),
            currency="INR",
            current_price=base,
            market_cap=profile.get("market_cap", 5e11),
            pe_ratio=profile.get("pe", 25.0),
            forward_pe=profile.get("pe", 25.0) * 0.95,
            pb_ratio=profile.get("pb", 3.0),
            ev_to_ebitda=profile.get("ev_ebitda", 16.0),
            roe=profile.get("roe", 0.18),
            debt_to_equity=profile.get("debt_to_equity", 0.25),
            profit_margin=profile.get("profit_margin", 0.14),
            revenue_growth=profile.get("revenue_growth", 0.09),
            dividend_yield=profile.get("dividend_yield", 0.015),
            fifty_two_week_high=base * 1.22,
            fifty_two_week_low=base * 0.81,
        )

    def get_news(self, symbol: str, limit: int = 10) -> List[NewsItem]:
        sym = normalize_symbol(symbol)
        profile = DEMO_PROFILES.get(sym, {})
        news_tuples = profile.get("news", [
            (f"{sym} reports solid quarterly performance in line with expectations", "positive"),
            (f"Industry analysts maintain constructive outlook on {sym}", "neutral"),
            (f"{sym} management addresses macro headwinds and supply chain factors", "neutral"),
        ])
        
        items = []
        for title, sent in news_tuples[:limit]:
            items.append(
                NewsItem(
                    title=title,
                    publisher="Demo Financial Wire",
                    link="https://stocklens.local/demo",
                    published_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                    sentiment=sent,
                )
            )
        return items

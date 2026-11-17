"""Base data provider interface and data models for StockLens."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import pandas as pd


@dataclass
class StockInfo:
    symbol: str
    name: str = ""
    sector: Optional[str] = None
    industry: Optional[str] = None
    currency: str = "INR"
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    pb_ratio: Optional[float] = None
    ev_to_ebitda: Optional[float] = None
    roe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    profit_margin: Optional[float] = None
    revenue_growth: Optional[float] = None
    dividend_yield: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "longName": self.name,
            "sector": self.sector,
            "industry": self.industry,
            "currency": self.currency,
            "currentPrice": self.current_price,
            "marketCap": self.market_cap,
            "trailingPE": self.pe_ratio,
            "forwardPE": self.forward_pe,
            "priceToBook": self.pb_ratio,
            "enterpriseToEbitda": self.ev_to_ebitda,
            "returnOnEquity": self.roe,
            "debtToEquity": self.debt_to_equity,
            "profitMargins": self.profit_margin,
            "revenueGrowth": self.revenue_growth,
            "dividendYield": self.dividend_yield,
            "fiftyTwoWeekHigh": self.fifty_two_week_high,
            "fiftyTwoWeekLow": self.fifty_two_week_low,
        }


@dataclass
class NewsItem:
    title: str
    publisher: str = "Unknown"
    link: str = ""
    published_at: Optional[str] = None
    sentiment: Optional[str] = None
    sentiment_score: Optional[float] = None


COMPANY_NAME_MAP: Dict[str, str] = {
    "RELIANCE": "RELIANCE.NS",
    "RELIANCE INDUSTRIES": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "TATA CONSULTANCY SERVICES": "TCS.NS",
    "INFY": "INFY.NS",
    "INFOSYS": "INFY.NS",
    "HDFC": "HDFCBANK.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "HDFC BANK": "HDFCBANK.NS",
    "ICICI": "ICICIBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "ICICI BANK": "ICICIBANK.NS",
    "SBIN": "SBIN.NS",
    "SBI": "SBIN.NS",
    "STATE BANK OF INDIA": "SBIN.NS",
    "BHARTIARTL": "BHARTIARTL.NS",
    "AIRTEL": "BHARTIARTL.NS",
    "BHARTI AIRTEL": "BHARTIARTL.NS",
    "ITC": "ITC.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
    "HINDUSTAN UNILEVER": "HINDUNILVR.NS",
    "LT": "LT.NS",
    "L&T": "LT.NS",
    "LARSEN & TOUBRO": "LT.NS",
    "TATAMOTORS": "TATAMOTORS.NS",
    "TATA MOTORS": "TATAMOTORS.NS",
    "WIPRO": "WIPRO.NS",
    "HCLTECH": "HCLTECH.NS",
    "HCL TECH": "HCLTECH.NS",
    "MARUTI": "MARUTI.NS",
    "MARUTI SUZUKI": "MARUTI.NS",
    "SUNPHARMA": "SUNPHARMA.NS",
    "SUN PHARMA": "SUNPHARMA.NS",
    "TITAN": "TITAN.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "BAJAJ FINANCE": "BAJFINANCE.NS",
    "ADANIENT": "ADANIENT.NS",
    "ADANI ENTERPRISES": "ADANIENT.NS",
}


def normalize_symbol(symbol: str) -> str:
    """Normalize user input (ticker or company name) to exchange-ready symbol.
    Defaults to NSE (.NS).
    """
    clean = symbol.strip().upper()
    if clean in COMPANY_NAME_MAP:
        return COMPANY_NAME_MAP[clean]

    # Check if name is in map keys ignoring whitespace/punctuation
    normalized_key = "".join(ch for ch in clean if ch.isalnum() or ch == ' ')
    if normalized_key in COMPANY_NAME_MAP:
        return COMPANY_NAME_MAP[normalized_key]

    # Already has an exchange suffix (e.g., .NS or .BO) or index prefix (e.g., ^NSEI)
    if "." in clean or clean.startswith("^"):
        return clean

    # NSE by default
    return f"{clean}.NS"


class BaseDataProvider(ABC):
    """Abstract base provider for financial market data."""

    @abstractmethod
    def get_history(self, symbol: str, years: int = 2) -> pd.DataFrame:
        """Fetch historical daily price data.
        Returns a DataFrame with columns: ['Open', 'High', 'Low', 'Close', 'Volume']
        and DatetimeIndex.
        """
        pass

    @abstractmethod
    def get_info(self, symbol: str) -> StockInfo:
        """Fetch fundamental company information and valuation ratios."""
        pass

    @abstractmethod
    def get_news(self, symbol: str, limit: int = 10) -> List[NewsItem]:
        """Fetch recent news headlines for the stock."""
        pass

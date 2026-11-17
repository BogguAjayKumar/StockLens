"""Analysis modules for StockLens."""
from stocklens.analysis.indicators import (
    sma,
    ema,
    rsi,
    macd,
    annual_volatility,
    max_drawdown,
    drawdown_series,
    signals,
)
from stocklens.analysis.valuation import (
    calculate_returns,
    market_cap_category,
    valuation_scorecard,
    format_currency_inr,
)
from stocklens.analysis.peers import get_sector_peers, compare_peers
from stocklens.analysis.sentiment import score_headline, score_news_batch, NewsSentimentResult

__all__ = [
    "sma",
    "ema",
    "rsi",
    "macd",
    "annual_volatility",
    "max_drawdown",
    "drawdown_series",
    "signals",
    "calculate_returns",
    "market_cap_category",
    "valuation_scorecard",
    "format_currency_inr",
    "get_sector_peers",
    "compare_peers",
    "score_headline",
    "score_news_batch",
    "NewsSentimentResult",
]

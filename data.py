"""Root compatibility wrapper for StockLens data layer."""
import pandas as pd
from stocklens.data.base import normalize_symbol
from stocklens.data.factory import get_data_provider
from stocklens.analysis.sentiment import score_news_batch

_default_provider = get_data_provider()


def normalize(sym: str) -> str:
    return normalize_symbol(sym)


def get_history(sym: str, years: int = 2) -> pd.DataFrame:
    return _default_provider.get_history(sym, years=years)


def get_info(sym: str) -> dict:
    info = _default_provider.get_info(sym)
    return info.to_dict()


def get_news_sentiment(sym: str, limit: int = 10):
    items = _default_provider.get_news(sym, limit=limit)
    scored = score_news_batch(items)
    return [(s.headline, s.sentiment.lower()) for s in scored]

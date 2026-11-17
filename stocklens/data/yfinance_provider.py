"""yfinance Data Provider for StockLens with SQLite caching."""
import io
import json
import logging
from typing import List, Optional
import pandas as pd

from stocklens.data.base import BaseDataProvider, StockInfo, NewsItem, normalize_symbol
from stocklens.data.cache import CacheManager

logger = logging.getLogger(__name__)


class YFinanceProvider(BaseDataProvider):
    """Fetches market data from Yahoo Finance with local SQLite caching."""

    def __init__(self, cache_manager: Optional[CacheManager] = None):
        self.cache = cache_manager or CacheManager()

    def get_history(self, symbol: str, years: int = 2) -> pd.DataFrame:
        sym = normalize_symbol(symbol)
        cache_key = f"hist:{sym}:{years}"
        cached_json = self.cache.get(cache_key)
        
        if cached_json:
            try:
                df = pd.read_json(io.StringIO(cached_json))
                df.index = pd.to_datetime(df.index)
                return df
            except Exception as e:
                logger.warning("Failed to deserialize cached history for %s: %s", sym, e)

        import yfinance as yf
        ticker = yf.Ticker(sym)
        df = ticker.history(period=f"{years}y", auto_adjust=True)
        
        if df.empty:
            raise ValueError(
                f"No price data found for '{sym}'. Verify the ticker (e.g., RELIANCE, TCS, INFY)."
            )

        # Standardize columns and remove timezone for clean calculation
        cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        df = df[cols].copy()
        if hasattr(df.index, "tz_localize"):
            df.index = df.index.tz_localize(None)

        self.cache.put(cache_key, df.to_json(date_format="iso"))
        return df

    def get_info(self, symbol: str) -> StockInfo:
        sym = normalize_symbol(symbol)
        cache_key = f"info:{sym}"
        cached_info = self.cache.get(cache_key)

        if cached_info:
            try:
                data = json.loads(cached_info)
                return self._parse_info_dict(sym, data)
            except Exception as e:
                logger.warning("Failed to deserialize cached info for %s: %s", sym, e)

        import yfinance as yf
        try:
            ticker = yf.Ticker(sym)
            raw = ticker.info or {}
        except Exception as e:
            logger.warning("Failed to fetch info for %s: %s", sym, e)
            raw = {}

        self.cache.put(cache_key, json.dumps(raw))
        return self._parse_info_dict(sym, raw)

    def _parse_info_dict(self, symbol: str, raw: dict) -> StockInfo:
        return StockInfo(
            symbol=symbol,
            name=raw.get("longName") or raw.get("shortName") or symbol,
            sector=raw.get("sector"),
            industry=raw.get("industry"),
            currency=raw.get("currency", "INR"),
            current_price=raw.get("currentPrice") or raw.get("regularMarketPrice"),
            market_cap=raw.get("marketCap"),
            pe_ratio=raw.get("trailingPE"),
            forward_pe=raw.get("forwardPE"),
            pb_ratio=raw.get("priceToBook"),
            ev_to_ebitda=raw.get("enterpriseToEbitda"),
            roe=raw.get("returnOnEquity"),
            debt_to_equity=raw.get("debtToEquity"),
            profit_margin=raw.get("profitMargins"),
            revenue_growth=raw.get("revenueGrowth"),
            dividend_yield=raw.get("dividendYield"),
            fifty_two_week_high=raw.get("fiftyTwoWeekHigh"),
            fifty_two_week_low=raw.get("fiftyTwoWeekLow"),
            raw=raw,
        )

    def get_news(self, symbol: str, limit: int = 10) -> List[NewsItem]:
        sym = normalize_symbol(symbol)
        cache_key = f"news:{sym}"
        cached_news = self.cache.get(cache_key)

        if cached_news:
            try:
                items_data = json.loads(cached_news)
                return [NewsItem(**item) for item in items_data]
            except Exception as e:
                logger.warning("Failed to parse cached news for %s: %s", sym, e)

        import yfinance as yf
        try:
            ticker = yf.Ticker(sym)
            raw_news = ticker.news or []
        except Exception as e:
            logger.warning("Failed to fetch yfinance news for %s: %s", sym, e)
            raw_news = []

        items: List[NewsItem] = []
        for item in raw_news[:limit]:
            title = item.get("title")
            if not title and "content" in item and isinstance(item["content"], dict):
                title = item["content"].get("title")
            if not title:
                continue

            publisher = item.get("publisher") or (
                item.get("content", {}).get("provider", {}).get("displayName", "News Feed")
                if isinstance(item.get("content"), dict) else "News Feed"
            )
            link = item.get("link") or (
                item.get("content", {}).get("canonicalUrl", {}).get("url", "")
                if isinstance(item.get("content"), dict) else ""
            )
            pub_time = item.get("providerPublishTime")

            items.append(
                NewsItem(
                    title=title.strip(),
                    publisher=publisher,
                    link=link,
                    published_at=str(pub_time) if pub_time else None,
                )
            )

        serializable = [
            {"title": it.title, "publisher": it.publisher, "link": it.link, "published_at": it.published_at}
            for it in items
        ]
        self.cache.put(cache_key, json.dumps(serializable))
        return items

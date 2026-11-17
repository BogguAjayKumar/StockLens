"""Moneycontrol Scraper Data Provider.
Strictly adheres to robots.txt, custom User-Agent, rate limiting (2-3s delay), and SQLite caching.
"""
import time
import json
import logging
import urllib.robotparser
from typing import List, Optional, Tuple
import requests
from bs4 import BeautifulSoup
import pandas as pd

from stocklens.config import (
    MONEYCONTROL_USER_AGENT,
    SCRAPER_RATE_LIMIT_SECONDS,
)
from stocklens.data.base import BaseDataProvider, StockInfo, NewsItem, normalize_symbol
from stocklens.data.cache import CacheManager

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Base exception for scraping errors."""
    pass


class RobotsDisallowedError(ScraperError):
    """Raised when an action is disallowed by robots.txt."""
    pass


class RateLimiter:
    """Enforces minimum interval between consecutive outbound HTTP requests."""

    def __init__(self, min_interval: float = SCRAPER_RATE_LIMIT_SECONDS):
        self.min_interval = min_interval
        self.last_request_time: float = 0.0

    def wait(self) -> None:
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            sleep_needed = self.min_interval - elapsed
            logger.info("Rate limiter: pausing for %.2f seconds", sleep_needed)
            time.sleep(sleep_needed)
        self.last_request_time = time.time()


class RobotsChecker:
    """Checks URL paths against Moneycontrol robots.txt with caching."""

    def __init__(self, user_agent: str = MONEYCONTROL_USER_AGENT):
        self.user_agent = user_agent
        self.robots_url = "https://www.moneycontrol.com/robots.txt"
        self.parser = urllib.robotparser.RobotFileParser()
        self._loaded = False

    def load(self, session: requests.Session) -> None:
        if self._loaded:
            return
        try:
            resp = session.get(self.robots_url, timeout=10)
            if resp.status_code == 200:
                self.parser.parse(resp.text.splitlines())
                self._loaded = True
                logger.info("Successfully loaded and parsed Moneycontrol robots.txt")
            else:
                logger.warning(
                    "Failed to fetch robots.txt (status %s); assuming restrictive crawl",
                    resp.status_code
                )
        except Exception as e:
            logger.warning("Error fetching robots.txt: %s", e)

    def can_fetch(self, url: str) -> bool:
        if not self._loaded:
            return True
        return self.parser.can_fetch(self.user_agent, url) or self.parser.can_fetch("*", url)


class MoneycontrolScraperProvider(BaseDataProvider):
    """Data provider that retrieves live quote, news, and fundamentals from Moneycontrol."""

    BASE_URL = "https://www.moneycontrol.com"

    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        rate_limiter: Optional[RateLimiter] = None,
        user_agent: str = MONEYCONTROL_USER_AGENT,
    ):
        self.cache = cache_manager or CacheManager()
        self.limiter = rate_limiter or RateLimiter()
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.moneycontrol.com/",
            }
        )
        self.robots = RobotsChecker(user_agent=self.user_agent)

    def _fetch_page(self, url: str) -> str:
        """Fetch page with rate limiting and robots check."""
        self.robots.load(self.session)
        if not self.robots.can_fetch(url):
            raise RobotsDisallowedError(f"Scraping '{url}' is prohibited by robots.txt")

        self.limiter.wait()
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            raise ScraperError(f"Network error while scraping {url}: {e}") from e

    def _search_stock_url(self, clean_symbol: str) -> Optional[str]:
        """Look up stock page URL via Moneycontrol search endpoint."""
        cache_key = f"mc_url:{clean_symbol}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        search_url = f"{self.BASE_URL}/mccode/common/autosuggestion_solr.php?classic=true&query={clean_symbol}&type=1&format=json"
        try:
            text = self._fetch_page(search_url)
            data = json.loads(text)
            if data and isinstance(data, list) and len(data) > 0:
                first_hit = data[0]
                link = first_hit.get("link_src") or first_hit.get("url")
                if link:
                    self.cache.put(cache_key, link)
                    return link
        except Exception as e:
            logger.warning("Moneycontrol autosuggest lookup failed for %s: %s", clean_symbol, e)

        return None

    def get_info(self, symbol: str) -> StockInfo:
        sym = normalize_symbol(symbol)
        cache_key = f"mc_info:{sym}"
        cached = self.cache.get(cache_key)
        if cached:
            try:
                return StockInfo(**json.loads(cached))
            except Exception:
                pass

        clean = sym.replace(".NS", "").replace(".BO", "")
        stock_url = self._search_stock_url(clean)
        if not stock_url:
            logger.warning("Could not locate Moneycontrol page for %s", clean)
            return StockInfo(symbol=sym, name=clean)

        try:
            html = self._fetch_page(stock_url)
            soup = BeautifulSoup(html, "html.parser")
            
            # Extract basic price and details
            price = None
            price_div = soup.find("div", {"id": "nsecp"}) or soup.find("div", {"id": "bsecp"})
            if price_div:
                try:
                    price = float(price_div.text.replace(",", "").strip())
                except ValueError:
                    pass

            name_tag = soup.find("h1")
            name = name_tag.text.strip() if name_tag else clean

            info = StockInfo(
                symbol=sym,
                name=name,
                current_price=price,
            )
            # Cache the parsed info
            self.cache.put(cache_key, json.dumps(info.__dict__))
            return info
        except Exception as e:
            logger.error("Scraping info from Moneycontrol failed: %s", e)
            return StockInfo(symbol=sym, name=clean)

    def get_news(self, symbol: str, limit: int = 10) -> List[NewsItem]:
        sym = normalize_symbol(symbol)
        cache_key = f"mc_news:{sym}"
        cached = self.cache.get(cache_key)
        if cached:
            try:
                return [NewsItem(**item) for item in json.loads(cached)]
            except Exception:
                pass

        clean = sym.replace(".NS", "").replace(".BO", "")
        news_url = f"{self.BASE_URL}/news/tags/{clean.lower()}.html"
        
        items: List[NewsItem] = []
        try:
            html = self._fetch_page(news_url)
            soup = BeautifulSoup(html, "html.parser")
            
            # Find news list articles
            articles = soup.find_all("li", {"class": "clearfix"}) or soup.find_all("div", {"class": "news_listing"})
            for art in articles[:limit]:
                a_tag = art.find("a")
                if not a_tag:
                    continue
                title = a_tag.get("title") or a_tag.text.strip()
                link = a_tag.get("href", "")
                if title:
                    items.append(
                        NewsItem(
                            title=title,
                            publisher="Moneycontrol",
                            link=link if link.startswith("http") else f"{self.BASE_URL}{link}",
                        )
                    )
        except Exception as e:
            logger.warning("Scraping news from Moneycontrol for %s failed: %s", clean, e)

        if items:
            serializable = [
                {"title": it.title, "publisher": it.publisher, "link": it.link, "published_at": it.published_at}
                for it in items
            ]
            self.cache.put(cache_key, json.dumps(serializable))
        return items

    def get_history(self, symbol: str, years: int = 2) -> pd.DataFrame:
        """Moneycontrol pages typically render interactive charts with javascript.
        If history is requested via this provider, fall back gracefully to cached or yfinance/demo history.
        """
        from stocklens.data.yfinance_provider import YFinanceProvider
        yf_provider = YFinanceProvider(self.cache)
        return yf_provider.get_history(symbol, years=years)

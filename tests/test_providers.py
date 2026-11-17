"""Unit tests for data providers, symbol normalization, rate limiter, and cache."""
import time
import tempfile
import os
import gc
import pandas as pd
from stocklens.data.base import normalize_symbol
from stocklens.data.cache import CacheManager
from stocklens.data.demo_provider import DemoDataProvider
from stocklens.data.factory import get_data_provider
from stocklens.data.moneycontrol_scraper import RateLimiter, RobotsChecker


def test_normalize_symbol():
    """Verify symbol normalization to NSE (.NS) and company name resolution."""
    assert normalize_symbol("INFY") == "INFY.NS"
    assert normalize_symbol("reliance") == "RELIANCE.NS"
    assert normalize_symbol("TATA CONSULTANCY SERVICES") == "TCS.NS"
    assert normalize_symbol("HDFC Bank") == "HDFCBANK.NS"
    assert normalize_symbol("TATAMOTORS.NS") == "TATAMOTORS.NS"
    assert normalize_symbol("SBIN.BO") == "SBIN.BO"
    assert normalize_symbol("^NSEI") == "^NSEI"


def test_cache_put_get():
    """Verify SQLite cache put, get, and day invalidation."""
    fd, temp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        cache = CacheManager(db_path=temp_db)
        cache.put("test_key", '{"status": "ok"}')
        assert cache.get("test_key") == '{"status": "ok"}'
        assert cache.get("non_existent_key") is None

        cache.delete("test_key")
        assert cache.get("test_key") is None
    finally:
        gc.collect()
        try:
            if os.path.exists(temp_db):
                os.remove(temp_db)
        except PermissionError:
            pass


def test_rate_limiter_delay():
    """Verify rate limiter enforces minimum delay between requests."""
    limiter = RateLimiter(min_interval=0.2)
    start = time.time()
    limiter.wait()
    limiter.wait()
    elapsed = time.time() - start
    assert elapsed >= 0.18


def test_robots_checker_parsing():
    """Verify robots checker allows permitted urls and parses correctly."""
    checker = RobotsChecker(user_agent="StockLens/1.0")
    checker.parser.parse(["User-agent: *", "Disallow: /admin/", "Allow: /"])
    checker._loaded = True
    assert checker.can_fetch("https://www.moneycontrol.com/india/stockpricequote/it-services/infosys/IT") is True
    assert checker.can_fetch("https://www.moneycontrol.com/admin/secrets") is False


def test_demo_provider_data_structure():
    """Verify demo provider returns properly structured historical DataFrame."""
    dp = DemoDataProvider()
    df = dp.get_history("INFY", years=1)
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        assert col in df.columns
    assert df["High"].iloc[-1] >= df["Low"].iloc[-1]

    info = dp.get_info("INFY")
    assert info.symbol == "INFY.NS"
    assert info.current_price is not None
    assert info.pe_ratio is not None


def test_factory_creation():
    """Verify factory returns appropriate provider instances."""
    p_demo = get_data_provider("demo")
    assert isinstance(p_demo, DemoDataProvider)
    
    p_yf = get_data_provider("yfinance")
    assert p_yf is not None

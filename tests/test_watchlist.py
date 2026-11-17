"""Unit tests for Watchlist and Alert Engine."""
import tempfile
import os
import gc
from stocklens.watchlist.manager import WatchlistManager
from stocklens.data.demo_provider import DemoDataProvider


def test_watchlist_crud():
    """Verify adding, updating, and removing watchlist items in SQLite."""
    fd, temp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        wm = WatchlistManager(db_path=temp_db)
        
        # Add stock
        wm.add_stock("INFY", target_high=2000.0, target_low=1600.0, rsi_lower=30.0, rsi_upper=70.0, notes="Core IT")
        items = wm.get_watchlist()
        assert len(items) == 1
        assert items[0]["symbol"] == "INFY.NS"
        assert items[0]["target_price_high"] == 2000.0
        assert items[0]["notes"] == "Core IT"

        # Update existing stock
        wm.add_stock("INFY", target_high=2100.0)
        items = wm.get_watchlist()
        assert len(items) == 1
        assert items[0]["target_price_high"] == 2100.0

        # Remove stock
        removed = wm.remove_stock("INFY")
        assert removed is True
        assert len(wm.get_watchlist()) == 0
    finally:
        gc.collect()
        try:
            if os.path.exists(temp_db):
                os.remove(temp_db)
        except PermissionError:
            pass


def test_watchlist_alert_triggers():
    """Verify alert triggers when target price or RSI condition is met."""
    fd, temp_db = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    try:
        wm = WatchlistManager(db_path=temp_db)
        demo_provider = DemoDataProvider()
        
        # INFY base price in demo is 1850.
        # Set target_high = 1800 (should trigger PRICE_TARGET_HIGH since 1850 >= 1800)
        # Set target_low = 1900 (should trigger PRICE_TARGET_LOW since 1850 <= 1900)
        wm.add_stock("INFY", target_high=1800.0, target_low=1900.0, alert_sentiment=1)

        fired = wm.check_alerts(demo_provider)
        alert_types = [a["type"] for a in fired]
        
        assert "PRICE_TARGET_HIGH" in alert_types
        assert "PRICE_TARGET_LOW" in alert_types
        assert "NEWS_POSITIVE" in alert_types

        # Check logged history
        hist = wm.get_alert_history()
        assert len(hist) >= 2
    finally:
        gc.collect()
        try:
            if os.path.exists(temp_db):
                os.remove(temp_db)
        except PermissionError:
            pass

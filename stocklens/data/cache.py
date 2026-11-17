"""SQLite caching layer and database storage for StockLens."""
import sqlite3
import datetime
import logging
from contextlib import contextmanager
from typing import Optional, Generator
from stocklens.config import CACHE_DB_PATH

logger = logging.getLogger(__name__)


class CacheManager:
    """Manages SQLite cache for price history, fundamentals, news, and watchlist."""

    def __init__(self, db_path: str = CACHE_DB_PATH):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create necessary tables if they do not exist."""
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    day TEXT,
                    payload TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT UNIQUE NOT NULL,
                    target_price_high REAL,
                    target_price_low REAL,
                    rsi_lower REAL,
                    rsi_upper REAL,
                    alert_sentiment INTEGER DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    message TEXT NOT NULL,
                    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def get(self, key: str, max_age_days: int = 1) -> Optional[str]:
        """Retrieve cached string payload if not expired."""
        try:
            today_str = str(datetime.date.today())
            with self._connection() as conn:
                row = conn.execute(
                    "SELECT day, payload FROM cache WHERE key = ?", (key,)
                ).fetchone()
                if not row:
                    return None
                
                day, payload = row["day"], row["payload"]
                if max_age_days == 1 and day != today_str:
                    return None
                return payload
        except Exception as e:
            logger.warning("Cache read failed for key %s: %s", key, e)
            return None

    def put(self, key: str, payload: str) -> None:
        """Insert or replace cache entry for today."""
        try:
            today_str = str(datetime.date.today())
            with self._connection() as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cache (key, day, payload, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (key, today_str, payload),
                )
                conn.commit()
        except Exception as e:
            logger.warning("Cache write failed for key %s: %s", key, e)

    def delete(self, key: str) -> None:
        """Delete specific cache entry."""
        with self._connection() as conn:
            conn.execute("DELETE FROM cache WHERE key = ?", (key,))
            conn.commit()

    def clear_all(self) -> None:
        """Clear all cached entries."""
        with self._connection() as conn:
            conn.execute("DELETE FROM cache")
            conn.commit()

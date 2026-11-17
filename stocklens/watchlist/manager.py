"""Watchlist and alerts evaluation engine using SQLite storage."""
import sqlite3
import logging
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Generator
from stocklens.config import CACHE_DB_PATH
from stocklens.data.base import BaseDataProvider, normalize_symbol
from stocklens.analysis.indicators import rsi
from stocklens.analysis.sentiment import score_news_batch

logger = logging.getLogger(__name__)


class WatchlistManager:
    """Manages favorite stocks, user-defined alert thresholds, and triggers."""

    def __init__(self, db_path: str = CACHE_DB_PATH):
        self.db_path = db_path
        self._init_tables()

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_tables(self) -> None:
        with self._connection() as conn:
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

    def add_stock(
        self,
        symbol: str,
        target_high: Optional[float] = None,
        target_low: Optional[float] = None,
        rsi_lower: Optional[float] = None,
        rsi_upper: Optional[float] = None,
        alert_sentiment: int = 0,
        notes: str = "",
    ) -> bool:
        """Add or update stock in the watchlist with custom alert conditions."""
        norm_sym = normalize_symbol(symbol)
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO watchlist (
                    symbol, target_price_high, target_price_low,
                    rsi_lower, rsi_upper, alert_sentiment, notes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    target_price_high = excluded.target_price_high,
                    target_price_low = excluded.target_price_low,
                    rsi_lower = excluded.rsi_lower,
                    rsi_upper = excluded.rsi_upper,
                    alert_sentiment = excluded.alert_sentiment,
                    notes = excluded.notes
                """,
                (norm_sym, target_high, target_low, rsi_lower, rsi_upper, alert_sentiment, notes),
            )
            conn.commit()
            return True

    def remove_stock(self, symbol: str) -> bool:
        """Remove stock from the watchlist."""
        norm_sym = normalize_symbol(symbol)
        with self._connection() as conn:
            cursor = conn.execute("DELETE FROM watchlist WHERE symbol = ?", (norm_sym,))
            conn.commit()
            return cursor.rowcount > 0

    def get_watchlist(self) -> List[Dict[str, Any]]:
        """Fetch all stocks saved in the watchlist."""
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM watchlist ORDER BY created_at DESC"
            ).fetchall()
            return [dict(r) for r in rows]

    def log_alert(self, symbol: str, alert_type: str, message: str) -> None:
        """Log a triggered alert to the audit history."""
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO alert_history (symbol, alert_type, message)
                VALUES (?, ?, ?)
                """,
                (symbol, alert_type, message),
            )
            conn.commit()

    def get_alert_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent alert notification history."""
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM alert_history ORDER BY triggered_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def check_alerts(self, provider: BaseDataProvider) -> List[Dict[str, Any]]:
        """Check all watchlist conditions against current market data and log triggered alerts."""
        items = self.get_watchlist()
        triggered_alerts: List[Dict[str, Any]] = []

        for item in items:
            sym = item["symbol"]
            target_high = item.get("target_price_high")
            target_low = item.get("target_price_low")
            rsi_lower = item.get("rsi_lower")
            rsi_upper = item.get("rsi_upper")
            alert_sentiment = item.get("alert_sentiment", 0)

            try:
                # 1. Price check
                info = provider.get_info(sym)
                current_price = info.current_price

                if current_price is not None:
                    if target_high and current_price >= target_high:
                        msg = f"Price target reached: ₹{current_price:,.2f} >= ₹{target_high:,.2f}"
                        self.log_alert(sym, "PRICE_TARGET_HIGH", msg)
                        triggered_alerts.append({"symbol": sym, "type": "PRICE_TARGET_HIGH", "message": msg})

                    if target_low and current_price <= target_low:
                        msg = f"Price dip alert: ₹{current_price:,.2f} <= ₹{target_low:,.2f}"
                        self.log_alert(sym, "PRICE_TARGET_LOW", msg)
                        triggered_alerts.append({"symbol": sym, "type": "PRICE_TARGET_LOW", "message": msg})

                # 2. RSI check
                if rsi_lower or rsi_upper:
                    try:
                        hist = provider.get_history(sym, years=1)
                        if not hist.empty and "Close" in hist.columns:
                            rsi_series = rsi(hist["Close"])
                            latest_rsi = float(rsi_series.iloc[-1])
                            
                            if rsi_lower and latest_rsi <= rsi_lower:
                                msg = f"RSI oversold condition: RSI {latest_rsi:.1f} <= {rsi_lower:.1f}"
                                self.log_alert(sym, "RSI_OVERSOLD", msg)
                                triggered_alerts.append({"symbol": sym, "type": "RSI_OVERSOLD", "message": msg})

                            if rsi_upper and latest_rsi >= rsi_upper:
                                msg = f"RSI overbought condition: RSI {latest_rsi:.1f} >= {rsi_upper:.1f}"
                                self.log_alert(sym, "RSI_OVERBOUGHT", msg)
                                triggered_alerts.append({"symbol": sym, "type": "RSI_OVERBOUGHT", "message": msg})
                    except Exception as e:
                        logger.warning("Could not calculate RSI for alert check on %s: %s", sym, e)

                # 3. News sentiment check
                if alert_sentiment != 0:
                    try:
                        news_items = provider.get_news(sym, limit=3)
                        sentiment_results = score_news_batch(news_items)
                        for s_res in sentiment_results:
                            if alert_sentiment == 1 and s_res.score >= 0.3:
                                msg = f"Positive news alert: '{s_res.headline}' (Score: {s_res.score:+.2f})"
                                self.log_alert(sym, "NEWS_POSITIVE", msg)
                                triggered_alerts.append({"symbol": sym, "type": "NEWS_POSITIVE", "message": msg})
                                break
                            elif alert_sentiment == -1 and s_res.score <= -0.3:
                                msg = f"Negative news alert: '{s_res.headline}' (Score: {s_res.score:+.2f})"
                                self.log_alert(sym, "NEWS_NEGATIVE", msg)
                                triggered_alerts.append({"symbol": sym, "type": "NEWS_NEGATIVE", "message": msg})
                                break
                    except Exception as e:
                        logger.warning("Could not check news sentiment for %s: %s", sym, e)

            except Exception as e:
                logger.error("Error evaluating alert rules for %s: %s", sym, e)

        return triggered_alerts

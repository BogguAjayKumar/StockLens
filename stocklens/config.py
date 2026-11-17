"""Configuration and environment management for StockLens."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Database configuration
CACHE_DB_PATH = os.getenv("STOCKLENS_DB_PATH", str(BASE_DIR / "stocklens_cache.db"))

# Data provider configuration
DEFAULT_PROVIDER = os.getenv("STOCKLENS_DEFAULT_PROVIDER", "yfinance")

# Moneycontrol scraper configuration
MONEYCONTROL_USER_AGENT = os.getenv(
    "MONEYCONTROL_USER_AGENT",
    "StockLens/1.0 (Indian Stock Analysis Educational Project; contact: user@stocklens.local)"
)
SCRAPER_RATE_LIMIT_SECONDS = float(os.getenv("SCRAPER_RATE_LIMIT_SECONDS", "2.5"))
CACHE_EXPIRY_HOURS = int(os.getenv("STOCKLENS_CACHE_HOURS", "24"))

# Optional API Keys loaded from .env (never hardcoded)
NSE_API_KEY = os.getenv("NSE_API_KEY", "")
FINANCIAL_API_KEY = os.getenv("FINANCIAL_API_KEY", "")

# Educational Disclaimer
DISCLAIMER = (
    "Educational analysis only. Not financial or investment advice. "
    "Always verify numbers with official regulatory and stock exchange filings (NSE/BSE/SEBI)."
)

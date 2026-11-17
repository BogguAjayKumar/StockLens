# StockLens
### Intelligent Indian Stock Market & IPO Real-Time Intelligence Platform

> **Educational & Research Use Only**  
> StockLens is built strictly for educational, research, and technical analysis purposes. It does not provide financial or investment advice. Always verify data and financial ratios with official regulatory filings and disclosures on [NSE India](https://www.nseindia.com) and [BSE India](https://www.bseindia.com).

---

## Key Capabilities

1. **Free Real-Time Ticks & Exact Intraday Candles**
   - **Zero-cost live feeds**: Pulls real-time prices, market breadth (Advances/Declines/Unchanged), order book stats, and intraday candles (1m, 5m, 15m) using NSE official session queries and high-resolution feeds.
   - **Broker API Readiness**: Connects with free Indian broker APIs (Dhan HQ, Shoonya/Finvasia) via credentials in `.env`, or seamlessly defaults to the zero-key official exchange session.

2. **Real-Time Trend Explainer ("The Why Engine")**
   - Synthesizes multi-factor price action, relative volume (RVOL), candlestick patterns, 50/200 DMA, RSI, and MACD into **plain-language institutional explanations**.
   - Answers: *What is the trend verdict? Why is the stock moving right now? What are the immediate pivots, support (S1), resistance (R1), and risk/reward outcome?*
   - Detects intraday price action candlestick patterns: **Hammer, Shooting Star, Bullish/Bearish Engulfing, Doji, and Marubozu**.

3. **Indian IPO Intelligence Tracker & Outcome Analyzer**
   - Tracks active, upcoming, and recently listed Indian IPOs (Mainboard & SME).
   - Monitors Price Bands, Issue Size (in ₹ Cr), Lot Size, and Open/Close dates.
   - Computes overall Subscription Multipliers (QIB/NII/Retail) and Grey Market Premiums (GMP %).
   - Generates listing-day outcome explanations (e.g. *High Listing Gains Potential*, *Moderate Gains*, *Discount Listing Risk*).

4. **Multi-Day Continuous Live Surveillance Daemon**
   - Designed to run continuously in the background for a trial of days (`python run_live.py` or `python main.py --live`).
   - Polls ticks every 15–30 seconds, computes 5-minute candle signals, checks user-defined price/RSI/news alert rules, and logs outcomes into SQLite (`live_stream_log`).

5. **Fundamental & Valuation Scorecard**
   - Standardized in Indian Rupee denominations (₹ Crores and Lakh Crores).
   - Multiples: P/E, Forward P/E, P/B, EV/EBITDA, Return on Equity (ROE), Debt/Equity, Net Profit Margin, Revenue Growth, and Dividend Yield.
   - **Market Cap Tiers**: Categorization into Large Cap (> ₹20,000 Cr), Mid Cap (₹5,000–₹20,000 Cr), and Small Cap (< ₹5,000 Cr).
   - Multi-factor Fundamental Health Scorecard (0–100 score).

6. **Local Offline News Sentiment Analysis**
   - Operates 100% offline without any paid APIs.
   - Financial domain lexicon covering Indian earnings reports, order wins, regulatory scrutiny, and corporate actions.
   - Accurately parses contextual negations (*"did not fall"*, *"failed to rise"*) and intensifiers (*"sharply"*, *"significantly"*).

7. **Streamlit Interactive Web Dashboard**
   - Multi-tab command center: Real-time Trend Explainer, Live 1m/5m Intraday Candlestick charts with VWAP, IPO Intelligence Center, Technical Overlays, Sector Peers, and Watchlist Alert Manager.

---

## Modular Directory Structure

```
Market/
├── stocklens/                   # Core package
│   ├── config.py                # Environment configuration & .env loader
│   ├── data/                    # Pluggable data layer
│   │   ├── base.py              # BaseDataProvider interface, StockInfo, NewsItem
│   │   ├── nse_live.py          # Official free NSE live session & intraday feed
│   │   ├── broker_api.py        # Broker API client (Dhan, Shoonya, Angel One)
│   │   ├── yfinance_provider.py # yfinance integration
│   │   ├── moneycontrol_scraper.py # Moneycontrol scraper (robots.txt, 2.5s rate limiter)
│   │   ├── demo_provider.py     # Offline synthetic data generator
│   │   ├── cache.py             # SQLite cache manager (stocklens_cache.db)
│   │   └── factory.py           # Provider factory
│   ├── analysis/                # Quantitative & technical analysis
│   │   ├── indicators.py        # 50/200 DMA, RSI(14), MACD, Volatility, Drawdown
│   │   ├── explainer.py         # Real-time trend & outcome explainer engine
│   │   ├── ipo.py               # Indian IPO tracker, GMP & listing outcome analyzer
│   │   ├── valuation.py         # Multiples, health scorecard, INR formatting
│   │   ├── peers.py             # Sector peer comparison matrix
│   │   └── sentiment.py         # Offline local financial news sentiment
│   ├── watchlist/               # Alert & Watchlist management
│   │   └── manager.py           # SQLite watchlist and alert engine
│   ├── live_runner.py           # Multi-day background surveillance engine
│   └── ui/                      # User interfaces
│       ├── cli.py               # Terminal report with rich tables
│       └── dashboard.py         # Multi-tab Streamlit dashboard
├── tests/                       # 47 Unit tests with known-value checks
├── run_live.py                  # Live surveillance trial daemon script
├── main.py                      # Primary CLI entrypoint
├── requirements.txt             # Dependencies
├── .env.example                 # Environment variables template
└── README.md                    # Documentation
```

---

## Quickstart Commands

### 1. Run Live Stock Analysis & Trend Explainer
```bash
python main.py INFY
python main.py RELIANCE
python main.py TCS
```

### 2. View Active & Upcoming Indian IPOs
```bash
python main.py --ipos
```

### 3. Launch Multi-Day Continuous Surveillance Trial
```bash
# Monitor default stocks (INFY, TCS, RELIANCE, HDFCBANK, WIPRO) for 3 days
python run_live.py

# Or customize symbols, interval, and trial duration:
python run_live.py --symbols INFY,TCS,RELIANCE --interval 15 --days 3
```

### 4. Interactive Streamlit Web Dashboard
```bash
python main.py --dashboard
# Or:
streamlit run stocklens/ui/dashboard.py
```

### 5. Watchlist & Condition-Based Alerts
```bash
# Add a stock with target price, RSI threshold, and news sentiment rules
python main.py --add-watchlist INFY --target-high 2600 --target-low 1600 --rsi-buy 30 --rsi-sell 70 --news-alert 1 --notes "Core IT"

# View saved watchlist
python main.py --watchlist

# Check alerts against current market data
python main.py --check-alerts
```

### 6. Run Complete Test Suite
```bash
pytest
# Result: 47 passed in ~3s
```

---

## Disclaimer
Educational and research use only. Not investment advice. Always verify with official SEBI and stock exchange disclosures.

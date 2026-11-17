# StockLens
Indian stock analysis (NSE by default). Educational use only, not investment advice.

    pip install -r requirements.txt
    python main.py INFY            # analyse a stock (needs internet)
    python main.py --demo          # try it offline with fake data
    pytest                         # run indicator tests

Files: `data.py` (swap this to change data source), `indicators.py` (SMA, EMA, RSI, MACD, volatility, drawdown),
`main.py` (report). Prices are cached per day in `stocklens_cache.db`.
Next ideas: watchlist + alerts, peer comparison, Streamlit dashboard, voice front-end via Benz.

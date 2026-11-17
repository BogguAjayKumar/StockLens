"""StockLens: python main.py INFY   |   python main.py --demo
Educational use only. Not investment advice."""
import argparse
import numpy as np
import pandas as pd
import indicators as ix

DISCLAIMER = "Educational analysis only. Not investment advice. Verify numbers with official filings."


def demo_data() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    close = 1500 * np.exp(np.cumsum(rng.normal(0.0004, 0.014, 520)))
    idx = pd.bdate_range(end=pd.Timestamp.today().normalize(), periods=520)
    return pd.DataFrame({"Close": close, "Volume": rng.integers(1e6, 5e6, 520)}, index=idx)


def fmt(v, kind=""):
    if v is None: return "n/a"
    if kind == "cr": return f"₹{v / 1e7:,.0f} cr"
    if kind == "pct": return f"{v * 100:.1f}%"
    return f"{v:,.2f}"


def report(sym, df, info, news):
    close = df["Close"]
    last = close.iloc[-1]
    ret = lambda n: (last / close.iloc[-n - 1] - 1) * 100 if len(close) > n else float("nan")
    print(f"\n=== {sym}  {info.get('longName') or ''} ===")
    print(f"Price: ₹{last:,.2f}   Sector: {info.get('sector') or 'n/a'}")
    print(f"52w range: {fmt(info.get('fiftyTwoWeekLow'))} - {fmt(info.get('fiftyTwoWeekHigh'))}   Market cap: {fmt(info.get('marketCap'), 'cr')}")
    print(f"P/E: {fmt(info.get('trailingPE'))}   P/B: {fmt(info.get('priceToBook'))}   ROE: {fmt(info.get('returnOnEquity'), 'pct')}   "
          f"Debt/Equity: {fmt(info.get('debtToEquity'))}   Profit margin: {fmt(info.get('profitMargins'), 'pct')}")
    print(f"\nReturns: 1M {ret(21):+.1f}%  3M {ret(63):+.1f}%  6M {ret(126):+.1f}%  1Y {ret(252):+.1f}%")
    print(f"Volatility (annual): {ix.annual_volatility(close) * 100:.1f}%   Max drawdown: {ix.max_drawdown(close) * 100:.1f}%")
    print("\nTechnical reading:")
    for k, v in ix.signals(close).items():
        print(f"  {k}: {v}")
    if news:
        print("\nRecent headlines (offline sentiment, crude):")
        for t, s in news: print(f"  [{s}] {t}")
    print(f"\n{DISCLAIMER}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol", nargs="?", help="e.g. INFY, TCS, RELIANCE")
    ap.add_argument("--demo", action="store_true", help="run on fake data, no internet")
    a = ap.parse_args()
    if a.demo or not a.symbol:
        report("DEMO.NS", demo_data(), {"longName": "Synthetic demo data"}, [])
    else:
        import data
        sym = data.normalize(a.symbol)
        report(sym, data.get_history(sym), data.get_info(sym), data.get_news_sentiment(sym))

"""Data layer. Swap this file to change providers (yfinance, NSE feed, a paid API...)."""
import io, json, sqlite3, datetime
import pandas as pd

DB = "stocklens_cache.db"
POS = {"surge", "beat", "beats", "record", "growth", "profit", "gain", "gains", "upgrade", "strong", "wins", "order", "buy", "rally", "rise", "jumps"}
NEG = {"fall", "falls", "drop", "loss", "losses", "downgrade", "weak", "fraud", "probe", "fine", "miss", "misses", "cut", "slump", "plunge", "sell", "debt", "decline"}


def normalize(sym: str) -> str:
    sym = sym.upper().strip()
    return sym if "." in sym or sym.startswith("^") else sym + ".NS"  # NSE by default


def _cache():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS cache(key TEXT PRIMARY KEY, day TEXT, payload TEXT)")
    return c


def _get(key):
    r = _cache().execute("SELECT day, payload FROM cache WHERE key=?", (key,)).fetchone()
    return r[1] if r and r[0] == str(datetime.date.today()) else None


def _put(key, payload):
    c = _cache(); c.execute("INSERT OR REPLACE INTO cache VALUES(?,?,?)", (key, str(datetime.date.today()), payload)); c.commit()


def get_history(sym: str, years: int = 2) -> pd.DataFrame:
    key = f"hist:{sym}:{years}"
    if (hit := _get(key)):
        return pd.read_json(io.StringIO(hit))
    import yfinance as yf
    df = yf.Ticker(sym).history(period=f"{years}y", auto_adjust=True)
    if df.empty:
        raise ValueError(f"No price data for {sym}. Check the symbol (try RELIANCE, TCS, INFY).")
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.index = df.index.tz_localize(None)
    _put(key, df.to_json())
    return df


def get_info(sym: str) -> dict:
    keys = ["longName", "sector", "marketCap", "trailingPE", "priceToBook", "returnOnEquity",
            "debtToEquity", "profitMargins", "revenueGrowth", "fiftyTwoWeekHigh", "fiftyTwoWeekLow"]
    key = f"info:{sym}"
    if (hit := _get(key)):
        return json.loads(hit)
    try:
        import yfinance as yf
        raw = yf.Ticker(sym).info
        info = {k: raw.get(k) for k in keys}
    except Exception:
        info = {k: None for k in keys}
    _put(key, json.dumps(info))
    return info


def get_news_sentiment(sym: str, limit: int = 10):
    """Offline lexicon scoring of recent headlines. Crude, treat as a hint only."""
    try:
        import yfinance as yf
        items = yf.Ticker(sym).news[:limit]
    except Exception:
        return []
    out = []
    for n in items:
        title = n.get("title") or (n.get("content") or {}).get("title")
        if not title: continue
        words = {w.strip(".,:;!?'\"").lower() for w in title.split()}
        score = len(words & POS) - len(words & NEG)
        out.append((title, "positive" if score > 0 else "negative" if score < 0 else "neutral"))
    return out

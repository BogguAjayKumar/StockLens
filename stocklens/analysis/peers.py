"""Peer comparison and sector analysis module for Indian markets."""
from typing import List, Optional, Dict
import pandas as pd

from stocklens.data.base import BaseDataProvider, normalize_symbol, StockInfo
from stocklens.analysis.indicators import annual_volatility
from stocklens.analysis.valuation import calculate_returns, market_cap_category, format_currency_inr

SECTOR_PEERS_MAP: Dict[str, List[str]] = {
    "IT": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS", "LTIM.NS"],
    "BANK": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS"],
    "ENERGY": ["RELIANCE.NS", "ONGC.NS", "IOC.NS", "BPCL.NS", "NTPC.NS", "POWERGRID.NS"],
    "AUTO": ["TATAMOTORS.NS", "MARUTI.NS", "M&M.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS"],
    "FMCG": ["HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS"],
    "PHARMA": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "LUPIN.NS"],
    "METALS": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "VEDL.NS", "COALINDIA.NS"],
    "INFRA": ["LT.NS", "ADANIPORTS.NS", "ADANIENT.NS", "ULTRACEMCO.NS", "GRASIM.NS"],
    "TELECOM": ["BHARTIARTL.NS", "IDEA.NS", "TATACOMM.NS"],
}


def get_sector_peers(symbol: str, sector_hint: Optional[str] = None) -> List[str]:
    """Find peers for a given symbol by looking up sector mappings."""
    norm = normalize_symbol(symbol)
    
    # Check if symbol is in any sector list
    for sector_key, peers in SECTOR_PEERS_MAP.items():
        if norm in peers:
            return [p for p in peers if p != norm]

    # Try sector hint
    if sector_hint:
        sh = sector_hint.upper()
        if "TECH" in sh or "SOFTWARE" in sh or "IT" in sh:
            return [p for p in SECTOR_PEERS_MAP["IT"] if p != norm]
        if "BANK" in sh or "FINANC" in sh:
            return [p for p in SECTOR_PEERS_MAP["BANK"] if p != norm]
        if "ENERGY" in sh or "OIL" in sh or "GAS" in sh:
            return [p for p in SECTOR_PEERS_MAP["ENERGY"] if p != norm]
        if "AUTO" in sh or "VEHICLE" in sh:
            return [p for p in SECTOR_PEERS_MAP["AUTO"] if p != norm]
        if "CONSUMER" in sh or "FMCG" in sh or "FOOD" in sh:
            return [p for p in SECTOR_PEERS_MAP["FMCG"] if p != norm]
        if "PHARMA" in sh or "HEALTH" in sh:
            return [p for p in SECTOR_PEERS_MAP["PHARMA"] if p != norm]
        if "METAL" in sh or "STEEL" in sh or "MINING" in sh:
            return [p for p in SECTOR_PEERS_MAP["METALS"] if p != norm]

    # Default fallback to major bellwethers
    return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS"]


def compare_peers(
    symbols: List[str], provider: BaseDataProvider, max_peers: int = 5
) -> pd.DataFrame:
    """Compare a list of stock symbols across valuation and technical metrics."""
    records = []
    
    for sym in symbols[:max_peers]:
        try:
            norm = normalize_symbol(sym)
            info = provider.get_info(norm)
            
            # Fetch price history to compute return & volatility
            ret_1y = None
            vol_ann = None
            try:
                hist = provider.get_history(norm, years=1)
                if not hist.empty and "Close" in hist.columns:
                    rets = calculate_returns(hist["Close"])
                    ret_1y = rets.get("1Y")
                    vol_ann = annual_volatility(hist["Close"]) * 100.0
            except Exception:
                pass

            records.append({
                "Symbol": norm.replace(".NS", ""),
                "Name": info.name or norm,
                "Price": info.current_price,
                "P/E": info.pe_ratio,
                "P/B": info.pb_ratio,
                "ROE (%)": (info.roe * 100.0) if info.roe is not None else None,
                "D/E": info.debt_to_equity,
                "1Y Return (%)": ret_1y,
                "Volatility (%)": vol_ann,
                "Market Cap": format_currency_inr(info.market_cap),
                "Category": market_cap_category(info.market_cap),
            })
        except Exception:
            continue

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)

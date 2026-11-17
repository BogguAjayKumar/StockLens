"""StockLens: Indian Stock Market Analysis, IPO Intelligence & Real-Time Surveillance.
Educational use only. Not investment advice.

Usage:
    python main.py INFY                  # Analyse a stock via live feeds
    python main.py --ipos                # Track active & upcoming Indian IPOs and outcomes
    python main.py --live                # Start continuous real-time market surveillance trial
    python main.py --watchlist           # View saved watchlist and alert rules
    python main.py --check-alerts        # Evaluate all alert rules against current data
    python main.py --dashboard           # Launch interactive Streamlit web dashboard
    python main.py --demo                # Offline demo on synthetic data
    pytest                               # Run complete 47-test indicator & explainer suite
"""
import argparse
import sys
import subprocess
from pathlib import Path

from stocklens.config import DISCLAIMER
from stocklens.data.factory import get_data_provider
from stocklens.ui.cli import (
    run_stock_report,
    display_watchlist,
    check_and_show_alerts,
    display_ipos,
    print_disclaimer,
)
from stocklens.watchlist.manager import WatchlistManager
from stocklens.live_runner import LiveRunner


def main() -> None:
    parser = argparse.ArgumentParser(
        description="StockLens: Indian Stock Market Analysis & Real-Time Intelligence Platform."
    )
    parser.add_argument(
        "symbol",
        nargs="?",
        help="Stock ticker or company name (e.g. INFY, TCS, RELIANCE, HDFCBANK, WIPRO)",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run offline analysis using synthetic data (no internet required)",
    )
    parser.add_argument(
        "--provider",
        choices=["yfinance", "moneycontrol", "demo"],
        default=None,
        help="Select pluggable data provider (yfinance, moneycontrol, demo)",
    )
    parser.add_argument(
        "--peers",
        action="store_true",
        default=True,
        help="Include sector peer comparison (default: True)",
    )
    parser.add_argument(
        "--ipos",
        action="store_true",
        help="Display active and upcoming Indian IPO intelligence and listing outcome verdicts",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Launch continuous real-time market surveillance trial loop",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Interval in seconds for live surveillance (default: 15)",
    )
    parser.add_argument(
        "--trial-days",
        type=int,
        default=3,
        help="Trial duration in days to run continuous surveillance (default: 3)",
    )
    parser.add_argument(
        "--watchlist",
        action="store_true",
        help="Show all saved stocks and alert rules in watchlist",
    )
    parser.add_argument(
        "--check-alerts",
        action="store_true",
        help="Evaluate alert conditions (price targets, RSI, news) across watchlist",
    )
    parser.add_argument(
        "--add-watchlist",
        metavar="SYMBOL",
        help="Add or update a stock in the watchlist",
    )
    parser.add_argument("--target-high", type=float, help="Target price high alert condition")
    parser.add_argument("--target-low", type=float, help="Target price low alert condition")
    parser.add_argument("--rsi-buy", type=float, help="RSI oversold buy alert threshold (e.g. 30)")
    parser.add_argument("--rsi-sell", type=float, help="RSI overbought sell alert threshold (e.g. 70)")
    parser.add_argument("--news-alert", type=int, choices=[-1, 0, 1], default=0, help="News alert: 1 (positive), -1 (negative), 0 (off)")
    parser.add_argument("--notes", default="", help="Optional notes for watchlist item")
    parser.add_argument(
        "--remove-watchlist",
        metavar="SYMBOL",
        help="Remove a stock from the watchlist",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch the interactive Streamlit web dashboard",
    )

    args = parser.parse_args()

    # Launch Streamlit dashboard
    if args.dashboard:
        dashboard_script = str(Path(__file__).resolve().parent / "stocklens" / "ui" / "dashboard.py")
        cmd = [sys.executable, "-m", "streamlit", "run", dashboard_script]
        print(f"Launching Streamlit Dashboard: {' '.join(cmd)}")
        subprocess.run(cmd)
        return

    # Continuous Live Market Surveillance Trial
    if args.live:
        symbols_to_monitor = [args.symbol] if args.symbol else ["INFY", "TCS", "RELIANCE", "HDFCBANK", "WIPRO"]
        runner = LiveRunner(
            symbols=symbols_to_monitor,
            poll_interval_seconds=args.interval,
            trial_days=args.trial_days,
        )
        runner.start()
        return

    # IPO intelligence
    if args.ipos:
        display_ipos()
        return

    wm = WatchlistManager()

    # Watchlist actions
    if args.add_watchlist:
        wm.add_stock(
            symbol=args.add_watchlist,
            target_high=args.target_high,
            target_low=args.target_low,
            rsi_lower=args.rsi_buy,
            rsi_upper=args.rsi_sell,
            alert_sentiment=args.news_alert,
            notes=args.notes,
        )
        print(f"Added/Updated {args.add_watchlist} in watchlist.")
        display_watchlist(wm)
        return

    if args.remove_watchlist:
        if wm.remove_stock(args.remove_watchlist):
            print(f"Removed {args.remove_watchlist} from watchlist.")
        else:
            print(f"Symbol {args.remove_watchlist} not found in watchlist.")
        return

    if args.watchlist:
        display_watchlist(wm)
        return

    if args.check_alerts:
        provider_type = "demo" if args.demo else (args.provider or "yfinance")
        provider = get_data_provider(provider_type)
        check_and_show_alerts(wm, provider)
        return

    # Stock Analysis Report
    provider_type = "demo" if args.demo else (args.provider or "yfinance")
    provider = get_data_provider(provider_type)

    target_symbol = args.symbol or ("INFY" if args.demo else None)
    if not target_symbol:
        print("No stock symbol provided. Running demo mode with INFY...")
        provider = get_data_provider("demo")
        run_stock_report("INFY", provider, show_peers=False)
        return

    run_stock_report(target_symbol, provider, show_peers=args.peers)


if __name__ == "__main__":
    main()

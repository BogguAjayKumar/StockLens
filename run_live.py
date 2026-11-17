"""StockLens Real-Time Live Market Surveillance & Trial Runner.
Run this script to test the real-time live tick-by-tick monitoring,
intraday candle alerts, and AI trend explanations continuously for days.

Usage:
    python run_live.py
    python run_live.py --symbols INFY,TCS,RELIANCE,HDFCBANK --interval 15 --days 3
"""
import argparse
from stocklens.live_runner import LiveRunner


def main():
    parser = argparse.ArgumentParser(description="StockLens Real-Time Live Market Surveillance Daemon")
    parser.add_argument(
        "--symbols",
        default="INFY,TCS,RELIANCE,HDFCBANK,TATAMOTORS",
        help="Comma-separated stock symbols to monitor in real-time",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Polling and alert evaluation interval in seconds (default: 15)",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=3,
        help="Trial duration in days to run continuous surveillance (default: 3)",
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=None,
        help="Optional max cycles to run (for testing)",
    )

    args = parser.parse_args()
    sym_list = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    runner = LiveRunner(
        symbols=sym_list,
        poll_interval_seconds=args.interval,
        trial_days=args.days,
    )
    runner.start(max_cycles=args.cycles)


if __name__ == "__main__":
    main()

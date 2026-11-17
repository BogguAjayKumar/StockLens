"""Terminal command-line reporting and interactive tools for StockLens."""
import sys
import logging
from typing import Optional, List
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from stocklens.config import DISCLAIMER
from stocklens.data.base import BaseDataProvider, normalize_symbol
from stocklens.data.factory import get_data_provider
from stocklens.analysis.indicators import signals, annual_volatility, max_drawdown
from stocklens.analysis.valuation import (
    calculate_returns,
    format_currency_inr,
    format_percent,
    format_ratio,
    market_cap_category,
    valuation_scorecard,
)
from stocklens.analysis.sentiment import score_news_batch
from stocklens.analysis.peers import get_sector_peers, compare_peers
from stocklens.analysis.explainer import explain_stock_trend
from stocklens.analysis.ipo import fetch_ipos
from stocklens.watchlist.manager import WatchlistManager

console = Console()
logger = logging.getLogger(__name__)


def print_disclaimer() -> None:
    """Print the prominent educational disclaimer."""
    console.print(
        Panel(
            Text(DISCLAIMER, justify="center", style="bold yellow"),
            title="[bold red]IMPORTANT DISCLAIMER[/bold red]",
            border_style="yellow",
        )
    )


def run_stock_report(
    symbol: str,
    provider: BaseDataProvider,
    show_peers: bool = True,
    years: int = 2,
) -> None:
    """Generate and display a terminal stock analysis report."""
    norm_sym = normalize_symbol(symbol)

    with console.status(f"[bold cyan]Analyzing {norm_sym}...[/bold cyan]"):
        try:
            info = provider.get_info(norm_sym)
            history = provider.get_history(norm_sym, years=years)
            news_items = provider.get_news(norm_sym, limit=6)
        except Exception as e:
            console.print(f"[bold red]Error fetching data for {norm_sym}:[/bold red] {e}")
            return

    close = history["Close"]
    last_price = float(close.iloc[-1])
    scorecard = valuation_scorecard(info)
    sig_data = signals(close)
    returns = calculate_returns(close)

    # 1. Header Information
    mcap_str = format_currency_inr(info.market_cap)
    cap_cat = market_cap_category(info.market_cap)
    header_text = Text()
    header_text.append(f"{info.name or norm_sym} ", style="bold green")
    header_text.append(f"({norm_sym})\n", style="bold white")
    header_text.append(f"Price: ₹{last_price:,.2f}  |  ", style="bold cyan")
    header_text.append(f"Sector: {info.sector or 'N/A'}  |  ", style="white")
    header_text.append(f"Market Cap: {mcap_str} ({cap_cat})\n", style="magenta")
    
    high_52 = info.fifty_two_week_high or (float(close[-252:].max()) if len(close) >= 252 else float(close.max()))
    low_52 = info.fifty_two_week_low or (float(close[-252:].min()) if len(close) >= 252 else float(close.min()))
    header_text.append(f"52-Week Range: ₹{low_52:,.2f} - ₹{high_52:,.2f}", style="dim")

    console.print(Panel(header_text, title="StockLens Analysis", border_style="cyan"))

    # 2. Real-Time Trend Outcome & Explainer
    headlines_list = [n.title for n in news_items]
    trend_exp = explain_stock_trend(
        symbol=norm_sym,
        history=history,
        info_dict=info.to_dict(),
        headlines=headlines_list,
    )
    t_trend = Table(title="Real-Time Trend Breakdown & Outcome Explanation", show_header=True, header_style="bold green")
    t_trend.add_column("Category", style="dim", width=22)
    t_trend.add_column("Analysis / Level", style="bold")
    t_trend.add_row("Trend Verdict", trend_exp.trend_verdict)
    t_trend.add_row("Momentum Rating", trend_exp.momentum_rating)
    t_trend.add_row("Candlestick Structure", trend_exp.candlestick_pattern)
    t_trend.add_row("Central Pivot", f"₹{trend_exp.pivot_level:,.2f} (S1: ₹{trend_exp.support_level:,.2f} | R1: ₹{trend_exp.resistance_level:,.2f})")
    t_trend.add_row("Why It's Moving", trend_exp.why_is_it_moving)
    t_trend.add_row("Risk / Reward Note", trend_exp.risk_reward_verdict)
    console.print(t_trend)

    # 3. Valuation & Financial Fundamentals Table
    t_fund = Table(title="Financial Fundamentals & Valuation Ratios", show_header=True, header_style="bold magenta")
    t_fund.add_column("Metric", style="dim", width=22)
    t_fund.add_column("Value", style="bold")
    t_fund.add_column("Metric", style="dim", width=22)
    t_fund.add_column("Value", style="bold")

    t_fund.add_row(
        "P/E Ratio (Trailing)", format_ratio(info.pe_ratio),
        "Return on Equity (ROE)", format_percent(info.roe),
    )
    t_fund.add_row(
        "Price to Book (P/B)", format_ratio(info.pb_ratio),
        "Debt to Equity", format_ratio(info.debt_to_equity),
    )
    t_fund.add_row(
        "EV / EBITDA", format_ratio(info.ev_to_ebitda),
        "Net Profit Margin", format_percent(info.profit_margin),
    )
    t_fund.add_row(
        "Dividend Yield", format_percent(info.dividend_yield),
        "Revenue Growth (YoY)", format_percent(info.revenue_growth),
    )
    console.print(t_fund)

    health_style = "green" if scorecard["score"] >= 70 else "yellow" if scorecard["score"] >= 50 else "red"
    console.print(
        f"Fundamental Health Score: [{health_style}]{scorecard['score']}/100 - {scorecard['rating']}[/{health_style}]\n"
    )

    # 4. Returns & Risk Metrics
    t_ret = Table(title="Historical Returns & Risk Profile", show_header=True, header_style="bold blue")
    t_ret.add_column("1 Week", justify="center")
    t_ret.add_column("1 Month", justify="center")
    t_ret.add_column("3 Months", justify="center")
    t_ret.add_column("6 Months", justify="center")
    t_ret.add_column("1 Year", justify="center")
    t_ret.add_column("Volatility (Ann.)", justify="center")
    t_ret.add_column("Max Drawdown", justify="center")

    def _color_ret(val: Optional[float]) -> str:
        if val is None:
            return "N/A"
        color = "green" if val > 0 else "red" if val < 0 else "white"
        return f"[{color}]{val:+.1f}%[/{color}]"

    vol_pct = sig_data.get("annual_volatility", 0.0) * 100.0
    mdd_pct = sig_data.get("max_drawdown", 0.0) * 100.0
    t_ret.add_row(
        _color_ret(returns.get("1W")),
        _color_ret(returns.get("1M")),
        _color_ret(returns.get("3M")),
        _color_ret(returns.get("6M")),
        _color_ret(returns.get("1Y")),
        f"{vol_pct:.1f}% ({sig_data.get('volatility_rating', 'N/A')})",
        f"[red]{mdd_pct:.1f}%[/red]",
    )
    console.print(t_ret)

    # 5. Peer Comparison
    if show_peers:
        peers = get_sector_peers(norm_sym, info.sector)
        if peers:
            all_peers = [norm_sym] + peers[:4]
            peer_df = compare_peers(all_peers, provider)
            if not peer_df.empty:
                t_peer = Table(title="Sector Peer Comparison", show_header=True, header_style="bold yellow")
                for col in ["Symbol", "Price", "P/E", "P/B", "ROE (%)", "1Y Return (%)", "Market Cap"]:
                    if col in peer_df.columns:
                        t_peer.add_column(col)
                for _, row in peer_df.iterrows():
                    sym_style = "bold green" if row["Symbol"] in norm_sym else "white"
                    t_peer.add_row(
                        f"[{sym_style}]{row['Symbol']}[/{sym_style}]",
                        f"₹{row['Price']:,.2f}" if row['Price'] else "N/A",
                        f"{row['P/E']:.1f}" if pd.notna(row['P/E']) else "N/A",
                        f"{row['P/B']:.1f}" if pd.notna(row['P/B']) else "N/A",
                        f"{row['ROE (%)']:.1f}%" if pd.notna(row['ROE (%)']) else "N/A",
                        f"{row['1Y Return (%)']:+.1f}%" if pd.notna(row['1Y Return (%)']) else "N/A",
                        str(row['Market Cap']),
                    )
                console.print(t_peer)

    # 6. News Sentiment Panel
    if news_items:
        scored_news = score_news_batch(news_items)
        t_news = Table(title="Recent Headlines & Local Offline Sentiment", show_header=True, header_style="bold green")
        t_news.add_column("Sentiment", width=16)
        t_news.add_column("Headline")
        t_news.add_column("Publisher", style="dim", width=18)

        for sn in scored_news:
            sent_color = (
                "bold green" if "Positive" in sn.sentiment
                else "bold red" if "Negative" in sn.sentiment
                else "white"
            )
            t_news.add_row(
                f"[{sent_color}][{sn.sentiment} ({sn.score:+.2f})][/{sent_color}]",
                sn.headline,
                "News Feed",
            )
        console.print(t_news)

    print_disclaimer()


def display_ipos() -> None:
    """Display active and upcoming Indian IPO intelligence."""
    ipos = fetch_ipos()
    t_ipo = Table(title="Indian IPO Tracker & Outcome Intelligence", show_header=True, header_style="bold cyan")
    t_ipo.add_column("Company", style="bold")
    t_ipo.add_column("Type", justify="center")
    t_ipo.add_column("Price Band", justify="right")
    t_ipo.add_column("Issue (Cr)", justify="right")
    t_ipo.add_column("Subs", justify="center")
    t_ipo.add_column("GMP (%)", justify="center")
    t_ipo.add_column("Status", justify="center")
    t_ipo.add_column("Outcome Verdict", style="green")

    for it in ipos:
        gmp_color = "green" if it.gmp_percent >= 20.0 else "yellow" if it.gmp_percent > 0 else "red"
        t_ipo.add_row(
            it.company_name,
            it.category,
            it.price_band,
            f"₹{it.issue_size_cr:,.0f} Cr",
            f"{it.subscription_times:.1f}x",
            f"[{gmp_color}]+{it.gmp_percent:.1f}%[/{gmp_color}]",
            it.status,
            it.verdict,
        )
    console.print(t_ipo)


def display_watchlist(wm: WatchlistManager) -> None:
    """Display the saved watchlist and trigger conditions."""
    items = wm.get_watchlist()
    if not items:
        console.print("[yellow]Watchlist is empty. Add a stock using --add-watchlist SYMBOL[/yellow]")
        return

    t_wl = Table(title="StockLens Watchlist & Alert Rules", show_header=True, header_style="bold green")
    t_wl.add_column("Symbol", style="bold")
    t_wl.add_column("Target High", justify="right")
    t_wl.add_column("Target Low", justify="right")
    t_wl.add_column("RSI Buy (<)", justify="right")
    t_wl.add_column("RSI Sell (>)", justify="right")
    t_wl.add_column("News Alert", justify="center")
    t_wl.add_column("Notes", style="dim")

    for it in items:
        sent_label = "Positive" if it.get("alert_sentiment") == 1 else "Negative" if it.get("alert_sentiment") == -1 else "Off"
        t_wl.add_row(
            it["symbol"],
            f"₹{it['target_price_high']:,.2f}" if it.get("target_price_high") else "None",
            f"₹{it['target_price_low']:,.2f}" if it.get("target_price_low") else "None",
            f"{it['rsi_lower']:.0f}" if it.get("rsi_lower") else "None",
            f"{it['rsi_upper']:.0f}" if it.get("rsi_upper") else "None",
            sent_label,
            it.get("notes") or "",
        )
    console.print(t_wl)


def check_and_show_alerts(wm: WatchlistManager, provider: BaseDataProvider) -> None:
    """Evaluate alerts across the watchlist and display results."""
    with console.status("[bold yellow]Scanning watchlist alert conditions...[/bold yellow]"):
        fired = wm.check_alerts(provider)

    if not fired:
        console.print("[bold green]All clear! No alert triggers met for current market prices/RSI.[/bold green]")
        return

    console.print(f"[bold red]ALERT TRIGGERED ({len(fired)} conditions met):[/bold red]")
    for alert in fired:
        console.print(f"  • [bold yellow]{alert['symbol']}[/bold yellow] [{alert['type']}]: {alert['message']}")

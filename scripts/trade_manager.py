#!/usr/bin/env python3
"""
trade_manager.py — CAN SLIM Paper Portfolio Trade Manager
Manages all trade actions: open, add, reduce, close positions.
Updates /home/ubuntu/paper_portfolio.json automatically.

Usage:
  python3 trade_manager.py open  TICKER PRICE SHARES [--pivot P] [--stop S] [--t1 T1] [--t2 T2] [--t3 T3] [--pattern "Cup with Handle"] [--stage "Stage 2"]
  python3 trade_manager.py add   TICKER PRICE SHARES
  python3 trade_manager.py reduce TICKER PRICE SHARES
  python3 trade_manager.py close  TICKER PRICE [--shares SHARES]
  python3 trade_manager.py list
  python3 trade_manager.py history
  python3 trade_manager.py pnl

Examples:
  python3 trade_manager.py open JAZZ 244.50 50 --pivot 244.00 --stop 225.00 --t1 263.00 --t2 275.00 --pattern "Ascending Base" --stage "Stage 2"
  python3 trade_manager.py add JAZZ 250.00 25
  python3 trade_manager.py reduce JAZZ 265.00 25
  python3 trade_manager.py close JAZZ 275.00
  python3 trade_manager.py list
"""

import argparse
import json
import os
from datetime import datetime

PORTFOLIO_FILE = "/home/ubuntu/paper_portfolio.json"

def load_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        return {
            "portfolio_name": "CAN SLIM Paper Portfolio",
            "created": datetime.now().strftime("%Y-%m-%d"),
            "currency": "USD",
            "total_capital": 100000,
            "positions": [],
            "watchlist": [],
            "closed_positions": [],
            "trade_log": [],
            "rules": {
                "max_position_size_pct": 0.25,
                "max_loss_per_trade_pct": 0.08,
                "portfolio_stop_drawdown_pct": 0.15,
                "buy_zone_max_above_pivot_pct": 0.05,
                "volume_confirmation_multiplier": 1.5
            }
        }
    with open(PORTFOLIO_FILE, 'r') as f:
        return json.load(f)

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump(portfolio, f, indent=2)

def log_trade(portfolio, action, ticker, price, shares, notes=""):
    if "trade_log" not in portfolio:
        portfolio["trade_log"] = []
    portfolio["trade_log"].append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "action": action,
        "ticker": ticker,
        "price": price,
        "shares": shares,
        "value": round(price * shares, 2),
        "notes": notes
    })

def cmd_open(args, portfolio):
    """Open a new position (建仓)."""
    ticker = args.ticker.upper()
    
    # Check if already open
    existing = next((p for p in portfolio["positions"] if p["ticker"] == ticker and p["status"] == "OPEN"), None)
    if existing:
        print(f"⚠️  Position in {ticker} already OPEN. Use 'add' to add shares.")
        return
    
    # Remove from watchlist if present
    portfolio["watchlist"] = [w for w in portfolio.get("watchlist", []) if w["ticker"] != ticker]
    portfolio["positions"] = [p for p in portfolio["positions"] if not (p["ticker"] == ticker and p["status"] == "WATCHING")]
    
    position = {
        "ticker": ticker,
        "status": "OPEN",
        "stage": args.stage or "Stage 2",
        "pattern": args.pattern or "N/A",
        "pivot_point": args.pivot or args.price,
        "entry_price": args.price,
        "entry_date": datetime.now().strftime("%Y-%m-%d"),
        "shares": args.shares,
        "avg_price": args.price,
        "stop_loss": args.stop or round(args.price * 0.92, 2),
        "target_1": args.t1 or round(args.price * 1.08, 2),
        "target_2": args.t2 or round(args.price * 1.15, 2),
        "target_3": args.t3 or None,
        "position_size_pct": round((args.price * args.shares) / portfolio["total_capital"], 3),
        "notes": f"B1 entry at ${args.price} x {args.shares} shares",
        "add_ons": []
    }
    
    portfolio["positions"].append(position)
    log_trade(portfolio, "OPEN (B1)", ticker, args.price, args.shares, f"Initial position. Stop: ${position['stop_loss']}")
    save_portfolio(portfolio)
    
    cost = args.price * args.shares
    print(f"\n✅ OPENED position in {ticker}")
    print(f"   Entry: ${args.price} x {args.shares} shares = ${cost:,.2f}")
    print(f"   Stop Loss: ${position['stop_loss']} | T1: ${position['target_1']} | T2: ${position['target_2']}")
    print(f"   Pattern: {position['pattern']} | Stage: {position['stage']}")

def cmd_add(args, portfolio):
    """Add to an existing position (加仓)."""
    ticker = args.ticker.upper()
    pos = next((p for p in portfolio["positions"] if p["ticker"] == ticker and p["status"] == "OPEN"), None)
    if not pos:
        print(f"❌ No open position found for {ticker}. Use 'open' first.")
        return
    
    old_shares = pos["shares"]
    old_avg = pos["avg_price"]
    new_shares = old_shares + args.shares
    new_avg = round((old_avg * old_shares + args.price * args.shares) / new_shares, 2)
    
    pos["shares"] = new_shares
    pos["avg_price"] = new_avg
    pos["position_size_pct"] = round((new_avg * new_shares) / portfolio["total_capital"], 3)
    
    add_on_num = len(pos.get("add_ons", [])) + 2
    pos.setdefault("add_ons", []).append({
        "date": datetime.now().strftime("%Y-%m-%d"),
        "label": f"B{add_on_num}",
        "price": args.price,
        "shares": args.shares
    })
    pos["notes"] += f" | B{add_on_num} add at ${args.price} x {args.shares}"
    
    log_trade(portfolio, f"ADD (B{add_on_num})", ticker, args.price, args.shares, f"New avg: ${new_avg}")
    save_portfolio(portfolio)
    
    print(f"\n✅ ADDED to {ticker} position")
    print(f"   Added: ${args.price} x {args.shares} shares")
    print(f"   Total: {new_shares} shares | New Avg Price: ${new_avg}")
    print(f"   Position Size: {pos['position_size_pct']*100:.1f}% of capital")

def cmd_reduce(args, portfolio):
    """Reduce a position / take partial profits (减仓)."""
    ticker = args.ticker.upper()
    pos = next((p for p in portfolio["positions"] if p["ticker"] == ticker and p["status"] == "OPEN"), None)
    if not pos:
        print(f"❌ No open position found for {ticker}.")
        return
    
    shares_to_sell = args.shares if args.shares else pos["shares"] // 2
    if shares_to_sell >= pos["shares"]:
        print(f"⚠️  Selling {shares_to_sell} shares would close the position. Use 'close' instead.")
        return
    
    pnl_per_share = args.price - pos["avg_price"]
    pnl_total = round(pnl_per_share * shares_to_sell, 2)
    pnl_pct = round(pnl_per_share / pos["avg_price"] * 100, 2)
    
    pos["shares"] -= shares_to_sell
    pos["position_size_pct"] = round((pos["avg_price"] * pos["shares"]) / portfolio["total_capital"], 3)
    pos["notes"] += f" | Reduced {shares_to_sell}sh at ${args.price} (P&L: ${pnl_total:+,.0f})"
    
    log_trade(portfolio, "REDUCE", ticker, args.price, shares_to_sell, f"P&L: ${pnl_total:+,.0f} ({pnl_pct:+.1f}%)")
    save_portfolio(portfolio)
    
    print(f"\n✅ REDUCED {ticker} position")
    print(f"   Sold: {shares_to_sell} shares @ ${args.price}")
    print(f"   P&L on this sale: ${pnl_total:+,.0f} ({pnl_pct:+.1f}%)")
    print(f"   Remaining: {pos['shares']} shares @ avg ${pos['avg_price']}")

def cmd_close(args, portfolio):
    """Close a position entirely (清仓)."""
    ticker = args.ticker.upper()
    pos = next((p for p in portfolio["positions"] if p["ticker"] == ticker and p["status"] == "OPEN"), None)
    if not pos:
        print(f"❌ No open position found for {ticker}.")
        return
    
    shares = args.shares if args.shares else pos["shares"]
    pnl_per_share = args.price - pos["avg_price"]
    pnl_total = round(pnl_per_share * shares, 2)
    pnl_pct = round(pnl_per_share / pos["avg_price"] * 100, 2)
    hold_days = (datetime.now() - datetime.strptime(pos["entry_date"], "%Y-%m-%d")).days
    
    # Archive to closed positions
    closed = dict(pos)
    closed["status"] = "CLOSED"
    closed["exit_price"] = args.price
    closed["exit_date"] = datetime.now().strftime("%Y-%m-%d")
    closed["exit_shares"] = shares
    closed["pnl_total"] = pnl_total
    closed["pnl_pct"] = pnl_pct
    closed["hold_days"] = hold_days
    
    portfolio.setdefault("closed_positions", []).append(closed)
    portfolio["positions"] = [p for p in portfolio["positions"] if not (p["ticker"] == ticker and p["status"] == "OPEN")]
    
    log_trade(portfolio, "CLOSE", ticker, args.price, shares, f"P&L: ${pnl_total:+,.0f} ({pnl_pct:+.1f}%) | Held {hold_days}d")
    save_portfolio(portfolio)
    
    emoji = "🟢" if pnl_total > 0 else "🔴"
    print(f"\n{emoji} CLOSED {ticker} position")
    print(f"   Sold: {shares} shares @ ${args.price}")
    print(f"   Entry: ${pos['avg_price']} | Exit: ${args.price}")
    print(f"   P&L: ${pnl_total:+,.0f} ({pnl_pct:+.1f}%) | Held {hold_days} days")

def cmd_list(portfolio):
    """List all current positions and watchlist (持仓列表)."""
    import yfinance as yf
    
    print(f"\n{'='*70}")
    print(f"  CAN SLIM Paper Portfolio — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Total Capital: ${portfolio['total_capital']:,}")
    print(f"{'='*70}")
    
    open_pos = [p for p in portfolio["positions"] if p["status"] == "OPEN"]
    watching = [p for p in portfolio["positions"] if p["status"] == "WATCHING"]
    watchlist = portfolio.get("watchlist", [])
    
    if open_pos:
        print(f"\n📈 OPEN POSITIONS ({len(open_pos)})")
        print(f"{'─'*70}")
        total_pnl = 0
        for pos in open_pos:
            try:
                current = yf.Ticker(pos["ticker"]).history(period="1d")["Close"].iloc[-1]
                pnl = (current - pos["avg_price"]) * pos["shares"]
                pnl_pct = (current - pos["avg_price"]) / pos["avg_price"] * 100
                total_pnl += pnl
                flag = "🟢" if pnl > 0 else "🔴"
                print(f"  {flag} {pos['ticker']:<6} | {pos['shares']}sh @ avg ${pos['avg_price']:.2f} | Now ${current:.2f} | P&L: ${pnl:+,.0f} ({pnl_pct:+.1f}%)")
                print(f"       Stage: {pos['stage']} | Pattern: {pos['pattern']}")
                print(f"       Stop: ${pos['stop_loss']} | T1: ${pos['target_1']} | T2: ${pos['target_2']}")
                if pos.get('target_3'): print(f"       T3: ${pos['target_3']}")
            except:
                print(f"  ❓ {pos['ticker']:<6} | {pos['shares']}sh @ avg ${pos['avg_price']:.2f} | (price unavailable)")
        print(f"\n  Total Open P&L: ${total_pnl:+,.0f}")
    else:
        print("\n  No open positions.")
    
    all_watching = watching + watchlist
    if all_watching:
        print(f"\n👀 WATCHLIST ({len(all_watching)})")
        print(f"{'─'*70}")
        for pos in all_watching:
            pivot = pos.get("pivot_point", "N/A")
            stage = pos.get("stage", "N/A")
            print(f"  ⏳ {pos['ticker']:<6} | Pivot: ${pivot} | Stop: ${pos.get('stop_loss','N/A')} | Stage: {stage}")
            print(f"       Pattern: {pos.get('pattern','N/A')}")
    
    closed = portfolio.get("closed_positions", [])
    if closed:
        total_realized = sum(p.get("pnl_total", 0) for p in closed)
        wins = sum(1 for p in closed if p.get("pnl_total", 0) > 0)
        print(f"\n📋 CLOSED POSITIONS ({len(closed)}) | Win Rate: {wins}/{len(closed)} | Total Realized P&L: ${total_realized:+,.0f}")

def cmd_history(portfolio):
    """Show trade log (交易历史)."""
    log = portfolio.get("trade_log", [])
    if not log:
        print("No trade history yet.")
        return
    print(f"\n{'='*70}")
    print(f"  Trade History ({len(log)} entries)")
    print(f"{'='*70}")
    print(f"{'Date':<17} {'Action':<15} {'Ticker':<7} {'Price':>8} {'Shares':>7} {'Value':>10} Notes")
    print(f"{'─'*70}")
    for t in log[-20:]:  # Show last 20
        print(f"{t['date']:<17} {t['action']:<15} {t['ticker']:<7} ${t['price']:>7.2f} {t['shares']:>7} ${t['value']:>9,.0f} {t.get('notes','')}")

def cmd_pnl(portfolio):
    """Show P&L summary (盈亏汇总)."""
    closed = portfolio.get("closed_positions", [])
    if not closed:
        print("No closed positions yet.")
        return
    
    print(f"\n{'='*60}")
    print(f"  P&L Summary — Closed Positions")
    print(f"{'='*60}")
    print(f"{'Ticker':<7} {'Entry':>8} {'Exit':>8} {'Shares':>7} {'P&L':>10} {'%':>7} {'Days':>5}")
    print(f"{'─'*60}")
    
    total_pnl = 0
    wins = 0
    for p in sorted(closed, key=lambda x: x.get("exit_date",""), reverse=True):
        pnl = p.get("pnl_total", 0)
        total_pnl += pnl
        if pnl > 0: wins += 1
        flag = "🟢" if pnl > 0 else "🔴"
        print(f"{flag} {p['ticker']:<6} ${p.get('avg_price',0):>7.2f} ${p.get('exit_price',0):>7.2f} {p.get('exit_shares',0):>7} ${pnl:>+9,.0f} {p.get('pnl_pct',0):>+6.1f}% {p.get('hold_days',0):>5}d")
    
    print(f"{'─'*60}")
    print(f"  Total Realized P&L: ${total_pnl:+,.0f}")
    print(f"  Win Rate: {wins}/{len(closed)} ({wins/len(closed)*100:.0f}%)")

def main():
    parser = argparse.ArgumentParser(description="CAN SLIM Paper Portfolio Trade Manager")
    subparsers = parser.add_subparsers(dest="command")
    
    # open
    p_open = subparsers.add_parser("open", help="Open a new position (建仓)")
    p_open.add_argument("ticker"); p_open.add_argument("price", type=float); p_open.add_argument("shares", type=int)
    p_open.add_argument("--pivot", type=float); p_open.add_argument("--stop", type=float)
    p_open.add_argument("--t1", type=float); p_open.add_argument("--t2", type=float); p_open.add_argument("--t3", type=float)
    p_open.add_argument("--pattern", default="N/A"); p_open.add_argument("--stage", default="Stage 2")
    
    # add
    p_add = subparsers.add_parser("add", help="Add to position (加仓)")
    p_add.add_argument("ticker"); p_add.add_argument("price", type=float); p_add.add_argument("shares", type=int)
    
    # reduce
    p_red = subparsers.add_parser("reduce", help="Reduce position (减仓)")
    p_red.add_argument("ticker"); p_red.add_argument("price", type=float); p_red.add_argument("shares", type=int, nargs="?", default=None)
    
    # close
    p_close = subparsers.add_parser("close", help="Close position (清仓)")
    p_close.add_argument("ticker"); p_close.add_argument("price", type=float)
    p_close.add_argument("--shares", type=int, default=None)
    
    # list / history / pnl
    subparsers.add_parser("list", help="List all positions (持仓列表)")
    subparsers.add_parser("history", help="Show trade history (交易历史)")
    subparsers.add_parser("pnl", help="Show P&L summary (盈亏汇总)")
    
    args = parser.parse_args()
    portfolio = load_portfolio()
    
    if args.command == "open":    cmd_open(args, portfolio)
    elif args.command == "add":   cmd_add(args, portfolio)
    elif args.command == "reduce":cmd_reduce(args, portfolio)
    elif args.command == "close": cmd_close(args, portfolio)
    elif args.command == "list":  cmd_list(portfolio)
    elif args.command == "history": cmd_history(portfolio)
    elif args.command == "pnl":   cmd_pnl(portfolio)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

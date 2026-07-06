#!/usr/bin/env python3
"""
daily_report.py — CAN SLIM Paper Portfolio Daily Report
Generates a daily watchlist and position update for the paper portfolio.
Run every trading day to track NBIX, CRWD, ACLS, JAZZ.
"""

import json
import warnings
from datetime import datetime, date
import sys

warnings.filterwarnings('ignore')

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "yfinance", "-q"], check=True)
    import yfinance as yf
    import pandas as pd
    import numpy as np

PORTFOLIO_FILE = "/home/ubuntu/paper_portfolio.json"

def safe(val):
    if val is None: return None
    if isinstance(val, float) and (np.isnan(val) or np.isinf(val)): return None
    return val

def compute_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def get_spy_return_1y():
    try:
        spy = yf.Ticker('SPY')
        h = spy.history(period='1y', auto_adjust=True)
        if not h.empty and len(h) >= 200:
            return (h['Close'].iloc[-1] / h['Close'].iloc[0] - 1) * 100
    except:
        pass
    return 20.0

SPY_RET_1Y = None

def get_stock_data(ticker):
    global SPY_RET_1Y
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo", interval="1d", auto_adjust=True)
        hist_1y = stock.history(period="1y", interval="1d", auto_adjust=True)
        if hist.empty or len(hist) < 20:
            return None
        close = hist['Close']
        vol   = hist['Volume']
        high  = hist['High']
        low   = hist['Low']

        current    = safe(close.iloc[-1])
        prev_close = safe(close.iloc[-2])
        day_change = ((current - prev_close) / prev_close * 100) if prev_close else 0
        day_high   = safe(high.iloc[-1])
        day_low    = safe(low.iloc[-1])
        day_vol    = safe(vol.iloc[-1])
        avg_vol    = safe(vol.rolling(20).mean().iloc[-1])
        vol_ratio  = safe(day_vol / avg_vol) if avg_vol else 1.0

        rsi_d = safe(compute_rsi(close).iloc[-1])
        ma20  = safe(close.rolling(20).mean().iloc[-1])
        ma50  = safe(close.rolling(50).mean().iloc[-1])

        # Weekly closing range (ZST sell signal check)
        weekly_close = close.resample('W').last().dropna()
        weekly_high  = high.resample('W').max().dropna()
        weekly_low   = low.resample('W').min().dropna()
        if len(weekly_close) >= 2:
            wh = safe(weekly_high.iloc[-1])
            wl = safe(weekly_low.iloc[-1])
            wc = safe(weekly_close.iloc[-1])
            wcr = round((wc - wl) / (wh - wl) * 100, 1) if wh and wl and (wh - wl) > 0 else 50
        else:
            wcr = 50

        # ATR Calculation
        tr = pd.concat([
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs()
        ], axis=1).max(axis=1)
        atr_14 = safe(tr.rolling(14).mean().iloc[-1])
        atr_pct = round((atr_14 / current) * 100, 1) if atr_14 and current else 0

        # RS Rating vs SPY
        if SPY_RET_1Y is None:
            SPY_RET_1Y = get_spy_return_1y()
        if not hist_1y.empty and len(hist_1y) >= 200:
            ret_1y = (hist_1y['Close'].iloc[-1] / hist_1y['Close'].iloc[0] - 1) * 100
            spy = SPY_RET_1Y
            rs_rating = 99 if ret_1y > spy * 3 else (80 if ret_1y > spy * 1.5 else (50 if ret_1y > spy else 30))
            rs_label = "Excellent" if rs_rating >= 90 else ("Strong" if rs_rating >= 80 else ("Average" if rs_rating >= 50 else "Weak"))
        else:
            rs_rating = None
            rs_label = "N/A"

        return {
            "price":      round(current, 2),
            "prev_close": round(prev_close, 2),
            "day_change": round(day_change, 2),
            "day_high":   round(day_high, 2),
            "day_low":    round(day_low, 2),
            "volume":     int(day_vol) if day_vol else 0,
            "avg_vol":    int(avg_vol) if avg_vol else 0,
            "vol_ratio":  round(vol_ratio, 2),
            "rsi":        round(rsi_d, 1),
            "ma20":       round(ma20, 2),
            "ma50":       round(ma50, 2),
            "wcr":        wcr,
            "rs_rating":  rs_rating,
            "rs_label":   rs_label,
            "atr_pct":    atr_pct,
        }
    except Exception as e:
        return None

def check_signals(pos, data):
    """Check buy, stop, and target signals for a position/watchlist item."""
    signals = []
    price   = data['price']
    pivot   = pos.get('pivot_point')
    stop    = pos.get('stop_loss')
    t1      = pos.get('target_1')
    t2      = pos.get('target_2')
    entry   = pos.get('entry_price')
    vol_r   = data['vol_ratio']
    rsi     = data['rsi']

    if pos['status'] == 'WATCHING':
        if pivot and price >= pivot:
            if vol_r >= 1.5:
                signals.append(f"🚨 BREAKOUT SIGNAL: Price ${price} broke pivot ${pivot} on {vol_r:.1f}x volume! BUY NOW")
            else:
                signals.append(f"⚠️  Price ${price} above pivot ${pivot} but volume only {vol_r:.1f}x avg — NOT confirmed yet")
        elif pivot:
            gap = pivot - price
            signals.append(f"📊 ${gap:.2f} below pivot ${pivot} ({gap/pivot*100:.1f}% away)")

    elif pos['status'] == 'OPEN':
        if entry:
            pnl_pct = (price - entry) / entry * 100
            signals.append(f"💰 P&L: {pnl_pct:+.1f}% (Entry ${entry} → Now ${price})")

        if stop and price <= stop:
            signals.append(f"🛑 STOP LOSS HIT: Price ${price} ≤ Stop ${stop}. SELL IMMEDIATELY")
        if t1 and price >= t1:
            signals.append(f"🎯 TARGET 1 HIT: Price ${price} ≥ T1 ${t1}. Take 30-50% profits, move stop to breakeven")
        if t2 and price >= t2:
            signals.append(f"🎯 TARGET 2 HIT: Price ${price} ≥ T2 ${t2}. Take another 30%, trail stop")

    # ZST sell signal check (for open positions)
    if pos['status'] == 'OPEN' and data['wcr'] < 40 and vol_r > 1.3:
        signals.append(f"⚠️  ZST SELL WARNING: WCR={data['wcr']}% (<40%) + Volume {vol_r:.1f}x (>1.3x) — Possible institutional distribution!")

    # RSI warnings
    if rsi > 78:
        signals.append(f"⚠️  RSI {rsi} — Overbought, do not add to position")

    # ATR warnings
    atr_pct = data.get('atr_pct', 0)
    if atr_pct > 8.0:
        signals.append(f"🚨 HIGH ATR WARNING: ATR is {atr_pct}% (>8%). Stock is too volatile for a standard -8% stop loss!")

    return signals

def generate_report():
    with open(PORTFOLIO_FILE, 'r') as f:
        portfolio = json.load(f)

    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    report_lines = []

    report_lines.append(f"# 📊 CAN SLIM Paper Portfolio — Daily Report")
    report_lines.append(f"**Date:** {today} | **Framework:** ZST TML (CAN SLIM + SEPA)\n")

    # Portfolio summary
    total_capital = portfolio['total_capital']
    open_positions = [p for p in portfolio['positions'] if p['status'] == 'OPEN']
    watching = [p for p in portfolio['positions'] if p['status'] == 'WATCHING']
    watchlist = portfolio.get('watchlist', [])

    report_lines.append(f"**Total Capital:** ${total_capital:,} | **Open Positions:** {len(open_positions)} | **Watching:** {len(watching) + len(watchlist)}\n")

    # ── OPEN POSITIONS ────────────────────────────────────────────────────────
    if open_positions:
        report_lines.append("---\n## 📈 Open Positions\n")
        for pos in open_positions:
            ticker = pos['ticker']
            data = get_stock_data(ticker)
            if not data:
                report_lines.append(f"### {ticker} — ⚠️ Data unavailable\n")
                continue

            signals = check_signals(pos, data)
            entry = pos.get('entry_price', 0)
            shares = pos.get('shares', 0)
            pnl = (data['price'] - entry) * shares if entry and shares else 0
            pnl_pct = (data['price'] - entry) / entry * 100 if entry else 0

            report_lines.append(f"### {ticker} — {pos['pattern']}")
            report_lines.append(f"**Stage:** {pos['stage']} | **Status:** OPEN")
            report_lines.append(f"| Metric | Value |")
            report_lines.append(f"| :--- | :--- |")
            report_lines.append(f"| Current Price | ${data['price']} ({data['day_change']:+.2f}%) |")
            report_lines.append(f"| Day Range | ${data['day_low']} – ${data['day_high']} |")
            report_lines.append(f"| Volume | {data['volume']:,} ({data['vol_ratio']:.1f}x avg) |")
            rs = data.get('rs_rating')
            rs_lbl = data.get('rs_label', 'N/A')
            report_lines.append(f"| RS Rating | {rs} ({rs_lbl}) |" if rs else "| RS Rating | N/A |")
            report_lines.append(f"| RSI (14D) | {data['rsi']} |")
            report_lines.append(f"| 20D MA | ${data['ma20']} |")
            report_lines.append(f"| Weekly Close Range | {data['wcr']}% |")
            report_lines.append(f"| Entry Price | ${entry} |")
            report_lines.append(f"| Stop Loss | ${pos['stop_loss']} |")
            report_lines.append(f"| P&L | ${pnl:+,.0f} ({pnl_pct:+.1f}%) |")
            report_lines.append("")

            if signals:
                report_lines.append("**Signals:**")
                for s in signals:
                    report_lines.append(f"- {s}")
            report_lines.append("")

    # ── WATCHING (Active Setups) ──────────────────────────────────────────────
    report_lines.append("---\n## 👀 Active Setups — Watching for Breakout\n")
    all_watching = watching + watchlist

    for pos in all_watching:
        ticker = pos['ticker']
        data = get_stock_data(ticker)
        if not data:
            report_lines.append(f"### {ticker} — ⚠️ Data unavailable\n")
            continue

        signals = check_signals(pos, data)
        pivot = pos.get('pivot_point', 0)
        gap_pct = (pivot - data['price']) / pivot * 100 if pivot else 0

        report_lines.append(f"### {ticker} — {pos.get('pattern', 'N/A')}")
        report_lines.append(f"**Stage:** {pos.get('stage', 'N/A')} | **Pivot:** ${pivot}")
        report_lines.append(f"| Metric | Value |")
        report_lines.append(f"| :--- | :--- |")
        report_lines.append(f"| Current Price | ${data['price']} ({data['day_change']:+.2f}%) |")
        report_lines.append(f"| Day Range | ${data['day_low']} – ${data['day_high']} |")
        report_lines.append(f"| Volume | {data['volume']:,} ({data['vol_ratio']:.1f}x avg) |")
        rs = data.get('rs_rating')
        rs_lbl = data.get('rs_label', 'N/A')
        report_lines.append(f"| RS Rating | {rs} ({rs_lbl}) |" if rs else "| RS Rating | N/A |")
        report_lines.append(f"| RSI (14D) | {data['rsi']} |")
        report_lines.append(f"| 20D MA | ${data['ma20']} |")
        report_lines.append(f"| Distance to Pivot | {gap_pct:+.1f}% |")
        report_lines.append(f"**Stage:** {pos.get('stage', 'N/A')} | **Pivot:** ${pivot} | **RS Rating:** {rs} ({rs_lbl})")
        report_lines.append(f"| Stop Loss (if bought) | ${pos.get('stop_loss', 'N/A')} |")
        report_lines.append(f"| T1 / T2 | ${pos.get('target_1', 'N/A')} / ${pos.get('target_2', 'N/A')} |")
        report_lines.append("")

        if signals:
            report_lines.append("**Signals:**")
            for s in signals:
                report_lines.append(f"- {s}")
        report_lines.append(f"*Note: {pos.get('notes', '')}*\n")

    report_lines.append("---")
    report_lines.append("*This report is for informational purposes only and does not constitute financial or investment advice.*")

    report = "\n".join(report_lines)
    print(report)
    return report

if __name__ == "__main__":
    generate_report()

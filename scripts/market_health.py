#!/usr/bin/env python3
"""
market_health.py — Daily Market Health Report
Generates a comprehensive market health assessment including:
  - Major indices (SPY, QQQ, IWM, DIA)
  - Treasury yields (2Y, 10Y, 30Y, yield curve)
  - Market breadth (% stocks above 200MA, A/D ratio)
  - Growth stock indices (IBD 50 proxy, ARKK, WCLD)
  - Sector rotation (risk-on vs risk-off)
  - Traffic light signal (Green / Yellow / Red)

Usage:
  python3 market_health.py
  python3 market_health.py --output /tmp/market_health.md
"""

import argparse
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

try:
    import yfinance as yf
    import pandas as pd
    import numpy as np
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "yfinance", "-q"], check=True)
    import yfinance as yf
    import pandas as pd
    import numpy as np

def safe(val):
    if val is None: return None
    if isinstance(val, float) and (np.isnan(val) or np.isinf(val)): return None
    return val

def get_price_data(ticker, period="6mo"):
    try:
        h = yf.Ticker(ticker).history(period=period, auto_adjust=True)
        if h.empty or len(h) < 20:
            return None
        close = h['Close']
        vol   = h['Volume']
        current = safe(close.iloc[-1])
        prev    = safe(close.iloc[-2])
        day_chg = (current / prev - 1) * 100 if prev else 0
        ret_1m  = (current / close.iloc[-22] - 1) * 100 if len(close) >= 22 else None
        ret_3m  = (current / close.iloc[-66] - 1) * 100 if len(close) >= 66 else None
        ma50    = safe(close.rolling(50).mean().iloc[-1])
        ma200   = safe(close.rolling(200).mean().iloc[-1])
        above_ma50  = current > ma50  if ma50  else None
        above_ma200 = current > ma200 if ma200 else None
        # RSI
        delta = close.diff()
        gain = delta.clip(lower=0).ewm(com=13, min_periods=14).mean()
        loss = (-delta.clip(upper=0)).ewm(com=13, min_periods=14).mean()
        rsi = safe((100 - 100 / (1 + gain / loss)).iloc[-1])
        return {
            "price": round(current, 2),
            "day_chg": round(day_chg, 2),
            "ret_1m": round(ret_1m, 1) if ret_1m else None,
            "ret_3m": round(ret_3m, 1) if ret_3m else None,
            "ma50": round(ma50, 2) if ma50 else None,
            "ma200": round(ma200, 2) if ma200 else None,
            "above_ma50": above_ma50,
            "above_ma200": above_ma200,
            "rsi": round(rsi, 1) if rsi else None,
        }
    except:
        return None

def get_yield(ticker):
    """Get treasury yield (stored as percentage in yfinance)."""
    try:
        h = yf.Ticker(ticker).history(period="5d")
        if not h.empty:
            return round(h['Close'].iloc[-1], 3)
    except:
        pass
    return None

def compute_market_signal(indices, breadth, growth):
    """
    Traffic light system:
    GREEN  = Bull market, buy aggressively
    YELLOW = Mixed signals, be selective
    RED    = Bear market, reduce/avoid
    """
    score = 0
    max_score = 0

    # Index health (4 points)
    max_score += 4
    spy = indices.get("SPY")
    qqq = indices.get("QQQ")
    if spy and spy.get("above_ma200"): score += 2
    if qqq and qqq.get("above_ma200"): score += 2

    # Trend (3 points)
    max_score += 3
    if spy and spy.get("above_ma50"): score += 1
    if spy and spy.get("ret_1m") and spy["ret_1m"] > 0: score += 1
    if spy and spy.get("ret_3m") and spy["ret_3m"] > 0: score += 1

    # Growth stocks (2 points)
    max_score += 2
    if growth.get("QQQ") and growth["QQQ"].get("above_ma50"): score += 1
    iwm = indices.get("IWM")
    if iwm and iwm.get("above_ma200"): score += 1

    # Breadth (2 points)
    max_score += 2
    pct_above_200 = breadth.get("pct_above_200")
    if pct_above_200 and pct_above_200 > 60: score += 2
    elif pct_above_200 and pct_above_200 > 40: score += 1

    ratio = score / max_score if max_score > 0 else 0

    if ratio >= 0.70:
        return "🟢 GREEN — Bull Market", "Conditions favorable. Buy breakouts aggressively. New bull market or confirmed uptrend.", score, max_score
    elif ratio >= 0.45:
        return "🟡 YELLOW — Caution", "Mixed signals. Be selective. Only buy the strongest setups. Reduce position sizes.", score, max_score
    else:
        return "🔴 RED — Bear Market", "Unfavorable conditions. Avoid new buys. Hold cash. Wait for Follow-Through Day.", score, max_score

def generate_report(output_path=None):
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []

    lines.append(f"# 📊 Daily Market Health Report")
    lines.append(f"**Date:** {date} | **Framework:** ZST CAN SLIM Market Direction (M Letter)\n")

    # ── MAJOR INDICES ─────────────────────────────────────────────────────────
    lines.append("---\n## 📈 Major Indices\n")
    index_tickers = {"SPY": "S&P 500", "QQQ": "Nasdaq 100", "IWM": "Russell 2000", "DIA": "Dow Jones"}
    indices = {}
    lines.append("| Index | Price | Day | 1M | 3M | vs MA50 | vs MA200 | RSI |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for ticker, name in index_tickers.items():
        d = get_price_data(ticker)
        indices[ticker] = d
        if d:
            m50  = "✅" if d.get("above_ma50")  else "❌"
            m200 = "✅" if d.get("above_ma200") else "❌"
            lines.append(f"| **{name}** ({ticker}) | ${d['price']} | {d['day_chg']:+.2f}% | {d['ret_1m']:+.1f}% | {d['ret_3m']:+.1f}% | {m50} | {m200} | {d['rsi']} |")
    lines.append("")

    # ── TREASURY YIELDS ────────────────────────────────────────────────────────
    lines.append("---\n## 🏦 Treasury Yields & Yield Curve\n")
    yield_2y  = get_yield("^IRX")   # 13-week proxy
    yield_10y = get_yield("^TNX")   # 10-year
    yield_30y = get_yield("^TYX")   # 30-year
    yield_5y  = get_yield("^FVX")   # 5-year

    lines.append("| Tenor | Yield | Signal |")
    lines.append("| :--- | :--- | :--- |")
    if yield_2y:  lines.append(f"| 3-Month T-Bill | {yield_2y:.2f}% | Short-term risk-free rate |")
    if yield_5y:  lines.append(f"| 5-Year Treasury | {yield_5y:.2f}% | Medium-term benchmark |")
    if yield_10y: lines.append(f"| 10-Year Treasury | {yield_10y:.2f}% | Key long-term benchmark |")
    if yield_30y: lines.append(f"| 30-Year Treasury | {yield_30y:.2f}% | Long-term inflation proxy |")

    if yield_10y and yield_2y:
        spread = round(yield_10y - yield_2y, 2)
        curve_signal = "✅ Normal (positive slope)" if spread > 0 else ("⚠️ Flat" if spread > -0.2 else "🔴 Inverted (recession risk)")
        lines.append(f"\n**Yield Curve (10Y - 3M):** {spread:+.2f}% — {curve_signal}")
    lines.append("")

    # ── MARKET BREADTH ─────────────────────────────────────────────────────────
    lines.append("---\n## 📊 Market Breadth\n")
    breadth = {}

    # Use $NYA200R proxy: % of NYSE stocks above 200-day MA
    # Approximate using a basket of stocks
    breadth_tickers = [
        "AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","BRK-B","JPM","JNJ",
        "V","PG","UNH","HD","MA","ABBV","MRK","PFE","KO","PEP",
        "COST","WMT","DIS","NFLX","ADBE","CRM","AMD","INTC","QCOM","TXN",
        "BAC","WFC","GS","MS","C","XOM","CVX","COP","SLB","EOG",
        "LLY","TMO","ABT","DHR","BMY","AMGN","GILD","ISRG","SYK","BSX"
    ]
    above_200 = 0
    above_50  = 0
    checked   = 0
    for t in breadth_tickers[:30]:  # Check 30 for speed
        try:
            h = yf.Ticker(t).history(period="1y", auto_adjust=True)["Close"]
            if len(h) >= 200:
                price = h.iloc[-1]
                ma200 = h.rolling(200).mean().iloc[-1]
                ma50  = h.rolling(50).mean().iloc[-1]
                if price > ma200: above_200 += 1
                if price > ma50:  above_50  += 1
                checked += 1
        except: pass

    pct_200 = round(above_200 / checked * 100, 1) if checked > 0 else None
    pct_50  = round(above_50  / checked * 100, 1) if checked > 0 else None
    breadth["pct_above_200"] = pct_200

    b200_signal = ("🟢 Healthy" if pct_200 and pct_200 > 60 else ("🟡 Caution" if pct_200 and pct_200 > 40 else "🔴 Weak")) if pct_200 else "N/A"
    b50_signal  = ("🟢 Healthy" if pct_50  and pct_50  > 60 else ("🟡 Caution" if pct_50  and pct_50  > 40 else "🔴 Weak")) if pct_50  else "N/A"

    lines.append("| Breadth Indicator | Value | Signal |")
    lines.append("| :--- | :--- | :--- |")
    lines.append(f"| % Stocks Above 200-Day MA (sample) | {pct_200}% | {b200_signal} |")
    lines.append(f"| % Stocks Above 50-Day MA (sample) | {pct_50}% | {b50_signal} |")

    # SPY:AGG ratio (risk-on vs risk-off)
    spy_d = get_price_data("SPY", "3mo")
    agg_d = get_price_data("AGG", "3mo")
    if spy_d and agg_d and spy_d.get("ret_3m") and agg_d.get("ret_3m"):
        risk_on = spy_d["ret_3m"] > agg_d["ret_3m"]
        lines.append(f"| SPY vs AGG (Risk-On/Off) | SPY {spy_d['ret_3m']:+.1f}% vs AGG {agg_d['ret_3m']:+.1f}% | {'✅ Risk-On (stocks > bonds)' if risk_on else '🔴 Risk-Off (bonds > stocks)'} |")

    # IWO:RSP (small-cap growth vs large-cap equal weight)
    iwo_d = get_price_data("IWO", "3mo")
    rsp_d = get_price_data("RSP", "3mo")
    if iwo_d and rsp_d and iwo_d.get("ret_3m") and rsp_d.get("ret_3m"):
        growth_on = iwo_d["ret_3m"] > rsp_d["ret_3m"]
        lines.append(f"| IWO vs RSP (Growth/Value) | IWO {iwo_d['ret_3m']:+.1f}% vs RSP {rsp_d['ret_3m']:+.1f}% | {'✅ Growth Leading' if growth_on else '⚠️ Value Leading'} |")
    lines.append("")

    # ── GROWTH STOCK INDICES ───────────────────────────────────────────────────
    lines.append("---\n## 🚀 Growth Stock Indices\n")
    growth_tickers = {
        "QQQ":  "Nasdaq 100 (Tech Leaders)",
        "ARKK": "ARK Innovation (Disruptive Tech)",
        "WCLD": "WisdomTree Cloud Computing",
        "IGV":  "iShares Software ETF",
        "FFTY": "Innovator IBD 50 ETF (Growth Leaders)",
    }
    growth = {}
    lines.append("| ETF | Name | Price | Day | 1M | 3M | vs MA50 | vs MA200 |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    for ticker, name in growth_tickers.items():
        d = get_price_data(ticker)
        growth[ticker] = d
        if d:
            m50  = "✅" if d.get("above_ma50")  else "❌"
            m200 = "✅" if d.get("above_ma200") else "❌"
            lines.append(f"| **{ticker}** | {name} | ${d['price']} | {d['day_chg']:+.2f}% | {d.get('ret_1m',0):+.1f}% | {d.get('ret_3m',0):+.1f}% | {m50} | {m200} |")
    lines.append("")

    # ── SECTOR ROTATION ────────────────────────────────────────────────────────
    lines.append("---\n## 🔄 Sector Rotation (3-Month Performance)\n")
    sector_etfs = {
        "XLK": "Technology", "XLV": "Healthcare", "XLF": "Financials",
        "XLY": "Consumer Disc.", "XLI": "Industrials", "XLE": "Energy",
        "XLB": "Materials", "XLU": "Utilities", "XLRE": "Real Estate",
        "XLC": "Comm. Services", "XLP": "Consumer Staples"
    }
    sector_rets = []
    for ticker, name in sector_etfs.items():
        d = get_price_data(ticker, "3mo")
        if d and d.get("ret_3m"):
            sector_rets.append((name, ticker, d["ret_3m"], d.get("above_ma50"), d.get("above_ma200")))
    sector_rets.sort(key=lambda x: x[2], reverse=True)

    lines.append("| Rank | Sector | ETF | 3M Return | vs MA50 | vs MA200 |")
    lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for i, (name, ticker, ret, m50, m200) in enumerate(sector_rets, 1):
        m50f  = "✅" if m50  else "❌"
        m200f = "✅" if m200 else "❌"
        lines.append(f"| {i} | {name} | {ticker} | {ret:+.1f}% | {m50f} | {m200f} |")
    lines.append("")

    # ── TRAFFIC LIGHT ──────────────────────────────────────────────────────────
    signal, description, score, max_score = compute_market_signal(indices, breadth, growth)
    lines.append("---\n## 🚦 Market Traffic Light\n")
    lines.append(f"## {signal}")
    lines.append(f"**Score:** {score}/{max_score} | **{description}**\n")

    # Timeline context
    lines.append("| Timeframe | Signal | Key Indicator |")
    lines.append("| :--- | :--- | :--- |")
    spy = indices.get("SPY")
    qqq = indices.get("QQQ")
    iwm = indices.get("IWM")
    lt = "🟢" if (spy and spy.get("above_ma200")) else "🔴"
    mt = "🟢" if (spy and spy.get("above_ma50"))  else "🔴"
    st = "🟢" if (spy and spy.get("day_chg") and spy["day_chg"] > 0) else "🔴"
    lines.append(f"| **Long-Term** | {lt} | SPY {'above' if spy and spy.get('above_ma200') else 'below'} 200-day MA |")
    lines.append(f"| **Medium-Term** | {mt} | SPY {'above' if spy and spy.get('above_ma50') else 'below'} 50-day MA |")
    lines.append(f"| **Short-Term** | {st} | SPY day change {spy['day_chg']:+.2f}%" if spy else f"| **Short-Term** | {st} | N/A |")
    lines.append("")

    lines.append("---")
    lines.append("*This report is for informational purposes only and does not constitute financial or investment advice.*")

    report = "\n".join(lines)

    if output_path:
        with open(output_path, 'w') as f:
            f.write(report)
        print(f"Market health report saved to: {output_path}")
    else:
        print(report)

    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Daily Market Health Report")
    parser.add_argument("--output", default=None, help="Output markdown file path")
    args = parser.parse_args()
    generate_report(args.output)

---
name: stock-analyst
description: "Comprehensive swing trading system based on CAN SLIM, SEPA, and ZST frameworks. Includes a market health analyzer (market_health.py), sector & breakout scanner (scanner.py), deep-dive analyzer (fetch_stock_data.py & generate_report.py), visual chart generator (chart_generator.py), and a paper trading portfolio manager (trade_manager.py). Use when the user asks to check market health, scan for breakouts, analyze specific stocks, or manage their trading portfolio."
---

# Stock Analyst Skill

## Overview

This skill is a complete, end-to-end swing trading system inspired by William O'Neil's CAN SLIM, Mark Minervini's SEPA, and the ZST "TML" framework. It is designed to find, analyze, and manage high-probability breakout trades in growth stocks.

The system is modular and contains five core functions:

1. **Market Health (M Letter):** Determines if the overall market is in an uptrend (Green/Yellow/Red light).
2. **Scanner (S & L Letters):** Finds the strongest sectors and scans for stocks with high Relative Strength (RS) and EPS acceleration.
3. **Deep Analysis & Charting:** Evaluates the Four-Dimensional Framework (Fundamentals, RS, Institutions, Technicals) and generates K-line charts for visual confirmation.
4. **Daily Reporting:** Runs a daily check on watchlist stocks for breakout signals and open positions for stop-loss triggers.
5. **Trade Management:** A built-in paper trading portfolio to log entries, adds, trims, and exits.

---

## 1. Market Health Check (`market_health.py`)

Always check the market direction first. Do not buy breakouts aggressively in a Red market.

```bash
python3 /home/ubuntu/skills/stock-analyst/scripts/market_health.py --output /tmp/market_health.md
```

**What it does:**
- Evaluates Major Indices (SPY, QQQ, IWM, DIA) vs 50D/200D MAs.
- Checks Treasury Yields and the Yield Curve (10Y - 3M).
- Measures Market Breadth (% of stocks above 50D/200D MAs).
- Tracks Growth Stock Indices (ARKK, WCLD, IGV).
- Outputs a Traffic Light Signal (🟢 GREEN, 🟡 YELLOW, 🔴 RED).

---

## 2. Sector & Breakout Scanner (`scanner.py`)

Find where the money is flowing and scan for leaders.

```bash
# Scan a specific sector (e.g., tech, healthcare, finance, consumer, energy, industrial, all)
python3 /home/ubuntu/skills/stock-analyst/scripts/scanner.py --sector tech --output /tmp/scan_results.md
```

**What it does:**
- Categorizes stocks into Tiers (Tier A: Small/Mid, Tier B: Large, Tier C: Mega).
- Filters for CAN SLIM criteria: EPS growth > 20%, RS Rating >= 80, Institutional Ownership > 30%.
- Checks the Trend Template (Price > 50D > 150D > 200D MA).
- Estimates the Base Stage (Stage 1, 2, 3, 4) based on price history and All-Time Highs (ATH).

---

## 3. Deep Dive & Visual Confirmation

When the user selects specific stocks from the scan, run the deep dive and generate charts.

**Fetch Data & Generate Markdown Report:**
```bash
python3 /home/ubuntu/skills/stock-analyst/scripts/fetch_stock_data.py TICKER1 TICKER2 --output /tmp/stock_analysis.json
python3 /home/ubuntu/skills/stock-analyst/scripts/generate_report.py /tmp/stock_analysis.json --output /tmp/stock_report.md
```

**Generate Charts for Visual Inspection:**
```bash
python3 /home/ubuntu/skills/stock-analyst/scripts/chart_generator.py TICKER1 TICKER2 --output-dir /tmp/charts
```

**AI Visual Confirmation Workflow:**
1. View the `_weekly.png` chart to confirm the macro structure (Cup, W-Bottom, Flat Base) and verify the Stage (Stage 2 is ideal). Ensure there is no heavy historical overhead resistance.
2. View the `_daily.png` chart to find the exact Pivot Point (top of the consolidation/handle + $0.10).
3. Output the final trading plan with Entry, -8% Stop Loss, and Targets.

---

## 4. Trade Management (`trade_manager.py`)

Manage the user's paper portfolio.

```bash
# Open a position (B1)
python3 /home/ubuntu/skills/stock-analyst/scripts/trade_manager.py open TICKER PRICE SHARES --pivot PIVOT --stop STOP --t1 T1 --t2 T2 --pattern "Cup with Handle" --stage "Stage 2"

# Add to a position (B2, B3)
python3 /home/ubuntu/skills/stock-analyst/scripts/trade_manager.py add TICKER PRICE SHARES

# Take partial profits
python3 /home/ubuntu/skills/stock-analyst/scripts/trade_manager.py reduce TICKER PRICE SHARES

# Close a position completely
python3 /home/ubuntu/skills/stock-analyst/scripts/trade_manager.py close TICKER PRICE

# View portfolio and P&L
python3 /home/ubuntu/skills/stock-analyst/scripts/trade_manager.py list
python3 /home/ubuntu/skills/stock-analyst/scripts/trade_manager.py pnl
python3 /home/ubuntu/skills/stock-analyst/scripts/trade_manager.py history
```

---

## 5. Daily Portfolio Report (`daily_report.py`)

This script is typically run via a scheduled task every trading day.

```bash
python3 /home/ubuntu/daily_report.py
```

**What it does:**
- Checks watchlist stocks for breakout signals (Price > Pivot AND Volume >= 1.5x average).
- Checks open positions for Stop Loss hits or Profit Target hits.
- Checks open positions for ZST Sell Signals (Weekly Closing Range < 40% on heavy volume).

---

## Trading Rules Summary

- **Buy Rule:** Buy exactly at the Pivot Point on heavy volume (>= 1.5x average). Do not chase extended stocks.
- **Stop Loss Rule (M2 Risk Management):** The absolute maximum stop loss for any single trade is -8% from the entry price. However, the total capital at risk on any single trade MUST NOT exceed 1% to 2% of the total account equity. (e.g., If the stop is -8%, position size should be maximum 12.5% to 25% of total capital).
- **ATR Warning:** If a stock's Average True Range (ATR) is exceptionally high (e.g., daily ATR > 8% of the stock price), issue a prominent warning. High ATR means the stock is too volatile and a standard -8% stop loss will likely be triggered by normal daily noise. Avoid these stocks or drastically reduce position size.
- **Language Support:** This skill fully supports Korean (한국어). If the user requests analysis in Korean, generate all reports, insights, and trader's plans in natural, professional Korean.
- **Stage Rule:** Prefer Stage 2 bases. Avoid Stage 4 completely. Treat Stage 3 with extreme caution.
- **RS Rule:** Only buy stocks with an RS Rating of 80 or higher (preferably 90+).

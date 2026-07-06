# Stock Analyst Agent Skill for Claude / AI Agents

A professional-grade, autonomous swing trading system built for AI agents (like Claude, Manus, etc.). It transforms a general-purpose AI into a specialized quantitative and technical equity analyst.

This system is based on the proven methodologies of:
- **William O'Neil's CAN SLIM**
- **Mark Minervini's SEPA (Specific Entry Point Analysis)**
- **ZST's TML (True Market Leader) Framework**

## Features

This repository provides a complete suite of Python scripts and an AI instruction prompt (`SKILL.md`) that allows an AI agent to execute a **Two-Step Funnel Workflow**:

1. **Machine Screening (Quantitative):** Scans the market for stocks with EPS acceleration, Relative Strength (RS) >= 80, and high institutional sponsorship.
2. **AI Visual Confirmation (Qualitative):** Automatically generates weekly and daily candlestick charts for the AI to visually inspect and confirm patterns (Cup with Handle, Flat Base, VCP) and identify precise Pivot Points.

### Core Modules

- `market_health.py`: Analyzes major indices, treasury yields, market breadth, and sector rotation to output a daily "Traffic Light" signal (Green/Yellow/Red).
- `scanner.py`: Scans predefined sectors (Tech, Healthcare, Finance, etc.) to find pre-breakout candidates, categorizing them by market cap tiers and scoring them on a Four-Dimensional framework.
- `fetch_stock_data.py` & `generate_report.py`: Fetches deep fundamental/technical data for specific tickers and generates a highly formatted Markdown report.
- `chart_generator.py`: Generates beautiful, annotated weekly (2-year) and daily (6-month) charts using `mplfinance` for the AI to "look" at using its vision capabilities.
- `trade_manager.py`: A local paper-trading portfolio manager to log entries, adds, trims, and exits, enforcing the strict -8% stop-loss rule.
- `daily_report.py`: A script designed to be run on a daily cron schedule to monitor the portfolio and watchlist for breakout signals, stop-loss triggers, and distribution warnings.

## How to Use

### For AI Agents (Claude, Manus, etc.)

If you are an AI agent, read the `SKILL.md` file. It contains the exact instructions, workflow, and rule sets you need to operate this system.

### Installation Requirements

The scripts require Python 3 and the following packages:
```bash
pip install yfinance pandas numpy matplotlib mplfinance
```

## The Trading Philosophy

This system enforces strict discipline based on the ZST M1/M2 Risk Management rules:

- **Never buy in a Stage 4 decline.**
- **Stop Loss placement:** The stop loss is placed at -8% below the entry price. This is the *location* of the stop, not the dollar risk.
- **Capital at risk per trade:** The actual capital risked on any single trade must NOT exceed 1%–2% of total account equity.
  - Formula: `Max Position Size = (Account Equity × 1%) ÷ 8%`
  - Example: $100,000 account → Max position = $1,000 ÷ 8% = $12,500 (12.5% of capital)
- **ATR Warning:** If a stock's daily ATR exceeds 8% of its price, the system issues a prominent warning. A stock that moves 8%+ daily will trigger a standard -8% stop loss through normal noise alone — avoid or drastically reduce size.
- **Only buy breakouts on heavy volume (>= 1.5x average).**
- **Only buy stocks with an RS Rating >= 80 (preferably 90+).**
- **Prefer Stage 2 bases (first or second base after a major advance).**

## Language Support

This skill fully supports **Korean (한국어)**. If the user requests analysis in Korean, all reports, trader's plans, and insights will be generated in natural, professional Korean.

## Disclaimer

*This software and the generated reports are for informational and educational purposes only. They do not constitute financial or investment advice. Always conduct your own due diligence before making investment decisions.*

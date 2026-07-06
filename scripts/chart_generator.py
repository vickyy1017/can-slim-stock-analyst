#!/usr/bin/env python3
"""
chart_generator.py — Candlestick Chart Generator for Visual Pattern Analysis
Generates weekly (2-year) and daily (6-month) K-line charts for one or more tickers.
Charts are saved as PNG files for visual inspection by the AI.

Usage:
  python3 chart_generator.py TICKER1 TICKER2 ... --output-dir /tmp/charts
"""

import argparse
import os
import warnings
warnings.filterwarnings('ignore')

try:
    import yfinance as yf
    import mplfinance as mpf
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import pandas as pd
    import numpy as np
except ImportError:
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "yfinance", "mplfinance", "-q"], check=True)
    import yfinance as yf
    import mplfinance as mpf
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import pandas as pd
    import numpy as np


def add_moving_averages(data, periods):
    """Add moving average columns to dataframe."""
    for p in periods:
        data[f'MA{p}'] = data['Close'].rolling(p).mean()
    return data


def generate_charts(ticker, output_dir):
    """Generate weekly (2Y) and daily (6M) charts for a ticker."""
    os.makedirs(output_dir, exist_ok=True)
    stock = yf.Ticker(ticker)
    info = stock.info
    name = info.get('longName', ticker)[:40]
    charts = {}

    # ── WEEKLY CHART (2 years) ────────────────────────────────────────────────
    try:
        weekly = stock.history(period="2y", interval="1wk", auto_adjust=True)
        if not weekly.empty and len(weekly) >= 20:
            weekly = weekly[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
            weekly.index = pd.DatetimeIndex(weekly.index)

            # Add MAs
            weekly['MA10'] = weekly['Close'].rolling(10).mean()
            weekly['MA20'] = weekly['Close'].rolling(20).mean()
            weekly['MA40'] = weekly['Close'].rolling(40).mean()

            # Build addplots
            ap = [
                mpf.make_addplot(weekly['MA10'], color='#FF6B35', width=1.5, label='10W MA'),
                mpf.make_addplot(weekly['MA20'], color='#FFA500', width=1.5, label='20W MA'),
                mpf.make_addplot(weekly['MA40'], color='#4169E1', width=2.0, label='40W MA'),
            ]

            # Style
            mc = mpf.make_marketcolors(up='#26a69a', down='#ef5350',
                                        wick={'up': '#26a69a', 'down': '#ef5350'},
                                        volume={'up': '#26a69a', 'down': '#ef5350'},
                                        edge='inherit')
            style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--',
                                        gridcolor='#e0e0e0', facecolor='white',
                                        figcolor='white', y_on_right=True)

            path_w = os.path.join(output_dir, f"{ticker}_weekly.png")
            fig, axes = mpf.plot(
                weekly, type='candle', style=style,
                title=f'\n{name} ({ticker}) — Weekly Chart (2 Years)',
                ylabel='Price (USD)', ylabel_lower='Volume',
                volume=True, addplot=ap,
                figsize=(14, 8), returnfig=True,
                tight_layout=True
            )
            # Add legend
            handles = [
                mpatches.Patch(color='#FF6B35', label='10W MA'),
                mpatches.Patch(color='#FFA500', label='20W MA'),
                mpatches.Patch(color='#4169E1', label='40W MA'),
            ]
            axes[0].legend(handles=handles, loc='upper left', fontsize=9)

            # Mark 52-week high
            high_52w = weekly['High'].max()
            axes[0].axhline(y=high_52w, color='#9C27B0', linestyle=':', linewidth=1.2, alpha=0.8)
            axes[0].text(0.01, high_52w, f' 52W High: ${high_52w:.2f}',
                         transform=axes[0].get_yaxis_transform(),
                         color='#9C27B0', fontsize=8, va='bottom')

            fig.savefig(path_w, dpi=150, bbox_inches='tight')
            plt.close(fig)
            charts['weekly'] = path_w
            print(f"  Weekly chart saved: {path_w}")
    except Exception as e:
        print(f"  Weekly chart error for {ticker}: {e}")

    # ── DAILY CHART (6 months) ────────────────────────────────────────────────
    try:
        daily = stock.history(period="6mo", interval="1d", auto_adjust=True)
        if not daily.empty and len(daily) >= 20:
            daily = daily[['Open', 'High', 'Low', 'Close', 'Volume']].dropna()
            daily.index = pd.DatetimeIndex(daily.index)

            # Add MAs
            daily['MA20'] = daily['Close'].rolling(20).mean()
            daily['MA50'] = daily['Close'].rolling(50).mean()
            daily['MA200'] = daily['Close'].rolling(200).mean()

            # Bollinger Bands
            daily['BB_mid'] = daily['Close'].rolling(20).mean()
            daily['BB_std'] = daily['Close'].rolling(20).std()
            daily['BB_upper'] = daily['BB_mid'] + 2 * daily['BB_std']
            daily['BB_lower'] = daily['BB_mid'] - 2 * daily['BB_std']

            # Volume MA
            daily['Vol_MA20'] = daily['Volume'].rolling(20).mean()

            ap = []
            if daily['MA20'].notna().any():
                ap.append(mpf.make_addplot(daily['MA20'], color='#FF6B35', width=1.5, label='20D'))
            if daily['MA50'].notna().any():
                ap.append(mpf.make_addplot(daily['MA50'], color='#FFA500', width=1.5, label='50D'))
            if daily['MA200'].notna().any():
                ap.append(mpf.make_addplot(daily['MA200'], color='#4169E1', width=2.0, label='200D'))
            if daily['BB_upper'].notna().any():
                ap.append(mpf.make_addplot(daily['BB_upper'], color='#90CAF9', width=0.8, linestyle='--'))
                ap.append(mpf.make_addplot(daily['BB_lower'], color='#90CAF9', width=0.8, linestyle='--'))
            if daily['Vol_MA20'].notna().any():
                ap.append(mpf.make_addplot(daily['Vol_MA20'], panel=1, color='#FF9800', width=1.2))

            mc = mpf.make_marketcolors(up='#26a69a', down='#ef5350',
                                        wick={'up': '#26a69a', 'down': '#ef5350'},
                                        volume={'up': '#26a69a', 'down': '#ef5350'},
                                        edge='inherit')
            style = mpf.make_mpf_style(marketcolors=mc, gridstyle='--',
                                        gridcolor='#e0e0e0', facecolor='white',
                                        figcolor='white', y_on_right=True)

            path_d = os.path.join(output_dir, f"{ticker}_daily.png")
            fig, axes = mpf.plot(
                daily, type='candle', style=style,
                title=f'\n{name} ({ticker}) — Daily Chart (6 Months)',
                ylabel='Price (USD)', ylabel_lower='Volume',
                volume=True, addplot=ap,
                figsize=(14, 8), returnfig=True,
                tight_layout=True
            )
            handles = [
                mpatches.Patch(color='#FF6B35', label='20D MA'),
                mpatches.Patch(color='#FFA500', label='50D MA'),
                mpatches.Patch(color='#4169E1', label='200D MA'),
                mpatches.Patch(color='#90CAF9', label='Bollinger Bands'),
            ]
            axes[0].legend(handles=handles, loc='upper left', fontsize=9)

            fig.savefig(path_d, dpi=150, bbox_inches='tight')
            plt.close(fig)
            charts['daily'] = path_d
            print(f"  Daily chart saved: {path_d}")
    except Exception as e:
        print(f"  Daily chart error for {ticker}: {e}")

    return charts


def main():
    parser = argparse.ArgumentParser(description="Generate K-line charts for visual pattern analysis.")
    parser.add_argument('tickers', nargs='+', help='Stock ticker symbols')
    parser.add_argument('--output-dir', default='/tmp/charts', help='Directory to save chart images')
    args = parser.parse_args()

    print(f"Generating charts for: {', '.join(args.tickers)}")
    print(f"Output directory: {args.output_dir}\n")

    all_charts = {}
    for ticker in args.tickers:
        print(f"Processing {ticker}...")
        charts = generate_charts(ticker.upper(), args.output_dir)
        all_charts[ticker.upper()] = charts

    print("\n=== Chart Summary ===")
    for ticker, paths in all_charts.items():
        print(f"{ticker}:")
        for chart_type, path in paths.items():
            print(f"  {chart_type}: {path}")

    return all_charts


if __name__ == "__main__":
    main()

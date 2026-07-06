#!/usr/bin/env python3
"""
fetch_stock_data.py
Enhanced Stock Data Fetcher for Four-Dimensional Framework
Fetches: Price, Technicals, VCP metrics, EPS Growth, RS vs SPY, Institutional Ownership
Outputs a structured JSON file used by the stock-analyst skill.
"""

import argparse
import json
import sys
from datetime import datetime, timedelta

try:
    import yfinance as yf
except ImportError:
    print("Installing yfinance...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "yfinance", "-q"], check=True)
    import yfinance as yf

import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

def safe(val):
    if val is None: return None
    if isinstance(val, float) and (np.isnan(val) or np.isinf(val)): return None
    if isinstance(val, (np.integer,)): return int(val)
    if isinstance(val, (np.floating,)): return float(val)
    return val

def compute_rsi(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def compute_macd(close, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    return macd_line, signal_line

def compute_supertrend(high, low, close, period=10, multiplier=3.0):
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    upper = (high + low) / 2 + multiplier * atr
    lower = (high + low) / 2 - multiplier * atr
    direction = pd.Series(index=close.index, dtype=int)
    for i in range(1, len(close)):
        if close.iloc[i] > upper.iloc[i-1]:
            direction.iloc[i] = 1
        elif close.iloc[i] < lower.iloc[i-1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i-1]
    st_val = lower.iloc[-1] if direction.iloc[-1]==1 else upper.iloc[-1]
    return direction.iloc[-1], st_val

def get_spy_return():
    try:
        spy = yf.Ticker("SPY")
        hist = spy.history(period="1y")
        if not hist.empty:
            return (hist['Close'].iloc[-1] / hist['Close'].iloc[0] - 1) * 100
    except:
        pass
    return 0

def analyze_ticker(ticker_symbol, spy_ret):
    ticker = yf.Ticker(ticker_symbol)
    info = ticker.info

    # --- Price History ---
    hist_1y = ticker.history(period="1y", interval="1d", auto_adjust=True)
    
    if hist_1y.empty or len(hist_1y) < 200:
        return {"ticker": ticker_symbol, "error": "Insufficient price history"}

    close = hist_1y["Close"]
    high = hist_1y["High"]
    low = hist_1y["Low"]
    volume = hist_1y["Volume"]

    current_price = safe(close.iloc[-1])
    price_52w_high = safe(high.max())
    price_52w_low = safe(low.min())
    
    ret_1m = safe((current_price / close.iloc[-22] - 1) * 100) if len(close) >= 22 else None
    ret_3m = safe((current_price / close.iloc[-66] - 1) * 100) if len(close) >= 66 else None
    ret_1y = safe((current_price / close.iloc[0] - 1) * 100)
    
    rs_score = 99 if ret_1y > (spy_ret * 3) else (80 if ret_1y > (spy_ret * 1.5) else (50 if ret_1y > spy_ret else 30))

    # --- Moving Averages ---
    ma20 = safe(close.rolling(20).mean().iloc[-1])
    ma50 = safe(close.rolling(50).mean().iloc[-1])
    ma150 = safe(close.rolling(150).mean().iloc[-1])
    ma200 = safe(close.rolling(200).mean().iloc[-1])
    
    weekly_close = close.resample('W').last().dropna()
    ma20w = safe(weekly_close.rolling(20).mean().iloc[-1]) if len(weekly_close) >= 20 else None

    # --- RSI ---
    rsi_14 = safe(compute_rsi(close).iloc[-1])
    rsi_weekly = safe(compute_rsi(weekly_close).iloc[-1]) if len(weekly_close) >= 14 else 50

    # --- MACD & SuperTrend ---
    macd_line, signal_line = compute_macd(close)
    macd_val = safe(macd_line.iloc[-1])
    macd_signal = safe(signal_line.iloc[-1])
    macd_trend = "Bullish" if macd_val and macd_signal and macd_val > macd_signal else "Bearish"

    st_dir, st_support = compute_supertrend(high, low, close)
    st_direction = "Bullish" if st_dir == 1 else "Bearish"

    # --- VCP Metrics ---
    vol_20d = safe(volume.rolling(20).mean().iloc[-1])
    vol_5d = safe(volume.tail(5).mean())
    volume_ratio = safe(vol_5d / vol_20d) if vol_20d and vol_20d > 0 else 1

    range_10d = (close.tail(10).max() - close.tail(10).min()) / close.tail(10).mean() * 100
    range_30d = (close.tail(30).max() - close.tail(30).min()) / close.tail(30).mean() * 100
    tightness = safe(range_10d / range_30d) if range_30d > 0 else 1

    # --- Fundamentals & Institutions ---
    def g(key): return safe(info.get(key))

    market_cap = g("marketCap")
    pe_forward = g("forwardPE")
    peg_ratio = g("pegRatio")
    
    eps_growth = g("earningsQuarterlyGrowth")
    eps_growth_pct = round(eps_growth * 100, 2) if eps_growth else 0
    
    rev_growth = g("revenueGrowth")
    rev_growth_pct = round(rev_growth * 100, 2) if rev_growth else 0
    
    inst_own = g("heldPercentInstitutions")
    inst_own_pct = round(inst_own * 100, 2) if inst_own else 0
    
    analyst_target = g("targetMeanPrice")
    analyst_recommendation = g("recommendationKey")
    company_name = g("longName") or ticker_symbol

    # --- Four-Dimensional Evaluation ---
    dim1_eps = eps_growth_pct >= 20
    dim2_rs = rs_score >= 80
    dim3_inst = inst_own_pct >= 30
    dim4_tech = (current_price > ma50 > ma150 > ma200) and (volume_ratio < 0.9) and (50 <= rsi_14 <= 70)
    
    score = sum([dim1_eps, dim2_rs, dim3_inst, dim4_tech])

    return {
        "ticker": ticker_symbol,
        "company_name": company_name,
        "as_of_date": datetime.now().strftime("%Y-%m-%d"),
        "price": {
            "current": current_price,
            "52w_high": price_52w_high,
            "52w_low": price_52w_low,
            "return_1m_pct": ret_1m,
            "return_3m_pct": ret_3m,
            "return_1y_pct": ret_1y,
            "spy_return_1y_pct": safe(spy_ret),
            "rs_rating": rs_score,
        },
        "four_dimensions": {
            "eps_acceleration": {"pass": bool(dim1_eps), "value": eps_growth_pct},
            "relative_strength": {"pass": bool(dim2_rs), "value": rs_score},
            "institutional_sponsorship": {"pass": bool(dim3_inst), "value": inst_own_pct},
            "technical_confirmation": {
                "pass": bool(dim4_tech),
                "rsi_daily": rsi_14,
                "volume_ratio": volume_ratio,
                "tightness_ratio": tightness,
                "ma_trend_template": bool(current_price > ma50 > ma150 > ma200)
            },
            "total_score": int(score)
        },
        "technicals": {
            "rsi_14_daily": rsi_14,
            "rsi_14_weekly": rsi_weekly,
            "macd_trend": macd_trend,
            "supertrend_direction": st_direction,
            "ma20_daily": ma20,
            "ma50_daily": ma50,
            "ma150_daily": ma150,
            "ma200_daily": ma200
        },
        "fundamentals": {
            "market_cap": market_cap,
            "pe_forward": pe_forward,
            "peg_ratio": peg_ratio,
            "revenue_growth_yoy_pct": rev_growth_pct,
        },
        "analyst": {
            "recommendation": analyst_recommendation,
            "target_mean": analyst_target,
        },
        "traders_plan": {
            "hold_period": "Multi-week Swing (2–6 weeks)",
            "entry_aggressive": current_price,
            "entry_conservative": safe(price_52w_high * 0.98),
            "stop_loss": safe(current_price * 0.95),
            "target_1": safe(current_price * 1.05),
            "target_2": safe(current_price * 1.15),
        },
    }

def main():
    parser = argparse.ArgumentParser(description="Fetch comprehensive stock data for Four-Dimensional analysis.")
    parser.add_argument("tickers", nargs="+", help="Stock ticker symbols (e.g. MRK LLY JNJ)")
    parser.add_argument("--output", default="/tmp/stock_analysis.json", help="Output JSON file path")
    args = parser.parse_args()

    spy_ret = get_spy_return()
    results = []
    
    for ticker in args.tickers:
        print(f"Fetching data for {ticker}...")
        try:
            data = analyze_ticker(ticker.upper(), spy_ret)
            results.append(data)
        except Exception as e:
            results.append({"ticker": ticker.upper(), "error": str(e)})

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nData saved to: {args.output}")
    return args.output

if __name__ == "__main__":
    main()

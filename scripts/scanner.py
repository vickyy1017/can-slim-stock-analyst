#!/usr/bin/env python3
"""
scanner.py — TML Breakout Scanner
Based on ZST "炒股与禅心" + CAN SLIM + SEPA Four-Dimensional Framework.

Scans a sector or custom ticker list and outputs a tiered report:
  - Tier A: Small/Mid-Cap Leaders ($500M–$10B) — highest upside potential
  - Tier B: Large-Cap Leaders ($10B–$100B) — liquid, institutional-grade
  - Tier C: Mega-Cap ($100B+) — defensive, lower upside

Usage:
  python3 scanner.py --sector healthcare --output /tmp/scan_results.md
  python3 scanner.py --sector tech --output /tmp/scan_results.md
  python3 scanner.py --tickers NVDA AAPL MSFT --output /tmp/scan_results.md
  python3 scanner.py --sector all --output /tmp/scan_results.md

Sectors: healthcare, tech, finance, consumer, energy, industrial, all
"""

import argparse
import json
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

# ─── Ticker Universe ──────────────────────────────────────────────────────────

SECTORS = {
    "healthcare": [
        "LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY", "AMGN",
        "GILD", "ISRG", "SYK", "BSX", "MDT", "EW", "REGN", "VRTX", "BIIB",
        "IDXX", "IQV", "CNC", "HUM", "CVS", "CI", "HCA", "MCK", "DGX", "RMD",
        "ALGN", "DXCM", "ZTS", "MRNA", "PFE", "ELV", "MOH", "GEHC",
        "NBIX", "INCY", "JAZZ", "EXEL", "PODD", "ALNY", "SRPT", "IONS",
        "ACAD", "BMRN", "VTRS", "OGN", "HIMS", "RXRX", "ROIV", "LEGN",
        "KRYS", "KYMR", "RCKT", "ARWR", "NVCR",
    ],
    "tech": [
        "NVDA", "MSFT", "AAPL", "META", "GOOGL", "AMZN", "TSLA", "AVGO",
        "AMD", "ORCL", "CRM", "ADBE", "NOW", "INTU", "QCOM", "TXN",
        "AMAT", "LRCX", "KLAC", "MU", "MRVL", "SMCI", "PLTR", "APP",
        "SNOW", "DDOG", "ZS", "CRWD", "PANW", "FTNT", "NET", "OKTA",
        "BILL", "HUBS", "MNDY", "TTD", "RBLX", "U", "GTLB",
        "ARM", "ASML", "TSM", "AEHR", "ONTO", "COHU", "FORM", "ACLS",
        "SMAR", "DOCN", "ESTC", "MDB", "CFLT", "DKNG", "HOOD",
    ],
    "finance": [
        "JPM", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "AXP", "V", "MA",
        "PYPL", "SQ", "AFRM", "SOFI", "NU", "LC", "UPST", "COIN",
        "CME", "ICE", "CBOE", "NDAQ", "SPGI", "MCO", "FDS",
        "BX", "KKR", "APO", "CG", "ARES",
    ],
    "consumer": [
        "AMZN", "TSLA", "NKE", "LULU", "SBUX", "MCD", "CMG", "DKNG",
        "ROST", "TJX", "COST", "WMT", "TGT", "HD", "LOW",
        "ELF", "ULTA", "COTY", "KVYO", "CELH", "MNST",
        "BURL", "FIVE", "OLLI", "BOOT", "DECK", "SKX", "CROX",
        "WING", "SHAK", "TXRH", "DENN", "JACK",
    ],
    "energy": [
        "XOM", "CVX", "COP", "EOG", "SLB", "HAL", "BKR", "PSX", "VLO",
        "MPC", "OXY", "DVN", "FANG", "PXD", "APA", "MRO",
        "CTRA", "SM", "MTDR", "CHRD", "NOG",
    ],
    "industrial": [
        "GE", "HON", "MMM", "CAT", "DE", "RTX", "LMT", "NOC", "GD", "BA",
        "UPS", "FDX", "EXPD", "XPO", "SAIA", "ODFL", "JBHT",
        "PWR", "STLD", "NUE", "RS", "WIRE",
        "AXON", "LDOS", "CACI", "SAIC", "BAH",
    ],
}

SECTORS["all"] = list({t for tickers in SECTORS.values() for t in tickers})

# ─── Helpers ──────────────────────────────────────────────────────────────────

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

def compute_macd(close):
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd.iloc[-1], signal.iloc[-1]

def get_spy_return():
    try:
        spy = yf.Ticker("SPY")
        h = spy.history(period="1y")
        if not h.empty:
            return (h['Close'].iloc[-1] / h['Close'].iloc[0] - 1) * 100
    except:
        pass
    return 20.0  # fallback

def cap_tier(market_cap):
    if market_cap is None: return "Unknown"
    if market_cap >= 100e9: return "Mega"
    if market_cap >= 10e9:  return "Large"
    if market_cap >= 2e9:   return "Mid"
    if market_cap >= 500e6: return "Small"
    return "Micro"

def cap_tier_label(tier):
    return {"Mega": "Tier C (Mega-Cap $100B+)", "Large": "Tier B (Large-Cap $10B–$100B)",
            "Mid": "Tier A (Mid-Cap $2B–$10B)", "Small": "Tier A (Small-Cap $500M–$2B)",
            "Micro": "Tier A (Micro-Cap <$500M)", "Unknown": "Unknown"}.get(tier, tier)

# ─── Core Scanner ─────────────────────────────────────────────────────────────

def scan_ticker(ticker, spy_ret):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y", interval="1d", auto_adjust=True)
        if hist.empty or len(hist) < 200:
            return None

        close = hist['Close']
        high  = hist['High']
        low   = hist['Low']
        vol   = hist['Volume']

        price     = safe(close.iloc[-1])
        high_52w  = safe(close.max())
        low_52w   = safe(close.min())
        pct_high  = (price / high_52w) * 100 if high_52w else 0

        # ── TML '高' conditions ──────────────────────────────────────────────
        # Price >= $30 (ZST: best >$100)
        if price < 30:
            return None

        # Dollar volume >= $50M/day (proxy for >$200M; strict filter later)
        avg_vol_20d = safe(vol.rolling(20).mean().iloc[-1])
        dollar_vol  = (price * avg_vol_20d) if avg_vol_20d else 0
        if dollar_vol < 50e6:
            return None

        # Near 52-week high (within 30% — ZST: best at ATH)
        if pct_high < 70:
            return None

        # ── Moving Averages (Trend Template) ────────────────────────────────
        ma50  = safe(close.rolling(50).mean().iloc[-1])
        ma150 = safe(close.rolling(150).mean().iloc[-1])
        ma200 = safe(close.rolling(200).mean().iloc[-1])
        ma10w = None
        weekly_close = close.resample('W').last().dropna()
        if len(weekly_close) >= 10:
            ma10w = safe(weekly_close.rolling(10).mean().iloc[-1])

        trend_template = bool(
            ma50 and ma150 and ma200 and
            price > ma50 > ma150 > ma200
        )

        # ── RSI ──────────────────────────────────────────────────────────────
        rsi_d = safe(compute_rsi(close).iloc[-1])
        rsi_w = safe(compute_rsi(weekly_close).iloc[-1]) if len(weekly_close) >= 14 else 50

        # ── MACD ─────────────────────────────────────────────────────────────
        macd_val, sig_val = compute_macd(close)
        macd_bull = bool(macd_val > sig_val)

        # ── VCP / Consolidation ──────────────────────────────────────────────
        vol_5d    = safe(vol.tail(5).mean())
        vol_ratio = safe(vol_5d / avg_vol_20d) if avg_vol_20d else 1.0

        range_10d = (close.tail(10).max() - close.tail(10).min()) / close.tail(10).mean() * 100
        range_30d = (close.tail(30).max() - close.tail(30).min()) / close.tail(30).mean() * 100
        tightness = safe(range_10d / range_30d) if range_30d > 0 else 1.0

        # ── Relative Strength vs SPY ─────────────────────────────────────────
        ret_1y = safe((price / close.iloc[0] - 1) * 100)
        rs_score = (99 if ret_1y > spy_ret * 3 else
                    80 if ret_1y > spy_ret * 1.5 else
                    50 if ret_1y > spy_ret else 30)

        # ── Fundamentals ─────────────────────────────────────────────────────
        info = stock.info
        market_cap   = safe(info.get('marketCap'))
        eps_growth   = safe(info.get('earningsQuarterlyGrowth'))
        eps_growth_p = round(eps_growth * 100, 1) if eps_growth else 0
        rev_growth   = safe(info.get('revenueGrowth'))
        rev_growth_p = round(rev_growth * 100, 1) if rev_growth else 0
        inst_own     = safe(info.get('heldPercentInstitutions'))
        inst_own_p   = round(inst_own * 100, 1) if inst_own else 0
        fwd_pe       = safe(info.get('forwardPE'))
        target_mean  = safe(info.get('targetMeanPrice'))
        rec          = info.get('recommendationKey', '')
        name         = info.get('longName', ticker)

        upside = round((target_mean / price - 1) * 100, 1) if target_mean and price else None

        # ── Weekly Closing Range (ZST sell signal check) ─────────────────────
        if len(weekly_close) >= 2:
            w_high  = hist['High'].resample('W').max().dropna().iloc[-1]
            w_low   = hist['Low'].resample('W').min().dropna().iloc[-1]
            w_close = weekly_close.iloc[-1]
            wcr = round((w_close - w_low) / (w_high - w_low) * 100, 1) if (w_high - w_low) > 0 else 50
        else:
            wcr = 50

        # ── CAN SLIM: Check if near ALL-TIME HIGH (no overhead resistance) ───────
        # Fetch 5-year history to check if current price is near all-time high
        try:
            hist_5y = stock.history(period="5y", interval="1wk", auto_adjust=True)
            all_time_high = safe(hist_5y['High'].max()) if not hist_5y.empty else high_52w
        except:
            all_time_high = high_52w
        pct_of_ath = (price / all_time_high * 100) if all_time_high else 0
        near_ath = pct_of_ath >= 90  # Within 10% of all-time high = minimal overhead resistance
        heavy_overhead = pct_of_ath < 70  # More than 30% below ATH = lots of overhead supply

        # ── CAN SLIM: A letter — Annual EPS trend ────────────────────────────
        eps_fwd = safe(info.get('forwardEps'))
        eps_ttm = safe(info.get('trailingEps'))
        annual_eps_positive = bool(eps_ttm and eps_ttm > 0 and eps_fwd and eps_fwd > eps_ttm)

        # ── Stage Estimation (O'Neil Base Count Approximation) ───────────────
        # Uses price structure to estimate which stage the stock is in.
        # Stage 1: Stock is still in a long base/repair phase after a major decline.
        #          Price is below or just recovering to the 200-day MA.
        # Stage 2: First or second proper base after a confirmed uptrend.
        #          Price is above all key MAs, near 52W high, RS strong.
        # Stage 3: Third or later base. Stock has already made a big advance.
        #          Price is far extended from original base, RS may be weakening.
        # Stage 4: Distribution / decline phase. Price below 200-day MA.
        #
        # Approximation logic (without full base-count tracking):
        # - Stage 1: price < ma200 OR (price < ma50 and pct_of_ath < 50)
        # - Stage 2: trend_template AND near_ath AND ret_1y between 20% and 150%
        # - Stage 3: trend_template AND near_ath AND ret_1y > 150% (already big advance)
        # - Stage 4: price < ma200 and declining
        #
        # Note: This is an approximation. Visual chart inspection is required
        # for accurate base counting (Stage 1 vs Stage 2 especially).
        if ma200 and price < ma200 * 0.95:
            stage = 4  # Below 200-day MA — distribution or decline
            stage_label = "Stage 4 — Decline ❌"
            stage_note = "Price below 200-day MA. Do NOT buy."
        elif ma200 and price < ma200 * 1.05 and pct_of_ath < 60:
            stage = 1  # Just recovering from a major decline
            stage_label = "Stage 1 — Base Building ⏳"
            stage_note = "Still forming base after major decline. Too early."
        elif trend_template and near_ath and ret_1y and ret_1y > 200:
            stage = 3  # Very extended — likely Stage 3 or late Stage 2
            stage_label = "Stage 3 — Late Stage ⚠️"
            stage_note = "Stock has advanced >200% from base. High failure risk. Caution."
        elif trend_template and near_ath and ret_1y and ret_1y > 80:
            stage = 3  # Moderately extended — could be Stage 2 late or Stage 3
            stage_label = "Stage 2-3 — Extended ⚠️"
            stage_note = "Big prior advance. May be late Stage 2 or early Stage 3. Confirm with chart."
        elif trend_template and near_ath:
            stage = 2  # Ideal: in uptrend, near ATH, not yet over-extended
            stage_label = "Stage 2 — Prime Zone ✅"
            stage_note = "Ideal CAN SLIM buy zone. First or second proper base."
        elif trend_template and not near_ath and pct_of_ath >= 70:
            stage = 2  # Likely Stage 2 but with some overhead
            stage_label = "Stage 2 — Moderate Overhead ⚠️"
            stage_note = "In uptrend but not at ATH. Some overhead supply remains."
        else:
            stage = 1
            stage_label = "Stage 1 — Base Building ⏳"
            stage_note = "Not yet in confirmed uptrend. Wait for Stage 2 confirmation."

        # Stage scoring adjustment
        if stage == 2 and 'Prime' in stage_label:  tml_score += 2  # Bonus for prime Stage 2
        elif stage == 3:                            tml_score -= 2  # Penalty for late stage
        elif stage == 4:                            tml_score -= 5  # Heavy penalty for Stage 4

        # ── Four-Dimensional Score ────────────────────────────────────────────
        d1 = eps_growth_p >= 20
        d2 = rs_score >= 80
        d3 = inst_own_p >= 30
        d4 = trend_template and (vol_ratio < 1.0) and (50 <= rsi_d <= 70)
        score_4d = sum([d1, d2, d3, d4])

        # ── ZST TML Score (bonus scoring) ────────────────────────────────────
        tml_score = 0
        if dollar_vol >= 200e6:  tml_score += 2   # High dollar volume
        if price >= 100:         tml_score += 1   # High price
        if near_ath:             tml_score += 3   # Near ATH = minimal overhead resistance (CAN SLIM N)
        elif pct_high >= 95:     tml_score += 1   # Near 52W high but not ATH
        if rs_score >= 80:       tml_score += 2   # RS >= 80 (L letter)
        if inst_own_p >= 50:     tml_score += 2   # Strong institutional (I letter)
        if eps_growth_p >= 25:   tml_score += 2   # C: Current EPS >= 25%
        if annual_eps_positive:  tml_score += 1   # A: Annual EPS growing
        if rev_growth_p >= 20:   tml_score += 1   # Sales growth (C/A support)
        if trend_template:       tml_score += 2   # Trend Template (S letter setup)
        if tightness < 0.5:      tml_score += 2   # VCP tightening (S letter)
        if vol_ratio < 0.8:      tml_score += 1   # Volume contraction (S letter)
        if macd_bull:            tml_score += 1   # MACD bullish
        if 50 <= rsi_d <= 68:    tml_score += 2   # RSI sweet spot
        if wcr >= 60:            tml_score += 1   # Strong weekly close
        if heavy_overhead:       tml_score -= 3   # Penalty: heavy overhead supply

        tier = cap_tier(market_cap)

        return {
            "ticker":       ticker,
            "name":         name[:35],
            "price":        price,
            "market_cap":   market_cap,
            "tier":         tier,
            "pct_from_high": round(pct_high, 1),
            "dollar_vol_m": round(dollar_vol / 1e6, 0),
            "rsi_daily":    round(rsi_d, 1),
            "rsi_weekly":   round(rsi_w, 1),
            "macd_bull":    macd_bull,
            "trend_template": trend_template,
            "vol_ratio":    round(vol_ratio, 2),
            "tightness":    round(tightness, 2),
            "wcr":          wcr,
            "rs_score":     rs_score,
            "ret_1y":       round(ret_1y, 1),
            "eps_growth":   eps_growth_p,
            "rev_growth":   rev_growth_p,
            "inst_own":     inst_own_p,
            "fwd_pe":       fwd_pe,
            "target_mean":  target_mean,
            "upside":       upside,
            "rec":          rec,
            "score_4d":     score_4d,
            "tml_score":    tml_score,
            "all_time_high": all_time_high,
            "pct_of_ath":   round(pct_of_ath, 1),
            "near_ath":     near_ath,
            "heavy_overhead": heavy_overhead,
            "annual_eps_positive": annual_eps_positive,
            "stage": stage,
            "stage_label": stage_label,
            "stage_note": stage_note,
            "dims": {
                "eps": bool(d1),
                "rs":  bool(d2),
                "inst": bool(d3),
                "tech": bool(d4),
            }
        }
    except Exception as e:
        return None

# ─── Report Generator ─────────────────────────────────────────────────────────

def generate_report(results, sector, output_path):
    date = datetime.now().strftime("%Y-%m-%d")
    lines = []

    lines.append(f"# TML Breakout Scanner — {sector.upper()} Sector")
    lines.append(f"**Date:** {date} | **Framework:** ZST TML (CAN SLIM + SEPA + VCP)**")
    lines.append(f"**Total candidates scanned:** {len(results)}\n")

    # Sort by TML score
    results.sort(key=lambda x: x['tml_score'], reverse=True)

    # Tier buckets
    tier_a = [r for r in results if r['tier'] in ('Small', 'Mid', 'Micro')]
    tier_b = [r for r in results if r['tier'] == 'Large']
    tier_c = [r for r in results if r['tier'] == 'Mega']

    def render_tier(title, emoji, desc, stocks, min_show=3, max_show=10):
        if not stocks:
            return
        lines.append(f"---\n## {emoji} {title}")
        lines.append(f"*{desc}*\n")
        lines.append("| Rank | Ticker | Stage | Price | %ATH | RSI-D | TrendTpl | EPS% | RS Rating | Inst% | Upside | TML |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |")
        for i, r in enumerate(stocks[:max_show], 1):
            tt  = "✅" if r['trend_template'] else "❌"
            rsi_flag = "⚠️" if r['rsi_daily'] > 70 else "✅"
            up = f"+{r['upside']}%" if r['upside'] and r['upside'] > 0 else (f"{r['upside']}%" if r['upside'] else "N/A")
            # Compact stage label
            sl = r.get('stage_label', '?')
            stage_short = sl.split('—')[0].strip() if '—' in sl else sl
            # RS Rating label
            rs = r['rs_score']
            rs_label = "Excellent" if rs >= 90 else ("Strong" if rs >= 80 else ("Avg" if rs >= 50 else "Weak"))
            lines.append(
                f"| {i} | **{r['ticker']}** | {stage_short} "
                f"| ${r['price']:.2f} | {r.get('pct_of_ath',0):.0f}% "
                f"| {r['rsi_daily']} {rsi_flag} | {tt} "
                f"| {r['eps_growth']}% | {rs} ({rs_label}) | {r['inst_own']}% "
                f"| {up} | {r['tml_score']} |"
            )
        lines.append("")

        # Top 3 deep-dive
        lines.append(f"### Top Picks — {title}\n")
        for r in stocks[:min(3, len(stocks))]:
            d = r['dims']
            ath_status = "✅ Near ATH — minimal overhead resistance" if r.get('near_ath') else ("⚠️ Heavy overhead supply — large base still forming" if r.get('heavy_overhead') else "~ Moderate overhead")
            stage_label = r.get('stage_label', 'Unknown')
            stage_note = r.get('stage_note', '')
            lines.append(f"**{r['ticker']} — {r['name']}**")
            lines.append(f"- **Stage: {stage_label}** — {stage_note}")
            lines.append(f"- Price: ${r['price']:.2f} | ATH: ${r.get('all_time_high',0):.2f} ({r.get('pct_of_ath',0):.0f}% of ATH) | {ath_status}")
            lines.append(f"  > *Note: Stage is estimated from price structure. Confirm with visual chart inspection.*")
            lines.append(f"- Market Cap: ${r['market_cap']/1e9:.1f}B | Fwd P/E: {r['fwd_pe']} | Dollar Vol: ${r['dollar_vol_m']:.0f}M/day")
            lines.append(f"- **C (Current EPS):** {r['eps_growth']}% {'✅' if d['eps'] else '❌'} | **A (Annual EPS):** {'✅ Growing' if r.get('annual_eps_positive') else '❌'} | Rev Growth: {r['rev_growth']}%")
            lines.append(f"- **L (RS Score):** {r['rs_score']} {'✅' if d['rs'] else '❌'} | **I (Institutions):** {r['inst_own']}% {'✅' if d['inst'] else '❌'}")
            lines.append(f"- **S (Technical):** Trend Template {'✅' if r['trend_template'] else '❌'} | RSI: {r['rsi_daily']} | Vol Ratio: {r['vol_ratio']}x | Tightness: {r['tightness']}")
            lines.append(f"- Weekly Closing Range: {r['wcr']}% {'✅ Strong' if r['wcr'] >= 60 else '⚠️ Weak'} | 1Y Return: {r['ret_1y']:+.1f}%")
            lines.append(f"- Analyst Target: ${r['target_mean']} ({r['upside']:+.1f}% upside)" if r['upside'] else "- Analyst Target: N/A")
            lines.append(f"- **Next Step:** Generate charts to visually confirm base pattern and identify exact Pivot Point")
            lines.append(f"- **Entry:** Breakout above Pivot Point on volume >= 1.5x avg | **Max Stop:** ${r['price']*0.92:.2f} (-8%)")
            lines.append("")

    render_tier(
        "Tier A — Small/Mid-Cap Leaders ($500M–$10B)", "🚀",
        "Highest upside potential. Most aligned with CAN SLIM / SEPA spirit. Prefer stocks with EPS acceleration, RS >= 80, and VCP tightening.",
        tier_a
    )
    render_tier(
        "Tier B — Large-Cap Leaders ($10B–$100B)", "📈",
        "Liquid, institutional-grade. Good for swing trades with tighter spreads. Requires stricter technical confirmation.",
        tier_b
    )
    render_tier(
        "Tier C — Mega-Cap ($100B+)", "🏦",
        "Defensive, lower upside. Use for portfolio anchoring or when market conditions are uncertain. Not ideal for CAN SLIM breakout plays.",
        tier_c
    )

    # ZST Sell Signal Warnings
    warnings_list = [r for r in results if r['wcr'] < 40 and r['vol_ratio'] > 1.3]
    if warnings_list:
        lines.append("---\n## ⚠️ ZST Sell Signal Warnings")
        lines.append("*Stocks showing potential institutional distribution (ZST 3-condition sell check)*\n")
        lines.append("| Ticker | Price | WCR% | Vol Ratio | RSI | Signal |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for r in warnings_list[:5]:
            lines.append(f"| **{r['ticker']}** | ${r['price']:.2f} | {r['wcr']}% ⚠️ | {r['vol_ratio']}x ⚠️ | {r['rsi_daily']} | Check 10W MA |")
        lines.append("")

    lines.append("---")
    lines.append("*This scan is for informational purposes only and does not constitute financial or investment advice.*")
    lines.append("*Always confirm setups on a weekly chart before entering. Use the 8% stop loss rule from ZST M2 Risk Management.*")

    with open(output_path, 'w') as f:
        f.write("\n".join(lines))

    print(f"Report saved to: {output_path}")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="TML Breakout Scanner — ZST CAN SLIM / SEPA Framework")
    parser.add_argument("--sector", default="healthcare",
                        choices=list(SECTORS.keys()),
                        help="Sector to scan")
    parser.add_argument("--tickers", nargs="+", help="Custom ticker list (overrides --sector)")
    parser.add_argument("--output", default="/tmp/scan_results.md", help="Output Markdown file")
    parser.add_argument("--json", default="/tmp/scan_results.json", help="Output JSON file")
    args = parser.parse_args()

    tickers = args.tickers if args.tickers else SECTORS.get(args.sector, [])
    sector  = "custom" if args.tickers else args.sector

    print(f"Scanning {len(tickers)} tickers in [{sector}] sector...")
    spy_ret = get_spy_return()
    print(f"SPY 1Y return: {spy_ret:.1f}%\n")

    results = []
    for i, t in enumerate(tickers):
        r = scan_ticker(t, spy_ret)
        if r:
            results.append(r)
        if (i + 1) % 10 == 0:
            print(f"  Processed {i+1}/{len(tickers)}, found {len(results)} candidates...")

    print(f"\nTotal candidates passing filters: {len(results)}")

    if not results:
        print("No candidates found. Try a different sector or loosen filters.")
        return

    # Save JSON
    with open(args.json, 'w') as f:
        json.dump(results, f, indent=2)

    # Generate report
    generate_report(results, sector, args.output)

    # Print quick summary
    results.sort(key=lambda x: x['tml_score'], reverse=True)
    print(f"\n{'─'*80}")
    print(f"{'TICKER':<8} {'PRICE':>8} {'%HI':>6} {'RSI':>6} {'TT':>4} {'4D':>4} {'TML':>5} {'TIER':<8}")
    print(f"{'─'*80}")
    for r in results[:20]:
        tt = "✅" if r['trend_template'] else "❌"
        print(f"{r['ticker']:<8} {r['price']:>8.2f} {r['pct_from_high']:>5.0f}% {r['rsi_daily']:>6.1f} {tt:>4} {r['score_4d']:>4} {r['tml_score']:>5} {r['tier']:<8}")

if __name__ == "__main__":
    main()

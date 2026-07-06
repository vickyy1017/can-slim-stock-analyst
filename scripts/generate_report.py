#!/usr/bin/env python3
"""
generate_report.py
Generates a Markdown report from the JSON data fetched by fetch_stock_data.py.
Features the Four-Dimensional Scorecard based on CAN SLIM / SEPA.
"""

import argparse
import json
import os

def generate_report(json_path, output_path):
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, "r") as f:
        data = json.load(f)

    if not data:
        print("Error: No data to report.")
        return

    valid_data = [d for d in data if "error" not in d]
    errors = [d for d in data if "error" in d]

    if not valid_data:
        print("Error: No valid stock data found in JSON.")
        return

    # Sort by 4D score descending
    valid_data.sort(key=lambda x: x.get("four_dimensions", {}).get("total_score", 0), reverse=True)

    lines = []
    
    # --- Multi-Stock Comparison ---
    if len(valid_data) > 1:
        lines.append("# Four-Dimensional Stock Comparison & Verdict")
        lines.append(f"**Generated:** {valid_data[0]['as_of_date']} | **Framework:** CAN SLIM / SEPA\n")
        
        lines.append("## Four-Dimensional Scorecard 🏆\n")
        lines.append("| Ticker | Total Score | EPS Growth | RS Score | Inst. Own | Tech / VCP |")
        lines.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for d in valid_data:
            t = d["ticker"]
            fd = d.get("four_dimensions", {})
            score = fd.get("total_score", 0)
            eps = "✅" if fd.get("eps_acceleration", {}).get("pass") else "❌"
            rs = "✅" if fd.get("relative_strength", {}).get("pass") else "❌"
            inst = "✅" if fd.get("institutional_sponsorship", {}).get("pass") else "❌"
            tech = "✅" if fd.get("technical_confirmation", {}).get("pass") else "❌"
            
            stars = "⭐" * score + "☆" * (4 - score)
            lines.append(f"| **{t}** | {stars} | {eps} ({fd.get('eps_acceleration',{}).get('value',0)}%) | {rs} ({fd.get('relative_strength',{}).get('value',0)}) | {inst} ({fd.get('institutional_sponsorship',{}).get('value',0)}%) | {tech} |")
        lines.append("\n")

        lines.append("## Quick Technical Comparison 📊\n")
        lines.append("| Ticker | Price | 1Y Return | RSI (Daily) | SuperTrend | Vol Ratio | Tightness |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for d in valid_data:
            t = d["ticker"]
            p = d["price"]["current"]
            ret = d["price"]["return_1y_pct"]
            tech = d["technicals"]
            fd_tech = d["four_dimensions"]["technical_confirmation"]
            
            rsi_flag = "⚠️ Overbought" if tech["rsi_14_daily"] > 70 else "✅"
            st_flag = "✅" if tech["supertrend_direction"] == "Bullish" else "❌"
            
            lines.append(f"| **{t}** | ${p:.2f} | {ret:+.1f}% | {tech['rsi_14_daily']:.1f} {rsi_flag} | {st_flag} | {fd_tech['volume_ratio']:.2f}x | {fd_tech['tightness_ratio']:.2f} |")
        lines.append("\n")

        lines.append("## Professional Verdict 🧐\n")
        best = valid_data[0]
        lines.append(f"**🥇 Top Pick: {best['ticker']}**")
        lines.append(f"Highest 4D score ({best['four_dimensions']['total_score']}/4). Watch for entry at ${best['traders_plan']['entry_aggressive']:.2f} with stop at ${best['traders_plan']['stop_loss']:.2f}.\n")
        
        lines.append("---\n*This report is for informational purposes only and does not constitute financial or investment advice.*\n\n---\n")

    # --- Individual Deep Dives ---
    lines.append("# Individual Stock Deep Dives\n")
    
    for d in valid_data:
        t = d["ticker"]
        name = d["company_name"]
        fd = d["four_dimensions"]
        tech = d["technicals"]
        tp = d["traders_plan"]
        
        stars = "⭐" * fd["total_score"] + "☆" * (4 - fd["total_score"])
        
        rs_rating = d['price'].get('rs_rating', fd['relative_strength']['value'])
        rs_label = "Excellent" if rs_rating >= 90 else ("Strong" if rs_rating >= 80 else ("Average" if rs_rating >= 50 else "Weak"))
        lines.append(f"## {name} ({t}) — Professional Analysis")
        lines.append(f"**4D Score:** {stars} | **Price:** ${d['price']['current']:.2f} | **RS Rating: {rs_rating} ({rs_label})**\n")
        
        lines.append("### 1. Fundamental Power (EPS Acceleration)")
        eps_val = fd['eps_acceleration']['value']
        lines.append(f"- **Quarterly EPS Growth:** {eps_val}% {'✅ (Pass >= 20%)' if fd['eps_acceleration']['pass'] else '❌ (Fail)'}")
        lines.append(f"- **Revenue Growth:** {d['fundamentals']['revenue_growth_yoy_pct']}%")
        lines.append(f"- **Forward P/E:** {d['fundamentals']['pe_forward']}x\n")
        
        lines.append("### 2. Relative Strength (RS Rating)")
        rs_val = fd['relative_strength']['value']
        lines.append(f"- **RS Rating: {rs_val}** ({rs_label}) {'\u2705 (Pass >= 80)' if fd['relative_strength']['pass'] else '\u274c (Fail < 80)'}")
        lines.append(f"- **1-Year Return:** {d['price']['return_1y_pct']:+.1f}% (SPY: {d['price']['spy_return_1y_pct']:+.1f}%)")
        ret_1m = d['price'].get('return_1m_pct')
        ret_3m = d['price'].get('return_3m_pct')
        if ret_1m: lines.append(f"- **1-Month Return:** {ret_1m:+.1f}%")
        if ret_3m: lines.append(f"- **3-Month Return:** {ret_3m:+.1f}%")
        lines.append("")
        
        lines.append("### 3. Institutional Sponsorship")
        inst_val = fd['institutional_sponsorship']['value']
        lines.append(f"- **Institutional Ownership:** {inst_val}% {'✅ (Pass >= 30%)' if fd['institutional_sponsorship']['pass'] else '❌ (Fail)'}\n")
        
        lines.append("### 4. Technical Confirmation (VCP/RSI/MAs)")
        lines.append(f"- **Trend Template (MAs):** {'✅ Price > 50 > 150 > 200' if fd['technical_confirmation']['ma_trend_template'] else '❌ Not aligned'}")
        lines.append(f"- **Volume Contraction:** {fd['technical_confirmation']['volume_ratio']:.2f}x (5D avg vs 20D avg)")
        lines.append(f"- **Price Tightness:** {fd['technical_confirmation']['tightness_ratio']:.2f} (10D range vs 30D range)")
        lines.append(f"- **Daily RSI:** {tech['rsi_14_daily']:.1f}")
        lines.append(f"- **SuperTrend:** {tech['supertrend_direction']}\n")
        
        lines.append("### Trader's Plan 📋")
        lines.append(f"**Hold Period:** {tp['hold_period']}")
        lines.append("| Scenario | Entry | Stop Loss | Target 1 | Target 2 |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        lines.append(f"| **Breakout/Aggressive** | ${tp['entry_aggressive']:.2f} | ${tp['stop_loss']:.2f} | ${tp['target_1']:.2f} | ${tp['target_2']:.2f} |")
        lines.append(f"| **Pullback/Conservative** | ${tp['entry_conservative']:.2f} | ${tp['stop_loss']:.2f} | ${tp['target_1']:.2f} | ${tp['target_2']:.2f} |\n")
        
        lines.append("**Trade Management Rules:**")
        lines.append("- At Target 1 (+5%): Sell 30-50% and move stop to breakeven.")
        lines.append("- At Target 2 (+15%): Sell another 30% and trail stop with 10-day MA.")
        lines.append(f"- **No-Trade Warning:** If daily RSI > 72, wait for pullback.\n")
        lines.append("---\n")

    if errors:
        lines.append("## Errors")
        for e in errors:
            lines.append(f"- **{e['ticker']}**: {e['error']}")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    print(f"Report saved to: {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Markdown report from stock JSON data.")
    parser.add_argument("json_path", help="Path to input JSON file")
    parser.add_argument("--output", default="/tmp/stock_report.md", help="Path to output Markdown file")
    args = parser.parse_args()

    generate_report(args.json_path, args.output)

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fetch_yields import fetch_all_yields, get_last_business_day, save_to_csv, load_history
from analyze_regime import compute_spreads, classify_regime, get_asset_recommendations
from call_deepseek import generate_daily_report

def main():
    print("🚀 Starting daily yield curve report...")
    
    # Get last business day
    last_biz = get_last_business_day()
    print(f"📅 Fetching yields for: {last_biz}")
    
    # Fetch yields
    yields = fetch_all_yields(last_biz)
    if yields.get('10Y') is None or yields.get('3M') is None:
        print("❌ Failed to fetch yield data. Check FRED API key.")
        return
    
    yields['date'] = last_biz
    
    # Save to CSV
    df = save_to_csv(yields)
    
    # Load history and compute spreads
    df = load_history()
    df = compute_spreads(df)
    
    # Get latest data
    latest = df.iloc[-1]
    regime, confidence, explanation = classify_regime(latest, df)
    
    # Generate report
    report = generate_daily_report(
        yields=yields,
        regime=regime,
        confidence=confidence,
        explanation=explanation,
        history_df=df
    )
    
    # Print report
    print(report)
    
    # Save report to file
    report_dir = "reports"
    os.makedirs(report_dir, exist_ok=True)
    report_file = f"{report_dir}/report_{last_biz}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"📄 Report saved to: {report_file}")
    
    # Also save latest summary to a JSON for easy consumption
    summary = {
        "date": last_biz,
        "yields": yields,
        "spreads": {
            "10Y_3M": yields['10Y_3M_spread'],
            "10Y_2Y": yields['10Y_2Y_spread']
        },
        "regime": regime,
        "confidence": confidence,
        "explanation": explanation
    }
    import json
    with open(f"{report_dir}/summary_{last_biz}.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("✅ Done!")

if __name__ == "__main__":
    main()

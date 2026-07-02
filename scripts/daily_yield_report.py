import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fetch_yields import fetch_missing_dates, load_history
from analyze_regime import compute_spreads, classify_regime
from call_deepseek import generate_daily_report

def main():
    print("🚀 Starting daily yield curve report...")
    
    # Fetch only missing data (smart incremental update)
    df = fetch_missing_dates()
    
    if df is None or df.empty:
        print("❌ Failed to fetch yield data. Check FRED API key.")
        return
    
    # Compute spreads
    df = compute_spreads(df)
    
    # Get latest data with spreads
    latest = df.iloc[-1]
    date = latest['date']
    
    # Prepare yields dict for report
    yields = {
        "date": date,
        "3M": latest['3M'],
        "2Y": latest['2Y'],
        "5Y": latest['5Y'],
        "10Y": latest['10Y'],
        "30Y": latest['30Y'],
        "10Y_3M_spread": latest['10Y_3M_spread'],
        "10Y_2Y_spread": latest['10Y_2Y_spread'],
        "2Y_3M_spread": latest['2Y_3M_spread']
    }
    
    # Classify regime
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
    report_file = f"{report_dir}/report_{date}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"📄 Report saved to: {report_file}")
    
    # Also save latest summary to a JSON
    summary = {
        "date": date,
        "yields": yields,
        "spreads": {
            "10Y_3M": yields['10Y_3M_spread'],
            "10Y_2Y": yields['10Y_2Y_spread'],
            "2Y_3M": yields['2Y_3M_spread']
        },
        "regime": regime,
        "confidence": confidence,
        "explanation": explanation
    }
    import json
    with open(f"{report_dir}/summary_{date}.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("✅ Done!")

if __name__ == "__main__":
    main()

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# ✅ FIX: Changed import from the missing 'fetch_yields' to 'fetch_all_data'
from fetch_all_data import fetch_all_data, load_history
from analyze_regime import compute_spreads, classify_regime
from call_deepseek import generate_daily_report

def main():
    print("🚀 Starting daily yield curve report...")
    
    # ✅ FIX: Use the correct function to load/update data
    df = fetch_all_data()
    
    if df is None or df.empty:
        print("❌ Failed to fetch yield data. Check FRED API key.")
        return
    
    # Compute spreads
    df = compute_spreads(df)
    
    # Get latest data (always use the most recent available)
    latest = df.iloc[-1]
    date = latest['date']
    
    print(f"📅 Using latest available data: {date}")
    
    # Prepare yields dict for report
    yields = {
        "date": date,
        "3M": latest['3M'],
        "2Y": latest['2Y'],
        "5Y": latest['5Y'],
        "10Y": latest['10Y'],
        "30Y": latest['30Y'],
        "DXY": latest.get('DXY'),
        "FEDFUNDS": latest.get('FEDFUNDS'),
        "10Y_3M_spread": latest['10Y_3M_spread'],
        "10Y_2Y_spread": latest['10Y_2Y_spread'],
        "2Y_3M_spread": latest['2Y_3M_spread']
    }
    
    # Classify regime
    regime, confidence, explanation = classify_regime(latest, df)
    
    # Generate report with Gemini (using last 365 days of data)
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
    
    # Write the file (automatically overwrites if exists)
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"📄 Report saved to: {report_file}")
    
    print("✅ Done!")

if __name__ == "__main__":
    main()

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fetch_yields import fetch_missing_dates, load_history
from analyze_regime import compute_spreads, classify_regime
from call_gemma import generate_daily_report_gemma

def main():
    print("🚀 Starting Gemma 2 9B report...")

    df = fetch_missing_dates()
    if df is None or df.empty:
        print("❌ No yield data found.")
        return

    df = compute_spreads(df)
    latest = df.iloc[-1]
    date = latest['date']

    yields = {
        'date': date,
        '3M': latest['3M'],
        '2Y': latest['2Y'],
        '5Y': latest['5Y'],
        '10Y': latest['10Y'],
        '30Y': latest['30Y'],
        '10Y_3M_spread': latest['10Y_3M_spread'],
        '10Y_2Y_spread': latest['10Y_2Y_spread'],
        '2Y_3M_spread': latest['2Y_3M_spread']
    }

    regime, confidence, explanation = classify_regime(latest, df)

    print(f"📅 Generating report for {date}...")
    report = generate_daily_report_gemma(yields, regime, confidence, explanation, df)

    report_file = f"reports/gemma_report_{date}.txt"
    with open(report_file, 'w') as f:
        f.write(report)

    print(f"✅ Gemma report saved to {report_file}")

if __name__ == "__main__":
    main()

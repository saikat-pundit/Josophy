import os
import sys
from datetime import datetime
import pandas as pd
from openai import OpenAI
from dateutil.relativedelta import relativedelta

def main():
    print("🚀 Starting parallel Nemotron-3-Ultra yield report...")
    
    # 1. Setup API Client
    NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
    if not NVIDIA_API_KEY:
        print("⚠️ No NVIDIA_API_KEY found. Check GitHub Secrets.")
        return

    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=NVIDIA_API_KEY
    )

    # 2. Load and prep data
    csv_file = "data/yield_history.csv"
    if not os.path.exists(csv_file):
        print(f"⚠️ {csv_file} not found.")
        return

    df = pd.read_csv(csv_file)
    if df.empty:
        return
        
    df['date'] = pd.to_datetime(df['date'])
    latest_date = df['date'].iloc[-1]
    date_str = latest_date.strftime('%Y-%m-%d')

    # 3. Smart Historical Calculator (With CAGR & Momentum tracking)
    def get_historical_metric(col, is_rate=False):
        if col not in df.columns:
            return f"{col}: N/A"
        valid_df = df[['date', col]].dropna()
        if valid_df.empty:
            return f"{col}: N/A"
            
        curr_val = valid_df[col].iloc[-1]
        
        def get_val_at(months_back):
            target_date = latest_date - relativedelta(months=months_back)
            past_df = valid_df[valid_df['date'] <= target_date]
            if not past_df.empty:
                return past_df[col].iloc[-1]
            return None

        val_1m = get_val_at(1)
        val_1q = get_val_at(3)
        val_1y = get_val_at(12)
        val_2y = get_val_at(24)
        
        def calc_change(past_val, months_back):
            if past_val is None or past_val == 0: return "N/A"
            if is_rate:
                bps = (curr_val - past_val) * 100
                if months_back == 24:
                    return f"{'+' if bps > 0 else ''}{bps:.0f} bps total ({'+' if bps/2 > 0 else ''}{bps/2:.0f} bps annualized)"
                return f"{'+' if bps > 0 else ''}{bps:.0f} bps"
            else:
                pct = ((curr_val - past_val) / past_val) * 100
                if months_back == 24:
                    cagr = (((curr_val / past_val) ** 0.5) - 1) * 100
                    return f"{'+' if cagr > 0 else ''}{cagr:.2f}% CAGR"
                return f"{'+' if pct > 0 else ''}{pct:.2f}%"

        return f"Current: {curr_val:.2f} | MoM: {calc_change(val_1m, 1)} | QoQ: {calc_change(val_1q, 3)} | YoY: {calc_change(val_1y, 12)} | 2-Year: {calc_change(val_2y, 24)}"

    # 4. Generate Pre-Calculated Growth Metrics
    macro_trends = f"""
    --- GROWTH & RATE TRAJECTORIES (MoM, QoQ, YoY, 2-Year CAGR) ---
    
    YIELDS & RATES (Changes in Basis Points):
    3M Yield: {get_historical_metric('3M', is_rate=True)}
    2Y Yield: {get_historical_metric('2Y', is_rate=True)}
    10Y Yield: {get_historical_metric('10Y', is_rate=True)}
    30Y Yield: {get_historical_metric('30Y', is_rate=True)}
    Fed Funds Rate: {get_historical_metric('FEDFUNDS', is_rate=True)}
    
    INFLATION EXPECTATIONS (Changes in Basis Points):
    1-Year Expected Inflation (EXPINF1YR): {get_historical_metric('EXPINF1YR', is_rate=True)}
    2-Year Expected Inflation (EXPINF2YR): {get_historical_metric('EXPINF2YR', is_rate=True)}
    3-Year Expected Inflation (EXPINF3YR): {get_historical_metric('EXPINF3YR', is_rate=True)}
    5-Year Expected Inflation (EXPINF5YR): {get_historical_metric('EXPINF5YR', is_rate=True)}
    10-Year Expected Inflation (EXPINF10YR): {get_historical_metric('EXPINF10YR', is_rate=True)}
    
    MACRO ECONOMY (Changes in Percentages):
    GDP (Trillions): {get_historical_metric('GDP')}
    Federal Debt (Trillions): {get_historical_metric('GFDEBTN')}
    CPI Inflation Index (Actual): {get_historical_metric('CPIAUCSL')}
    PPI Inflation Index (Actual): {get_historical_metric('PPIACO')}
    US Dollar Index (DXY): {get_historical_metric('DXY')}
    
    LABOR, WAGES, & HOUSING (Changes in Percentages):
    Unemployment Rate: {get_historical_metric('UNRATE', is_rate=True)}
    Nonfarm Payrolls: {get_historical_metric('PAYEMS')}
    Average Hourly Earnings (Wages): {get_historical_metric('AHE')}
    Housing Supply (Months): {get_historical_metric('HOSINV')}
    
    LIQUIDITY (Changes in Percentages):
    M2 Money Supply: {get_historical_metric('M2SL')}
    Fed Balance Sheet (WALCL): {get_historical_metric('WALCL')}
    """

    two_years_ago = latest_date - relativedelta(years=2)
    df_last_2_years = df[df['date'] >= two_years_ago]
    raw_2y_data_str = df_last_2_years.to_string(index=False)

    # 5. The Highly Constrained Prompt
    prompt = f"""
    You are a top-tier macro strategist writing for an institutional client. I have pre-calculated the exact growth trajectories (MoM, QoQ, YoY, 2-Year CAGR) for the US economy, bond yields, forward inflation expectations, and the labor market. I am also providing the raw 2-year timeline.
    
    DATA TRAJECTORIES:
    {macro_trends}

    RAW 2-YEAR HISTORICAL DATA:
    {raw_2y_data_str}

    Your mandate is to provide a complete, vivid, and highly authentic 360° analysis.

    STRICT RULES FOR YOUR OUTPUT:
    1. TONE & LUCIDITY: Your language must be lucid, direct, and accessible. Write like a seasoned Wall Street strategist—crisp and insightful, but easy to read. Do not use overly flowery prose or dramatic metaphors. Never explain economic jargon.
    2. ADVANCED DATA WEAVING: Do not just quote raw numbers. You MUST use the provided CAGR (Compound Annual Growth Rate) or annualized basis points to describe the long-term trend, and juxtapose it directly against recent MoM or QoQ momentum to show if the trend is accelerating, stalling, or reversing. 
    3. THE INFLATION EXPECTATIONS NEXUS (CRITICAL): You MUST explicitly weave the forward inflation expectations (1Y through 10Y) into ALL 9 sections. Analyze the spread between *actual* CPI and *expected* inflation. How are changing expectations driving yield curve dynamics, wage growth negotiations, DXY strength, and asset class valuations?
    4. ASSET CLASS OUTLOOK & PREFERENCES (CRITICAL): For Equities, Bonds, Gold, Commodities, and FX, you MUST follow a two-part structure: 
       - First, provide a concise, Current scenarios and forward-looking forecast for the sector driven by liquidity, yield spreads, and inflation expectations. 
       - Second, explicitly list what to "PREFER" and what to "AVOID" with a crisp rationale tied to the data. While analysing always look yield curve, Yield Spread , Histocial Precedence. Dont Just look one single data points compare it with other available data points to find the. A perfect comperative analysis.
    5. THE HUMAN ANGLE: Explicitly compare Average Hourly Earnings (wage growth) against CPI (actual inflation) AND 1Y/2Y Inflation Expectations. Is Main Street's real purchasing power growing or shrinking? Are consumers bracing for higher prices? How is the current unemployment rate, combined with mortgage rates (implied by 10Y/30Y yields), impacting housing supply (HOSINV)?
    6. In Scenario Sections, discuss all three Base / Bull / Bear case with probability and reasoning according to past history. Must be SHORT and SPOT-on
    7. Actionable Strategy discuss:- Risky / Conservative / Balanced Investor strategy with reasoning and precise
    8. In macro economincs always take a look at 30Y - 2Y Spread (Global Liquidity Proxy) , 10Y - 2Y Spread (Federal Policy & Risk Sentiment) , 10Y - 3M Spread (Recession Inversion Warning), 30Y - 5Y Spread (Long-Term Bond Curve)
    
    Structure your response exactly as follows:
    1. MACROECONOMIC, INFLATION EXPECTATIONS & LIQUIDITY TRENDS
    2. YIELD OUTLOOK (Short/Medium/Long)
    3. EQUITIES
    4. BONDS
    5. GOLD & PRECIOUS METALS
    6. COMMODITIES
    7. CASH & FX
    8. PORTFOLIO MIX, SCENARIOS & ACTIONABLE STRATEGY
    9. THE HUMAN ANGLE (Wages, Real Earnings, & Consumer Expectations)
    """

    print(f"🔄 Requesting analysis from nvidia/nemotron-3-ultra-550b-a55b (Streaming) for {date_str}...")

    try:
        completion = client.chat.completions.create(
            model="nvidia/nemotron-3-ultra-550b-a55b",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0, 
            top_p=0.95,
            max_tokens=36384,
            extra_body={"chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 36384},
            stream=True
        )
        
        reasoning_content_full = ""
        analysis_content_full = ""

        print("\n--- Model Reasoning (Live) ---")

        for chunk in completion:
            if not chunk.choices:
                continue
            
            # Capture the Thinking/Reasoning layer
            reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
            if reasoning:
                reasoning_content_full += reasoning
                print(reasoning, end="", flush=True)
                
            # Capture the Final Analysis content
            content = chunk.choices[0].delta.content
            if content is not None:
                # Add a visual separator in the console when transitioning from thinking to answering
                if reasoning_content_full and not analysis_content_full:
                    print("\n------------------------------\n")
                    print("--- Final Analysis (Live) ---")
                
                analysis_content_full += content
                print(content, end="", flush=True)

        print("\n✅ Analysis generated successfully. Saving report...")

        # Build the final text report (excluding the raw reasoning text to keep the report clean, 
        # but you can add reasoning_content_full here if you want it saved to the file)
        report = f"============================================================\n"
        report += f"📅 YIELD CURVE DAILY REPORT (Nemotron-3-Ultra) - {date_str}\n"
        report += f"============================================================\n\n"
        report += f"📋 AI ANALYSIS:\n{analysis_content_full}\n"
        report += f"============================================================\n"
        report += f"✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | nvidia/nemotron-3-ultra-550b-a55b\n"

        report_dir = "reports"
        os.makedirs(report_dir, exist_ok=True)
        report_file = f"{report_dir}/nemotron_report_{date_str}.txt"
        
        with open(report_file, 'w') as f:
            f.write(report)
        print(f"📄 Nemotron report saved to: {report_file}")

    except Exception as e:
        print(f"\n⚠️ NVIDIA Nemotron API error: {e}")

if __name__ == "__main__":
    main()

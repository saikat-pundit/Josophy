import os
from datetime import datetime
from dotenv import load_dotenv
import requests
import pandas as pd

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def safe_val(df, col, rows_back):
    """Safely get historical values based on trading day offsets."""
    if df is not None and col in df.columns and len(df) > rows_back:
        val = df[col].iloc[-(rows_back + 1)]
        return f"{val:.2f}" if pd.notnull(val) else "N/A"
    return "N/A"

def call_gemini(yields, history_df):
    """Call Gemini with pre-calculated macro trends to save tokens and prevent math hallucinations."""
    if not GEMINI_API_KEY:
        return "⚠️ No API key. Please set GEMINI_API_KEY."

    # 1. Process historical data context (Shrunk from 365 to 30 days to save tokens)
    if history_df is not None and len(history_df) > 0:
        history_df = history_df.sort_values("date")
        last_30 = history_df.tail(30)
        yield_history = last_30.to_string(index=False)
        latest_macro = history_df.iloc[-1]
    else:
        yield_history = "No historical data available."
        latest_macro = {}

    # Calculate all 4 spreads
    s30_2 = yields.get('30Y', 0) - yields.get('2Y', 0)
    s10_2 = yields.get('10Y', 0) - yields.get('2Y', 0)
    s10_3 = yields.get('10Y', 0) - yields.get('3M', 0)
    s30_5 = yields.get('30Y', 0) - yields.get('5Y', 0)
    
    dxy = yields.get('DXY')
    fedfunds = yields.get('FEDFUNDS')
    dxy_str = f"{dxy:.2f}" if pd.notnull(dxy) else "N/A"
    fed_str = f"{fedfunds:.2f}" if pd.notnull(fedfunds) else "N/A"

    # Helper to safely format macro data
    def fmt(val): 
        return f"{val:.3f}" if pd.notnull(val) else "N/A"

    # 2. Pre-calculate Python Math for the AI (1W=5 days, 1M=21 days, 1Y=252 days)
    macro_snapshot = f"""
    --- CURRENT DATA vs 1 MONTH AGO vs 1 YEAR AGO ---
    10Y Yield: {yields.get('10Y', 0):.2f}% (1M Ago: {safe_val(history_df, '10Y', 21)}%, 1Y Ago: {safe_val(history_df, '10Y', 252)}%)
    2Y Yield: {yields.get('2Y', 0):.2f}% (1M Ago: {safe_val(history_df, '2Y', 21)}%, 1Y Ago: {safe_val(history_df, '2Y', 252)}%)
    DXY (USD): {dxy_str} (1M Ago: {safe_val(history_df, 'DXY', 21)}, 1Y Ago: {safe_val(history_df, 'DXY', 252)})
    
    M2 Money Supply (Trillions): {fmt(latest_macro.get('M2SL'))} (1M Ago: {safe_val(history_df, 'M2SL', 21)}, 1Y Ago: {safe_val(history_df, 'M2SL', 252)})
    Fed Balance Sheet - WALCL (Trillions): {fmt(latest_macro.get('WALCL'))} (1M Ago: {safe_val(history_df, 'WALCL', 21)})
    Unemployment Rate: {fmt(latest_macro.get('UNRATE'))}% (1M Ago: {safe_val(history_df, 'UNRATE', 21)}%, 1Y Ago: {safe_val(history_df, 'UNRATE', 252)}%)
    CPI (AUCSL): {fmt(latest_macro.get('CPIAUCSL'))} (1Y Ago: {safe_val(history_df, 'CPIAUCSL', 252)})
    Nonfarm Payrolls (Millions): {fmt(latest_macro.get('PAYEMS'))}
    """
    
    prompt = f"""
You are a top-tier macro strategist. Analyze the US Treasury yield curve and the comprehensive macroeconomic data using the dataset below.

Last 30 days of raw yield data (for immediate momentum):
{yield_history}

Current Yields Snapshot: 
3M={yields.get('3M', 0):.2f}%, 2Y={yields.get('2Y', 0):.2f}%, 5Y={yields.get('5Y', 0):.2f}%, 10Y={yields.get('10Y', 0):.2f}%, 30Y={yields.get('30Y', 0):.2f}%
Spreads: 30Y-2Y={s30_2:.2f}%, 10Y-2Y={s10_2:.2f}%, 10Y-3M={s10_3:.2f}%, 30Y-5Y={s30_5:.2f}%
Fed Funds Rate: {fed_str}%

Pre-calculated Historical Trends:
{macro_snapshot}

Provide a complete, vivid, and highly authentic 360° analysis backed by the data provided.

For your analysis, you MUST:
- Analyze the Month-over-Month (MoM) and Year-over-Year (YoY) changes provided in the Pre-calculated Historical Trends section.
- Include the rationale/mechanism behind every prediction (why, not just what).
- Detail how global money flows and liquidity (M2/WALCL) are moving and impacting asset prices.
- Use varied, institutional vocabulary.

Do NOT include:
- Any explanation of economic jargon (no footnotes, no definitions).
- Duplicate display of yields or spreads.
- Internal instructions or chain-of-thought processing.

Structure your response exactly as follows:

1. MACROECONOMIC & LIQUIDITY TRENDS
   Detailed breakdown of MoM, and YoY changes in the provided macro data (CPI, M2, WALCL, Jobs). Analyze the current macro regime based on these shifts.

2. YIELD OUTLOOK (Short/Medium/Long)
   For each tenor and key spread, state the direction, historical trend, and rationale. Reference historical parallels.

3. EQUITIES
   Preferred/avoid sectors + regions with rationale. Mention valuation mechanics relative to the liquidity and employment data.

4. BONDS
   Preferred/avoid duration + credit quality. Explain why each is favored or avoided.

5. GOLD & PRECIOUS METALS
   Direction and rationale. Compare gold vs silver in the context of the current DXY, CPI, and Fed Balance Sheet trends.

6. COMMODITIES
   Energy, metals, agriculture – outlook and drivers.

7. CASH & FX
   USD direction and key FX pairs. Explain yield differentials and safe-haven flows.

8. PORTFOLIO MIX & ACTIONABLE STRATEGY
   a. Suggested allocation % (Equity, Bonds, Gold, Silver, Bitcoin, Cash)
   b. Preferred equity theme and why
   c. Avoid equity theme and why
   d. Preferred bond duration and why
   e. Avoid bond duration and why
   f. Gold vs Silver vs Bitcoin – which one and why
   g. Global money flow trend – where capital is moving

9. SCENARIO ANALYSIS
   Provide 2–3 plausible future scenarios (Base, Bull, Bear) for yields and markets over the next 12 months.
   For each scenario, explicitly state:
   - The specific future outlook
   - The underlying rationale and macro triggers
   - The precise probability of this outcome occurring

Keep the analysis exhaustive, highly analytical, and forward-looking. Maximize output quality.
"""
    headers = {"Content-Type": "application/json"}
    
    models_to_try = [
    "gemini-1.5-pro",         # 1st Choice: Stable flagship model (Best Analysis)
    "gemini-1.5-pro-latest",  # 2nd Choice: Fallback to the bleeding-edge Pro model
    "gemini-1.5-flash",        # 3rd Choice: Fast/Stable fallback if Pro hits rate limits
    "gemini-2.5-flash"
]
    
    for model in models_to_try:
        print(f"🔄 Trying model: {model}...")
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": 8192,
                "temperature": 0.7,
                "topP": 0.95
            }
        }
        
        try:
            response = requests.post(f"{api_url}?key={GEMINI_API_KEY}", headers=headers, json=payload, timeout=90)
            
            if response.status_code == 200:
                result = response.json()
                if "candidates" in result and len(result["candidates"]) > 0:
                    if "content" in result["candidates"][0] and "parts" in result["candidates"][0]["content"]:
                        text = result["candidates"][0]["content"]["parts"][0]["text"]
                        if text and len(text.strip()) > 0:
                            print(f"✅ Success with model: {model}")
                            return text
                        else:
                            print(f"⚠️ Model {model} returned empty text")
                    else:
                        print(f"⚠️ Model {model} returned invalid structure")
                else:
                    print(f"⚠️ Model {model} returned no candidates")
            else:
                print(f"⚠️ Model {model} failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"⚠️ Model {model} error: {e}")
    
    return "⚠️ All Gemini models failed to generate analysis. Please check API key or try again later."


def generate_daily_report(yields, regime, confidence, explanation, history_df):
    """Generate full report with AI analysis."""
    analysis = call_gemini(yields, history_df)

    s30_2 = yields.get('30Y', 0) - yields.get('2Y', 0)
    s10_2 = yields.get('10Y', 0) - yields.get('2Y', 0)
    s10_3 = yields.get('10Y', 0) - yields.get('3M', 0)
    s30_5 = yields.get('30Y', 0) - yields.get('5Y', 0)

    return f"""
============================================================
📅 YIELD CURVE DAILY REPORT - {yields['date']}
============================================================

📊 YIELD DATA:
  3M: {yields.get('3M', 0):.2f}%   2Y: {yields.get('2Y', 0):.2f}%   5Y: {yields.get('5Y', 0):.2f}%
  10Y: {yields.get('10Y', 0):.2f}%   30Y: {yields.get('30Y', 0):.2f}%

📈 SPREADS:
  30Y-2Y (Liquidity): {s30_2:.2f}%
  10Y-2Y (Risk):      {s10_2:.2f}%
  10Y-3M (Recession): {s10_3:.2f}%
  30Y-5Y (Long-Term): {s30_5:.2f}%

🔍 REGIME: {regime} (Confidence: {confidence:.2f})
  {explanation}

📋 AI ANALYSIS:
{analysis}
============================================================
✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Gemini
"""

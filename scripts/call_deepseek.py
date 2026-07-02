import os
from datetime import datetime
from dotenv import load_dotenv
import requests
import pandas as pd

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def call_gemini(yields, history_df):
    """Call Gemini with last 365 days and return AI analysis only."""
    if not GEMINI_API_KEY:
        return "⚠️ No API key. Please set GEMINI_API_KEY."

    # Last 365 days as context
    if history_df is not None and len(history_df) > 0:
        history_df = history_df.sort_values("date")
        last_365 = history_df.tail(365)
        yield_history = last_365.to_string(index=False)
    else:
        yield_history = "No historical data available."

    # Calculate all 4 spreads
    s30_2 = yields.get('30Y', 0) - yields.get('2Y', 0)
    s10_2 = yields.get('10Y', 0) - yields.get('2Y', 0)
    s10_3 = yields.get('10Y', 0) - yields.get('3M', 0)
    s30_5 = yields.get('30Y', 0) - yields.get('5Y', 0)

    prompt = f"""
You are a macro strategist. Analyze the US Treasury yield curve using the data below.

Last 365 days of yields:
{yield_history}

Current yields: 3M={yields['3M']:.2f}%, 2Y={yields['2Y']:.2f}%, 5Y={yields['5Y']:.2f}%, 10Y={yields['10Y']:.2f}%, 30Y={yields['30Y']:.2f}%
Spreads: 30Y-2Y={s30_2:.2f}%, 10Y-2Y={s10_2:.2f}%, 10Y-3M={s10_3:.2f}%, 30Y-5Y={s30_5:.2f}%

Provide a complete 360° analysis. For each prediction, include:
- The rationale/mechanism behind it (why, not just what)
- How global money flows are likely to move
- Use varied vocabulary—avoid repeating phrases like "this suggests" or "this indicates"

Do NOT include:
- Any explanation of economic jargon (no footnotes, no definitions)
- Duplicate display of yields or spreads

Structure your response exactly as follows:

1. YIELD OUTLOOK (Short/Medium/Long)
   For each tenor, state direction and rationale. Reference historical parallels where useful.

2. EQUITIES
   Preferred/avoid sectors + regions with rationale. Mention valuation mechanics.

3. BONDS
   Preferred/avoid duration + credit quality. Explain why each is favored or avoided.

4. GOLD & PRECIOUS METALS
   Direction and rationale. Compare gold vs silver.

5. COMMODITIES
   Energy, metals, agriculture – outlook and drivers.

6. CASH & FX
   USD direction and key FX pairs. Explain yield differentials and safe-haven flows.

7. PORTFOLIO MIX & ACTIONABLE STRATEGY
   a. Suggested allocation % (Equity, Bonds, Gold, Silver, Bitcoin, Cash)
   b. Preferred equity theme and why
   c. Avoid equity theme and why
   d. Preferred bond duration and why
   e. Avoid bond duration and why
   f. Gold vs Silver vs Bitcoin – which one and why
   g. Global money flow trend – where capital is moving

8. SCENARIO ANALYSIS
   Provide 2–3 plausible future scenarios (Base, Bull, Bear) for yields and markets over the next 12 months. For each, assign a probability and explain the triggers and implications.

Keep the analysis concise yet exhaustive. Prioritize forward-looking reasoning over repetition.
"""
    headers = {"Content-Type": "application/json"}
    
    models_to_try = ["gemini-2.5-pro", "gemini-3.5-flash", "gemini-2.5-flash"]
    
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
            response = requests.post(f"{api_url}?key={GEMINI_API_KEY}", headers=headers, json=payload, timeout=60)
            
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
  3M: {yields['3M']:.2f}%   2Y: {yields['2Y']:.2f}%   5Y: {yields['5Y']:.2f}%
  10Y: {yields['10Y']:.2f}%   30Y: {yields['30Y']:.2f}%

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

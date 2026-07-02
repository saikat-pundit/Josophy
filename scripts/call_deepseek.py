import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
import pandas as pd

load_dotenv()

# Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

def call_gemini(prompt, history_df):
    """Call Gemini API with last 365 days of yield data."""
    
    if not GEMINI_API_KEY:
        print("⚠️ GEMINI_API_KEY not found. Using fallback.")
        return generate_fallback_response(prompt)
    
    # Get last 365 days of data
    if history_df is not None and len(history_df) > 0:
        # Sort by date and get last 365 days
        history_df = history_df.sort_values("date")
        last_365 = history_df.tail(365)
        
        # Format as CSV-like string for context
        yield_history = last_365.to_string(index=False)
    else:
        yield_history = "No historical data available."
    
    # Build the full prompt with yield history
    full_prompt = f"""
You are a macro strategist analyzing the US Treasury yield curve.

Here is the yield history for the last 365 days:

{yield_history}

Based on this historical data, provide:

1. SHORT-TERM OUTLOOK (next 1-3 months): 
   - Direction of yields (up/down/flat)
   - Key risks to watch

2. MEDIUM-TERM OUTLOOK (3-12 months):
   - Expected regime shifts
   - Major macro drivers

3. LONG-TERM OUTLOOK (1-3 years):
   - Structural trends
   - Secular themes

4. ASSET CLASS RECOMMENDATIONS:
   - Equities (sector/regional bias)
   - Bonds (duration/credit)
   - Gold/Precious Metals
   - Commodities (energy/metals/agriculture)
   - Cash/USD

5. ACTIONABLE STRATEGY:
   - Specific trades/positions
   - Risk management (stop-loss levels)
   - Entry/exit timing

Be concise but thorough. Use the yield curve playbook from your training.
"""
    
    # Call Gemini API
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": full_prompt}]
        }]
    }
    
    try:
        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            if "candidates" in result and len(result["candidates"]) > 0:
                return result["candidates"][0]["content"]["parts"][0]["text"]
            else:
                return "No analysis generated."
        else:
            print(f"⚠️ Gemini API error: {response.status_code} - {response.text}")
            return generate_fallback_response(prompt)
            
    except Exception as e:
        print(f"⚠️ Gemini API error: {e}")
        return generate_fallback_response(prompt)

def generate_fallback_response(prompt):
    """Generate a rule-based fallback response when API is unavailable."""
    
    # Extract regime from prompt
    lines = prompt.split('\n')
    regime = "NORMAL_UPWARD_SLOPING"
    for line in lines:
        if "CURRENT REGIME:" in line:
            regime = line.replace("CURRENT REGIME:", "").strip()
            break
    
    # Extract yields from prompt
    yields = {}
    for line in lines:
        if "10-Year:" in line:
            try:
                yields['10Y'] = float(line.split(':')[1].replace('%', '').strip())
            except:
                pass
        if "3-Month:" in line:
            try:
                yields['3M'] = float(line.split(':')[1].replace('%', '').strip())
            except:
                pass
    
    fallback_responses = {
        "NORMAL_UPWARD_SLOPING": f"""
**SHORT-TERM OUTLOOK (1-3 months):**
- Yields: Gradually rising on healthy growth expectations (10Y at {yields.get('10Y', 'N/A')}%, 3M at {yields.get('3M', 'N/A')}%)
- Risks: Inflation data surprises to the upside could accelerate Fed tightening

**MEDIUM-TERM OUTLOOK (3-12 months):**
- Regime: Likely transition to bear flattening as Fed continues rate hikes
- Drivers: Strong labor market, persistent core inflation, fiscal spending

**LONG-TERM OUTLOOK (1-3 years):**
- Structural: Higher neutral rate due to massive fiscal deficits and de-globalization
- Secular: 10Y yields likely to trend toward 5-6% over the cycle

**ASSET CLASS RECOMMENDATIONS:**
- Equities: Overweight cyclicals (industrials, financials), underweight growth/tech
- Bonds: Underweight long-duration (avoid rate risk), prefer T-bills and floating rate
- Gold: Neutral (opportunity cost remains high with positive real rates)
- Commodities: Neutral on industrial metals, watch energy for supply shocks
- Cash/USD: Neutral to overweight (yields attractive at {yields.get('3M', 'N/A')}% on 3M)

**ACTIONABLE STRATEGY:**
- Rotate from defensive to cyclical sectors
- Keep bond duration under 5 years
- Set stop-loss at 10% for growth names
- Maintain 10-15% cash allocation for dip buying
""",
        # ... add other regimes as needed ...
    }
    
    return fallback_responses.get(regime, "Analysis unavailable. Please check API connectivity.")

def generate_daily_report(yields, regime, confidence, explanation, history_df):
    """Generate complete daily report with Gemini or fallback."""
    
    # Call Gemini with last 365 days of data
    analysis = call_gemini("", history_df)  # Empty prompt since we build it inside call_gemini
    
    report = f"""
============================================================
📅 YIELD CURVE DAILY REPORT - {yields['date']}
============================================================

📊 YIELD DATA:
  3-Month:   {yields['3M']:.2f}%
  2-Year:    {yields['2Y']:.2f}%
  5-Year:    {yields['5Y']:.2f}%
  10-Year:   {yields['10Y']:.2f}%
  30-Year:   {yields['30Y']:.2f}%

📈 KEY SPREADS:
  10Y-3M:    {yields.get('10Y_3M_spread', yields['10Y'] - yields['3M']):.2f}%
  10Y-2Y:    {yields.get('10Y_2Y_spread', yields['10Y'] - yields['2Y']):.2f}%

🔍 CURRENT REGIME: {regime} (Confidence: {confidence:.2f})
  {explanation}

📋 ANALYSIS (Powered by Gemini):
{analysis}

============================================================
✅ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💡 Powered by Google Gemini
============================================================
"""
    return report

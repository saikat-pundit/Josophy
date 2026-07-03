import os
import requests
from datetime import datetime

# Hugging Face API settings
HF_API_URL = "https://api-inference.huggingface.co/models/microsoft/Phi-3.5-mini-instruct"
HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

def call_hf_cloud(yields, history_df):
    """Send yield data to Hugging Face cloud API and get analysis."""
    if not HF_TOKEN:
        return "⚠️ No Hugging Face token found. Please set HUGGINGFACE_TOKEN in secrets."

    # Calculate spreads
    s30_2 = yields.get('30Y', 0) - yields.get('2Y', 0)
    s10_2 = yields.get('10Y', 0) - yields.get('2Y', 0)
    s10_3 = yields.get('10Y', 0) - yields.get('3M', 0)
    s30_5 = yields.get('30Y', 0) - yields.get('5Y', 0)

    # Build prompt
    prompt = f"""
You are a macro strategist. Analyze the US Treasury yield curve using the data below.

Current yields: 3M={yields['3M']:.2f}%, 2Y={yields['2Y']:.2f}%, 5Y={yields['5Y']:.2f}%, 10Y={yields['10Y']:.2f}%, 30Y={yields['30Y']:.2f}%
Spreads: 30Y-2Y={s30_2:.2f}%, 10Y-2Y={s10_2:.2f}%, 10Y-3M={s10_3:.2f}%, 30Y-5Y={s30_5:.2f}%

Provide a concise 360° analysis covering:
1. Yield outlook (short/medium/long)
2. Equities – sectors and regions
3. Bonds – duration and credit
4. Gold & silver
5. Commodities (energy, metals)
6. Cash & FX
7. Portfolio mix (%) + preferred/avoid themes

Keep it concise. No jargon explanations. Focus on forward-looking reasoning.
"""

    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": prompt}

    try:
        print("🔄 Sending request to Hugging Face cloud...")
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                # Extract the generated text
                text = result[0].get("generated_text", "")
                # Remove the prompt from the response
                if text.startswith(prompt):
                    text = text[len(prompt):].strip()
                print("✅ Analysis received from Hugging Face cloud!")
                return text
            else:
                return f"⚠️ Unexpected response format: {result}"
        else:
            return f"⚠️ API error: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"⚠️ Request failed: {e}"

def generate_daily_report_hf(yields, regime, confidence, explanation, history_df):
    """Generate full report using Hugging Face cloud API."""
    analysis = call_hf_cloud(yields, history_df)

    s30_2 = yields.get('30Y', 0) - yields.get('2Y', 0)
    s10_2 = yields.get('10Y', 0) - yields.get('2Y', 0)
    s10_3 = yields.get('10Y', 0) - yields.get('3M', 0)
    s30_5 = yields.get('30Y', 0) - yields.get('5Y', 0)

    return f"""
============================================================
📅 HUGGING FACE CLOUD REPORT - {yields['date']}
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

📋 HUGGING FACE ANALYSIS:
{analysis}
============================================================
✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Hugging Face Cloud
"""

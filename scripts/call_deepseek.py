import os
import json
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()

# Choose your provider
PROVIDER = "huggingface"  # Options: "huggingface", "together", "openrouter", "deepseek"

# API keys
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
TOGETHER_KEY = os.getenv("TOGETHER_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

def call_llm(prompt, fallback=True):
    """Call LLM with chosen provider."""
    
    if PROVIDER == "huggingface" and HUGGINGFACE_TOKEN:
        return call_huggingface(prompt)
    elif PROVIDER == "together" and TOGETHER_KEY:
        return call_together_ai(prompt)
    elif PROVIDER == "openrouter" and OPENROUTER_KEY:
        return call_openrouter(prompt)
    elif PROVIDER == "deepseek" and DEEPSEEK_API_KEY:
        return call_deepseek_api(prompt)
    else:
        print("⚠️ No valid API key found. Using fallback.")
        return generate_fallback_response(prompt)

def call_huggingface(prompt):
    """Call Hugging Face free inference API."""
    # Try different models that work better with the free tier
    models = [
        "mistralai/Mistral-7B-Instruct-v0.2",
        "google/flan-t5-large",  # Smaller, faster
        "gpt2"  # Simple, always works
    ]
    
    for model in models:
        API_URL = f"https://api-inference.huggingface.co/models/{model}"
        headers = {"Authorization": f"Bearer {HUGGINGFACE_TOKEN}"}
        
        # Different formats for different models
        if "mistral" in model:
            formatted_prompt = f"<s>[INST] {prompt} [/INST]"
        elif "flan" in model:
            formatted_prompt = prompt
        elif "gpt2" in model:
            formatted_prompt = prompt
        
        payload = {
            "inputs": formatted_prompt,
            "parameters": {
                "max_length": 1000,
                "temperature": 0.7,
                "top_p": 0.95,
                "return_full_text": False
            }
        }
        
        try:
            response = requests.post(API_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                
                # Handle different response formats
                if isinstance(result, list) and len(result) > 0:
                    if "generated_text" in result[0]:
                        return result[0]["generated_text"]
                    else:
                        return str(result[0])
                elif isinstance(result, dict) and "generated_text" in result:
                    return result["generated_text"]
                else:
                    return str(result)
            else:
                print(f"⚠️ Model {model} returned {response.status_code}, trying next...")
                continue
        except Exception as e:
            print(f"⚠️ HuggingFace API error with {model}: {e}")
            continue
    
    # If all models fail, use fallback
    return generate_fallback_response(prompt)

def call_together_ai(prompt):
    """Call Together.ai free inference API."""
    API_URL = "https://api.together.xyz/v1/completions"
    headers = {
        "Authorization": f"Bearer {TOGETHER_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "mistralai/Mistral-7B-Instruct-v0.2",
        "prompt": prompt,
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        return response.json()["choices"][0]["text"]
    except Exception as e:
        print(f"⚠️ Together.ai API error: {e}")
        return generate_fallback_response(prompt)

def call_openrouter(prompt):
    """Call OpenRouter with free credits."""
    API_URL = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "mistralai/mistral-7b-instruct:free",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"⚠️ OpenRouter API error: {e}")
        return generate_fallback_response(prompt)

def call_deepseek_api(prompt):
    """Call DeepSeek API (requires credits)."""
    from openai import OpenAI
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"⚠️ DeepSeek API error: {e}")
        return generate_fallback_response(prompt)

def build_prompt(yields, regime, confidence, explanation, history_df):
    """Build the prompt for LLM with yield data and regime context."""
    
    # Get recent trend (last 30 days for context)
    if history_df is not None and len(history_df) >= 30:
        recent = history_df.tail(30)
        trend_10y = recent['10Y'].tolist()
        trend_3m = recent['3M'].tolist()
        trend_spread = recent['10Y_3M_spread'].tolist()
        
        # Calculate 30-day change
        change_10y = trend_10y[-1] - trend_10y[0]
        change_3m = trend_3m[-1] - trend_3m[0]
    else:
        trend_10y = []
        trend_3m = []
        trend_spread = []
        change_10y = 0
        change_3m = 0
    
    # Safely get spreads
    spread_10y_3m = yields.get('10Y_3M_spread', yields.get('10Y', 0) - yields.get('3M', 0))
    spread_10y_2y = yields.get('10Y_2Y_spread', yields.get('10Y', 0) - yields.get('2Y', 0))
    
    prompt = f"""
You are a macro strategist analyzing the US Treasury yield curve daily.

**TODAY'S DATA ({yields['date']}):**
- 3-Month: {yields['3M']:.2f}%
- 2-Year: {yields['2Y']:.2f}%
- 5-Year: {yields['5Y']:.2f}%
- 10-Year: {yields['10Y']:.2f}%
- 30-Year: {yields['30Y']:.2f}%
- 10Y-3M Spread: {spread_10y_3m:.2f}%
- 10Y-2Y Spread: {spread_10y_2y:.2f}%

**30-DAY CHANGE:**
- 10Y: {change_10y:.2f}%
- 3M: {change_3m:.2f}%

**CURRENT REGIME:** {regime} (Confidence: {confidence:.2f})
**EXPLANATION:** {explanation}

Based on the yield curve regime and macro principles, provide:

1. **SHORT-TERM OUTLOOK (next 1-3 months):** 
   - Direction of yields (up/down/flat)
   - Key risks to watch
   
2. **MEDIUM-TERM OUTLOOK (3-12 months):**
   - Expected regime shifts
   - Major macro drivers

3. **LONG-TERM OUTLOOK (1-3 years):**
   - Structural trends
   - Secular themes

4. **ASSET CLASS RECOMMENDATIONS:**
   - Equities (sector/regional bias)
   - Bonds (duration/credit)
   - Gold/Precious Metals
   - Commodities (energy/metals/agriculture)
   - Cash/USD

5. **ACTIONABLE STRATEGY:**
   - Specific trades/positions
   - Risk management (stop-loss levels)
   - Entry/exit timing

Be concise but thorough. Use the yield curve playbook from your training.
"""
    return prompt

def generate_fallback_response(prompt):
    """Generate a rule-based fallback response when API is unavailable."""
    
    # Extract regime from prompt
    lines = prompt.split('\n')
    regime = "NORMAL_UPWARD_SLOPING"
    for line in lines:
        if "CURRENT REGIME:" in line:
            regime = line.replace("CURRENT REGIME:", "").strip()
            break
    
    fallback_responses = {
        "NORMAL_UPWARD_SLOPING": """
**SHORT-TERM OUTLOOK (1-3 months):**
- Yields: Gradually rising on healthy growth expectations
- Risks: Inflation data surprises to the upside

**MEDIUM-TERM OUTLOOK (3-12 months):**
- Regime: Likely transition to bear flattening as Fed tightens
- Drivers: Strong labor market, persistent inflation

**LONG-TERM OUTLOOK (1-3 years):**
- Structural: Higher neutral rate due to fiscal spending
- Secular: De-globalization puts upward pressure on yields

**ASSET CLASS RECOMMENDATIONS:**
- Equities: Overweight cyclicals, industrials, growth
- Bonds: Underweight long-duration (avoid rate risk)
- Gold: Neutral
- Commodities: Neutral on industrial metals
- Cash/USD: Neutral

**ACTIONABLE STRATEGY:**
- Rotate from defensives to cyclicals
- Keep duration under 5 years
- Set stop-loss at 10% for growth names
""",
        "BEAR_FLATTENER": """
**SHORT-TERM OUTLOOK (1-3 months):**
- Yields: Short-end rising rapidly, long-end flat
- Risks: Fed overtightening causing liquidity crunch

**MEDIUM-TERM OUTLOOK (3-12 months):**
- Regime: Could invert if Fed continues hiking
- Drivers: Persistent inflation forces hawkish policy

**LONG-TERM OUTLOOK (1-3 years):**
- Structural: Risk of recession post-inversion
- Secular: Higher cost of capital impacts valuations

**ASSET CLASS RECOMMENDATIONS:**
- Equities: Underweight (especially tech/growth)
- Bonds: Underweight long-duration
- Gold: Neutral to underweight
- Commodities: Underweight
- Cash/USD: Overweight (capital preservation)

**ACTIONABLE STRATEGY:**
- Trim equity exposure by 20-30%
- Rotate to short-duration T-bills
- Stop-loss on speculative names: 5%
""",
        "INVERTED_CURVE": """
**SHORT-TERM OUTLOOK (1-3 months):**
- Yields: Short-term elevated, long-term falling
- Risks: Recession warnings intensifying

**MEDIUM-TERM OUTLOOK (3-12 months):**
- Regime: Expect bull steepener as Fed cuts rates
- Drivers: Economic slowdown forces monetary easing

**LONG-TERM OUTLOOK (1-3 years):**
- Structural: Recession followed by recovery
- Secular: Deflationary pressures post-recession

**ASSET CLASS RECOMMENDATIONS:**
- Equities: Underweight cyclicals, overweight defensives
- Bonds: Overweight long-duration (prepare for rally)
- Gold: Begin accumulating physical gold
- Commodities: Underweight
- Cash/USD: Build reserves

**ACTIONABLE STRATEGY:**
- Rotate to utilities, consumer staples
- Accumulate long bonds (10Y+)
- Build 15-20% cash position
""",
        "BULL_STEEPENER": """
**SHORT-TERM OUTLOOK (1-3 months):**
- Yields: Short-term collapsing, long-term sticky
- Risks: Equity market crash risk at peak

**MEDIUM-TERM OUTLOOK (3-12 months):**
- Regime: Transition to normal as recovery begins
- Drivers: Fed panic cuts, recession materializes

**LONG-TERM OUTLOOK (1-3 years):**
- Structural: Massive fiscal stimulus post-recession
- Secular: Inflation risks re-emerge

**ASSET CLASS RECOMMENDATIONS:**
- Equities: Highly defensive, exit cyclicals
- Bonds: Overweight long-duration (capital gains)
- Gold: Strong Buy (opportunity cost vanishes)
- Commodities: Neutral to underweight
- Cash/USD: Preserve dry powder

**ACTIONABLE STRATEGY:**
- Exit high-multiple growth stocks
- Buy long-term treasuries (10Y+)
- Maximize gold allocation (10-15% portfolio)
""",
        "BEAR_STEEPENER": """
**SHORT-TERM OUTLOOK (1-3 months):**
- Yields: Long-term surging
- Risks: Fiscal concerns, inflation expectations rising

**MEDIUM-TERM OUTLOOK (3-12 months):**
- Regime: Stabilizing as recovery gains traction
- Drivers: Fiscal spending, reflation trade

**LONG-TERM OUTLOOK (1-3 years):**
- Structural: Higher nominal growth environment
- Secular: Commodity super-cycle

**ASSET CLASS RECOMMENDATIONS:**
- Equities: Overweight value, financials, industrials
- Bonds: Short/underweight long-duration
- Gold: Tactical hedge (competes with yields)
- Commodities: Overweight (copper, energy)
- Cash/USD: Neutral

**ACTIONABLE STRATEGY:**
- Re-enter cyclicals aggressively
- Short long-duration bonds
- Allocate to copper and crude oil
""",
        "BULL_FLATTENER": """
**SHORT-TERM OUTLOOK (1-3 months):**
- Yields: Long-term falling rapidly
- Risks: Disinflation accelerating

**MEDIUM-TERM OUTLOOK (3-12 months):**
- Regime: Could invert if slowdown deepens
- Drivers: Flight to safety, cooling inflation

**LONG-TERM OUTLOOK (1-3 years):**
- Structural: Lower neutral rate environment
- Secular: Safe-haven demand for bonds

**ASSET CLASS RECOMMENDATIONS:**
- Equities: Neutral to bearish on cyclicals
- Bonds: Highly bullish on long-duration
- Gold: Neutral
- Commodities: Underweight
- Cash/USD: Neutral

**ACTIONABLE STRATEGY:**
- Buy long-term treasuries
- Trim industrial commodity exposure
- Maintain neutral equity positioning
"""
    }
    
    return fallback_responses.get(regime, "Unable to generate fallback response for this regime.")

def generate_daily_report(yields, regime, confidence, explanation, history_df):
    """Generate complete daily report with LLM or fallback."""
    
    prompt = build_prompt(yields, regime, confidence, explanation, history_df)
    analysis = call_llm(prompt)
    
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

📋 ANALYSIS:
{analysis}

============================================================
✅ Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💡 Powered by {PROVIDER.upper()}
============================================================
"""
    return report

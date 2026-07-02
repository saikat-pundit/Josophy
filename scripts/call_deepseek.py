def build_prompt(yields, regime, confidence, explanation, history_df):
    """Build the prompt for DeepSeek with yield data and regime context."""
    
    # Get recent trend (last 5 days)
    if history_df is not None and len(history_df) >= 5:
        recent = history_df.tail(5)
        trend_10y = recent['10Y'].tolist()
        trend_3m = recent['3M'].tolist()
        trend_spread = recent['10Y_3M_spread'].tolist()
    else:
        trend_10y = []
        trend_3m = []
        trend_spread = []
    
    # Safely get spreads with defaults
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

**CURRENT REGIME:** {regime} (Confidence: {confidence:.2f})
**EXPLANATION:** {explanation}

**RECENT TREND (last 5 days):**
- 10Y: {trend_10y}
- 3M: {trend_3m}
- Spread: {trend_spread}

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

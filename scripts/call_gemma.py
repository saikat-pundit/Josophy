import os
import pandas as pd
from datetime import datetime
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_NAME = "google/gemma-2-9b-it"
MODEL_CACHE = "/home/runner/.cache/huggingface"

def load_model():
    """Load Gemma 2 9B on CPU (slow but works)."""
    print("⏳ Loading Gemma 2 9B model (this may take 2–3 minutes)...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir=MODEL_CACHE)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        cache_dir=MODEL_CACHE,
        torch_dtype=torch.float32,
        device_map="cpu"
    )
    return tokenizer, model

def generate_analysis(yields, history_df):
    """Generate analysis using Gemma 2 9B."""
    tokenizer, model = load_model()

    # Build prompt (same structure as before, but shorter to save tokens)
    s30_2 = yields.get('30Y', 0) - yields.get('2Y', 0)
    s10_2 = yields.get('10Y', 0) - yields.get('2Y', 0)
    s10_3 = yields.get('10Y', 0) - yields.get('3M', 0)
    s30_5 = yields.get('30Y', 0) - yields.get('5Y', 0)

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

    inputs = tokenizer(prompt, return_tensors="pt")
    outputs = model.generate(
        inputs.input_ids,
        max_new_tokens=1024,
        temperature=0.7,
        do_sample=True,
        top_p=0.95
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    return response.replace(prompt, "").strip()

def generate_daily_report_gemma(yields, regime, confidence, explanation, history_df):
    """Generate full report using Gemma."""
    analysis = generate_analysis(yields, history_df)

    s30_2 = yields.get('30Y', 0) - yields.get('2Y', 0)
    s10_2 = yields.get('10Y', 0) - yields.get('2Y', 0)
    s10_3 = yields.get('10Y', 0) - yields.get('3M', 0)
    s30_5 = yields.get('30Y', 0) - yields.get('5Y', 0)

    return f"""
============================================================
📅 GEMMA 2 9B REPORT - {yields['date']}
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

📋 GEMMA ANALYSIS:
{analysis}
============================================================
✅ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Gemma 2 9B (CPU)
"""

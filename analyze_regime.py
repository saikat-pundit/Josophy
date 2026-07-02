import pandas as pd
import numpy as np
from datetime import datetime

def compute_spreads(df):
    """Calculate key yield spreads from historical data."""
    if df.empty:
        return df
    
    df = df.copy()
    df['10Y_3M_spread'] = df['10Y'] - df['3M']
    df['10Y_2Y_spread'] = df['10Y'] - df['2Y']
    df['2Y_3M_spread'] = df['2Y'] - df['3M']
    return df

def classify_regime(row, history_df=None):
    """
    Classify yield curve regime based on PDF definitions.
    Returns: (regime_name, confidence_score, explanation)
    """
    if row['10Y'] is None or row['3M'] is None:
        return "INSUFFICIENT_DATA", 0.0, "Missing yield data"
    
    spread_10y_3m = row['10Y_3M_spread']
    spread_10y_2y = row['10Y_2Y_spread']
    
    # Check for inversion (10Y-3M < 0)
    if spread_10y_3m < 0:
        # Check if inverted for > 1 month (approx 30 days)
        if history_df is not None and len(history_df) >= 30:
            recent = history_df.tail(30)
            if (recent['10Y_3M_spread'] < 0).sum() >= 20:  # at least 20 of last 30 days
                return (
                    "INVERTED_CURVE",
                    0.95,
                    "10Y-3M spread negative for >20 of last 30 days. Acute recession warning."
                )
        return (
            "INVERTED_CURVE",
            0.80,
            "10Y-3M spread negative. Recession warning, but need >1 month confirmation."
        )
    
    # Bull Steepener: Short yields collapse, long yields sticky
    # Detected by: short-term yields falling rapidly, spread widening
    if history_df is not None and len(history_df) >= 5:
        recent = history_df.tail(5)
        if len(recent) >= 5:
            short_change = recent['3M'].iloc[-1] - recent['3M'].iloc[0]
            long_change = recent['10Y'].iloc[-1] - recent['10Y'].iloc[0]
            if short_change < -0.5 and abs(short_change) > abs(long_change):
                return (
                    "BULL_STEEPENER",
                    0.85,
                    "Short-term yields collapsing faster than long-term. Monetary panic & rate cuts."
                )
    
    # Bear Steepener: Long yields surge, short yields flat/slower
    if history_df is not None and len(history_df) >= 5:
        recent = history_df.tail(5)
        if len(recent) >= 5:
            short_change = recent['3M'].iloc[-1] - recent['3M'].iloc[0]
            long_change = recent['10Y'].iloc[-1] - recent['10Y'].iloc[0]
            if long_change > 0.5 and long_change > short_change:
                return (
                    "BEAR_STEEPENER",
                    0.80,
                    "Long-term yields surging faster than short-term. Fiscal expansion & re-inflation."
                )
    
    # Bull Flattener: Long yields fall faster than short yields
    if history_df is not None and len(history_df) >= 5:
        recent = history_df.tail(5)
        if len(recent) >= 5:
            short_change = recent['3M'].iloc[-1] - recent['3M'].iloc[0]
            long_change = recent['10Y'].iloc[-1] - recent['10Y'].iloc[0]
            if long_change < -0.3 and long_change < short_change:
                return (
                    "BULL_FLATTENER",
                    0.75,
                    "Long-term yields falling faster than short-term. Disinflation & flight to safety."
                )
    
    # Bear Flattener: Short yields rise faster than long yields
    if history_df is not None and len(history_df) >= 5:
        recent = history_df.tail(5)
        if len(recent) >= 5:
            short_change = recent['3M'].iloc[-1] - recent['3M'].iloc[0]
            long_change = recent['10Y'].iloc[-1] - recent['10Y'].iloc[0]
            if short_change > 0.3 and short_change > long_change:
                return (
                    "BEAR_FLATTENER",
                    0.70,
                    "Short-term yields rising faster than long-term. Hawkish monetary squeeze."
                )
    
    # Normal Upward-Sloping (default)
    if spread_10y_3m > 1.0:
        return (
            "NORMAL_UPWARD_SLOPING",
            0.90,
            "Positive steep curve. Healthy expansion, wide NIM, steady credit creation."
        )
    else:
        return (
            "NORMAL_UPWARD_SLOPING",
            0.60,
            "Positive but flat curve. Moderate expansion, watch for directional change."
        )

def get_asset_recommendations(regime):
    """Return asset recommendations based on PDF playbook."""
    recommendations = {
        "NORMAL_UPWARD_SLOPING": {
            "equities": "Overweight cyclicals, industrials, growth equities",
            "bonds": "Underweight long-duration bonds",
            "gold": "Neutral",
            "cash": "Neutral",
            "commodities": "Neutral"
        },
        "BEAR_FLATTENER": {
            "equities": "Underweight equities, especially speculative/high-valuation",
            "bonds": "Underweight long-duration bonds",
            "gold": "Neutral to underweight",
            "cash": "Overweight USD/cash",
            "commodities": "Underweight"
        },
        "INVERTED_CURVE": {
            "equities": "Underweight cyclicals, overweight defensives (staples, utilities)",
            "bonds": "Overweight long-duration bonds (accumulate)",
            "gold": "Begin accumulating physical gold",
            "cash": "Build cash reserves",
            "commodities": "Underweight"
        },
        "BULL_STEEPENER": {
            "equities": "Highly defensive. Exit cyclicals. Crash risk peak.",
            "bonds": "Overweight long-duration bonds (massive capital gains)",
            "gold": "Strong Buy (opportunity cost vanishes)",
            "cash": "Preserve dry powder",
            "commodities": "Neutral to underweight"
        },
        "BEAR_STEEPENER": {
            "equities": "Overweight value equities, financials, industrials",
            "bonds": "Short/underweight long-duration bonds",
            "gold": "Tactical inflation hedge (but faces competition)",
            "cash": "Neutral",
            "commodities": "Overweight (copper, energy, metals)"
        },
        "BULL_FLATTENER": {
            "equities": "Neutral to bearish on cyclicals",
            "bonds": "Highly bullish on long-duration bonds",
            "gold": "Neutral",
            "cash": "Neutral",
            "commodities": "Underweight"
        }
    }
    return recommendations.get(regime, {})

import pandas as pd
import numpy as np

def compute_spreads(df):
    """Calculate key yield spreads from historical data."""
    if df.empty:
        return df
    
    df = df.copy()
    df['10Y_3M_spread'] = df['10Y'] - df['3M']
    df['10Y_2Y_spread'] = df['10Y'] - df['2Y']
    df['2Y_3M_spread'] = df['2Y'] - df['3M']
    return df

def _get_latest_valid(history_df, col):
    """Helper to get the most recent non-null value for monthly macro data."""
    if history_df is not None and col in history_df.columns:
        valid_data = history_df[col].dropna()
        if not valid_data.empty:
            return valid_data.iloc[-1]
    return None

def _get_trend(history_df, col, lookback_months=6):
    """Calculate the trend (change) over the last N months."""
    if history_df is not None and col in history_df.columns:
        valid_data = history_df[col].dropna()
        if len(valid_data) >= lookback_months:
            return valid_data.iloc[-1] - valid_data.iloc[-lookback_months]
    return 0.0

def classify_regime(row, history_df=None):
    """
    Classify yield curve regime based on spreads + macro confirmation.
    Returns: (regime_name, confidence_score, explanation)
    """
    if pd.isna(row.get('10Y')) or pd.isna(row.get('3M')):
        return "INSUFFICIENT_DATA", 0.0, "Missing yield data"
    
    spread_10y_3m = row['10Y_3M_spread']
    
    # Get latest macro conditions for confirmation signals
    unrate_latest = _get_latest_valid(history_df, 'UNRATE') or 0.0
    unrate_trend = _get_trend(history_df, 'UNRATE', lookback_months=6) # 6-month change
    m2_trend = _get_trend(history_df, 'M2SL', lookback_months=6) # 6-month liquidity change
    cpi_latest = _get_latest_valid(history_df, 'CPIAUCSL') or 0.0
    cpi_trend = _get_trend(history_df, 'CPIAUCSL', lookback_months=12) # YoY inflation proxy
    
    macro_context = ""
    confidence_modifier = 0.0

    # Check for inversion (10Y-3M < 0)
    if spread_10y_3m < 0:
        if history_df is not None and len(history_df) >= 30:
            recent = history_df.tail(30)
            if (recent['10Y_3M_spread'] < 0).sum() >= 20:
                if unrate_trend > 0.3:
                    macro_context = f" Confirmed by rising unemployment (+{unrate_trend:.1f}% in 6M)."
                    confidence_modifier = 0.04
                return (
                    "INVERTED_CURVE",
                    min(0.95 + confidence_modifier, 0.99),
                    "10Y-3M spread negative for >20 of last 30 days. Acute recession warning." + macro_context
                )
        return (
            "INVERTED_CURVE",
            0.80,
            "10Y-3M spread negative. Recession warning, but need >1 month confirmation."
        )
    
    # Bull Steepener: Short yields collapse, long yields sticky
    if history_df is not None and len(history_df) >= 5:
        recent = history_df.tail(5)
        if len(recent) >= 5:
            short_change = recent['3M'].iloc[-1] - recent['3M'].iloc[0]
            long_change = recent['10Y'].iloc[-1] - recent['10Y'].iloc[0]
            
            if short_change < -0.5 and abs(short_change) > abs(long_change):
                if unrate_latest >= 4.5 or unrate_trend > 0.5:
                    macro_context = " High/rising unemployment confirms Fed panic cuts."
                    confidence_modifier = 0.10
                return (
                    "BULL_STEEPENER",
                    min(0.85 + confidence_modifier, 0.95),
                    "Short-term yields collapsing. Monetary easing phase." + macro_context
                )
    
    # Bear Steepener: Long yields surge, short yields flat/slower
    if history_df is not None and len(history_df) >= 5:
        recent = history_df.tail(5)
        if len(recent) >= 5:
            short_change = recent['3M'].iloc[-1] - recent['3M'].iloc[0]
            long_change = recent['10Y'].iloc[-1] - recent['10Y'].iloc[0]
            
            if long_change > 0.5 and long_change > short_change:
                if cpi_trend > 0:
                    macro_context = " Confirmed by sticky/rising inflation data."
                elif m2_trend > 0:
                    macro_context = " Driven by expanding liquidity/fiscal deficit."
                return (
                    "BEAR_STEEPENER",
                    0.80 + (0.05 if macro_context else 0.0),
                    "Long-term yields surging faster than short-term. Fiscal expansion or inflation fears." + macro_context
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
                if cpi_trend > 0:
                    macro_context = " Fed tightening into sticky inflation."
                    confidence_modifier = 0.10
                return (
                    "BEAR_FLATTENER",
                    min(0.70 + confidence_modifier, 0.85),
                    "Short-term yields rising faster than long-term. Hawkish monetary squeeze." + macro_context
                )
    
    # Normal Upward-Sloping (default)
    if spread_10y_3m > 1.0:
        if m2_trend > 0 and unrate_trend <= 0:
            macro_context = " Supported by expanding liquidity and stable employment."
        return (
            "NORMAL_UPWARD_SLOPING",
            0.90,
            "Positive steep curve. Healthy expansion, wide NIM, steady credit creation." + macro_context
        )
    else:
        return (
            "NORMAL_UPWARD_SLOPING",
            0.60,
            "Positive but flat curve. Moderate expansion, watch for directional change."
        )

def get_asset_recommendations(regime):
    """Return asset recommendations based on playbook, updated for macro awareness."""
    recommendations = {
        "NORMAL_UPWARD_SLOPING": {
            "equities": "Overweight cyclicals, industrials, growth equities",
            "bonds": "Underweight long-duration bonds",
            "gold": "Neutral",
            "cash": "Neutral",
            "commodities": "Neutral"
        },
        "BEAR_FLATTENER": {
            "equities": "Underweight equities, especially speculative/high-valuation (Liquidity drain)",
            "bonds": "Underweight long-duration bonds",
            "gold": "Neutral to underweight",
            "cash": "Overweight USD/cash",
            "commodities": "Underweight"
        },
        "INVERTED_CURVE": {
            "equities": "Underweight cyclicals, overweight defensives (staples, utilities, healthcare)",
            "bonds": "Overweight long-duration bonds (accumulate)",
            "gold": "Begin accumulating physical gold",
            "cash": "Build cash reserves",
            "commodities": "Underweight"
        },
        "BULL_STEEPENER": {
            "equities": "Highly defensive. Exit cyclicals. Crash risk peak as unemployment rises.",
            "bonds": "Overweight long-duration bonds (massive capital gains expected)",
            "gold": "Strong Buy (opportunity cost vanishes as Fed cuts)",
            "cash": "Preserve dry powder",
            "commodities": "Neutral to underweight"
        },
        "BEAR_STEEPENER": {
            "equities": "Overweight value equities, financials, industrials",
            "bonds": "Short/underweight long-duration bonds (Term premium rising)",
            "gold": "Tactical inflation hedge (but faces competition from high yields)",
            "cash": "Neutral",
            "commodities": "Overweight (copper, energy, metals)"
        },
        "BULL_FLATTENER": {
            "equities": "Neutral to bearish on cyclicals (Growth slowing)",
            "bonds": "Highly bullish on long-duration bonds",
            "gold": "Neutral",
            "cash": "Neutral",
            "commodities": "Underweight"
        }
    }
    return recommendations.get(regime, {})

import os
import pandas as pd
import numpy as np

# Ensure execution directories exist
os.makedirs("reports", exist_ok=True)

def process_market_data(file_path="data/FO_Position.csv"):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Source data file not found at: {file_path}")
        
    # Load and clean dataset
    df = pd.read_csv(file_path)
    
    # Standardize Column Names (strip whitespace)
    df.columns = df.columns.str.strip()
    
    # Parse Dates (Format: DDMMYYYY)
    df['DATE'] = pd.to_datetime(df['DATE'].astype(str).str.zfill(8), format='%d%m%Y')
    df = df.sort_values(by=['DATE', 'Client Type']).reset_index(drop=True)
    
    # Fill NaN values in Cash Market columns with 0
    df['CASH MARKET BUY'] = pd.to_numeric(df['CASH MARKET BUY'], errors='coerce').fillna(0)
    df['CASH MARKET SELL'] = pd.to_numeric(df['CASH MARKET SELL'], errors='coerce').fillna(0)
    
    # --- 1. Core Mathematical Metrics (As per specified logic) ---
    df['Net_Index_Future'] = df['Future Index Long'] - df['Future Index Short']
    df['Net_Index_Call'] = df['Option Index Call Long'] - df['Option Index Call Short']
    df['Net_Index_Put'] = df['Option Index Put Long'] - df['Option Index Put Short']
    df['Net_Index_Option'] = df['Net_Index_Call'] - df['Net_Index_Put']
    
    df['Net_Stock_Call'] = df['Option Stock Call Long'] - df['Option Stock Call Short']
    df['Net_Stock_Put'] = df['Option Stock Put Long'] - df['Option Stock Put Short']
    df['Net_Stock_Option'] = df['Net_Stock_Call'] - df['Net_Stock_Put']
    df['Net_Stock_Future'] = df['Future Stock Long'] - df['Future Stock Short']
    
    df['Net_Cash_Market'] = df['CASH MARKET BUY'] - df['CASH MARKET SELL']
    
    # --- 2. 7-Day Moving Averages & Momentum (Calculated per Participant Category) ---
    metrics_to_average = [
        'Net_Index_Future', 'Net_Index_Option', 'Net_Stock_Future', 
        'Net_Stock_Option', 'Net_Cash_Market', 'Future Index Long', 'Future Index Short'
    ]
    
    for metric in metrics_to_average:
        # 7DMA of the final net position
        df[f'{metric}_7DMA'] = df.groupby('Client Type')[metric].transform(
            lambda x: x.rolling(window=7, min_periods=1).mean()
        )
        
        # Everyday position change (Daily Delta)
        df[f'{metric}_Change'] = df.groupby('Client Type')[metric].diff().fillna(0)
        
        # 7DMA of the day-over-day changes
        df[f'{metric}_Change_7DMA'] = df.groupby('Client Type')[f'{metric}_Change'].transform(
            lambda x: x.rolling(window=7, min_periods=1).mean()
        )

    # --- 3. Forward Price Performance Engine (Determining Winners & Losers) ---
    # Extract historical underlying index price tracking per day
    price_df = df[['DATE', 'NIFTY50', 'BANK NIFTY']].drop_duplicates().sort_values('DATE').reset_index(drop=True)
    # Calculate 3-day and 5-day forward market returns to evaluate positional success
    price_df['Nifty_5D_Forward_Return'] = price_df['NIFTY50'].shift(-5) - price_df['NIFTY50']
    price_df['BankNifty_5D_Forward_Return'] = price_df['BANK NIFTY'].shift(-5) - price_df['BANK NIFTY']
    
    df = pd.merge(df, price_df[['DATE', 'Nifty_5D_Forward_Return', 'BankNifty_5D_Forward_Return']], on='DATE', how='left')
    
    # Calculate Directional Accuracy Score (%)
    # Success condition: Position bias matches forward actual index direction
    df['Index_Future_Win'] = np.where(
        ((df['Net_Index_Future'] > 0) & (df['Nifty_5D_Forward_Return'] > 0)) | 
        ((df['Net_Index_Future'] < 0) & (df['Nifty_5D_Forward_Return'] < 0)), 1, 0
    )
    df['Index_Option_Win'] = np.where(
        ((df['Net_Index_Option'] > 0) & (df['Nifty_5D_Forward_Return'] > 0)) | 
        ((df['Net_Index_Option'] < 0) & (df['Nifty_5D_Forward_Return'] < 0)), 1, 0
    )

    # Aggregate performance statistics across the 6+ months dataset
    performance_summary = {}
    unique_clients = df['Client Type'].unique()
    
    for client in unique_clients:
        client_data = df[df['Client Type'] == client].dropna(subset=['Nifty_5D_Forward_Return'])
        if len(client_data) > 0:
            future_win_rate = (client_data['Index_Future_Win'].sum() / len(client_data)) * 100
            option_win_rate = (client_data['Index_Option_Win'].sum() / len(client_data)) * 100
            
            # Find current positional trends
            latest_row = df[df['Client Type'] == client].iloc[-1]
            
            performance_summary[client] = {
                "future_win_rate_5d": round(future_win_rate, 2),
                "option_win_rate_5d": round(option_win_rate, 2),
                "current_index_future_bias": "BULLISH" if latest_row['Net_Index_Future'] > 0 else "BEARISH",
                "current_index_option_bias": "BULLISH" if latest_row['Net_Index_Option'] > 0 else "BEARISH",
                "current_cash_net": round(latest_row['Net_Cash_Market'], 2)
            }

    # --- 4. Structure the Deep AI Prompt Injection Layout ---
    latest_date = df['DATE'].max().strftime('%Y-%m-%d')
    latest_snapshot = df[df['DATE'] == df['DATE'].max()]
    
    prompt_content = f"""SYSTEM INSTRUCTION & DATA PAYLOAD: INDIAN STOCK MARKET DERIVATIVES ANALYSIS
Target Context Date: {latest_date}
Data Horizon Analyzed: >6 Months (From Dec 2025 onwards)

======================================================================
PART 1: PERFORMANCE TRACKING MATRIX (HISTORICAL WIN/LOSS ALIGNMENT)
======================================================================
Below is the statistical historical 5-Day forward accuracy mapping for each market participant type across the analyzed dataset:

"""
    for client, stats in performance_summary.items():
        prompt_content += f"""Participant Profile: {client}
  - Index Futures Historical Win Rate (5-Day Outlook): {stats['future_win_rate_5d']}%
  - Index Options Historical Win Rate (Weekly Outlook): {stats['option_win_rate_5d']}%
  - Current Active Futures Stance: {stats['current_index_future_bias']}
  - Current Active Options Stance: {stats['current_index_option_bias']}
  - Latest Day Net Cash Activity: INR {stats['current_cash_net']} Crs
----------------------------------------------------------------------
"""

    prompt_content += """
======================================================================
PART 2: LATEST DAILY POSITION SNAPSHOT vs 7-DAY MOVING AVERAGES (7DMA)
======================================================================
Detailed transactional snapshot for the most recent trading session, containing direct divergence and momentum metrics against 7DMAs:

"""
    for idx, row in latest_snapshot.iterrows():
        prompt_content += f"""[Client Type: {row['Client Type']}]
- Market Context: NIFTY50: {row['NIFTY50']} | BANK NIFTY: {row['BANK NIFTY']} | India VIX: {row['VIX']} | USDINR: {row['USDINR']}
- Derivatives Breakdown:
  * Net Index Futures: {row['Net_Index_Future']} (7DMA: {round(row['Net_Index_Future_7DMA'], 2)}) | Daily Change: {row['Net_Index_Future_Change']} (7DMA Change: {round(row['Net_Index_Future_Change_7DMA'], 2)})
  * Net Index Options: {row['Net_Index_Option']} (7DMA: {round(row['Net_Index_Option_7DMA'], 2)}) | Daily Change: {row['Net_Index_Option_Change']} (7DMA Change: {round(row['Net_Index_Option_Change_7DMA'], 2)})
  * Net Stock Futures: {row['Net_Stock_Future']} (7DMA: {round(row['Net_Stock_Future_7DMA'], 2)})
  * Net Stock Options: {row['Net_Stock_Option']} (7DMA: {round(row['Net_Stock_Option_7DMA'], 2)})
  * Net Cash Segment: {row['Net_Cash_Market']} (7DMA: {round(row['Net_Cash_Market_7DMA'], 2)})
- Core Divergence Flags:
  * Future Index Long Position is {'ABOVE' if row['Future Index Long'] > row['Future Index Long_7DMA'] else 'BELOW'} its 7DMA.
  * Future Index Short Position is {'ABOVE' if row['Future Index Short'] > row['Future Index Short_7DMA'] else 'BELOW'} its 7DMA.
----------------------------------------------------------------------
"""

    prompt_content += """
======================================================================
PART 3: ANALYTICAL EXPECTATIONS
======================================================================
Based on the data matrix above, provide a comprehensive market commentary detailing:
1. Smart Money Divergence: Cross-reference high win-rate players (typically FII/Pro) with retail positions to find liquidity pools and potential traps.
2. Macro Risk Confluence: Synthesize the current behavior of the USDINR and VIX relative to structural FII Cash and Futures positions.
3. Market Outlook: Provide an explicit weekly outlook (via options alignment) and a monthly outlook (via futures build-up).
"""

    # Export report prompt payload to text file
    output_path = "reports/processed_data_prompt.txt"
    with open(output_path, "w") as f:
        f.write(prompt_content)
        
    print(f"Success: Processed dataset and generated AI prompt payload at: {output_path}")

if __name__ == "__main__":
    process_market_data()

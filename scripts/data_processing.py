# data_processing.py
import os
import sys
import subprocess
import pandas as pd
import numpy as np
from datetime import datetime

os.makedirs("reports", exist_ok=True)

def run_fo_update():
    """Run FO_Position.py and return True if data was appended"""
    if not os.path.exists('scripts/FO_Position.py'):
        print("⚠️ FO_Position.py not found")
        return False
    result = subprocess.run(['python', 'scripts/FO_Position.py'],
                            capture_output=True, text=True)
    if "Appended" in result.stdout:
        print("✅ New data appended to FO_Position.csv")
        return True
    elif "No new data" in result.stdout:
        print("ℹ️ No new data available")
    return False

def process_market_data(file_path="data/FO_Position.csv"):
    # --- 1. Ensure data exists ---
    if not os.path.exists(file_path):
        print("⚠️ Source data missing. Running FO_Position.py first...")
        run_fo_update()
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source data file still not found at: {file_path}")

    # --- 2. Read data and get latest date (DDMMYYYY) ---
    df = pd.read_csv(file_path)
    df['DATE'] = pd.to_datetime(df['DATE'].astype(str).str.zfill(8), format='%d%m%Y')
    latest_date = df['DATE'].max().strftime('%d%m%Y')          # DDMMYYYY
    ai_report_path = f"reports/ai_market_analysis_{latest_date}.txt"

    # --- 3. CHECK IF AI REPORT ALREADY EXISTS ---
    if os.path.exists(ai_report_path):
        print(f"✅ AI report already exists for date {latest_date}. Skipping.")
        return  # <--- STOP HERE

    # --- 4. Update data if we are behind today ---
    today = datetime.now().strftime('%d%m%Y')
    if df['DATE'].max().strftime('%d%m%Y') < today:
        print(f"🔄 Updating data up to {today}...")
        run_fo_update()
        df = pd.read_csv(file_path)
        df['DATE'] = pd.to_datetime(df['DATE'].astype(str).str.zfill(8), format='%d%m%Y')
        latest_date = df['DATE'].max().strftime('%d%m%Y')
        ai_report_path = f"reports/ai_market_analysis_{latest_date}.txt"
        
        # Check again after update
        if os.path.exists(ai_report_path):
            print(f"✅ AI report already exists for updated date {latest_date}. Skipping.")
            return

    # --- 5. Data processing (calculations) ---
    df.columns = df.columns.str.strip()
    df = df.sort_values(by=['DATE', 'Client Type']).reset_index(drop=True)

    df['CASH MARKET BUY'] = pd.to_numeric(df['CASH MARKET BUY'], errors='coerce').fillna(0)
    df['CASH MARKET SELL'] = pd.to_numeric(df['CASH MARKET SELL'], errors='coerce').fillna(0)

    df['Net_Index_Future'] = df['Future Index Long'] - df['Future Index Short']
    df['Net_Index_Call'] = df['Option Index Call Long'] - df['Option Index Call Short']
    df['Net_Index_Put'] = df['Option Index Put Long'] - df['Option Index Put Short']
    df['Net_Index_Option'] = df['Net_Index_Call'] - df['Net_Index_Put']
    df['Net_Stock_Call'] = df['Option Stock Call Long'] - df['Option Stock Call Short']
    df['Net_Stock_Put'] = df['Option Stock Put Long'] - df['Option Stock Put Short']
    df['Net_Stock_Option'] = df['Net_Stock_Call'] - df['Net_Stock_Put']
    df['Net_Stock_Future'] = df['Future Stock Long'] - df['Future Stock Short']
    df['Net_Cash_Market'] = df['CASH MARKET BUY'] - df['CASH MARKET SELL']

    metrics = [
        'Net_Index_Future', 'Net_Index_Option', 'Net_Stock_Future',
        'Net_Stock_Option', 'Net_Cash_Market',
        'Future Index Long', 'Future Index Short'
    ]
    for m in metrics:
        df[f'{m}_7DMA'] = df.groupby('Client Type')[m].transform(
            lambda x: x.rolling(7, min_periods=1).mean()
        )
        df[f'{m}_Change'] = df.groupby('Client Type')[m].diff().fillna(0)
        df[f'{m}_Change_7DMA'] = df.groupby('Client Type')[f'{m}_Change'].transform(
            lambda x: x.rolling(7, min_periods=1).mean()
        )

    price_df = df[['DATE', 'NIFTY50', 'BANK NIFTY']].drop_duplicates().sort_values('DATE')
    price_df['Nifty_5D_Forward_Return'] = price_df['NIFTY50'].shift(-5) - price_df['NIFTY50']
    price_df['BankNifty_5D_Forward_Return'] = price_df['BANK NIFTY'].shift(-5) - price_df['BANK NIFTY']
    df = pd.merge(df, price_df[['DATE', 'Nifty_5D_Forward_Return', 'BankNifty_5D_Forward_Return']],
                  on='DATE', how='left')

    df['Index_Future_Win'] = np.where(
        ((df['Net_Index_Future'] > 0) & (df['Nifty_5D_Forward_Return'] > 0)) |
        ((df['Net_Index_Future'] < 0) & (df['Nifty_5D_Forward_Return'] < 0)),
        1, 0
    )
    df['Index_Option_Win'] = np.where(
        ((df['Net_Index_Option'] > 0) & (df['Nifty_5D_Forward_Return'] > 0)) |
        ((df['Net_Index_Option'] < 0) & (df['Nifty_5D_Forward_Return'] < 0)),
        1, 0
    )

    # --- 6. Performance summary ---
    summary = {}
    for client in df['Client Type'].unique():
        cd = df[df['Client Type'] == client].dropna(subset=['Nifty_5D_Forward_Return'])
        if len(cd) > 0:
            latest = df[df['Client Type'] == client].iloc[-1]
            summary[client] = {
                'future_win_rate_5d': round((cd['Index_Future_Win'].sum() / len(cd)) * 100, 2),
                'option_win_rate_5d': round((cd['Index_Option_Win'].sum() / len(cd)) * 100, 2),
                'current_index_future_bias': 'BULLISH' if latest['Net_Index_Future'] > 0 else 'BEARISH',
                'current_index_option_bias': 'BULLISH' if latest['Net_Index_Option'] > 0 else 'BEARISH',
                'current_cash_net': round(latest['Net_Cash_Market'], 2)
            }

    latest_date_str = df['DATE'].max().strftime('%Y-%m-%d')
    latest_snapshot = df[df['DATE'] == df['DATE'].max()]

    # --- 7. Build AI prompt ---
    prompt = f"""SYSTEM INSTRUCTION & DATA PAYLOAD: INDIAN STOCK MARKET DERIVATIVES ANALYSIS
Target Context Date: {latest_date_str}
Data Horizon Analyzed: >6 Months (From Dec 2025 onwards)

======================================================================
PART 1: PERFORMANCE TRACKING MATRIX (HISTORICAL WIN/LOSS ALIGNMENT)
======================================================================
Below is the statistical historical 5-Day forward accuracy mapping for each market participant type across the analyzed dataset:

"""
    for client, stats in summary.items():
        prompt += f"""Participant Profile: {client}
  - Index Futures Historical Win Rate (5-Day Outlook): {stats['future_win_rate_5d']}%
  - Index Options Historical Win Rate (Weekly Outlook): {stats['option_win_rate_5d']}%
  - Current Active Futures Stance: {stats['current_index_future_bias']}
  - Current Active Options Stance: {stats['current_index_option_bias']}
  - Latest Day Net Cash Activity: INR {stats['current_cash_net']} Crs
----------------------------------------------------------------------
"""
    prompt += """
======================================================================
PART 2: LATEST DAILY POSITION SNAPSHOT vs 7-DAY MOVING AVERAGES (7DMA)
======================================================================
Detailed transactional snapshot for the most recent trading session, containing direct divergence and momentum metrics against 7DMAs:

"""
    for _, row in latest_snapshot.iterrows():
        prompt += f"""[Client Type: {row['Client Type']}]
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
    prompt += """
======================================================================
PART 3: ANALYTICAL EXPECTATIONS
======================================================================
Based on the data matrix above, provide a comprehensive market commentary detailing:
1. Smart Money Divergence: Cross-reference high win-rate players (typically FII/Pro) with retail positions to find liquidity pools and potential traps.
2. Macro Risk Confluence: Synthesize the current behavior of the USDINR and VIX relative to structural FII Cash and Futures positions.
3. Market Outlook: Provide an explicit weekly outlook (via options alignment) and a monthly outlook (via futures build-up).
"""

    # --- 8. Save temp prompt and call feed_to_ai.py ---
    temp_prompt_path = f"reports/temp_prompt_{latest_date}.txt"
    with open(temp_prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt)

    print(f"🔄 Sending to AI for analysis...")
    subprocess.run(['python', 'feed_to_ai.py', temp_prompt_path, latest_date],
                   capture_output=True)

    if os.path.exists(temp_prompt_path):
        os.remove(temp_prompt_path)

    print(f"✅ AI analysis saved to: {ai_report_path}")

if __name__ == "__main__":
    process_market_data()

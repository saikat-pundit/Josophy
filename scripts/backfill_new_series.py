import pandas as pd
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")
BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# New series that need backfilling
NEW_SERIES_MAP = {
    "GDP": "GDP",
    "GFDEBTN": "GFDEBTN",
    "CPIAUCSL": "CPIAUCSL",
    "PPIACO": "PPIACO",
    "AHE": "CES0500000003",
    "UNRATE": "UNRATE",
    "PAYEMS": "PAYEMS",
    "JTSJOL": "JTSJOL",
    "HOSINV": "HOSINVUSM495N"
}

def fetch_bulk_series(series_id, start_date, end_date):
    """Fetch all observations for a series in one API call."""
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": start_date,
        "observation_end": end_date,
        "limit": 5000
    }
    response = requests.get(BASE_URL, params=params)
    if response.status_code != 200:
        return {}
    data = response.json()
    results = {}
    for obs in data.get("observations", []):
        date = obs["date"]
        val = obs["value"]
        if val != ".":
            results[date] = float(val)
    return results

def backfill_new_series():
    """Backfill all new series from 2019-01-01 to today."""
    filename = "data/yield_history.csv"
    if not os.path.exists(filename):
        print("❌ CSV file not found. Run fetch_yields.py first.")
        return
    
    df_existing = pd.read_csv(filename)
    print(f"📅 Existing CSV has {len(df_existing)} rows.")
    
    # Fetch all new series from 2019-01-01 to today
    start_date = "2019-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📅 Fetching new series from {start_date} to {end_date}...")
    
    all_series_data = {}
    for tenure, series_id in NEW_SERIES_MAP.items():
        print(f"  Fetching {tenure} ({series_id})...")
        all_series_data[tenure] = fetch_bulk_series(series_id, start_date, end_date)
    
    # Build a DataFrame from the fetched data
    all_dates = set()
    for data in all_series_data.values():
        all_dates.update(data.keys())
    all_dates = sorted(all_dates)
    
    new_rows = []
    for date in all_dates:
        row = {"date": date}
        for tenure in NEW_SERIES_MAP.keys():
            row[tenure] = all_series_data[tenure].get(date)
        new_rows.append(row)
    
    df_new = pd.DataFrame(new_rows)
    
    # Convert to billions where needed
    for col in ["GDP", "GFDEBTN"]:
        if col in df_new.columns:
            df_new[col] = df_new[col] / 1000.0
    
    # Convert PAYEMS and JTSJOL from thousands to millions
    for col in ["PAYEMS", "JTSJOL"]:
        if col in df_new.columns:
            df_new[col] = df_new[col] / 1000.0
    
    # ✅ FIX: Use concat instead of merge to avoid duplicate columns
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    df_combined = df_combined.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    df_combined.to_csv(filename, index=False)
    
    print(f"✅ Backfilled {len(df_new)} rows with new series data.")
    print(f"📊 Total rows: {len(df_combined)}")
    print(df_combined.tail())

if __name__ == "__main__":
    backfill_new_series()

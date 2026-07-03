import pandas as pd
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")
BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# US Treasury constant maturity yields
SERIES_MAP = {
    "3M": "DGS3MO",
    "2Y": "DGS2",
    "5Y": "DGS5",
    "10Y": "DGS10",
    "30Y": "DGS30",
    "DXY": "DXY",
    "FEDFUNDS": "FEDFUNDS"
}

def fetch_yield(series_id, date=None):
    """Fetch yield for a specific series and date."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": date,
        "observation_end": date
    }
    
    response = requests.get(BASE_URL, params=params)
    
    if response.status_code != 200:
        return None
    
    data = response.json()
    
    if data.get("observations") and len(data["observations"]) > 0:
        value = data["observations"][0]["value"]
        return float(value) if value != "." else None
    return None

def get_last_recorded_date(filename="data/yield_history.csv"):
    """Get the last date recorded in the CSV file."""
    if not os.path.exists(filename):
        return None
    
    df = pd.read_csv(filename)
    if df.empty:
        return None
    
    # Get the latest date
    last_date = df["date"].max()
    return last_date

def fetch_missing_dates():
    """Fetch only the missing dates since last recorded date."""
    filename = "data/yield_history.csv"
    last_date = get_last_recorded_date(filename)
    
    if last_date is None:
        print("📅 No historical data found. Fetching all data from 2019...")
        # Run backfill for first time
        try:
            from backfill_history import build_historical_csv
            return build_historical_csv()
        except ImportError:
            print("⚠️ backfill_history.py not found. Please run backfill first.")
            return None
    
    print(f"📅 Last recorded date: {last_date}")
    
    # Start from the day after last recorded date
    start_date = (datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    if start_date > end_date:
        print("✅ Already up to date!")
        return pd.read_csv(filename)
    
    print(f"📅 Fetching new data from {start_date} to {end_date}")
    
    # Get all business days between start_date and end_date
    current_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date_dt = datetime.strptime(end_date, "%Y-%m-%d")
    
    new_data = []
    while current_date <= end_date_dt:
        date_str = current_date.strftime("%Y-%m-%d")
        # Skip weekends
        if current_date.weekday() < 5:  # Monday-Friday
            yields = fetch_all_yields_for_date(date_str)
            if yields and yields.get("10Y") is not None:
                new_data.append(yields)
                print(f"  ✅ Fetched {date_str}: 10Y={yields['10Y']:.2f}%")
            else:
                print(f"  ⚠️ No data for {date_str}")
        current_date += timedelta(days=1)
    
    if not new_data:
        print("✅ No new data available.")
        return pd.read_csv(filename)
    
    # Append new data to CSV
    df_new = pd.DataFrame(new_data)
    df_existing = pd.read_csv(filename)
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    
    # Sort by date and remove duplicates
    df_combined = df_combined.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    
    # ✅ FIX: Save the combined DataFrame back to CSV
    df_combined.to_csv(filename, index=False)
    
    print(f"✅ Added {len(new_data)} new rows. Total: {len(df_combined)} rows")
    return df_combined

def fetch_all_yields_for_date(date):
    """Fetch all benchmark yields for a specific date."""
    yields = {"date": date}
    for tenure, series_id in SERIES_MAP.items():
        val = fetch_yield(series_id, date)
        if val is not None:
            yields[tenure] = val
        else:
            yields[tenure] = None
    return yields

def save_to_csv(yields_dict, filename="data/yield_history.csv"):
    """Append daily yield data to CSV, avoiding duplicates."""
    date = yields_dict.get("date")
    row = {
        "date": date,
        "3M": yields_dict.get("3M"),
        "2Y": yields_dict.get("2Y"),
        "5Y": yields_dict.get("5Y"),
        "10Y": yields_dict.get("10Y"),
        "30Y": yields_dict.get("30Y"),
        "DXY": yields_dict.get("DXY"),
        "FEDFUNDS": yields_dict.get("FEDFUNDS")
    }
    
    df_new = pd.DataFrame([row])
    
    if os.path.exists(filename):
        df_existing = pd.read_csv(filename)
        # Check if date already exists
        if date in df_existing["date"].values:
            print(f"⚠️ Data for {date} already exists. Updating...")
            # Remove the existing row
            df_existing = df_existing[df_existing["date"] != date]
            # Append the new row
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.to_csv(filename, index=False)
            return df_combined
        else:
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.to_csv(filename, index=False)
            print(f"✅ Appended data for {date}")
            return df_combined
    else:
        # Ensure directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        df_new.to_csv(filename, index=False)
        print(f"✅ Created new CSV with data for {date}")
        return df_new

def load_history(filename="data/yield_history.csv"):
    """Load historical yield data from CSV."""
    if os.path.exists(filename):
        return pd.read_csv(filename)
    return pd.DataFrame()

# --- MAIN TEST ---
if __name__ == "__main__":
    # Fetch only missing data
    df = fetch_missing_dates()
    print(f"\n📊 Total rows: {len(df)}")
    print(df.tail())
# At the bottom of fetch_yields.py, add these exports:

__all__ = [
    'fetch_yield',
    'fetch_all_yields',
    'fetch_all_yields_for_date',
    'get_last_recorded_date',
    'fetch_missing_dates',
    'save_to_csv',
    'load_history'
]

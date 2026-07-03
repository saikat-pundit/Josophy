import pandas as pd
import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")
BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

# Complete series map with all new indicators
SERIES_MAP = {
    # Treasury yields
    "3M": "DGS3MO",
    "2Y": "DGS2",
    "5Y": "DGS5",
    "10Y": "DGS10",
    "30Y": "DGS30",
    # Macro indicators
    "DXY": "TWEXBGSMTH",
    "FEDFUNDS": "RIFSPFFNB",
    "M2SL": "M2SL",
    "WALCL": "WALCL",
    # New additions
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

def get_last_recorded_date(filename="data/yield_history.csv"):
    """Get the last date recorded in the CSV file."""
    if not os.path.exists(filename):
        return None
    df = pd.read_csv(filename)
    if df.empty:
        return "2019-01-01"
    return df["date"].max()

def fetch_missing_dates():
    """Fetch all missing data in bulk."""
    filename = "data/yield_history.csv"
    
    # If CSV doesn't exist, create empty with headers
    if not os.path.exists(filename):
        df_empty = pd.DataFrame(columns=[
            "date", "3M", "2Y", "5Y", "10Y", "30Y", 
            "DXY", "FEDFUNDS", "M2SL", "WALCL",
            "GDP", "GFDEBTN", "CPIAUCSL", "PPIACO", 
            "AHE", "UNRATE", "PAYEMS", "JTSJOL", "HOSINV"
        ])
        df_empty.to_csv(filename, index=False)
        print("✅ Created empty CSV with headers.")
    
    df_existing = pd.read_csv(filename)
    if df_existing.empty:
        last_date = "2019-01-01"
        print("📅 CSV is empty. Starting from 2019-01-01...")
    else:
        last_date = df_existing["date"].max()
        print(f"📅 Last recorded date: {last_date}")
    
    start_date = (datetime.strptime(last_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    if start_date > end_date:
        print("✅ Already up to date!")
        return df_existing
    
    print(f"📅 Fetching bulk data from {start_date} to {end_date}...")
    
    # Fetch all series in bulk
    all_series_data = {}
    for tenure, series_id in SERIES_MAP.items():
        print(f"  Fetching {tenure} ({series_id})...")
        all_series_data[tenure] = fetch_bulk_series(series_id, start_date, end_date)
    
    # Build new rows from merged data
    all_dates = set()
    for data in all_series_data.values():
        all_dates.update(data.keys())
    all_dates = sorted(all_dates)
    
    new_rows = []
    for date in all_dates:
        row = {"date": date}
        for tenure in SERIES_MAP.keys():
            row[tenure] = all_series_data[tenure].get(date)
        new_rows.append(row)
    
    if not new_rows:
        print("✅ No new data available.")
        return df_existing
    
    df_new = pd.DataFrame(new_rows)
    
    # Convert to billions where needed
    for col in ["M2SL", "WALCL", "GDP", "GFDEBTN"]:
        if col in df_new.columns:
            df_new[col] = df_new[col] / 1000.0
    
    # Convert PAYEMS and JTSJOL from thousands to millions
    for col in ["PAYEMS", "JTSJOL"]:
        if col in df_new.columns:
            df_new[col] = df_new[col] / 1000.0
    
    # Merge with existing
    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    df_combined = df_combined.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    df_combined.to_csv(filename, index=False)
    
    print(f"✅ Added {len(new_rows)} new rows. Total: {len(df_combined)} rows")
    return df_combined

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
        "FEDFUNDS": yields_dict.get("FEDFUNDS"),
        "M2SL": yields_dict.get("M2SL"),
        "WALCL": yields_dict.get("WALCL"),
        "GDP": yields_dict.get("GDP"),
        "GFDEBTN": yields_dict.get("GFDEBTN"),
        "CPIAUCSL": yields_dict.get("CPIAUCSL"),
        "PPIACO": yields_dict.get("PPIACO"),
        "AHE": yields_dict.get("AHE"),
        "UNRATE": yields_dict.get("UNRATE"),
        "PAYEMS": yields_dict.get("PAYEMS"),
        "JTSJOL": yields_dict.get("JTSJOL"),
        "HOSINV": yields_dict.get("HOSINV")
    }
    df_new = pd.DataFrame([row])
    
    if os.path.exists(filename):
        df_existing = pd.read_csv(filename)
        if date in df_existing["date"].values:
            print(f"⚠️ Data for {date} already exists. Updating...")
            df_existing = df_existing[df_existing["date"] != date]
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.to_csv(filename, index=False)
            return df_combined
        else:
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            df_combined.to_csv(filename, index=False)
            print(f"✅ Appended data for {date}")
            return df_combined
    else:
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
    df = fetch_missing_dates()
    if df is not None:
        print(f"\n📊 Total rows: {len(df)}")
        print(df.tail())
    else:
        print("❌ Could not fetch data.")

__all__ = [
    'fetch_bulk_series',
    'get_last_recorded_date',
    'fetch_missing_dates',
    'save_to_csv',
    'load_history'
]

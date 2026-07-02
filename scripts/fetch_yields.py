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
    "30Y": "DGS30"
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

def get_most_recent_available_date():
    """Find the most recent date with available data."""
    # Check today, yesterday, and up to 7 days back
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        # Skip weekends (FRED only has weekday data)
        weekday = datetime.strptime(date, "%Y-%m-%d").weekday()
        if weekday >= 5:  # Saturday=5, Sunday=6
            continue
        
        # Try to fetch 10Y yield for this date
        val = fetch_yield("DGS10", date)
        if val is not None:
            return date
    
    # Fallback: use yesterday
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

def fetch_all_yields(date=None):
    """Fetch all benchmark yields for a given date."""
    if date is None:
        date = get_most_recent_available_date()
    
    print(f"📅 Fetching yields for: {date}")
    
    yields = {}
    for tenure, series_id in SERIES_MAP.items():
        val = fetch_yield(series_id, date)
        if val is not None:
            yields[tenure] = val
        else:
            yields[tenure] = None
            print(f"⚠️ No data for {tenure} on {date}")
    
    yields["date"] = date
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
        "30Y": yields_dict.get("30Y")
    }
    
    # If file doesn't exist, create it
    if not os.path.exists(filename):
        df_new = pd.DataFrame([row])
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        df_new.to_csv(filename, index=False)
        print(f"✅ Created new CSV with data for {date}")
        return df_new
    
    # Read existing data
    df_existing = pd.read_csv(filename)
    
    # Check if date already exists
    if date in df_existing["date"].values:
        print(f"⚠️ Data for {date} already exists. Updating...")
        # Find the index of the existing row
        idx = df_existing[df_existing["date"] == date].index[0]
        # Update the row using .loc with a list of values
        df_existing.loc[idx] = [row['date'], row['3M'], row['2Y'], row['5Y'], row['10Y'], row['30Y']]
        df_existing.to_csv(filename, index=False)
        return df_existing
    else:
        # Append new row
        df_combined = pd.concat([df_existing, pd.DataFrame([row])], ignore_index=True)
        df_combined.to_csv(filename, index=False)
        print(f"✅ Appended data for {date}")
        return df_combined

def load_history(filename="data/yield_history.csv"):
    """Load historical yield data from CSV."""
    if os.path.exists(filename):
        return pd.read_csv(filename)
    return pd.DataFrame()

# --- MAIN TEST ---
if __name__ == "__main__":
    # Get most recent available date
    date = get_most_recent_available_date()
    print(f"📅 Most recent available date: {date}")
    
    # Fetch all yields
    yields = fetch_all_yields(date)
    print(f"📊 Yields: {yields}")
    
    # Save to CSV
    df = save_to_csv(yields)
    print("\n📊 Current data shape:", df.shape)
    print(df.tail())

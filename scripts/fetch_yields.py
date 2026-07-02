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
    data = response.json()
    
    if data.get("observations") and len(data["observations"]) > 0:
        value = data["observations"][0]["value"]
        return float(value) if value != "." else None
    return None

def fetch_all_yields(date=None):
    """Fetch all benchmark yields for a given date."""
    yields = {}
    for tenure, series_id in SERIES_MAP.items():
        val = fetch_yield(series_id, date)
        if val is not None:
            yields[tenure] = val
    return yields

def get_last_business_day():
    """Get the most recent business day (weekday, not today if weekend)."""
    today = datetime.now()
    # If today is weekend, go back to Friday
    if today.weekday() == 5:  # Saturday
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    elif today.weekday() == 6:  # Sunday
        return (today - timedelta(days=2)).strftime("%Y-%m-%d")
    else:
        return today.strftime("%Y-%m-%d")

def save_to_csv(yields_dict, filename="data/yield_history.csv"):
    """Append daily yield data to CSV."""
    date = yields_dict.get("date", datetime.now().strftime("%Y-%m-%d"))
    row = {
        "date": date,
        "3M": yields_dict.get("3M"),
        "2Y": yields_dict.get("2Y"),
        "5Y": yields_dict.get("5Y"),
        "10Y": yields_dict.get("10Y"),
        "30Y": yields_dict.get("30Y")
    }
    
    df_new = pd.DataFrame([row])
    
    if os.path.exists(filename):
        df_existing = pd.read_csv(filename)
        # Check if date already exists, avoid duplicates
        if date in df_existing["date"].values:
            print(f"⚠️ Data for {date} already exists. Skipping append.")
            return df_existing
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_combined = df_new
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    df_combined.to_csv(filename, index=False)
    print(f"✅ Saved yield data for {date}")
    return df_combined

def load_history(filename="data/yield_history.csv"):
    """Load historical yield data from CSV."""
    if os.path.exists(filename):
        return pd.read_csv(filename)
    return pd.DataFrame()

# --- MAIN TEST ---
if __name__ == "__main__":
    # Get last business day
    last_biz = get_last_business_day()
    print(f"Fetching yields for: {last_biz}")
    
    # Fetch all yields
    yields = fetch_all_yields(last_biz)
    yields["date"] = last_biz
    print(f"Yields: {yields}")
    
    # Save to CSV
    df = save_to_csv(yields)
    print("\n📊 Current data shape:", df.shape)
    print(df.tail())

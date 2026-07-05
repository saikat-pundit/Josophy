import requests
import csv
from datetime import datetime, timedelta
import os
import sys
import time

def generate_dates(start_date_str, end_date_str):
    start = datetime.strptime(start_date_str, "%d%m%Y")
    end = datetime.strptime(end_date_str, "%d%m%Y")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%d%m%Y"))
        current += timedelta(days=1)
    return dates

def fetch_and_process(date_str):
    url = f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_vol_{date_str}.csv"
    try:
        # Add timeout and headers to avoid being blocked
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 404:
            print(f"{date_str}: no data (holiday/weekend)")
            return None
        response.raise_for_status()
        lines = response.text.strip().split('\n')
        if len(lines) < 3:
            print(f"{date_str}: no data (incomplete file)")
            return None
        # Skip first row (header with description)
        header_line = lines[1].strip()
        headers = [h.strip() for h in header_line.split(',')]
        # Add DATE column
        new_headers = ['DATE'] + headers
        
        rows = []
        for line in lines[2:]:
            if not line.strip():
                continue
            values = [v.strip() for v in line.split(',')]
            if len(values) != len(headers):
                continue
            # Skip if the row is TOTAL (last row)
            if values[0].upper() == 'TOTAL':
                continue
            # Add date to the beginning
            new_row = [date_str] + values
            rows.append(new_row)
        
        print(f"{date_str}: data fetched ✓")
        return new_headers, rows
    except requests.exceptions.Timeout:
        print(f"{date_str}: timeout - skipping")
        return None
    except requests.exceptions.ConnectionError:
        print(f"{date_str}: connection error - skipping")
        return None
    except Exception as e:
        print(f"{date_str}: error - {e}")
        return None

def main():
    start_date = "01122025"
    end_date = datetime.now().strftime("%d%m%Y")
    dates = generate_dates(start_date, end_date)
    
    all_rows = []
    headers = None
    
    for date in dates:
        result = fetch_and_process(date)
        if result:
            h, rows = result
            if headers is None:
                headers = h
            all_rows.extend(rows)
        # Small delay between requests to avoid rate limiting
        time.sleep(0.5)
    
    if not all_rows:
        print("No data collected")
        sys.exit(1)
    
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    # Write to CSV
    output_file = 'data/FO_Position.csv'
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(all_rows)
    
    print(f"Data saved to {output_file}")
    print(f"Total rows: {len(all_rows)}")

if __name__ == "__main__":
    main()

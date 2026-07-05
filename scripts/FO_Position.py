import requests
import csv
from datetime import datetime, timedelta
import os
import sys
import time
import json

def generate_dates(start_date_str, end_date_str):
    start = datetime.strptime(start_date_str, "%d%m%Y")
    end = datetime.strptime(end_date_str, "%d%m%Y")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%d%m%Y"))
        current += timedelta(days=1)
    return dates

def fetch_index_data(index_type, start_date, end_date):
    url = f"https://www.nseindia.com/api/historicalOR/indicesHistory?indexType={index_type}&from={start_date}&to={end_date}&csv=true"
    
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'identity',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Host': 'www.nseindia.com',
        'Referer': 'https://www.nseindia.com/get-quotes/equity?symbol=RELIANCE',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:136.0) Gecko/20100101 Firefox/136.0'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return {}
        
        try:
            data = response.json()
            index_data = {}
            for item in data.get('data', []):
                date_str = item.get('EOD_TIMESTAMP', '')
                if date_str:
                    try:
                        date_obj = datetime.strptime(date_str, '%d-%b-%Y')
                        date_key = date_obj.strftime('%d%m%Y')
                        index_data[date_key] = item.get('EOD_CLOSE_INDEX_VAL', 0)
                    except:
                        continue
            return index_data
        except json.JSONDecodeError:
            cleaned_text = response.text.replace('\x00', '')
            try:
                data = json.loads(cleaned_text)
                index_data = {}
                for item in data.get('data', []):
                    date_str = item.get('EOD_TIMESTAMP', '')
                    if date_str:
                        try:
                            date_obj = datetime.strptime(date_str, '%d-%b-%Y')
                            date_key = date_obj.strftime('%d%m%Y')
                            index_data[date_key] = item.get('EOD_CLOSE_INDEX_VAL', 0)
                        except:
                            continue
                return index_data
            except:
                return {}
    except Exception as e:
        print(f"Error fetching {index_type}: {e}")
        return {}

def fetch_and_process(date_str, nifty_data, banknifty_data):
    url = f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_vol_{date_str}.csv"
    try:
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
        # Remove last 2 columns from header
        headers = headers[:-2]  # <--- FIX: Strip last 2 columns
        # Add DATE, NIFTY50, BANK NIFTY columns
        new_headers = ['DATE', 'NIFTY50', 'BANK NIFTY'] + headers
        
        nifty_close = nifty_data.get(date_str, '')
        banknifty_close = banknifty_data.get(date_str, '')
        
        rows = []
        for line in lines[2:]:
            if not line.strip():
                continue
            values = [v.strip() for v in line.split(',')]
            if len(values) != len(headers) + 2:  # Original has 2 extra columns
                continue
            # Skip if the row is TOTAL (last row)
            if values[0].upper() == 'TOTAL':
                continue
            # Remove last 2 columns from data row
            values = values[:-2]  # <--- FIX: Strip last 2 columns
            # Add date and index values to the beginning
            new_row = [date_str, nifty_close, banknifty_close] + values
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
    
    # Convert dates for index API (DD-MM-YYYY format)
    start_date_api = datetime.strptime(start_date, "%d%m%Y").strftime("%d-%m-%Y")
    end_date_api = datetime.now().strftime("%d-%m-%Y")
    
    print("Fetching NIFTY50 data...")
    nifty_data = fetch_index_data('NIFTY%2050', start_date_api, end_date_api)
    print(f"NIFTY50 data fetched for {len(nifty_data)} days")
    
    print("Fetching BANK NIFTY data...")
    banknifty_data = fetch_index_data('NIFTY%20BANK', start_date_api, end_date_api)
    print(f"BANK NIFTY data fetched for {len(banknifty_data)} days")
    
    dates = generate_dates(start_date, end_date)
    
    all_rows = []
    headers = None
    
    for date in dates:
        result = fetch_and_process(date, nifty_data, banknifty_data)
        if result:
            h, rows = result
            if headers is None:
                headers = h
            all_rows.extend(rows)
        time.sleep(0.5)
    
    if not all_rows:
        print("No data collected")
        sys.exit(1)
    
    os.makedirs('data', exist_ok=True)
    
    output_file = 'data/FO_Position.csv'
    with open(output_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(all_rows)
    
    print(f"Data saved to {output_file}")
    print(f"Total rows: {len(all_rows)}")

if __name__ == "__main__":
    main()

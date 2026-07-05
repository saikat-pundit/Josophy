import requests
import json
from datetime import datetime

def fetch_usdinr_data(start_date, end_date):
    url = f"https://www.nseindia.com/api/historicalOR/rbi-reference-rate-stats?from={start_date}&to={end_date}&csv=true"
    
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
        print(f"Fetching USDINR from {start_date} to {end_date}...")
        response = requests.get(url, headers=headers, timeout=15)
        print(f"Status code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        if response.status_code != 200:
            print(f"Response: {response.text[:500]}")
            return {}
        
        try:
            data = response.json()
            usdinr_data = {}
            print(f"Data structure: {type(data)}")
            print(f"Data keys: {data.keys() if isinstance(data, dict) else 'not a dict'}")
            print(f"Data preview: {str(data)[:500]}")
            
            for item in data.get('data', []):
                date_str = item.get('Trade Date', '')
                if date_str:
                    try:
                        date_obj = datetime.strptime(date_str, '%d-%b-%Y')
                        date_key = date_obj.strftime('%d%m%Y')
                        usdinr_data[date_key] = item.get('1 USD ', 0)
                        print(f"Date: {date_key}, USDINR: {item.get('1 USD ', 0)}")
                    except Exception as e:
                        print(f"Date parsing error: {e}")
                        continue
            return usdinr_data
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            print(f"Response preview: {response.text[:200]}")
            return {}
    except Exception as e:
        print(f"Error: {e}")
        return {}

def main():
    start_date = "01-06-2026"
    end_date = "05-07-2026"
    
    print("=== Testing USDINR Data Fetch ===")
    usdinr_data = fetch_usdinr_data(start_date, end_date)
    
    print(f"\nTotal USDINR records: {len(usdinr_data)}")
    for date, value in usdinr_data.items():
        print(f"Date: {date}, USDINR: {value}")

if __name__ == "__main__":
    main()

# script/FO_Position.py
import requests, csv, os, sys, time, json
from datetime import datetime, timedelta

HEADERS = {
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

def get_dates(start, end):
    return [(datetime.strptime(start, "%d%m%Y") + timedelta(days=i)).strftime("%d%m%Y") 
            for i in range((datetime.strptime(end, "%d%m%Y") - datetime.strptime(start, "%d%m%Y")).days + 1)]

def fetch_api(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200: return {}
        return r.json()
    except: return {}

def parse_index(data):
    return {datetime.strptime(d['EOD_TIMESTAMP'], '%d-%b-%Y').strftime('%d%m%Y'): d['EOD_CLOSE_INDEX_VAL'] 
            for d in data.get('data', []) if d.get('EOD_TIMESTAMP')}

def parse_usdinr(text):
    if text.startswith('\ufeff'): text = text[1:]
    return {datetime.strptime(v[0], '%d-%b-%Y').strftime('%d%m%Y'): float(v[1]) 
            for v in [p.strip().strip('"') for p in l.split(',')] 
            for l in text.strip().split('\n')[1:] if l.strip() 
            if len(v := [p.strip().strip('"') for p in l.split(',')]) >= 2}

def parse_cash(data):
    return {datetime.strptime(d['date'], '%d-%b-%Y').strftime('%d%m%Y'): {d['category']: {'buy': d['buyValue'], 'sell': d['sellValue']}}
            for d in data if d.get('date') and d.get('category')}

def get_last_date():
    if not os.path.exists('data/FO_Position.csv'): return None
    with open('data/FO_Position.csv') as f:
        rows = list(csv.reader(f))
        return rows[-1][0] if len(rows) > 1 else None

def main():
    last = get_last_date()
    start = (datetime.strptime(last, "%d%m%Y") + timedelta(days=1)).strftime("%d%m%Y") if last else "01122025"
    end = datetime.now().strftime("%d%m%Y")
    
    if datetime.strptime(start, "%d%m%Y") > datetime.strptime(end, "%d%m%Y"):
        print("Already up to date."); sys.exit(0)
    
    api_start = datetime.strptime(start, "%d%m%Y").strftime("%d-%m-%Y")
    api_end = datetime.now().strftime("%d-%m-%Y")
    
    # Fetch all data
    nifty = parse_index(fetch_api(f"https://www.nseindia.com/api/historicalOR/indicesHistory?indexType=NIFTY%2050&from={api_start}&to={api_end}&csv=true"))
    bank = parse_index(fetch_api(f"https://www.nseindia.com/api/historicalOR/indicesHistory?indexType=NIFTY%20BANK&from={api_start}&to={api_end}&csv=true"))
    
    usdinr_resp = requests.get(f"https://www.nseindia.com/api/historicalOR/rbi-reference-rate-stats?from={api_start}&to={api_end}&csv=true", headers=HEADERS)
    usdinr = parse_usdinr(usdinr_resp.text) if usdinr_resp.status_code == 200 else {}
    
    vix = parse_index(fetch_api(f"https://www.nseindia.com/api/historicalOR/vixhistory?from={api_start}&to={api_end}&csv=true"))
    cash = parse_cash(fetch_api("https://www.nseindia.com/api/fiidiiTradeReact"))
    
    all_rows, headers = [], None
    
    for date in get_dates(start, end):
        url = f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_vol_{date}.csv"
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if r.status_code == 404: continue
            lines = r.text.strip().split('\n')
            if len(lines) < 3: continue
            
            h = [x.strip() for x in lines[1].split(',')][:-2]
            if headers is None: headers = ['DATE', 'NIFTY50', 'BANK NIFTY', 'USDINR', 'VIX'] + h + ['CASH MARKET BUY', 'CASH MARKET SELL']
            
            for line in lines[2:]:
                if not line.strip(): continue
                vals = [x.strip() for x in line.split(',')]
                if len(vals) != len(h) + 2 or vals[0].upper() == 'TOTAL': continue
                vals = vals[:-2]
                
                cb, cs = '', ''
                if date in cash:
                    if vals[0] == 'FII' and 'FII/FPI' in cash[date]:
                        cb, cs = cash[date]['FII/FPI']['buy'], cash[date]['FII/FPI']['sell']
                    elif vals[0] == 'DII' and 'DII' in cash[date]:
                        cb, cs = cash[date]['DII']['buy'], cash[date]['DII']['sell']
                
                all_rows.append([date, nifty.get(date, ''), bank.get(date, ''), usdinr.get(date, ''), 
                                vix.get(date, '')] + vals + [cb, cs])
            print(f"{date}: data fetched ✓")
        except: print(f"{date}: skipped"); continue
        time.sleep(0.5)
    
    if not all_rows: print("No new data"); sys.exit(0)
    
    os.makedirs('data', exist_ok=True)
    file_exists = os.path.exists('data/FO_Position.csv')
    with open('data/FO_Position.csv', 'a' if file_exists else 'w', newline='') as f:
        w = csv.writer(f)
        if not file_exists: w.writerow(headers)
        w.writerows(all_rows)
    
    print(f"Appended {len(all_rows)} rows to data/FO_Position.csv")

if __name__ == "__main__": main()

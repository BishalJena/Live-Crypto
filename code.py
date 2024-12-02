import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import sys
import os
import json
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_KEY = '5cb5d0bd-d35a-4d0b-8c7a-58dc7c1a598b'
SPREADSHEET_KEY = '1vXTteq2185As4JFhXtyL-m2q_x2lUg-FmiFTW2-6Nf0'
UPDATE_INTERVAL = 300

# Load credentials from the environment variable
CREDENTIALS = json.loads(os.getenv('CREDENTIALS'))

API_URL = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'

IST = timezone(timedelta(hours=5, minutes=30))

def fetch_live_data():
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': API_KEY,
    }
    params = {
        'start': '1',
        'limit': '50',
        'convert': 'USD'
    }
    try:
        response = requests.get(API_URL, headers=headers, params=params)
        data = response.json()
        if response.status_code != 200:
            raise Exception(data.get('status', {}).get('error_message', 'Unknown error'))
        return data['data']
    except Exception as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

def analyze_data(data):
    top_5 = sorted(data, key=lambda x: x['quote']['USD']['market_cap'], reverse=True)[:5]

    total_price = sum(item['quote']['USD']['price'] for item in data)
    average_price = total_price / len(data)

    highest_change = max(data, key=lambda x: x['quote']['USD']['percent_change_24h'])
    lowest_change = min(data, key=lambda x: x['quote']['USD']['percent_change_24h'])

    analysis = {
        'top_5': top_5,
        'average_price': average_price,
        'highest_change': highest_change,
        'lowest_change': lowest_change
    }
    return analysis

def authenticate_google_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_dict(CREDENTIALS, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SPREADSHEET_KEY).sheet1
        return sheet
    except Exception as e:
        print(f"Error authenticating Google Sheets: {e}")
        sys.exit(1)

def update_google_sheet(sheet, data, analysis):
    try:
        sheet.clear()

        headers = [
            'Cryptocurrency Name',
            'Symbol',
            'Current Price (USD)',
            'Market Capitalization',
            '24h Trading Volume',
            'Price Change (24h)'
        ]
        sheet.append_row(headers)

        for item in data:
            row = [
                item['name'],
                item['symbol'],
                f"{item['quote']['USD']['price']:,.2f}",
                f"{item['quote']['USD']['market_cap']:,.2f}",
                f"{item['quote']['USD']['volume_24h']:,.2f}",
                item['quote']['USD']['percent_change_24h']
            ]
            sheet.append_row(row)

        sheet.append_row([])
        sheet.append_row(['Data Analysis'])

        top_5_names = ', '.join([crypto['name'] for crypto in analysis['top_5']])
        sheet.append_row(['Top 5 Cryptocurrencies by Market Cap', top_5_names])

        sheet.append_row(['Average Price of Top 50 Cryptocurrencies (USD)', f"{analysis['average_price']:,.2f}"])

        sheet.append_row([
            'Highest 24h Price Change',
            analysis['highest_change']['name'],
            analysis['highest_change']['quote']['USD']['percent_change_24h']
        ])

        sheet.append_row([
            'Lowest 24h Price Change',
            analysis['lowest_change']['name'],
            analysis['lowest_change']['quote']['USD']['percent_change_24h']
        ])

        print(f"Google Sheet updated at {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')}")

    except Exception as e:
        print(f"Error updating Google Sheet: {e}")

def main():
    sheet = authenticate_google_sheet()
    while True:
        data = fetch_live_data()
        analysis = analyze_data(data)
        update_google_sheet(sheet, data, analysis)
        time.sleep(UPDATE_INTERVAL)

if __name__ == '__main__':
    main()

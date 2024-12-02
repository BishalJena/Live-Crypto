import os
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import sys
from datetime import datetime, timezone, timedelta

API_KEY = os.getenv('API_KEY')
SPREADSHEET_KEY = os.getenv('SPREADSHEET_KEY')
UPDATE_INTERVAL = 300

CREDENTIALS = {
    "type": "service_account",
    "project_id": os.getenv('PROJECT_ID'),
    "private_key_id": os.getenv('PRIVATE_KEY_ID'),
    "private_key": os.getenv('PRIVATE_KEY').replace('\\n', '\n'),
    "client_email": os.getenv('CLIENT_EMAIL'),
    "client_id": os.getenv('CLIENT_ID'),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.getenv('CLIENT_X509_CERT_URL'),
    "universe_domain": "googleapis.com"
}

API_URL = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
IST = timezone(timedelta(hours=5, minutes=30))

def fetch_live_data():
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': API_KEY,
    }
    params = {'start': '1', 'limit': '50', 'convert': 'USD'}
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
    return {
        'top_5': top_5,
        'average_price': average_price,
        'highest_change': highest_change,
        'lowest_change': lowest_change
    }

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


import requests
import pandas as pd
import time
import json
from datetime import datetime
import datetime

from .config import SETTINGS

def get_historical_data(symbol: str, interval: str, start_time: datetime, end_time: datetime) -> pd.DataFrame:
    """
    Fetch historical candlestick data from Binance API.

    Args:
        symbol (str): Trading pair symbol (e.g., 'BTCUSDT').
        interval (str): Candlestick interval (e.g., '5m', '1h').
        start_time (datetime): Start time in 'YYYY-MM-DD HH:MM:SS' format.
        end_time (datetime): End time in 'YYYY-MM-DD HH:MM:SS' format.

    Returns:
        pd.DataFrame: DataFrame containing historical candlestick data.
    """
    url = SETTINGS["URL_HISTORIQUE"]
    # start_timestamp = int(datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S').timestamp() * 1000)
    # end_timestamp = int(datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S').timestamp() * 1000)
    start_timestamp = int(start_time.timestamp() * 1000)
    end_timestamp = int(end_time.timestamp() * 1000)

    all_data = []
    limit = 1000
    while start_timestamp < end_timestamp:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': start_timestamp,
            'endTime': end_timestamp,
            'limit': limit
        }
        response = requests.get(url, params=params)
        data = response.json()

        if not data:
            break

        all_data.extend(data)
        start_timestamp = data[-1][0] + 1  # Move to the next timestamp

        time.sleep(0.5)  # To respect API rate limits

    # Convert to DataFrame
    df = pd.DataFrame(all_data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])

    # Convert timestamps to datetime
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    df['close_time'] = pd.to_datetime(df['close_time'], unit='ms')

    # Convert numeric columns to float
    numeric_cols = ['open', 'high', 'low', 'close', 'volume',
                    'quote_asset_volume', 'taker_buy_base_asset_volume',
                    'taker_buy_quote_asset_volume']
    df[numeric_cols] = df[numeric_cols].astype(float)
    df['number_of_trades'] = df['number_of_trades'].astype(int)
    return df
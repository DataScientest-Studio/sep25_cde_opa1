import os
import pandas as pd
from binance.spot import Spot
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

client = Spot(
    api_key=os.getenv("BINANCE_API_KEY"),
    api_secret=os.getenv("BINANCE_API_SECRET")
)



def conversion_date(date):
    #date fuseau horaire paris "strippé"
    format_date = datetime.strptime(date, "%d/%m/%Y")
    #récupération du fuseau horaire de paris
    paris = pytz.timezone("Europe/Paris")
    #format de date paris en incluant le fuseau
    format_date_paris = paris.localize(format_date)
    #conversion en UTC
    return int(format_date_paris.timestamp() * 1000)

print(conversion_date("01/01/2024"))

def historical_data(crypto, start, end, candle):
    start_UNIX=conversion_date(start)
    end_UNIX=conversion_date(end)

    klines = client.klines(symbol=crypto, startTime= start_UNIX, endTime=end_UNIX, interval=candle)
    df = pd.DataFrame(klines, columns=[
    "Open time", "Open", "High", "Low", "Close", "Volume",
    "Close time", "Quote asset volume", "Number of trades",
    "Taker buy base asset volume", "Taker buy quote asset volume", "Ignore"
    ])

    df["Open time"] = pd.to_datetime(df["Open time"], unit="ms")
    df["Close time"] = pd.to_datetime(df["Close time"], unit="ms")

    return df



data=historical_data('BNBEUR', "20/12/2025", "22/12/2025","15m")

print(data)

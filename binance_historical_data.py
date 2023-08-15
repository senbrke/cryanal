from binance.client import Client
import talib
import numpy as np
import pandas as pd
import time

client = Client()


def get_top_volume_symbols(limit=10):
    # Binance vadeli işlemler borsasındaki tüm USDT çiftlerini al
    tickers = client.get_ticker()
    usdt_pairs = [ticker['symbol'] for ticker in tickers if 'USDT' in ticker['symbol']]

    # En yüksek hacimli USDT çiftlerini sırala (Son 12 saat)
    sorted_pairs = sorted(usdt_pairs, key=lambda pair: float(
        [ticker for ticker in tickers if ticker['symbol'] == pair][0]['volume']), reverse=True)

    return sorted_pairs[:limit]


top_symbols = get_top_volume_symbols(2) # Verisetini oluşturmak istediğiniz coin sayısını girin.

# Configuration
CONFIG = {
    'symbols': top_symbols,
    # Bu kısımda top_symbols kullanmayıp istersen belirli coinleri liste içinde sıralayabilirsiniz.
    # Örn : ["BTCUSDT", "ETHUSDT"]
    'interval': Client.KLINE_INTERVAL_4HOUR,  # Mum periyodu. Örn: 1HOUR, 2HOUR, 12HOUR, 1DAY, 1WEEK
    'start_date': "1 Jan, 2023",
    'end_date': "15 Aug, 2023",
    'add_indicators': True,  # Veri setinizde indikatör değerlerinin bulunmasını istemiyorsanız : False
    'output_file': 'deneme.csv' # veri setine isim veriniz.
}


def get_historical_data(symbol, interval, start_date, end_date):
    """Fetch historical klines data from Binance."""
    return client.get_historical_klines(symbol, interval, start_date, end_date)


def calculate_technical_indicators(data):
    """TA-Lib kütüphanesi ile indikatör değerlerinin hesaplanması."""
    close = np.array([float(x[4]) for x in data])
    high = np.array([float(x[2]) for x in data])
    low = np.array([float(x[3]) for x in data])
    volume = np.array([float(x[5]) for x in data])

    indicators = {
        'RSI': talib.RSI(close, timeperiod=14),
        'RSI_MA': talib.SMA(close, timeperiod=14),
        'MACD': talib.MACD(close)[0],
        'MACD_signal': talib.MACD(close)[1],
        'ema5': talib.EMA(close, timeperiod=5),
        'ema9': talib.EMA(close, timeperiod=9),
        'ema12': talib.EMA(close, timeperiod=12),
        'ema18': talib.EMA(close, timeperiod=18),
        'ema50': talib.EMA(close, timeperiod=50),
        'ema100': talib.EMA(close, timeperiod=100),
        'ema200': talib.EMA(close, timeperiod=200),
        'psar': talib.SAR(high, low),
        'obv': talib.OBV(close, volume),
        'adx': talib.ADX(high, low, close),
        'pdf': talib.PLUS_DI(high, low, close),
        'mdx': talib.MINUS_DI(high, low, close)
    }

    return indicators


def fetch_and_save_data():
    all_data = []

    for symbol in CONFIG['symbols']:
        klines = get_historical_data(symbol, CONFIG['interval'], CONFIG['start_date'], CONFIG["end_date"])

        if klines:
            df = pd.DataFrame(klines, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
                'taker_buy_quote_asset_volume', 'ignore'
            ])

            # Adding symbol and date columns
            df['symbol'] = symbol
            df['date'] = pd.to_datetime(df['open_time'], unit='ms')

            if CONFIG['add_indicators']:
                indicators = calculate_technical_indicators(klines)
                for key, values in indicators.items():
                    df[key] = values

            all_data.append(df)

            time.sleep(1)  # To respect Binance API rate limits

    # Saving all data to a CSV file
    all_data_df = pd.concat(all_data)
    all_data_df.to_csv(CONFIG['output_file'], index=False)

    return all_data_df


# Fetching and saving the data
data_df = fetch_and_save_data()
data_df.head()  # Displaying the head of the data

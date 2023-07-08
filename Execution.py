import pandas as pd
from binance.client import Client
import time
import talib

# Binance API erişim anahtarları
api_key = 'YOUR_API_KEY'
api_secret = 'YOUR_API_SECRET'

# Binance istemci nesnesi oluşturma
client = Client(api_key, api_secret)

# USDT ile eşleşen ve kontrat türü PERPETUAL olanları seçer.
top_symbols = [s for s in client.futures_exchange_info()['symbols'] if
               'USDT' in s['pair'] and s['contractType'] == 'PERPETUAL']



daily_volumes = []

for s in top_symbols:
    daily_volume = client.futures_historical_klines(s['symbol'], Client.KLINE_INTERVAL_1MONTH, '1 month ago UTC')[0][7]
    daily_volumes.append((s['symbol'], float(daily_volume)))


# Günlük hacmi en yüksek 50 coin/usdt çifti.
top_symbols = [pair[0] for pair in sorted(daily_volumes, key=lambda x: x[1], reverse=True)[:50]] # analiz etmek istenilen coin sayısı. Bu örnekte 50

print("İlk 50 kripto para sembolü:")
print(top_symbols)

# istenilen zaman serisi verileri için kripto para birimi listesi. Bu örnekte 1 günlük.
# (Örneğin 4 saatlik veri için : Client.KLINE_INTERVAL_4HOUR)
interval = Client.KLINE_INTERVAL_1DAY
candles = {}

# OHLC ve hacim verilerini çekme
end_time = int(time.time() * 1000)
start_time = end_time - (365 * 24 * 60 * 60 * 1000)

def get_historical_data(symbol, interval, start_time, end_time):
    klines = client.futures_historical_klines(symbol, interval, start_time, end_time)
    df = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time',
                                       'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
                                       'taker_buy_quote_asset_volume', 'ignore'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    df.drop(['close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume',
             'taker_buy_quote_asset_volume', 'ignore'], axis=1, inplace=True)
    df.columns = ['open', 'high', 'low', 'close', 'volume']
    return df



candles = {}
for symbol in top_symbols:
    df = get_historical_data(symbol, interval, start_time, end_time)
    candles[symbol] = df
    print(f"{symbol} için tarihsel veriler alındı")


def calculate_fibonacci_levels(df):
    high = max(df['high'].astype(float))
    low = min(df['low'].astype(float))
    diff = high - low

    levels = {
        '0.236': high - 0.236 * diff,
        '0.382': high - 0.382 * diff,
        '0.5': high - 0.5 * diff,
        '0.618': high - 0.618 * diff,
        '0.786': high - 0.786 * diff,
    }

    return levels

def analyze_and_score(symbol, df):
    if df.isnull().all().all():
        return {
            'symbol': symbol,
            'error': 'All data is NaN',
        }

    # Yeterli veri kontrolü
    if len(df) < 200:
        return {
            'symbol': symbol,
            'error': 'Insufficient data for EMA calculations',
        }


    points = 1
    open_ = df['open'].astype(float)
    close = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    ema5 = talib.EMA(close, timeperiod=5)
    ema10 = talib.EMA(close, timeperiod=10)
    fib_levels = calculate_fibonacci_levels(df[-50:])  # Son 50 veri anoktasını kullanarak hesapla
    pdx = talib.PLUS_DI(high, low, close, timeperiod=14)
    mdx = talib.MINUS_DI(high, low, close, timeperiod=14)

    # RSI
    for i in range(-3, 0):

        # EMA 5 combinations
        ema_sma_points = 1
        if ema5[i] > ema10[i] and ema5[i - 1] < ema10[i - 1]:
            ema_sma_points *= 1.2
        elif ema5[i] < ema10[i] and ema5[i - 1] > ema10[i - 1]:
            ema_sma_points /= 1.2

        points *= ema_sma_points

        # fib
        fib_points = 1
        for level in fib_levels.values():
            if close[i] > level > close[i - 1]:
                fib_points *= 1.2
            elif close[i] < level < close[i - 1]:
                fib_points /= 1.2

        points *= fib_points

        # ADX

        pdx_points = 1
        if pdx[i] > mdx[i] and pdx[i - 1] < mdx[i - 1]:
            pdx_points *= 1.2
        elif pdx[i] < mdx[i] and pdx[i - 1] > mdx[i - 1]:
            pdx_points /= 1.2

        points *= pdx_points



    return {
        'symbol': symbol,
        'date': df.index[-1],  # Tarih bilgisini ekleyin
        'price': df['close'][-1],  # Fiyat bilgisini ekleyin
        "fib_points" : fib_points,
        'ema_sma_points': ema_sma_points,
        "pdx_points" : pdx_points,
        'points': points
    }


# Tüm kripto paraları analiz et ve puanlamaları sakla
crypto_scores = []
for symbol, df in candles.items():
    score = analyze_and_score(symbol, df)
    crypto_scores.append(score)

# En yüksek puanlı ve en düşük puanlı 10 kripto parayı al
top_10_symbols = sorted([score for score in crypto_scores if 'points' in score], key=lambda x: x['points'], reverse=True)

# Puanları DataFrame'e dönüştürme
def scores_to_dataframe(symbols):
    return pd.DataFrame(symbols).set_index('symbol')

pd.set_option('display.max_columns', None)  # Bütün sütunları göster
pd.set_option('display.width', 1000)        # Ekran genişliğini artır (sütunlar arasında yatay kaydırma olmaması için)
pd.set_option('display.max_rows', None)

# En yüksek puanlı 10 kripto para ve indikatör puanlarını DataFrame'de göster
top_10_df = scores_to_dataframe(top_10_symbols)
print("En yüksek puanlı 10 kripto para ve indikatör puanları:")
print(top_10_df)

print(crypto_scores)



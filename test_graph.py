import requests
import pandas as pd
import numpy as np
import talib
from datetime import datetime
import matplotlib.pyplot as plt

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
pd.set_option('display.max_rows', None)


def get_binance_data(symbol, interval, start_time, end_time, limit=5000):
    """
    Binance API üzerinden belirli bir zaman aralığı için belirli bir sembolün kline (candlestick) verilerini çeker.

    Parameters
    ----------
    symbol : str
        Çekmek istediğiniz sembol. Örneğin: 'BTCUSDT'.

    interval : str
        Candlestick intervali. Örneğin: '1m', '3m', '1h', '1d' vb.

    start_time : int
        Başlangıç zamanı, milisaniye cinsinden timestamp.

    end_time : int
        Bitiş zamanı, milisaniye cinsinden timestamp.

    limit : int, optional
        Tek bir istekte çekilebilecek maksimum kline sayısı. Varsayılan değer 5000.

    Returns
    -------
    pandas.DataFrame
        Binance'ten alınan kline verileri. Sütunlar: 'open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time',
        'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'.
        DataFrame 'open_time' sütunu üzerine indekslenmiştir ve bu sütun pandas datetime tipine dönüştürülmüştür.
    """
    base_url = "https://api.binance.com/api/v3/klines"
    columns = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume',
               'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore']
    data = []

    while start_time < end_time:
        url = f"{base_url}?symbol={symbol}&interval={interval}&startTime={start_time}&endTime={end_time}&limit={limit}"
        response = requests.get(url)
        temp_data = response.json()
        data.extend(temp_data)

        if len(temp_data) == 0:
            break
        else:
            start_time = temp_data[-1][0] + 1

        if len(data) >= 5000:
            data = data[:5000]
            break

    df = pd.DataFrame(data, columns=columns)
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    df.set_index('open_time', inplace=True)
    return df


def calculate_points(df, rsip=1.4, macdp=1.2):
    """
    Talib kütüphanesindeki indikatörler temelinde belirli parametrelere ve stratejiye dayalı bir puan hesaplar.
    Kodda örnek olarak RSI ve MACD indikatörleri kesişimlerinden puan alacak şekilde kullanılmıştır.

    Parameters
    ----------
    df : pandas.DataFrame
        'open', 'close', 'high', 'low' ve 'volume' sütunlarına sahip bir DataFrame. Fiyat verileri float tipinde olmalıdır.

    Returns
    -------
    float
        Hesaplanan toplam puan.
    """
    points = 1

    open_ = df['open'].astype(float)
    close = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)

    # RSI
    rsi = talib.RSI(close, timeperiod=14)
    rsi_ma = talib.SMA(rsi, timeperiod=14)
    rsi_points = 1
    if rsi[-1] > rsi_ma[-1] and rsi[-2] < rsi_ma[-2]:
        rsi_points *= rsip
    elif rsi[-1] < rsi_ma[-1] and rsi[-2] > rsi_ma[-2]:
        rsi_points /= rsip
    if rsi[-1] > 80:
        rsi_points *= 0.9
    elif rsi[-1] < 20:
        rsi_points *= 1.1
    points *= rsi_points

    # MACD
    macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
    macd_points = 1
    if macd[-1] < macd_signal[-1] and macd[-1] < 0 and macd[-3] > macd[-2] < macd[-1]:
        macd_points *= macdp
    elif macd[-1] > macd_signal[-1] and macd[-1] > 0 and macd[-3] < macd[-2] > macd[-1]:
        macd_points /= macdp
    points *= macd_points

    return points


symbol = 'ETHUSDT'
interval = "1d"
start_time = "2020-01-01 00:00:00"
end_time = "2023-05-07 00:00:00"

start_time_unix = int(datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").timestamp()) * 1000
end_time_unix = int(datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S").timestamp()) * 1000

## Threshold belirleme
# Alım/Long işlem eşik değeri
buy_th = 1.5
# Satım/Short işlem eşik değeri
sell_th = 0.5

try:
    btc_data = get_binance_data(symbol, interval, start_time_unix, end_time_unix)
    btc_data[['open', 'high', 'low', 'close']] = btc_data[['open', 'high', 'low', 'close']].astype(float)
except Exception as e:
    print(f"Error occurred while getting data: {e}")

try:
    btc_data['Signal'] = btc_data['close'].expanding(min_periods=20).apply(
        lambda x: calculate_points(btc_data.loc[x.index]))

    btc_data['Buy'] = np.where(btc_data['Signal'] >= buy_th, btc_data['close'], np.nan)
    btc_data['Sell'] = np.where(btc_data['Signal'] <= sell_th, btc_data['close'], np.nan)

    print(btc_data[['close', 'Signal', 'Buy', 'Sell']].sort_values("Signal"))

    display_data = len(btc_data)

    # Grafik ayarlamaları
    plt.figure(figsize=(12, 6))
    plt.plot(btc_data.index[-display_data:], btc_data['close'][-display_data:], label=f'{symbol}', alpha=0.7)
    plt.scatter(btc_data.index[-display_data:], btc_data['Buy'][-display_data:], label='Buy Signal', marker='^',
                color='g', alpha=1)
    plt.scatter(btc_data.index[-display_data:], btc_data['Sell'][-display_data:], label='Sell Signal', marker='v',
                color='r', alpha=1)

    plt.title(f'{symbol} Buy and Sell Signals')
    plt.xlabel('Date')
    plt.ylabel('Price')
    plt.legend(loc='upper left')

    plt.show()
except Exception as e:
    print(f"Error occurred while processing data: {e}")

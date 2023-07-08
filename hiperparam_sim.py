import pandas as pd
import requests
from datetime import datetime
import talib
from statistics import median
from joblib import Parallel, delayed
import multiprocessing


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
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&startTime={start_time}&endTime={end_time}&limit={limit}"
    columns = ['open_time', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume',
               'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore']

    data = []
    while start_time < end_time:
        response = requests.get(url)
        temp_data = response.json()
        data.extend(temp_data)

        if len(temp_data) == 0:
            break
        else:
            start_time = temp_data[-1][0] + 1
            url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&startTime={start_time}&endTime={end_time}&limit={limit}"

        # 5000 k-line verisine ulaştığında döngüyü durdur
        if len(data) >= 5000:
            data = data[:5000]
            break

    df = pd.DataFrame(data, columns=columns)
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    df.set_index('open_time', inplace=True)
    return df


interval = "1d"
start_time = "2018-01-01 00:00:00"
end_time = "2022-01-01 00:00:00"
coins = ["BTCUSDT", "ETHUSDT", "XRPUSDT"] # İstenilen coin/usdt çiftleri girilmeli. İlgili coin ilgili tarihte
# binance borsasında işlem gördüğine emin olunmalı.


start_time_unix = int(datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S").timestamp()) * 1000
end_time_unix = int(datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S").timestamp()) * 1000


def calculate_points(df, rsip=1.8, macdp=1.8):
    """
    Talib kütüphanesindeki indikatörler temelinde belirli parametrelere ve stratejiye dayalı bir puan hesaplar.
    Kodda örnek olarak RSI ve MACD indikatörleri kesişimlerinden puan alacak şekilde kullanılmıştır.

    Parameters
    ----------
    df : pandas.DataFrame
        'open', 'close', 'high', 'low' ve 'volume' sütunlarına sahip bir DataFrame. Fiyat verileri float tipinde olmalıdır.

    rsip : float, optional
        RSI hesaplamasında kullanılan parametre. Varsayılan değer 1.8.

    macdp : float, optional
        MACD hesaplamasında kullanılan parametre. Varsayılan değer 1.8.

    Returns
    -------
    float
        Hesaplanan toplam puan.
    """
    total_points = 1
    open_ = df['open'].astype(float)
    close = df['close'].astype(float)
    high = df['high'].astype(float)
    low = df['low'].astype(float)
    volume = df['volume'].astype(float)
    rsi = talib.RSI(close, timeperiod=14)
    rsi_ma = talib.SMA(rsi, timeperiod=14)
    macd, macd_signal, macd_hist = talib.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)


    # RSI
    for i in range(-3, 0):
        points = 1

        rsi_points = 1
        if rsi[i] > rsi_ma[i] and rsi[i - 1] < rsi_ma[i - 1] and rsi[i] < 40:
            rsi_points *= rsip
        elif rsi[i] < rsi_ma[i] and rsi[i - 1] > rsi_ma[i - 1] and rsi[i] > 70:
            rsi_points /= rsip


        # MACD
        macd_points = 1
        if macd[i] > macd_signal[i] and macd[i] < 0 and macd[i - 1] < macd_signal[i - 1]:
            macd_points *= macdp
        elif macd[i] < macd_signal[i] and macd[i] > 0 and macd[i - 1] > macd_signal[i - 1]:
            macd_points /= macdp

        points = rsi_points * macd_points
        total_points *= points

    return total_points


def trading_signal(df, higher_than=2, short_th=0.5, rsip=1.8, macdp=1.8):
    """
    Verilen DataFrame'de ticaret sinyallerini belirler ve 'points', 'long_signal' ve 'short_signal' sütunlarını döndürür.

    Parameters
    ----------
    df : pandas.DataFrame
        'close' sütununa sahip bir DataFrame. Fiyat verileri float tipinde olmalıdır.

    higher_than : float, optional
        Uzun pozisyon almak için gereken minimum puan. Varsayılan değer 2.

    short_th : float, optional
        Kısa pozisyon almak için gereken maksimum puan. Varsayılan değer 0.5.

    rsip : float, optional
        RSI hesaplamasında kullanılan parametre. Varsayılan değer 1.8.

    macdp : float, optional
        MACD hesaplamasında kullanılan parametre. Varsayılan değer 1.8.

    Returns
    -------
    pandas.DataFrame
        Girdi DataFrame'ine 'points', 'long_signal' ve 'short_signal' sütunları eklenmiş hali.
    """
    df['points'] = df['close'].expanding(min_periods=20).apply(
        lambda x: calculate_points(df.loc[x.index], rsip=rsip, macdp=macdp))

    df['long_signal'] = df['points'] > higher_than
    df['short_signal'] = df['points'] < short_th

    return df


def simulate_trades(df, leverage):
    """
    Verilen DataFrame'deki ticaret sinyalleri üzerinde bir simülasyon gerçekleştirir. Simülasyonun sonucunda ticaret işlemleri,
    son bakiye ve maksimum düşüş miktarı döndürülür.

    Parameters
    ----------
    df : pandas.DataFrame
        Sütunları 'long_signal', 'short_signal', 'close', 'close_time', ve 'points' olan bir DataFrame. 'long_signal' ve
        'short_signal' sütunları ticaret sinyallerini belirtir. 'close' ve 'close_time' sütunları, işlemlerin gerçekleştiği
        zamandaki fiyatı ve zamanı belirtir. 'points' sütunu, her işlem için hesaplanan puanları belirtir.

    leverage : float
        Ticaretlerde kullanılan kaldıraç miktarı. Kaldıraç, yatırımcının yatırım miktarının üzerinde bir ticaret pozisyonu açmasına
        olanak sağlar.

    Returns
    -------
    list
        Gerçekleştirilen ticaret işlemlerinin detaylarını içeren bir liste. Her işlem, alış zamanı, satış zamanı, işlem tipi, alış
        ve satış fiyatı, kar/zarar, giriş ve çıkış bakiyesi ve alış puanları gibi bilgileri içeren bir sözlük olarak temsil edilir.
    float
        Simülasyon sonrası elde edilen son bakiye.
    float
        Simülasyon sürecinde yaşanan maksimum düşüş miktarı.
    """
    trades = []
    position = 0
    balance = 100
    highest_balance = 100
    max_drawdown = 0
    entry_time = None
    entry_points = None
    margin_call = False
    for index, row in df.iterrows():
        if position == 0:
            if row['long_signal'] and not margin_call:
                position = 1
                entry_price = row['close']
                entry_time = index
                entry_points = row['points']
            elif row['short_signal'] and not margin_call:
                position = -1
                entry_price = row['close']
                entry_time = index
                entry_points = row['points']
        elif position == 1:
            points_condition = 0.6 != None and row['points'] < 0.6
            exit_condition = points_condition or margin_call
            if exit_condition:
                exit_price = row['close']
                pnl = (exit_price - entry_price) / entry_price * leverage
                new_balance = balance * (1 + pnl)
                position = 0
                entry_balance = balance
                balance = new_balance
                trades.append({"entry_time": entry_time, "close_time": row['close_time'], "type": "long", "entry_price": entry_price, "exit_price": exit_price, "pnl": pnl, "entry_balance": entry_balance, "exit_balance": balance, "entry_points": entry_points})
                highest_balance = max(highest_balance, balance)
                max_drawdown = max(max_drawdown, highest_balance - balance)
                if balance <= 0:
                    margin_call = True
        elif position == -1:
            points_condition = 0.6 != None and row['points'] > 0.6
            exit_condition = points_condition or margin_call
            if exit_condition:
                exit_price = row['close']
                pnl = (entry_price - exit_price) / entry_price * leverage
                new_balance = balance * (1 + pnl)
                position = 0
                entry_balance = balance
                balance = new_balance
                trades.append({"entry_time": entry_time, "close_time": row['close_time'], "type": "short", "entry_price": entry_price, "exit_price": exit_price, "pnl": pnl, "entry_balance": entry_balance, "exit_balance": balance, "entry_points": entry_points})
                highest_balance = max(highest_balance, balance)
                max_drawdown = max(max_drawdown, highest_balance - balance)
                if balance <= 0:
                    margin_call = True
    return trades, balance, max_drawdown


def print_trades(trades):
    """
    Ticaret işlemlerini formatlı bir şekilde yazdırır. Her işlem için alış ve satış tarihleri, işlem tipi, alış ve satış
    fiyatları, işlem süresi, mum sayısı, yüzdelik kar/zarar, giriş ve çıkış bakiyeleri ve alış puanı gibi bilgileri içerir.
    Args:
        trades (list): Ticaret işlemlerini içeren bir liste. Her işlem, bir sözlük olup alış tarihi, satış tarihi, işlem tipi,
                       alış ve satış fiyatları, giriş ve çıkış bakiyeleri, ve alış puanı gibi bilgileri içerir.

    Returns:
        None: Bu fonksiyon hiçbir şey döndürmez. Sadece ticaret işlemlerini formatlı bir şekilde yazdırır.
    """
    print(
        f"{'Alış Tarihi':<20} {'Satış Tarihi':<20} {'İşlem Tipi':<10} {'Alış Fiyatı':<12} {'Satış Fiyatı':<12} {'Gün Sayısı':<10} {'Mum Sayısı':<10} {'Kâr/Zarar (%)':<12} {'Giriş Bakiyesi':<15} {'Çıkış Bakiyesi':<15} {'Alış Puanı':<12}")
    print("=" * 168)
    for trade in trades:
        entry_date = trade['entry_time'].strftime('%Y-%m-%d %H:%M:%S')
        exit_date = pd.to_datetime(trade['close_time'], unit='ms').strftime('%Y-%m-%d %H:%M:%S')
        days = (pd.to_datetime(trade['close_time'], unit='ms') - trade['entry_time']).days
        candles = days * 6
        if trade['type'] == 'long':
            pnl_percentage = ((trade['exit_price'] - trade['entry_price']) / trade['entry_price']) * leverage * 100
        elif trade['type'] == 'short':
            pnl_percentage = ((trade['entry_price'] - trade['exit_price']) / trade['entry_price']) * leverage * 100

        print(
            f"{entry_date:<20} {exit_date:<20} {trade['type']:<10} {trade['entry_price']:<12.2f} {trade['exit_price']:<12.2f} {days:<10} {candles:<10} {pnl_percentage:<12.2f} {trade['entry_balance']:<15.2f} {trade['exit_balance']:<15.2f} {trade['entry_points']:<12.2f}")
    print("\n")

## HİPERPARAMETRE OPTİMİZASYONU ##

best_score = -float('inf')
best_parameters = None
max_avg_days_in_trade = 45
max_num_trades = 1  # initial value, it will be updated during the optimization
leverage = 1
higher_thans = [1.2, 1.8]
rsips = [1.8, 1.2]
macdps = [1.8, 1.2]



def calculate_score(params):
    """
    Belirli parametreler ile alım satım sinyallerini hesaplar, bu sinyaller üzerinde ticaret simülasyonları yapar ve
    sonuçları skorlar. Hesaplanan skor, normalize edilmiş karlı işlem oranı, normalize edilmiş medyan kar/zarar ve
    normalize edilmiş işlem sayısı çarpımıdır.
    Eğer belirli parametrelerle hiçbir sinyal oluşturulamazsa, bir mesaj yazdırır ve None döner.

    :param params (tuple): Optimize edilecek parametreler.
    :return: tuple: Hesaplanan skor, parametreler,
    işlem sayıları (medyan, min, max), karlı işlem oranı, işlem başına kar/zarar (medyan, min, max).
    Eğer hiçbir sinyal oluşturulamazsa, None döner.
    """
    higher_than, rsip, macdp = params
    all_results = []
    num_trades_per_coin = []
    for coin in coins:
        df = get_binance_data(coin, interval, start_time_unix, end_time_unix)
        df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)

        trading_signals = trading_signal(df, higher_than=higher_than, rsip=rsip, macdp=macdp)

        trades, final_balance, max_drawdown = simulate_trades(trading_signals, leverage)
        num_trades_per_coin.append(len(trades))

        all_results.extend([(trade['pnl'], (pd.to_datetime(trade['close_time'], unit='ms') - trade['entry_time']).days) for trade in trades])

    if len(all_results) == 0:
        print(
            f"Verilen parametreler (higher_than={higher_than}, rsip={rsip}, macdp={macdp}) ile hiçbir sinyal oluşmamıştır.")
        return None

    if len(all_results) == 0:
        avg_days_in_trade = 0
    else:
        avg_days_in_trade = sum([trade[1] for trade in all_results]) / len(all_results)

    if avg_days_in_trade > max_avg_days_in_trade:
        return None

    profitable_trade_ratios = [trade[0] > 0 for trade in all_results]

    median_pnls = [trade[0] for trade in all_results]

    if len(profitable_trade_ratios) > 0:
        normalized_profit_trade_ratio = sum(profitable_trade_ratios) / len(profitable_trade_ratios)
    else:
        normalized_profit_trade_ratio = 0

    if len(median_pnls) > 0 and max(median_pnls) != min(median_pnls):
        normalized_median_pnl = (median(median_pnls) - min(median_pnls)) / (max(median_pnls) - min(median_pnls))
    else:
        normalized_median_pnl = 0

    if len(num_trades_per_coin) > 0 and max(num_trades_per_coin) != min(num_trades_per_coin):
        normalized_num_trades = (median(num_trades_per_coin) - min(num_trades_per_coin)) / (
                    max(num_trades_per_coin) - min(num_trades_per_coin))
    else:
        normalized_num_trades = 0

    score = normalized_profit_trade_ratio * normalized_median_pnl * normalized_num_trades

    print(f"Denenen parametreler: higher_than={higher_than}, rsip={rsip}, macdp={macdp}")
    print(f"Hesaplanan skor: {score}")
    print(f"İşlem sayısı (medyan, min, max): {median(num_trades_per_coin)}, {min(num_trades_per_coin)}, {max(num_trades_per_coin)}")
    if len(profitable_trade_ratios) > 0:
        profit_ratio = sum(profitable_trade_ratios) / len(profitable_trade_ratios)
    else:
        profit_ratio = 0
    print(f"Karlı işlem oranı: {profit_ratio}")
    print(f"İşlem başına kar/zarar (medyan, min, max): {median(median_pnls)}, {min(median_pnls)}, {max(median_pnls)}\n")

    return (score, (higher_than, rsip, macdp), (median(num_trades_per_coin), min(num_trades_per_coin), max(num_trades_per_coin)), sum(profitable_trade_ratios) / len(profitable_trade_ratios), (median(median_pnls), min(median_pnls), max(median_pnls)))


# Parametre kombinasyonlarını bir listeye alın
params = [(higher_than, rsip, macdp) for higher_than in higher_thans for rsip in rsips for macdp in macdps]

# Çekirdek sayısını belirleyin
num_cores = multiprocessing.cpu_count()

# Paralel hesaplamayı başlatın
results = Parallel(n_jobs=num_cores)(delayed(calculate_score)(p) for p in params)

# None olan sonuçları filtreleyin ve en iyi skoru bulun
results = [r for r in results if r is not None]
best_score, best_parameters, trade_numbers, profitable_ratio, pnl_per_trade = max(results, key=lambda x: x[0])

print(f"En iyi hiperparametreler: higher_than={best_parameters[0]}, risp={best_parameters[1]}, macd={best_parameters[2]}")
print(f"En iyi skor: {best_score}")
print(f"En iyi parametrelerin işlem sayısı (medyan, min, max): {trade_numbers}")
print(f"En iyi parametrelerin karlı işlem oranı: {profitable_ratio}")
print(f"En iyi parametrelerin işlem başına kar/zarar (medyan, min, max): {pnl_per_trade}")
####

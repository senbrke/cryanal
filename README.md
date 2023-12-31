# cryanal
## Amaç 
**cryanal** (*crypto* *analysis*), bir kripto para birimi sinyal botudur.
## Nasıl ? 
Binance API aracılığı ile coin/usdt çiftlerinin versini çekip bu veriler üzerinde TAlib kütüphanesini kullanarak belirli indikatörler arcılığı ile puan ataması yapıp coinleri listelemek. 
Kodlarda gösterdiğim indikatörler ve stratejiler tamamen örnek olması amacıyla yazılmıştır. Kendi stratejinizi ve kendi seçtiğiniz indikatörleri yine kendi istediğiniz şekilde kullanabilirsiniz. [Daha fazla bilgi için talib kütüphanesini ziyaret edin.](https://github.com/mrjbq7/ta-lib)
## Gerekli Kütüphaneler :
- [pandas](https://pandas.pydata.org/)
- [binance-client](https://github.com/binance/binance-connector-python)
- [talib](https://github.com/mrjbq7/ta-lib)
- [numpy](https://numpy.org/)
- [matplotlib](https://matplotlib.org/)
- [requests](https://docs.python-requests.org/en/latest/)
- [joblib](https://joblib.readthedocs.io/en/latest/)
- [statistics](https://docs.python.org/3/library/statistics.html)
- [datetime](https://docs.python.org/3/library/datetime.html)
- [multiprocessing](https://docs.python.org/3/library/multiprocessing.html)

# Dosyalar
## test_graph 
Bu kısımda, belirlediğimiz puanlama stratejisini bir grafik üzerinde inceleyebiliriz. Hangi indikatörlerin kullanılacağını, hangi indikatörlere kaç puan atanacağını, alım sinyali için minimum puan sınırımızın (threshold) ne olacağını ve satım ya da belki de kısa pozisyon (short) sinyali için minimum puan sınırımızın ne olacağını bizim belirlememiz gerekiyor. İstediğimiz bir kripto para birimi (coin) ve USDT çifti üzerinde, istediğimiz bir zaman aralığında ve istediğimiz bir candlestick (mum çubuk) verisi üzerinde stratejimizi test edebilir ve sonuçları görselleştirebiliriz. Bu sayede, stratejimizin belirli piyasa koşulları ve varlıklar üzerinde nasıl performans gösterdiğini anlamamıza yardımcı olabilir. Bu grafikler, stratejimizi ayarlamak ve iyileştirmek için değerli bir araç olabilir. Aynı zamanda çıktı olarak hangi zamanda kaç puan alınmış ve bu andaki fiyat bilgisine de ulaşabiliyoruz. 

## hiperparam_sim: 
Bu bölüm, indikatörlerin, indikatörlere verilen puanların, alım ve satım eşik değerlerinin ve herhangi bir değerin optimize edilmesine olanak sağlar. Ancak, sadece bir alım ya da satım sinyali optimizasyon için yeterli değildir. Ayrıca bir strateji oluşturulmalı, bu stratejiye dayalı bir simülasyon yapılmalı ve bir başarı ölçütü belirlenmelidir. Verilen örnekte, alım ve satım doğrudan puan bazında gerçekleşir. Başarı ölçütü olarak, üç farklı metrik normlaleştirilip çarpılarak bir skor elde edilir. Ancak, bu bölümlerle ilgili kesinlikle emin olamam. Çünkü sonuçta bu simülasyon, kapanış fiyatlarına dayanarak yapılıyor.
Burada farklı çözümler mevcut. Örneğin, çıkış stratejisi olarak, “belirli bir oranda düşüş yaşandığında (örneğin %10) işlemden çık.” şeklinde bir yaklaşım benimsenebilir. Bu sayede, kapanış fiyatı bizim işlemlerimizi kısıtlamaz. Çünkü eğer %10'luk düşüş en yüksek ve en düşük değer arasındaysa, doğrudan o fiyatla çıkış yapabiliriz.

Bunun yanında, yalnızca puanlama sistemine dayalı birçok strateji oluşturabiliriz. Örnek olarak, belirli bir süre boyunca alınan puanın ortalamasının üzerine çıktığında işleme gir ve aynı süre zarfında alınan puanın ortalamasının altına düştüğünde işlemden çık. Bu ve benzeri örnekleri daha da çoğaltabilirsiniz.

Hiperparametre optimizasyonu bölümünde dikkat edilmesi gereken bazı noktalar bulunuyor. Çok fazla parametrenin optimizasyonu, işlemleri oldukça zorlaştırabilir. Kodumuzda bulunan optimizasyon algoritması oldukça basittir ve işlemleri hızlandırmak için paralel olarak çalışır. Ayrıca girilen değerlere de dikkat etmek önemlidir. Mantıksız değerler girildiğinde, uygun bir puanlama yapamazsınız.

## sim_metrics: 
Bu kod parçası, daha önce oluşturduğumuz ve optimize ettiğimiz stratejinin backtesting işlemlerini gerçekleştirmek için tasarlanmıştır. Kendi çapımızda oluşturduğumuz stratejiyi, istediğimiz kripto para birimi/USDT çiftleri üzerinde test edebiliyoruz.
Backtesting süreci, bir stratejinin belirlenen geçmiş dönemde nasıl performans gösterdiğini simüle eder. Bu süreç, stratejimizin gerçekte ne kadar etkili olacağına dair bir fikir verir ve stratejimizi gerektiğinde iyileştirmemize yardımcı olabilir.

Simülasyon sonunda, tüm işlemlerimizin başarı metriklerini gösteririz. Bu metrikler, stratejimizin genel performansını değerlendirebilmemiz ve gelecekteki potansiyelini belirleyebilmemiz için çok önemlidir. Örneğin, ortalama kar/zarar yüzdesi, en yüksek kar ve zarar, ortalama işlem sayısı, en çok üst üste karlı ve zararlı işlem sayısı, ve ortalama mum sayısı gibi metrikleri ele alırız. Bu sayede stratejimizin hangi durumlarda daha iyi ya da kötü performans sergilediğini anlayabilir ve gerektiğinde stratejimizi bu bilgilere göre düzenleyebiliriz.

## Execution 
Bu kısım, hazırlıkların tamamlandığı ve kodumuzun canlı olarak çalıştırılmasının beklendiği noktadır. Kendi Binance 'api_key' ve 'api_secret' bilgilerinizi kullanarak kodu canlı olarak çalıştırabilirsiniz. Bu, Binance API'si üzerinden gerçek zamanlı olarak kripto para birimi/USDT çiftlerinin analizini gerçekleştirir ve her bir çift için bir puan üretir. Sonuç olarak, bu bölüm, kodumuzun gerçek zamanlı veriler üzerinde analiz yapabilmesini ve bu analiz sonuçlarına göre potansiyel yatırım kararları verebilmesini sağlar.

## binance_historical_data
Bu kısım Binance API kullanrak istediğiniz COINUSDT çiftlerinin mum verilerini çekip tek bir csv dosyasına aktarabileceğiniz bölüm. Bu py dosyasının özellikleri şu şekilde :
* İsterseniz kendi belirlediğiniz COINUSDT çiftlerinin verilerini isterseniz otomatik olarak 24 saatlik hacmi en yüksek x COINUSDT çiftinin verisini çekebilirsiniz.
* Çekeceğiniz mum verilerinin periyotlarını kendiniz belirleyebilirsiniz. (Örn. : 4HOUR, 1HOUR, 1DAY ...)
* İndikatör hesaplamalarını verisetine ekleyip eklememek yine size kalmış. CONFIG bölümünde add_indicators kısmında bunu seçiyor olacaksınız.
* İstediğiniz tarih aralığında veri çekebilirsiniz.

## Notlar:
* Her bir dosyanın içindeki yorumlarla ve her bir fonksiyonu docstirnglerle olabildiğince açıklamaya çalıştım.
* Her bir dosyada calculate_points fonksiyonumuzdaki indikatörler için farklı kullanım örneklerini vermeye çalıştım. Aynı indikatörleri farklı stratejiler ile kullanabiliriz.
* backtesting işlemlerinde calculate_points fonksiyonların başındaki for döngüsüne dikka çekmek istiyorum. Uyguladığım stratejide yaptığım incelemeler neticesinde her indikatörün aynı zaman diliminde kesişmediğini farkettim. Bu sorunun önüne geçebilmek amacıyla bu for döngüsü yazılmıştır.
* bir diğer önemli nokta calculate_points fonksiyonunda kullanılan iki farklı points değişkeni (total_points ve points). Bunu gerekli kılan hadise ise bir önceki notta bahsettiğim for döngüsü. total_points değişkeni for döngüsünün dışında ve points değişkeni for döngüsünün içinde kullanılıyor. Eğer bu kullanım olmasaydı puanlar sürekli yeniden atanacaktı ve biz total puanı görmek yerine son zaman dilimindeki kesişimlerden gelen puanı görebilcektik.
* Başka bir önemli nokta koddaki debugging kısımları. Özellikle hiperparametre kısmında bir çok hata ayıklama mesajları yerleştirdim. Burası benim en çok hata mesajı aldığım yerdi. Mantıklı olmayan parametre setleriyle çok fazla 0'a bölünme mesajı alabiliyoruz.
* **!!** Koddaki tüm stratejiler örnek olarak verilmiştir **YTD**  

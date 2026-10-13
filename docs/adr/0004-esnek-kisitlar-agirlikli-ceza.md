# ADR 0004: Esnek kısıtların ağırlıklı toplam ceza olarak birleştirilmesi

Durum: Kabul edildi (2026-10-06)

## Bağlam

Zorunlu kısıtları sağlayan çok sayıda program vardır. Bunların çoğu kullanılamaz: sınıfların
gün ortasında boş saatleri olur, öğretmenler dersler arasında bekler, çift dersler bölünür.
Bu istekler (CLAUDE.md bölüm 7, esnek kısıtlar) birbiriyle çatışabilir. Örneğin öğretmen
penceresini kapatmak bir sınıfta boşluk açabilir. Bu yüzden hangisinin ne kadar önemli olduğu
okul tarafından ayarlanabilmelidir.

## Karar

- Her esnek kural `(ceza ifadesi, ağırlık)` çiftleri döner. `CpSatCozucu` tek bir amaç
  fonksiyonunu en aza indirir: `Σ ağırlık × ceza`.
- Varsayılan ağırlıklar (2026-10-13 güncellemesi): sınıf boşluğu 30, en az değişiklik 8,
  tercih etmez 5, öğretmene boş gün 4, öğretmen penceresi 3, bölünmüş ders 2. Sınıf boşluğu
  ilk sürümde 10'du. Gün ortasında boş kalan sınıf okulda kabul edilemez olduğu için diğer
  bütün esnek kurallardan baskın olacak şekilde 30'a çıkarıldı. Okul bunları `kisit.agirlik` ile değiştirebilir. Ağırlık 0 verilirse kural kapanır.
- Her ceza, kullanıcının anlayacağı bir birimi sayar: "boş saat", "pencere saati", "bölünmüş
  ders günü", "tercih edilmeyen saate konan ders". Ceza 0 ise o ölçüde program kusursuzdur.
- Yardımcı değişkenler yalnızca alttan sınırlanır (ör. "bu saatte ya da sonrasında dersi var"
  ≥ "bu saatte dersi var"). Amaç fonksiyonu bu değişkenleri aşağı ittiği için en iyi çözümde
  tam doğru değeri alırlar. Model doğrusal kalır ve ek değişken sayısı saat başına sabittir.
- Aynı ölçüler `cozucu/kalite.py` içinde çözücüden bağımsız olarak düz Python ile de hesaplanır.
  Testler, en iyi çözümde modelin cezasının bu ölçümlerin ağırlıklı toplamına eşit olduğunu
  denetler.

## Değerlendirilen alternatifler

- **Sözlükbilimsel (öncelik sıralı) optimizasyon:** Önce sınıf boşluğu en aza indirilir, sonra
  bu değer sabitlenip pencere en aza indirilir ve böyle devam eder. Öncelikler kesin olur, ama
  çözücü birkaç kez çalışır ve süre sınırını bölmek gerekir. Ayrıca "biraz daha kötü bir sınıf
  programına karşılık çok daha iyi bir öğretmen programı" gibi takaslar yapılamaz. Ağırlıkları
  yeterince farklı seçmek gerekirse aynı etkiyi zaten verir.
- **Esnek istekleri zorunlu yapmak:** Ör. "sınıfta hiç ara boşluk olmasın". Gerçek verilerde
  (öğretmen müsaitlikleri, kilitler) çoğu zaman çözümsüzlüğe yol açar. Kullanıcı ise hiç program
  alamaz.
- **İlk/son ders saatini tamsayı değişkenle modellemek (pencere için):** Önce bu planlanmıştı.
  `min`/`max` kısıtları gerektirir ve CP-SAT'ta boolean önek/sonek değişkenlerinden daha zayıf
  yayılım verir.

## Sonuçlar

- Okul, öncelikleri yalnızca sayıları değiştirerek ayarlar. Yeni bir esnek kural eklemek mevcut
  kodu değiştirmez (ADR 0002).
- Esnek kurallar eklendiğinde çözücü "herhangi bir uygun program" yerine en iyisini arar ve
  süre artar. Mini sette 0,1 sn'den yaklaşık 5-7 sn'ye çıktı. Büyük setlerde süre dolduğunda en
  iyi bulunan program `uygun` durumuyla döner. Bu davranış 5. alt adımdaki süre ölçümüyle
  izlenecek.
- Ağırlıkların mutlak değeri anlamsızdır, yalnızca oranları önemlidir. Kullanıcı arayüzünde
  bunları "önem düzeyi" olarak sunmak gerekebilir.

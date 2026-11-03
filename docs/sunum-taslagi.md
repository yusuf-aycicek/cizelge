# Sunum taslağı: Çizelge – Okul Ders Programı Oluşturma Sistemi

Yazılım Tasarımı ve Mimarisi dönem projesi · Yusuf Ayçiçek

12 slayt, 5-7 dakika. Her slaytta başlık, maddeler ve konulacak görsel; konuşma notları en sonda
(slayt başına süreyle). Görsellerin yolları depo köküne göredir; diyagramların hepsi A3 olarak
`docs/diyagramlar/diyagramlar.pdf` içinde de vardır.

---

## Slayt 1 · Çizelge: okullar için çakışmasız ders programı

- Yazılım Tasarımı ve Mimarisi dönem projesi
- Yusuf Ayçiçek
- Fırat Üniversitesi Teknoloji Fakültesi, Yazılım Mühendisliği

**Görsel:** `docs/ekranlar/teslim/03-cizelge-sube.png` (arka planda, soluk)

## Slayt 2 · Problem

- Haftalık program: öğretmen ve şube aynı saatte iki yerde olamaz
- Gerçek kurallar birbirine bağlı: müsaitlik, günlük sınırlar, blok dersler, boş gün
- Bir öğretmen değişince program baştan dağılmamalı
- Hedef: tek okul için değil, birçok okulun ayrı ayrı kullandığı genel bir sistem

**Görsel:** yok (dört maddeyi simgelerle göstermek yeterli)

## Slayt 3 · Ne yapıyor? (kullanıcı akışı)

- Veri girişi: öğretmen, şube, ders; seviye şablonu ve şube istisnaları; Excel'den aktarma
- Program üretme: kuyrukta, durum takibiyle; çözüm yoksa nedeni kullanıcının diliyle
- Elle düzeltme: sürükle bırak, yer değiştirme, kilit, geri alma
- Çıktı: PDF, Excel, yayın ve öğretmene girişsiz link

**Görsel:** `docs/ekranlar/teslim/02-ders-dagilimi.png` ve `docs/ekranlar/teslim/05-indir-menusu.png` yan yana

## Slayt 4 · Mimari: dört parça, bir veritabanı

- React → FastAPI → PostgreSQL; üretim Redis kuyruğu üzerinden worker'da
- Çözücü saf Python paketi: veritabanından ve web'den habersiz
- Neden ayrı worker: üretim dakikalar sürer, API diğer okulları bekletmemeli
- `docker compose up --scale worker=N` ile yatay ölçek

**Görsel:** `docs/diyagramlar/cikti/09-dagitim.png` (dağıtım diyagramı)

## Slayt 5 · Modüler monolit ve katmanlar

- Çekirdek (okul, öğretmen, şube, ders) modülleri bilmez; modüller birbirini bilmez (testle denetlenir)
- Modül çekirdeğe sözleşmeyle kaydolur; migration'lar modül başına ayrı dal
- Router → servis → depo → model; iş kuralı servis katmanında
- Neden mikroservis değil: tek veritabanı, tek geliştirici; maliyet var, kazanç yok

**Görsel:** `docs/diyagramlar/cikti/01-genel-bakis.png` (sağda küçük `12-api-katmanlari.png`)

## Slayt 6 · Okul izolasyonu: üç bağımsız katman

- ORM filtresi tek yerde: her sorguya okul koşulu, okul yalnızca oturumdan
- Bileşik yabancı anahtar: bir okulun kaydı başka okulun kaydını gösteremez
- PostgreSQL RLS: `SET LOCAL app.okul_id`; havuzdaki bağlantıda okul taşmaz (testle kanıtlı)
- Giriş: okul bilinmeden, dar kapsamlı `SECURITY DEFINER` fonksiyonlarla

**Görsel:** `docs/diyagramlar/cikti/02-cekirdek-modeller.png` (yalnızca `kiraci` ve `OkulaAitMixin` kısmı kırpılabilir)

## Slayt 7 · Çözücü ve strategy deseni

- `ProgramCozucu` arayüzü → `CpSatCozucu` (OR-Tools CP-SAT)
- Her kural ayrı sınıf: 10 zorunlu, 9 esnek; yeni kural = yeni sınıf + `@kaydet`
- Esnek kurallar ağırlıklı ceza; sınıf boşluğu (30) her şeyden baskın
- Bağımsız doğrulayıcı ve kalite ölçümü çözücünün kodunu kullanmaz

**Görsel:** `docs/diyagramlar/cikti/06-cozucu.png`

## Slayt 8 · Çözüm yoksa: ön kontrol ve çelişki analizi

- Ön kontrol saniyenin altında: "9-A'nın 40 saat dersi var, öğretmenlerinin gelebildiği 39 saat"
- Ön kontrol yetmezse en küçük çelişen kural kümesi, kullanıcının diliyle
- Süre yetmezse "süre yetmedi", tek tıkla daha uzun deneme
- En az değişiklikle güncelleme: temel programdan her sapma ceza

**Görsel:** `docs/ekranlar/teslim/07-on-kontrol.png`

## Slayt 9 · Veri modeli ve nesne görünümü

- 18 tablo; her (şube, ders) için tek ders ataması
- Kural ve özel ayar tek tabloda: en özel kapsam kazanır (ders + şube > ders > şube > okul)
- "9-A Felsefe almaz": şablon yeniden uygulansa da korunur
- Kurallar veritabanında da: CHECK, kısmi benzersiz indeks ("okulda tek etkin üretim")

**Görsel:** `docs/diyagramlar/cikti/11-alan-modeli.png` ve `docs/diyagramlar/cikti/07-nesne-veri-girisi.png`

## Slayt 10 · Ölçüme dayalı kararlar

- Süre sınırı 120 sn: iki sette sınıf boşluğunu her tohumda sıfırlayan en kısa süre
- İki aşamalı çözüm: büyük sette ilk program 9-12 sn → 4-5 sn
- ADR 0024: günlere yayılım açıkken öğretmen konforu bozuldu (eski ölçüler 69 → 156) → okul genelinde kapalı
- ADR 0025: "günde en az ders" kapatılınca 123 → 69, K6 öncesine döndü

**Görsel:** rapordaki bölüm 9.3 tablosu (beş satır); sütun grafiği olarak da çizilebilir: "eski ölçüler" 69 / 156 / 123 / 98 / 69

## Slayt 11 · Test stratejisi

- Çözücü, API (gerçek PostgreSQL), arayüz bileşen testleri; tarayıcıda uçtan uca (masaüstü + telefon)
- İzolasyon ve bağlantı havuzu taşma testleri; mutasyon denemesi kritik yerlerde
- Diyagram-kod tutarlılık testi: diyagramdaki her ad kodda var mı?
- Kontrast (WCAG 2.2) ve taşma denetimi; başarı çıkış koduyla denetlenir

**Görsel:** test sayıları tablosu (rapor bölüm 8)

## Slayt 12 · Sınırlar ve gelecek

- Optimal değil "uygun" çözüm: ağırlıkla ayarlanan ödünleşim
- Sentetik veri; gerçek okul verisiyle ölçüm sırada
- Gelecek: ders notları modülü, dönem/yıl, öğretmen hesapları, mekan kısıtları
- Teşekkürler · sorular

**Görsel:** `docs/ekranlar/teslim/04-cizelge-ogretmen.png`

---

## Konuşma notları (yaklaşık 6 dakika)

**Slayt 1 (15 sn).** Merhaba. Projem Çizelge: okullar için haftalık ders programını otomatik
üreten, birden fazla okulun aynı anda kullanabildiği bir web uygulaması.

**Slayt 2 (30 sn).** Ders programı basit görünüyor ama kurallar birbirine bağlı. Bir öğretmen aynı
saatte iki sınıfta olamaz; başka okulda da görevli öğretmen bazı günler gelemez; iki saatlik
dersler art arda olmalı; sınıfın gün ortasında boş saati kalmamalı. Üstelik bir öğretmen değişince
bütün program baştan dağılmamalı. Hedefim tek bir okul değil, okuldan okula değişen her şeyin
ayarlanabildiği genel bir sistemdi.

**Slayt 3 (30 sn).** Yönetici öğretmenleri, şubeleri ve dersleri girer; seviye şablonuyla dersleri
bir kez tanımlayıp bütün şubelere uygular. Programı üretir, sonucu şube ve öğretmen bazında görür,
sürükleyip bırakarak düzeltir, yayımlar; PDF ve Excel alır, öğretmenlere girişsiz bir link gönderir.

**Slayt 4 (40 sn).** Mimaride dört parça var. Tasarımın merkezindeki gözlem şu: program üretmek
dakikalar sürer ve işlemciyi tüketir, diğer bütün istekler milisaniyeler sürer. Bu yüzden çözücü
API'de değil, kuyruktan iş alan ayrı bir worker'da çalışır. Dönem başında birçok okul aynı anda
program üretirse istekler sıraya girer, worker sayısı artırılır. Çözücü de veritabanından habersiz
saf bir Python paketi; komut satırından ve testlerden aynı girdiyle çalışıyor.

**Slayt 5 (35 sn).** API bir modüler monolit. Çekirdek okul, öğretmen, şube ve dersi tutar; ders
programı bir modül. Çekirdek modülü bilmez, modül çekirdeğe bir sözleşmeyle kaydolur; bu kuralı bir
test denetliyor. Mikroservisleri değerlendirdim, ama tek veritabanı ve tek geliştiricili bir
sistemde ağ çağrılarının ve dağıtık işlemin maliyeti var, kazancı yok.

**Slayt 6 (40 sn).** Çok kiracılı sistemde en büyük risk, bir okulun başka okulun verisini görmesi.
Bunu üç bağımsız katmanda engelledim: ORM her sorguya okul koşulunu tek yerden ekliyor; bileşik
yabancı anahtarlar okullar arası ilişkiyi veritabanında imkânsız kılıyor; PostgreSQL satır düzeyi
güvenliği de son savunma hattı. Bağlantı havuzunda aynı bağlantı farklı okullar için
kullanıldığında okul bilgisinin taşmadığını bir testle kanıtladım.

**Slayt 7 (40 sn).** Çözücü OR-Tools'un CP-SAT'ı. Her kural ayrı bir sınıf; strategy deseni. Bugün
on zorunlu, dokuz esnek kural var ve sonradan eklenenlerin her biri yeni bir sınıf ve tek bir kayıt
satırıydı, çözücü sınıfına dokunmadan. Esnek kurallar ağırlıklı ceza; sınıf boşluğu hepsinden
baskın. Çözücünün sonucunu, çözücünün kodunu kullanmayan bağımsız bir doğrulayıcı denetliyor.

**Slayt 8 (30 sn).** Çözüm yoksa "çözüm yok" demek yetmez. Ön kontrol en sık hataları saniyenin
altında, adlarla söylüyor. Yetmezse çözücü çelişen en küçük kural grubunu buluyor. Bir öğretmen
değişirse eski programı temel alıp, ondan her sapmayı cezalandırarak yeniden üretiyoruz.

**Slayt 9 (30 sn).** Veri modelinde temel kural "bir şube, bir ders, bir öğretmen" ve bu bir
benzersizlik kısıtı. Okul geneli kurallar ve derse, şubeye, öğretmene özel ayarlar aynı tabloda;
en özel kapsam kazanıyor. Nesne diyagramında "9-A Felsefe almaz" istisnasını görüyorsunuz.

**Slayt 10 (50 sn).** Kararları ölçümle verdim, her ölçüm üç tohumla. 120 saniyelik süre sınırı,
iki sette de sınıf boşluğunu her seferinde sıfırlayan en kısa süre. İki aşamalı çözüm büyük okulda
ilk programı yarı sürede veriyor. En ilginç sonuç şu: iki makul görünen kuralı varsayılan olarak
açtığımda öğretmen konforu ölçüsü 69'dan 156'ya kötüleşti. Günlere yayılımı kapatınca 123'e, "günde
en az ders"i kapatınca yeniden 69'a döndü. Kuralları silmedim, isteyen okul açabilir; ama varsayılanı
ölçüm belirledi.

**Slayt 11 (35 sn).** Test tarafında çözücü, gerçek PostgreSQL'e karşı API ve arayüz testleri,
tarayıcıda masaüstü ve telefon boyutunda uçtan uca test var. Kritik yerlerde mutasyon denemesi
yaptım: kodu bilerek bozup testlerin yakaladığını gördüm, kaçanlar için test ekledim. Diyagramlar
da test ediliyor: diyagramdaki her sınıf ve alan adı kodda yoksa test kırılıyor.

**Slayt 12 (25 sn).** Sınırlar: çözücü optimal değil, iyi bir çözüm veriyor; veriler sentetik.
Mimari yeni modüllere hazır: ders notları, dönem yönetimi, öğretmen hesapları. Teşekkürler,
sorularınızı alabilirim.

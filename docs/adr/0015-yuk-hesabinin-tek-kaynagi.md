# ADR 0015: Öğretmen ve sınıf yükü hesabının tek kaynağı

Durum: Kabul edildi (2026-10-16).

## Bağlam

Ders dağılımı ekranı erken uyarı göstermeli:
- müsaitliği ve günlük ders sınırıyla birlikte kapasitesini aşan öğretmen;
- toplam ders saati haftalık kapasiteyi aşan şube;
- öğretmeni seçilmemiş atamalar.

Aynı kurallar program üretiminin ön kontrolünde (`cozucu/on_kontrol.py`) zaten vardır. Kullanıcı ön
kontrolde bu hatayı alır ve üretim başlamaz.

Arayüz planı (docs/arayuz-plani.md bölüm 2.6) hesabı arayüzde, listelerden yapmayı öneriyordu. Aynı
sonucu verdiğini de ortak bir örnek dosyayla iki tarafta test etmeyi. Kullanıcı 5.4'te açıkça
istedi: hesap ön kontrolle aynı kaynaktan yapılsın, iki yerde ayrı ayrı yazılmasın.

Kuralın ince noktaları iki ayrı gerçeklemede kolayca ayrışır:
- "tercih etmez" müsait sayılır;
- aynı hücre için iki kayıt bir kez sayılır;
- her gün ayrı ayrı `min(müsait saat, M)` alınır;
- M zorunlu değilse gün uzunluğu kabul edilir;
- M gün uzunluğundan büyükse gün uzunluğu geçerlidir.

Ayrışırsa arayüz "sorun yok" der, üretim reddedilir. Ya da tersi olur.

## Karar

- **Hesap çözücü paketinde, tek yerde:** `cozucu/yuk.py`. `YukHesabi` günlük sınırları, müsait
  saatleri, öğretmen ve sınıf yüklerini (`OgretmenYuku`, `SinifYuku`) ve aşım mesajlarını üretir.
  Paket saf Python kalır: veritabanı ve web bilgisi yoktur.
- **Ön kontrol bu modülü kullanır.** `ogretmen_kapasitesi` ve `sinif_kapasitesi` kontrolleri artık
  yalnızca `YukHesabi`'nin aşımlarını `Celiski`'ye çevirir. Diğer kontroller (ders-gün kapasitesi,
  sınıf müsaitliği) de günlük sınırları ve müsait saatleri oradan alır.
- **API bir özet ucu sunar:** `GET /api/ders-programi/dagilim-ozeti`. Ucun yaptıkları:
  - okulun verisini çözücü girdisine çevirir; bunu program üretimiyle aynı dönüştürücü yapar
    (`cozum_girdisi_olustur`);
  - `YukHesabi`'ni çalıştırır;
  - her öğretmen ve şube için ders saati, kapasite, aşım ve ön kontrolün mesajını döner;
  - öğretmensiz atama sayısını döner.
- **Arayüz hesap yapmaz,** yalnızca gösterir. Atama değiştikçe özet sorgusu tazelenir. Ana sayfanın
  kontrol listesi (5.6) "N dersin öğretmeni seçilmedi" sayısını aynı uçtan alır.
- **Toplu öğretmen atama** (`POST /atamalar/toplu-ogretmen`) aynı ekranın ihtiyacıdır ve tek işlemde
  yapılır: atamalardan biri bu okulda yoksa hiçbiri değişmez. Arayüzden tek tek `PATCH`
  gönderilseydi yarıda kesilen bir istek kısmi bir durum bırakırdı.

## Değerlendirilen alternatifler

- **Hesabı arayüzde (TypeScript) yeniden yazmak, ortak örnek dosyayla iki tarafı test etmek:** ağ
  isteği olmadan anında güncellenir. Ama aynı kural iki dilde iki kez yazılır. Test yalnızca
  örnek dosyadaki durumları yakalar; ön kontrole eklenen yeni bir ayrıntı arayüze kendiliğinden
  geçmez.
- **Ön kontrolün tamamını çalıştırıp sonucunu döndürmek:** mesajlar aynı olurdu, ama sorunsuz
  öğretmenlerin sayıları (çubuk göstergesi için "18/24 saat") ön kontrolden çıkmaz. Sayılar için yine
  ayrı bir hesap gerekirdi.
- **Hesabı API'de (veritabanı sorgusuyla) yazmak:** çözücü paketinden bağımsız ikinci bir gerçekleme
  olurdu; asıl sorun (iki kaynak) sürerdi.

## Sonuçlar

- Bir kural değişirse (ör. "tercih etmez" de kapasiteden düşülsün) tek yerde değişir; arayüz ve ön
  kontrol birlikte değişir.
- Her atama değişikliğinden sonra arayüz özeti yeniden ister. Veri küçüktür (bir okul). Ölçülen
  süreler:
  - hesabın kendisi gerçekçi sette (42 öğretmen, 24 şube) 0,3 ms, büyük sette (75 öğretmen, 40
    şube) 0,5 ms;
  - yanıt süresini asıl belirleyen, okulun verisinin veritabanından okunmasıdır.
- Testler:
  - `cozucu/tests/test_yuk.py`: hesap kuralları, ön kontrolün aynı mesajları verdiği;
  - `api/tests/test_dagilim.py`: gerçek veritabanıyla özetin mesajlarının ön kontrolün kapasite
    sorunlarıyla birebir aynı olduğu, okul izolasyonu, toplu atamanın hepsi-ya-da-hiçbiri olduğu.

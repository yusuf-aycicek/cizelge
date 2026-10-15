# ADR 0011: Program üretimi: kuyruk ve worker

Durum: Kabul edildi (2026-10-15). Ayrıntılı plan: `docs/kuyruk-plani.md`.

## Bağlam

Program üretmek saniyelerden dakikalara sürer ve işlemciyi tüketir. Varsayılan süre 120 sn'dir;
çözüm bulunamazsa ikinci bir kontrol ve çelişki analizi de çalışır. CLAUDE.md'nin 1. ve 2. mimari
kararları bu yüzden çözücüyü API'nin dışına ve bir kuyruğun arkasına koyar. Bu ADR, bu kararın
nasıl uygulandığını kaydeder. Açık sorular şunlardır:

- iş nerede tanımlanır;
- bir iş iki kez çalışırsa ne olur;
- worker çökerse ne olur;
- okul izolasyonu worker'da nasıl korunur.

## Karar

1. **Redis + RQ.** API, işi (`okul_id`, `program_id`) Redis'teki bir RQ kuyruğuna koyar. Worker
   kuyruktan alır ve çalıştırır. İş yalnızca kimlikleri taşır. Asıl veri her zaman PostgreSQL'den
   okunur, kuyrukta okul verisi durmaz.
2. **İş fonksiyonu modüldedir** (`okulapi.moduller.ders_programi.uretim`). `/worker` genel bir
   çalıştırıcıdır:
   - ayarlar, veritabanı motoru, günlük ve RQ worker'ını başlatmaktan sorumludur;
   - hiçbir modülü bilmez;
   - böylece modül kuralları tek pakette kalır ve yeni bir modülün arka plan işi worker'ı
     değiştirmeyi gerektirmez (ADR 0008'deki kuralın worker'a uzantısı).
3. **Kuyruk bir arayüzün arkasındadır** (`IsKuyrugu`, çekirdekte). RQ gerçeklemesi üretimde,
   bellek içi gerçekleme testlerde kullanılır. Testlerin çoğu Redis'siz çalışır.
4. **Önce commit, sonra kuyruk.** Program satırı (`bekliyor`) commit edildikten sonra iş kuyruğa
   konur. Kuyruğa ekleme başarısız olursa program `basarisiz` yapılır, API 503 döner.
5. **İdempotent başlatma.** Worker program satırını `SELECT ... FOR UPDATE` ile kilitler.
   - Durum `bekliyor` değilse hiçbir şey yapmaz.
   - `bekliyor` ise `uretiliyor` yapar ve `baslama` zamanını yazar.
   - Aynı iş iki kez gelirse (yeniden deneme, iki worker) ikincisi boşa döner.
6. **Çözüm sırasında bağlantı açık tutulmaz.** Yazmadan önce girdi yeniden üretilir ve özeti
   (`girdi_ozeti`) karşılaştırılır. Çözüm sürerken veri değiştiyse eski veriyle üretilmiş program
   yazılmaz, `basarisiz` olur.
7. **Okul başına bir etkin üretim.** `bekliyor` ya da `uretiliyor` programı olan okul yeni üretim
   isteyemez (409).
8. **Takılı üretimin temizliği.** `uretiliyor` durumunda ve `baslama + iş süresi sınırı` geçmiş
   program `basarisiz` ("üretim yarıda kaldı") yapılır. Temizlik iki yerde yapılır:
   - program okunurken;
   - yeni üretim isteği geldiğinde, 7. maddedeki kontrolden **önce**. Yoksa çökmüş bir worker'ın
     bıraktığı program okulun yeni üretim yapmasını kalıcı olarak engellerdi.
   RQ'nun başarısızlık geri çağrısı, worker süreci ayakta kaldığı durumlarda (istisna, zaman aşımı)
   aynı işi hemen yapar.
9. **İş süresi sınırı** `2 × sure_siniri_sn + 120 sn`'dir. Ana çözüm, zorunlu kısıtlarla ikinci
   kontrol ve çelişki analizi aynı işte çalışır.
10. **Okul izolasyonu worker'da da geçerlidir.** Worker uygulama rolüyle (RLS) bağlanır ve işteki
    `okul_id` ile `okul_oturumu` açar. Başka okulun programını kimliğiyle bile bulamaz.
11. **Durum tutarlılığı veritabanında da korunur** (migration `ders_programi_0004`, CHECK
    kısıtları):
    - `uretiliyor` ve `hazir` programın başlama zamanı vardır;
    - `hazir` programın çözüm durumu `optimal` ya da `uygun`'dur;
    - biten programın bitiş zamanı vardır.

## Değerlendirilen alternatifler

- **Celery:** daha çok özelliği var (zamanlanmış görevler, iş akışları), ama bu iş tek tür ve basit.
  RQ'nun yapılandırması çok daha az, kavramları ders sunumunda anlatılabilir ölçüde.
- **PostgreSQL'i kuyruk olarak kullanmak** (`SELECT ... FOR UPDATE SKIP LOCKED`): ek bir parça
  (Redis) gerektirmez. İş ile program satırı aynı işlemde yazıldığı için "commit edildi ama
  kuyruğa girmedi" durumu da olmaz. Bu ölçek için ciddi bir seçenekti. CLAUDE.md Redis + RQ'yu
  seçmişti. Kuyruğu ayrı bir parça olarak göstermek mimari dersinde de daha açık. `IsKuyrugu`
  arayüzü sayesinde ileride bu gerçeklemeye geçmek yalnızca yeni bir sınıf demektir.
- **Outbox deseni** (işi önce veritabanındaki bir tabloya yazıp oradan kuyruğa aktarmak): 4.
  maddedeki "commit edildi, kuyruğa eklenemedi" boşluğunu tamamen kapatır. Ama ayrı bir aktarıcı
  süreç gerektirir. Bu boşluk 4. ve 8. maddelerle zaten kapanıyor: program ya `basarisiz` olur ya
  da zaman aşımıyla temizlenir.
- **İş mantığını `/worker` içine koymak:** modülün kuralları iki pakete dağılırdı ve API, işi
  kuyruğa koyarken worker'ı bilmek zorunda kalırdı.
- **Takılı üretimi worker açılışında taramak:** worker RLS'ye tabi rolle bağlandığı için bütün
  okulların programlarını göremez. Sahip rolüyle bağlanmak ise izolasyonu delerdi.
- **WebSocket ile durum bildirimi:** CLAUDE.md 6. karar. Sorgulama (polling) bu ölçekte yeterli.

## Sonuçlar

- API çözücüyü hiç çalıştırmaz. Çok sayıda üretim isteği yalnızca kuyruğu uzatır, API'yi
  yavaşlatmaz. Gerekirse worker sayısı artırılır, 5. madde sayesinde aynı iş iki kez yapılmaz.
- RQ'nun worker'ı `fork` kullanır, Windows'ta çalışmaz. Worker yalnızca Linux konteynerinde
  çalışır. Bilgisayardaki testler iş fonksiyonunu doğrudan çağırır. Gerçek RQ ve Redis'i
  uçtan uca kabul testi sınar.
- Program tablosu artık üretim sonucunu da taşır: `cozum_durumu`, `toplam_ceza`, `olcumler`,
  `celiskiler`, `sure_sn`, `girdi_ozeti`. Girdi özeti, yapım sırası 8'de "eski veriyle üretildi"
  uyarısında da kullanılacak (docs/api-plani.md bölüm 15).
- Kapsam dışı: üretimi iptal etme, okul başına adil sıralama.

# ADR 0011: Program üretimi: kuyruk ve worker

Durum: Kabul edildi (2026-10-15); 4, 7 ve 8. maddeler aynı gün güncellendi (öksüz program
kararı, aşağıda). Ayrıntılı plan: `docs/kuyruk-plani.md`.

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
3. **Kuyruk bir arayüzün arkasındadır** (`IsKuyrugu`, `okulapi/cekirdek/kuyruk.py`):
   - `kuyruga_ekle(is_id, fonksiyon, argumanlar, zaman_asimi_sn, basarisizlikta)`;
   - `kuyrukta_mi(is_id)`: iş sırada bekliyor, çalışıyor ya da yeniden denenecek mi.

   RQ gerçeklemesi (`RqKuyrugu`) üretimde, bellek içi gerçekleme (`BellekKuyrugu`) testlerde
   kullanılır; ikisi de aynı soruyu yanıtlar. RQ ve Redis'i yalnızca `kuyruk.py` içe aktarır, bunu
   bir mimari testi denetler. Üretim kodu RQ'yu bilmez. RQ'ya özgü başarısızlık geri çağrısı da
   (`on_failure(job, connection, type, value, traceback)`) orada kuyruktan bağımsız bir çağrıya
   çevrilir: `f(**argumanlar, zaman_asimi=...)`.
4. **İşin kimliği program kimliğidir. Sıra: önce kuyruk, sonra commit.**
   - Program satırı eklenir (henüz commit edilmemiş, başka işlemler görmez), iş program
     kimliğiyle kuyruğa konur, sonra commit edilir.
   - Kuyruğa ekleme başarısız olursa program **aynı istekte** `basarisiz` ("kuyruğa ulaşılamadı")
     yapılıp commit edilir ve API 503 döner. Program `bekliyor`da kalıp okulu engellemez.
   - Neden bu sıra: 8. maddedeki öksüz program kuralı "bekliyor ama işi kuyrukta yok" durumuna
     bakar. Ters sırada (commit, sonra kuyruk) iki adım arasındaki anda gelen bir okuma isteği
     meşru bir programı öksüz sayıp iptal ederdi. Bu sırada temizlik, işi henüz kuyrukta olmayan
     bir programı hiç göremez (testle kanıtlandı).
   - Bedeli: worker işi API commit etmeden alabilir ve programı bulamaz. Worker bu yüzden programı
     kısa aralıklarla birkaç kez daha arar (toplam ~4 sn); bulamazsa iş hiçbir şey yapmadan biter.
5. **İdempotent başlatma.** Worker program satırını `SELECT ... FOR UPDATE` ile kilitler.
   - Durum `bekliyor` değilse hiçbir şey yapmaz.
   - `bekliyor` ise `uretiliyor` yapar ve `baslama` zamanını yazar.
   - Aynı iş iki kez gelirse (yeniden deneme, iki worker) ikincisi boşa döner.
6. **Çözüm sırasında bağlantı açık tutulmaz.** Yazmadan önce girdi yeniden üretilir ve özeti
   (`girdi_ozeti`) karşılaştırılır. Çözüm sürerken veri değiştiyse eski veriyle üretilmiş program
   yazılmaz, `basarisiz` olur.
7. **Okul başına bir etkin üretim.** `bekliyor` ya da `uretiliyor` programı olan okul yeni üretim
   isteyemez (409). Uygulama önce kendisi bakar (anlaşılır mesaj). Aynı anda gelen iki istek bu
   denetimi birlikte geçebilir; kısmi benzersiz indeks (`UNIQUE (okul_id) WHERE durum IN
   ('bekliyor', 'uretiliyor')`, migration `ders_programi_0005`) ikincisini veritabanında durdurur,
   o da 409'a çevrilir.
8. **Takılı üretimin temizliği.** İki tür takılı üretim vardır, ikisi farklı ölçütle anlaşılır:
   - **`uretiliyor` ve süresi geçmiş:** `baslama + iş süresi sınırı < now()` ise `basarisiz`
     ("üretim yarıda kaldı"). Worker başlattı ama bitiremedi (süreç öldü).
   - **`bekliyor` ve öksüz:** süreye bakılmaz, kuyruğa sorulur: `kuyrukta_mi(program_id)`. İş
     kuyrukta yoksa (hiç girmedi, kayboldu, bitti ama program başlamadı) program öksüzdür ve
     `basarisiz` yapılır. İş kuyruktaysa program gerçekten sırada bekliyordur ve dokunulmaz,
     kuyruk ne kadar uzun olursa olsun. Kuyruğa ulaşılamazsa bu adım atlanır: "bilmiyorum" diye
     program iptal edilmez. `bekliyor` satırları `FOR UPDATE SKIP LOCKED` ile alınır: o anda
     worker'ın başlatmakta olduğu (kilitlediği) programa dokunulmaz ve temizlik onu beklemez.

   Temizlik iki yerde yapılır:
   - program okunurken (liste ve tek program);
   - yeni üretim isteği geldiğinde, 7. maddedeki denetimden **önce**. Yoksa takılı bir üretim
     okulun yeni üretim yapmasını kalıcı olarak engellerdi.

   RQ'nun başarısızlık geri çağrısı, worker süreci ayakta kaldığı durumlarda (istisna, zaman aşımı)
   programı hemen kapatır.
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

- **`bekliyor` için süreye dayalı kural** (belli bir süreden eski bekleyen program takılıdır):
  kuyruk yoğunken gerçekten sırada bekleyen bir programı iptal ederdi; kısa tutulursa yanlış iptal,
  uzun tutulursa okul uzun süre engellenir. Kuyruğa sormak doğru cevabı doğrudan verir. İşin
  kimliğini program kimliği yapmak bunu ek bir eşleme tablosu olmadan mümkün kılar.
- **Önce commit, sonra kuyruk** (ilk karar): 4. maddedeki yarış yüzünden bırakıldı.

- **Celery:** daha çok özelliği var (zamanlanmış görevler, iş akışları), ama bu iş tek tür ve basit.
  RQ'nun yapılandırması çok daha az, kavramları ders sunumunda anlatılabilir ölçüde.
- **PostgreSQL'i kuyruk olarak kullanmak** (`SELECT ... FOR UPDATE SKIP LOCKED`): ek bir parça
  (Redis) gerektirmez. İş ile program satırı aynı işlemde yazıldığı için "commit edildi ama
  kuyruğa girmedi" durumu da olmaz. Bu ölçek için ciddi bir seçenekti. CLAUDE.md Redis + RQ'yu
  seçmişti. Kuyruğu ayrı bir parça olarak göstermek mimari dersinde de daha açık. `IsKuyrugu`
  arayüzü sayesinde ileride bu gerçeklemeye geçmek yalnızca yeni bir sınıf demektir.
- **Outbox deseni** (işi önce veritabanındaki bir tabloya yazıp oradan kuyruğa aktarmak):
  veritabanı ile kuyruk arasındaki tutarsızlığı tamamen kapatır, ama ayrı bir aktarıcı süreç
  gerektirir. 4. ve 8. maddelerle kalan durumlar zararsız:
  - kuyruğa eklendi ama commit başarısız oldu ya da API o anda çöktü: program hiç oluşmaz; worker
    onu bulamaz ve iş hiçbir şey yapmadan biter;
  - program commit edildi ama işi bir şekilde kayboldu: program öksüzdür, ilk okumada ya da yeni
    istekte `basarisiz` olur.
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

# Yapım sırası 3: kuyruk ve worker (plan)

Durum: **tamamlandı (2026-10-15)**. Alt adım notları bölüm 5'te.

Kabul (CLAUDE.md bölüm 8): API'den istek atılır, durum `bekliyor` → `uretiliyor` → `hazir` olarak
değişir. Tasarımın temeli `docs/api-plani.md` bölüm 14 (ters yön: sonuç → program ve yerleşim).

## 1. Akış

```
Yönetici            API                      PostgreSQL           Redis (RQ)        Worker
  | POST /programlar  |                          |                    |                 |
  |------------------>| program (bekliyor) ekle   |                    |                 |
  |                   |   (commit edilmedi)       |                    |                 |
  |                   |-- iş (kimliği = program_id) ---------------->|                 |
  |                   |-- commit --------------->|                    |                 |
  |<-- 202 + program --|                          |                    |-- iş --------->|
  |                   |                          |<-- FOR UPDATE, uretiliyor, commit --|
  | GET /programlar/{id} (birkaç sn'de bir)       |                    |   girdi, çöz    |
  |------------------>|-- okur ----------------->|                    |   (bağlantısız) |
  |<-- uretiliyor -----|                          |<-- FOR UPDATE, özet, yerleşimler,  |
  |        ...        |                          |    hazir / basarisiz, commit ------|
  |<-- hazir ----------|                          |                    |                 |
```

- **Önce kuyruk, sonra commit; işin kimliği program kimliği** (2026-10-15 kararıyla değişti; ilk
  plan "önce commit, sonra kuyruk" idi). Gerekçe ADR 0011 madde 4: öksüz program temizliği
  "bekliyor ama işi kuyrukta yok" durumuna bakar; ters sırada iki adım arasında gelen bir okuma
  meşru programı iptal ederdi. Worker işi commit'ten önce alırsa programı kısa süre yeniden arar.
- Kuyruğa ekleme başarısız olursa (Redis kapalı) program aynı istekte `basarisiz` ("kuyruğa
  ulaşılamadı") yapılır, API 503 döner.
- Worker, işteki `okul_id` ile `okul_oturumu` açar ve uygulama rolüyle (RLS) bağlanır. Başka
  okulun verisine worker da dokunamaz.
- Başlatma, çözme ve yazma adımları bölüm 14'teki gibidir: `FOR UPDATE` ile idempotent başlatma,
  çözüm boyunca açık bağlantı yok, yazmadan önce girdi özeti karşılaştırması, son bir `dogrula`
  savunması, tek işlemde yazma.

## 2. Önerilen kararlar (onayınız gerekiyor)

| # | Karar | Öneri | Alternatif ve neden seçilmedi |
|---|---|---|---|
| a | İş fonksiyonu nerede | **Modülde** (`okulapi.moduller.ders_programi.uretim`). `/worker` yalnızca genel bir çalıştırıcıdır: ayarlar, veritabanı motoru, günlük, RQ worker'ı başlatma. Hiçbir modülü bilmez. | İş mantığı `/worker` içinde: o zaman modülün kuralları iki pakete dağılır ve API, iş adını verirken worker'ı bilmek zorunda kalır. |
| b | Kilitli hücreler nereden | **Temel programdan.** Tek parametre: `temel_program_id`. Temel programdaki kilitli hücreler yeni programda da kilitli kalır. | Ayrı `kilit_programi_id`: dönüştürücü bunu destekliyor ama iki farklı programdan kilit ve temel almak kullanıcıya anlamsız. |
| c | Aynı anda kaç üretim | **Okul başına bir etkin üretim.** `bekliyor` ya da `uretiliyor` durumunda programı olan okul yenisini isterse 409. | Sınırsız: tek okul dönem başında kuyruğu doldurup diğer okulları bekletebilir. |
| d | Ön kontroller nerede | **Worker'da** (çözücünün içinde, bugünkü gibi). Hata, sonuçla aynı yoldan gelir (`basarisiz` + mesaj). | API'de eşzamanlı ön kontrol: anında 422 verirdi ama iki ayrı hata yolu olurdu, API çözücü mantığını çalıştırmaya başlardı. |
| e | Takılan üretim | **Okunurken ve yeni üretim isteğinde temizleme:** `uretiliyor` durumunda ve `baslama + iş süresi sınırı` geçmiş program `basarisiz` ("üretim yarıda kaldı") yapılır. Bu temizlik hem program okunurken hem de yeni üretim isteği geldiğinde, (c)'deki 409 kontrolünden **önce** yapılır; yoksa takılı bir üretim okulun yeni üretim yapmasını kalıcı olarak engellerdi (kullanıcı düzeltmesi, 2026-10-15). **`bekliyor` için** süreye bakılmaz, kuyruğa sorulur: işi kuyrukta olmayan program öksüzdür ve `basarisiz` olur; kuyruktaysa dokunulmaz (kullanıcı kararı, 2026-10-15; ADR 0011 madde 8). RQ'nun başarısızlık geri çağrısı da aynı şeyi hemen yapar. | Worker açılışında tarama: worker uygulama rolüyle bağlanır, RLS yüzünden bütün okulları göremez. Zamanlanmış görev: yeni bir parça gerektirir. |
| f | İş süresi sınırı (RQ `job_timeout`) | `2 × sure_siniri_sn + 120 sn`. Ana çözüm, süre dolunca zorunlu kısıtlarla ikinci kontrol ve çelişki analizi aynı işte çalışır. | Yalnızca `sure_siniri_sn`: ikinci kontrol ve çelişki analizi yarıda kesilirdi. |
| g | Redis portu | **Bilgisayara açılmaz.** Yalnızca konteynerler arası (`redis:6379`). Uçtan uca test HTTP üzerinden yapılır. | 6379'u açmak: gerek yok ve başka projelerle çakışma riski. |

## 3. Değişiklikler

**Migration `ders_programi_0004`** (0003 RLS'ye gitti). `program` tablosuna şunlar eklenir:
- `baslama`;
- `cozum_durumu` (optimal / uygun / cozumsuz / on_kontrol_hatasi / bilinmiyor);
- `toplam_ceza`;
- `olcumler` (JSONB, `kalite.olc`);
- `celiskiler` (JSONB);
- `sure_sn`;
- `girdi_ozeti`.

`durum` için CHECK kısıtı. Bölüm 14'teki "0003" ifadesi düzeltildi.

**Çekirdek:**
- `IsKuyrugu` arayüzü (`kuyruga_ekle(fonksiyon_yolu, **argumanlar, zaman_asimi)`);
- RQ gerçeklemesi;
- testler için bellek içi gerçekleme.

Çekirdek hangi işlerin olduğunu bilmez. Kuyruk FastAPI bağımlılığıyla verilir, testte değiştirilir.

**Ders programı modülü:**
- `uretim.py`:
  - `programi_uret(fabrika, okul_id, program_id, cozucu=None)`: iş fonksiyonu; adımları `baslat`, `coz`, `yaz`;
  - çözücü dışarıdan verilebilir, böylece testlerde sahte çözücü kullanılabilir (ADR 0001'deki arayüzün getirisi).
- `ProgramServisi.uret(ad, temel_program_id, sure_siniri_sn)`: program satırı, kural (c), kuyruk.
- `POST /api/ders-programi/programlar` → 202.
- `GET /programlar/{id}` yeni alanları döner ve kural (e)'yi uygular.

**`/worker`:**
- `okulworker` paketi, `python -m okulworker` ile çalışır;
- RQ `Worker`, kuyruk adı `program_uretimi`;
- imaj: API imajıyla aynı Dockerfile.

**docker-compose:**
- `redis` (`redis:7`, sağlık kontrolü);
- `worker` (aynı imaj, `depends_on: db, redis`);
- `api`'ye `OKULAPI_REDIS_URL`.

**Belgeler:**
- ADR 0011 (kuyruk ve worker: RQ, iş fonksiyonunun yeri, idempotent başlatma, okurken temizleme);
- değerlendirilen alternatifler: Celery, PostgreSQL'i kuyruk olarak kullanmak (`FOR UPDATE SKIP LOCKED`), outbox deseni;
- diyagramlar: 09'da redis ve worker artık planlanan değil, 05'e `uretim` ve kuyruk;
- README.

## 4. Testler

Çoğu test Redis'siz çalışır, bellek içi kuyruk ve sahte çözücüyle:

1. Mini set uçtan uca, gerçek çözücüyle (süre sınırı kısa): `hazir`, yerleşimler doğrulayıcıdan
   geçer, kilitli hücre yerinde.
2. Durum geçişi: sahte çözücü çözüm sırasında programı başka bir oturumdan okur. Gördüğü durum
   `uretiliyor` olmalı.
3. Aynı iş iki kez çalışır: ikincisi hiçbir şey yazmaz.
4. Çözüm sırasında atama silinir (sahte çözücü yapar): `basarisiz`, "veriler değişti", yerleşim
   yazılmaz.
5. Çözümsüz girdi: `basarisiz`, `celiskiler` ve okunur `hata_mesaji` yazılır.
6. Başka okulun program kimliğiyle iş: bulunamaz, hiçbir şey yazılmaz (RLS).
7. Temel programla güncelleme: değişen yerleşim sayısı küçük, `temel_program_id` dolu.
8. API:
   - 202 ve `bekliyor`;
   - iş doğru argümanlarla kuyrukta;
   - etkin üretim varken 409;
   - kuyruk hatasında 503 ve `basarisiz`;
   - süresi geçmiş `uretiliyor` okunurken `basarisiz` olur;
   - **takılı üretim yeni üretimi engellemez:** bir program `uretiliyor` durumunda takılı kalmış
     ve zaman aşımı geçmişken yeni üretim isteği 202 ile kabul edilir, takılı program `basarisiz`
     olur; zaman aşımı geçmemişse istek yine 409 alır.
9. **Kabul (uçtan uca, `-m uctan_uca`):** `docker compose up` ile çalışan sistemde HTTP ile mini set
   yüklenir, üretim istenir, durum sorgulanır. Gözlenen sıra `bekliyor` → `uretiliyor` → `hazir`
   olmalı. Gerçek Redis, gerçek RQ ve gerçek worker kullanılır. Sistem çalışmıyorsa test atlanır
   (nedeni yazılarak).

Risk: RQ'nun worker'ı `fork` kullanır, Windows'ta çalışmaz. Worker yalnızca Linux konteynerinde
çalışacak. Bilgisayardaki testler RQ worker'ı başlatmaz (iş fonksiyonunu doğrudan çağırır). Gerçek
RQ'yu kabul testi konteynerde sınar. API tarafında `rq` paketinin Windows'ta içe aktarılabildiği
3. alt adımda doğrulanacak; aktarılamazsa RQ gerçeklemesi yalnızca kullanıldığında içe aktarılır.

## 5. Alt adımlar

Her alt adım testler geçince commit edilir, onayınız olmadan sonrakine geçilmez.

1. **Şema ve ADR:** migration 0004, model ve şema alanları, ADR 0011.
2. **Üretim mantığı:** `uretim.py` (başlat, çöz, yaz), testler 1-7.
3. **Kuyruk ve endpoint:** `IsKuyrugu` ve RQ gerçeklemesi, `POST /programlar`, okurken temizleme,
   testler 8.
4. **Worker ve Docker:** `/worker`, redis ve worker servisleri, kabul testi 9, diyagramlar, README.

**Durum:**

| # | Alt adım | Durum |
|---|---|---|
| 1 | Şema ve ADR | Bitti (2026-10-15) |
| 2 | Üretim mantığı | Bitti (2026-10-15) |
| 3 | Kuyruk ve endpoint | Bitti (2026-10-15) |
| 4 | Worker ve Docker | Bitti (2026-10-15) |

Yapım sırası 3 tamamlandı (2026-10-15).

1. alt adımdan notlar:
- `durum` için CHECK zaten vardı. Buna ek olarak durumla alanların tutarlılığı için beş kısıt eklendi:
  `cozum_durumu` değerleri, `toplam_ceza >= 0`, `uretiliyor`/`hazir` için `baslama`, `hazir` için
  geçerli çözüm, biten program için `bitis`. Ayrıca `(okul_id, durum)` indeksi (karar c).
- Test bir hata yakaladı: `cozum_durumu IN (...)` NULL için NULL döner, CHECK de NULL'ı geçti
  sayar. Çözümü boş "hazır" program kabul ediliyordu. Koşula `IS NOT NULL` eklendi.
- Var olan bir test geçersiz bir "hazır" program oluşturuyordu (başlama ve çözüm yok). Yeni
  kısıt bunu reddetti. Test gerçekçi alanlarla düzeltildi.
- `girdi_ozeti` API yanıtında yok: iç bilgi.
- Testler: 206/206.

2. alt adımdan notlar:
- `moduller/ders_programi/uretim.py`:
  - `programi_uret` (başlat, çöz, yaz);
  - `uretimi_basarisiz_yap` (bitmemiş üretimi kapatır; 3. alt adımda RQ geri çağrısı ve kuyruk
    hatası da bunu kullanacak);
  - `takili_uretimleri_temizle` (tek UPDATE, süre program başına, veritabanı saatiyle);
  - `girdi_ozeti` (kanonik JSON'un SHA-256'sı: liste sırası özeti değiştirmez).
- Herhangi bir adımda beklenmeyen istisna olursa program `basarisiz` yapılır ve istisna yeniden
  fırlatılır. Program `uretiliyor`da kalmaz; yalnızca worker sürecinin kendisi ölürse temizlik
  gerekir.
- Yazma adımında durum yeniden denetlenir: çözüm iş süresi sınırını aşıp bu arada temizlenmiş bir
  program, geç gelen sonuçla yeniden "hazır" olmaz.
- **Bölüm 14'ten sapma:** yerleşimler Core toplu INSERT ile değil, ORM `add_all` ile ekleniyor.
  SQLAlchemy 2 bunları zaten çok değerli INSERT'lerle gönderiyor ("insertmanyvalues"). Böylece
  `okul_id`'yi de okul filtresi yazıyor, ayrı bir yol açılmıyor.
- Testler (`tests/test_uretim.py`, 19):
  - plandaki 1-7 numaralı testler;
  - iki worker'ın aynı anda aynı işi alması (gerçek commit, iki iş parçacığı);
  - çözücü istisnası;
  - doğrulayıcı savunması;
  - temizlenmiş programa geç gelen sonuç;
  - temizliğin yalnızca süresi geçenleri ve yalnızca kendi okulunu etkilemesi.
- Mutasyon denemesi: altı bozma denendi (FOR UPDATE yok, başlatmada gevşek durum denetimi, özet
  karşılaştırması yok, yazmada durum denetimi yok, temizlikte süre sınırı yok, doğrulayıcı yok).
  Hepsini en az bir test yakaladı.
- Takılı üretim düzeltmesinin API testi (zaman aşımı geçmiş `uretiliyor` varken yeni istek 202
  alır) 3. alt adımda, endpoint ile birlikte (bölüm 4, madde 8). Temizliğin kendisi burada test
  edildi.
- Testler: 225/225.

3. alt adımdan notlar:
- Öksüz `bekliyor` program kararı (kullanıcı, 2026-10-15) uygulandı:
  - işin kimliği program kimliği;
  - `IsKuyrugu.kuyrukta_mi`, RQ'da iş durumuna bakar (queued, started, deferred, scheduled:
    kuyrukta);
  - temizlik `bekliyor` programlar için kuyruğa sorar, süreye bakmaz.
- Bu karar sırayı değiştirdi: **önce kuyruk, sonra commit** (ADR 0011 madde 4). Sıra testle
  kanıtlandı: eski sıraya dönen mutasyonu bir test yakalıyor.
- Kuyruk hatasında program aynı istekte `basarisiz` olur, 503 döner. Gerçek konteynerde Redis
  yokken de denendi.
- Plana ek: **kısmi benzersiz indeks** (migration `ders_programi_0005`): okul başına tek etkin
  üretim, aynı anda gelen iki istekte de veritabanında korunur.
- `okulapi/cekirdek/kuyruk.py`: `IsKuyrugu`, `RqKuyrugu`, `BellekKuyrugu`, `KuyrukHatasi`.
  - RQ'nun on_failure imzası kuyruktan bağımsız bir çağrıya çevrilir.
  - RQ ve Redis'i yalnızca bu dosya içe aktarır (mimari testi).
  - RQ Windows'ta içe aktarılabiliyor; RQ gerçeklemesi fakeredis ile bilgisayarda test
    ediliyor (plandaki risk maddesi böylece daraldı).
- `okulapi/cekirdek/isci.py`: worker sürecinin oturum fabrikası. Tembel kurulur: RQ'nun `fork`
  ettiği alt süreçte açılır.
- `uretim.py`'ye eklenenler:
  - kuyruk giriş noktaları `uretim_isi` ve `uretim_basarisiz_oldu`;
  - programı bulamayınca kısa süre yeniden arama.
- Endpoint'ler:
  - `POST /api/ders-programi/programlar` → 202 + `Location`; 409 (etkin üretim var), 422 (temel
    program hazır değil), 404 (temel program başka okulun), 503 (kuyruk yok);
  - GET'ler temizliği çalıştırır.
- Mutasyon denemesi: dokuz bozma denendi, hepsini en az bir test yakaladı:
  - 409 denetimi temizlikten önce;
  - yeni istekte temizlik yok;
  - eski sıra;
  - kuyruk hatasında program kapatılmaz;
  - benzersizlik hatası 409'a çevrilmez;
  - kuyruğa sorulmaz;
  - ulaşılamazken öksüz sayılır;
  - süreye dayalı kural;
  - worker yeniden aramaz.
- Testler: 269/269 (test_kuyruk 17, test_program_uretimi 19, test_uretim 27).

3\. alt adımdan sonra iki doğrulama (kullanıcı isteği, 2026-10-15), test olarak:
- Kuyruğa eklenip commit edilemeyen programın işi: gerçek RQ worker kodu (fakeredis üzerinde
  SimpleWorker) işi alır. Programı ~4 sn arar, bulamaz, sessizce biter. Sonuç: iş `finished`,
  başarısız işler kaydı boş, yeniden deneme yok.
- Eşzamanlı iki istekte kuyruğa ekleme bir kez çağrılır. Benzersizlik ihlali flush'ta, yani
  kuyruktan önce alınır.
- İkisi de mutasyonla denendi: flush kaldırılınca ve bulunamayan programda istisna
  fırlatılınca testler kırılıyor.

4. alt adımdan notlar:
- `/worker` (`okulworker`): `python -m okulworker`. Günlük, ayarlar ve modül listesini açılışta
  denetler, sonra `cekirdek.kuyruk.rq_worker_calistir`'ı çağırır. RQ yine yalnızca
  `cekirdek/kuyruk.py`'de. Worker hiçbir modülü içe aktarmaz.
- `docker-compose.yml`:
  - `redis` (redis:7.4, sağlık kontrolü, port açılmaz);
  - `worker` (api imajı, api sağlıklı olunca başlar);
  - api Redis'i bekler.
  - Redis'in kalıcı birimi yok: kaybolan işlerin programları öksüz olarak kapanır.
- Kabul testi `tests/test_kabul_uctan_uca.py` (`-m uctan_uca`, varsayılan çalıştırmada yok):
  - gerçek sistemde HTTP ile mini set yüklenir, program istenir, durum 20 ms aralıkla izlenir;
  - beş çalıştırmanın beşinde de `bekliyor → uretiliyor → hazir` görüldü (çözüm ~0,2 sn);
  - 71 yerleşim, sınıf boşluğu 0;
  - test sonunda 9-A'nın haftalık çizelgesini yazdırır.
- Diyagramlar:
  - 01: worker gerçek paket; Redis eklendi;
  - 03: `HizmetKullanilamiyor`;
  - 05: `uretim`, `IsKuyrugu` ve gerçeklemeleri, `ProgramServisi.uret`;
  - 09: redis ve worker konteynerleri; yalnızca web planlanan.
  - Diyagram denetleyicisi `self.a, self.b = ...` atamasını tanımıyordu; AST'ye geçirildi.
- README: servisler, program üretme akışı, kabul testi.
- Testler: api 279 (+1 kabul testi, ayrıca çalıştırılır), çözücü 137.

## 6. Kapsam dışı (bu adımda)

- Üretimi iptal etme.
- Kuyruk önceliği ve okul başına adil sıralama.
- Birden çok worker ile yük ölçümü. Tasarım buna engel değil, ölçüm yapılmayacak.

# Yapım sırası 3: kuyruk ve worker (plan)

Durum: **onaylandı (2026-10-15)**, (e) kullanıcı düzeltmesiyle. Alt adım durumu bölüm 5'te.

Kabul (CLAUDE.md bölüm 8): API'den istek atılır, durum `bekliyor` → `uretiliyor` → `hazir` olarak
değişir. Tasarımın temeli `docs/api-plani.md` bölüm 14 (ters yön: sonuç → program ve yerleşim).

## 1. Akış

```
Yönetici            API                      PostgreSQL           Redis (RQ)        Worker
  | POST /programlar  |                          |                    |                 |
  |------------------>| program (bekliyor) ekle   |                    |                 |
  |                   |-- commit --------------->|                    |                 |
  |                   |-- iş: (okul_id, program_id) ---------------->|                 |
  |<-- 202 + program --|                          |                    |-- iş --------->|
  |                   |                          |<-- FOR UPDATE, uretiliyor, commit --|
  | GET /programlar/{id} (birkaç sn'de bir)       |                    |   girdi, çöz    |
  |------------------>|-- okur ----------------->|                    |   (bağlantısız) |
  |<-- uretiliyor -----|                          |<-- FOR UPDATE, özet, yerleşimler,  |
  |        ...        |                          |    hazir / basarisiz, commit ------|
  |<-- hazir ----------|                          |                    |                 |
```

- **Önce commit, sonra kuyruk.** İş kuyruğa program satırı commit edildikten sonra konur. Tersi
  olsaydı worker henüz görünmeyen bir programı arayabilirdi.
- Kuyruğa ekleme başarısız olursa (Redis kapalı) program `basarisiz` ("kuyruğa ulaşılamadı")
  yapılır, API 503 döner.
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
| e | Takılan üretim | **Okunurken ve yeni üretim isteğinde temizleme:** `uretiliyor` durumunda ve `baslama + iş süresi sınırı` geçmiş program `basarisiz` ("üretim yarıda kaldı") yapılır. Bu temizlik hem program okunurken hem de yeni üretim isteği geldiğinde, (c)'deki 409 kontrolünden **önce** yapılır; yoksa takılı bir üretim okulun yeni üretim yapmasını kalıcı olarak engellerdi (kullanıcı düzeltmesi, 2026-10-15). RQ'nun başarısızlık geri çağrısı da aynı şeyi hemen yapar. | Worker açılışında tarama: worker uygulama rolüyle bağlanır, RLS yüzünden bütün okulları göremez. Zamanlanmış görev: yeni bir parça gerektirir. |
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

`durum` için CHECK kısıtı. Bölüm 14'teki "0003" ifadesi düzeltilecek.

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
| 1 | Şema ve ADR | **Sıradaki** |
| 2 | Üretim mantığı | |
| 3 | Kuyruk ve endpoint | |
| 4 | Worker ve Docker | |

## 6. Kapsam dışı (bu adımda)

- Üretimi iptal etme.
- Kuyruk önceliği ve okul başına adil sıralama.
- Birden çok worker ile yük ölçümü. Tasarım buna engel değil, ölçüm yapılmayacak.

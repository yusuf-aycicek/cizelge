# Veritabanı ve API planı (Yapım sırası, 2. adım)

Durum: **onaylandı (2026-10-14).** Alt adımların durumu bölüm 9'da.

Kaynak: CLAUDE.md bölüm 4, 6, 8. **Kabul kriterleri:** iki okul oluşturulur, biri diğerinin
verisine erişemez (testle kanıtlanır); bağlantı havuzunda aynı bağlantı art arda farklı okullar
için kullanıldığında okul bilgisi bir istekten diğerine taşmaz (testle kanıtlanır).

## 1. Hedefler

1. Docker Compose ile PostgreSQL + API tek komutla ayağa kalkar.
2. Tablolar Alembic migration'larıyla oluşur. Elle `CREATE TABLE` yapılmaz.
3. Okul izolasyonu tek bir yerde, veri erişim katmanında uygulanır. Ayrıca veritabanı da
   okullar arası ilişkiyi reddeder.
4. Çekirdek (okul, kullanıcı, öğretmen, sınıf, ders) ile ders programı modülü ayrıdır. İleride
   eklenecek modüller (ör. ders notları ve dosya paylaşımı, kütüphane) çekirdeği değiştirmeden
   eklenebilir.
5. Temel CRUD endpoint'leri.
6. Sınıflar ve sorumluluklar, dersin istediği class, object ve deployment diyagramlarına
   doğrudan dökülebilecek kadar net ayrılır.

Kapsam dışı (sonraki adımlar): program üretme isteği ve worker (3), kimlik doğrulama (4), arayüz
(5-7), seviye şablonunun şubelere uygulanması (5), Excel içe aktarma (8).

## 2. Mimari: modüler monolit

API tek bir süreçtir (tek dağıtım birimi). İçeride ise **çekirdek** ve **modüller** diye ayrılır.

```
api/
  pyproject.toml
  alembic.ini
  src/okulapi/
    main.py                  uygulama fabrikası: çekirdeği kurar, modülleri kaydeder
    ayarlar.py               ortam değişkenlerinden ayarlar (veritabanı adresi, etkin modüller)
    cekirdek/                ÇEKİRDEK: her modülün ihtiyaç duyduğu ortak varlıklar
      veritabani.py          motor (engine), oturum (session), Base, OkulaAitMixin
      kiraci.py              istek bağlamındaki okul (KiraciBaglami) + otomatik okul filtresi
      modul.py               Modul sözleşmesi ve ModulKayitDefteri
      depo.py                OkulaAitDepo: CRUD tabanı (her sorgu okula göre süzülür)
      modeller.py            Okul, Kullanici, Ogretmen, Sinif, Ders (SQLAlchemy)
      semalar.py             Pydantic istek/yanıt şemaları
      servisler.py           OkulServisi, OgretmenServisi, SinifServisi, DersServisi
      api.py                 /api/okullar, /api/ogretmenler, /api/siniflar, /api/dersler
      migrations/            çekirdeğin Alembic dalı (branch label: cekirdek)
    moduller/
      ders_programi/         MODÜL: ders programı
        __init__.py          MODUL = Modul(ad="ders_programi", ...)
        modeller.py          SeviyeSablonu, DersAtama, Musaitlik, Kisit, Program, Yerlesim
        semalar.py, servisler.py, api.py   (/api/ders-programi/...)
        migrations/          modülün Alembic dalı (cekirdek dalına bağımlı)
      # ileride: ders_notlari/, kutuphane/ aynı sözleşmeyle
  tests/
    cekirdek/, ders_programi/, test_izolasyon.py (kabul testi)
docker-compose.yml           db (PostgreSQL 17), api; 3. adımda redis, worker; 5. adımda web
```

### Bağımlılık kuralları (mimari değişmezler)
- **Modül → çekirdek** bağımlılığı serbesttir. Modül, çekirdeğin varlıklarına yabancı anahtarla
  (FK) bağlanabilir (ör. `ders_atama.ogretmen_id → ogretmen.id`) ve çekirdeğin depo, kiracı ve
  modül sözleşmesini kullanır.
- **Çekirdek → modül** bağımlılığı yasaktır. Çekirdek hiçbir modülü içe aktarmaz, modül
  tablolarını bilmez.
- **Modül → modül** doğrudan bağımlılığı yasaktır. Gerekirse ortak ihtiyaç çekirdeğe taşınır.
- Çözücü paketi (`/cozucu`) yalnızca ders programı modülü tarafından, girdi/çıktı dönüşümü için
  kullanılır. Çözücü API'yi bilmez (CLAUDE.md mimari karar 3).
- Bu kurallar bir testle denetlenir: çekirdek paketinin içe aktarmaları taranır, `moduller`
  geçerse test kırılır.

### Modül sözleşmesi
```python
@dataclass(frozen=True)
class Modul:
    ad: str                      # "ders_programi"
    router: APIRouter            # /api/<onek> altında bağlanır
    onek: str                    # "ders-programi"
    modeller: ModuleType         # içe aktarılınca tabloları ortak Base.metadata'ya kaydolur
    migration_dizini: Path       # Alembic'e bu modülün sürüm klasörü olarak verilir
```
`main.py`, `ayarlar.ETKIN_MODULLER` listesindeki modülleri yükler ve router'larını bağlar.
Alembic `env.py` aynı listeden sürüm klasörlerini toplar. **Yeni bir modül eklemek** şu kadardır:
`moduller/<yeni>/` klasörünü sözleşmeye uygun yazmak ve adını ayardaki listeye eklemek. Çekirdekte
tek satır değişmez.

## 3. Katmanlar ve sorumluluklar

Bu ayrım class diyagramının da iskeletidir.

| Katman | Sınıflar (örnek) | Sorumluluk | Bilmediği şey |
|---|---|---|---|
| API (router) | `ogretmen_router` | HTTP: yol, durum kodu, Pydantic doğrulaması, bağımlılık enjeksiyonu | SQL, iş kuralı |
| Servis | `OgretmenServisi`, `DersAtamaServisi` | İş kuralları ve işlem (transaction) sınırı. Ör. "atamanın öğretmeni aynı okulda olmalı", "bir sınıf, bir ders, bir atama" | HTTP |
| Depo (repository) | `OkulaAitDepo[T]`, `DersAtamaDeposu` | Veri erişimi, sorgular. Okul filtresi burada otomatik uygulanır | HTTP, iş kuralı |
| Model (ORM) | `Ogretmen`, `DersAtama` | Tablo eşlemesi, ilişkiler | Her şey |
| Kiracı bağlamı | `KiraciBaglami` | İsteğin hangi okula ait olduğunu taşır | — |
| Şema | `OgretmenOlustur`, `OgretmenYanit` | API sözleşmesi (girdi/çıktı biçimi). ORM modelinden ayrıdır | — |

Pydantic şemalarının ORM modellerinden ayrı tutulmasının nedeni: veritabanı alanı eklemek API'yi
kendiliğinden değiştirmesin, API alanı da veritabanını. (Çözücüdeki ADR 0003 ile aynı gerekçe.)

## 4. Tablolar ve ilişkiler

Ortak kurallar:
- Birincil anahtar `id uuid`. Uygulama tarafında `uuid4` ile üretilir.
- Okula ait her tabloda `okul_id uuid NOT NULL REFERENCES okul(id)` vardır.
- Okula ait her tabloda ayrıca `UNIQUE (okul_id, id)` bulunur. Böylece diğer tablolar ona
  **bileşik yabancı anahtarla** `(okul_id, x_id) → x(okul_id, id)` bağlanır. Sonuç: veritabanı,
  A okulunun ders atamasının B okulunun öğretmenini göstermesini **kendisi reddeder**.
  Uygulamada hata olsa bile ilişki kurulamaz.
- Zaman damgaları: `olusturma`, `guncelleme` (`timestamptz`).

**Çekirdek**

| Tablo | Alanlar | Kısıtlar |
|---|---|---|
| `okul` | id, ad, gun_sayisi, gunluk_ders_saati | CHECK gun_sayisi 1-7, gunluk_ders_saati ≥ 1 |
| `kullanici` | id, okul_id, email, sifre_hash, ad, rol | UNIQUE email (bütün sistemde tek); rol CHECK ('mudur', 'mudur_yardimcisi') |
| `ogretmen` | id, okul_id, ad, brans | |
| `sinif` | id, okul_id, ad, seviye | UNIQUE (okul_id, ad) |
| `ders` | id, okul_id, ad, kisa_ad | UNIQUE (okul_id, ad) |

**Ders programı modülü**

| Tablo | Alanlar | Kısıtlar |
|---|---|---|
| `seviye_sablonu` | id, okul_id, seviye, ders_id, haftalik_saat | UNIQUE (okul_id, seviye, ders_id); FK (okul_id, ders_id) |
| `ders_atama` | id, okul_id, sinif_id, ders_id, ogretmen_id (boş olabilir), haftalik_saat | **UNIQUE (okul_id, sinif_id, ders_id)** ("bir sınıf, bir ders, bir öğretmen"); FK'ler bileşik; CHECK haftalik_saat ≥ 1 |
| `musaitlik` | id, okul_id, ogretmen_id, gun, saat, durum | UNIQUE (okul_id, ogretmen_id, gun, saat); CHECK durum ∈ (gelemez, tercih_etmez), gun 0-6, saat ≥ 0 |
| `kisit` | id, okul_id, tur, parametreler `jsonb`, zorunlu, agirlik | UNIQUE (okul_id, tur); CHECK agirlik ≥ 0 |
| `program` | id, okul_id, ad, durum, hata_mesaji, temel_program_id, sure_siniri_sn, olusturma, bitis | CHECK durum ∈ (bekliyor, uretiliyor, hazir, basarisiz); FK (okul_id, temel_program_id) → program (kendine) |
| `yerlesim` | id, okul_id, program_id, ders_atama_id, gun, saat, kilitli | UNIQUE (program_id, ders_atama_id, gun, saat); FK'ler bileşik; program silinince yerleşimleri de silinir (ON DELETE CASCADE) |

İlişkiler (class diyagramındaki çokluklar): Okul 1—* Kullanıcı/Öğretmen/Sınıf/Ders;
Sınıf 1—* DersAtama *—1 Ders; Öğretmen 0..1—* DersAtama; Öğretmen 1—* Müsaitlik;
Program 1—* Yerleşim *—1 DersAtama; Program 0..1—* Program (temel).

Silme davranışı: çekirdek kayıtları (öğretmen, sınıf, ders) modül kayıtları tarafından
kullanılıyorsa silme reddedilir (`ON DELETE RESTRICT`). API bunu "bu öğretmenin 5 ders ataması
var" gibi anlaşılır bir hataya çevirir. Çekirdek bu hatayı modül adını bilmeden üretir: veritabanı
hatasından tablo adını okur ve ilgili modülden mesaj ister (sözleşmeye `silme_engeli_mesaji`
eklenebilir).

## 5. Okul izolasyonu

CLAUDE.md mimari karar 5: satır düzeyi, filtre tek yerde. Önerilen üç katman:

1. **Kiracı bağlamı:** her istekte `aktif_okul_id` belirlenir ve istek boyunca
   `KiraciBaglami`'nda (bir `contextvars.ContextVar`) taşınır. 4. adıma (kimlik doğrulama)
   kadar okul geçici olarak bir istek başlığından (`X-Okul-Id`) alınır. 4. adımda bu yalnızca
   oturumdan (token) okunur ve başlık kaldırılır. Okul seçimi yalnızca tek bir bağımlılık
   fonksiyonunda yapılır, bu yüzden değişiklik tek yerde olur.
2. **ORM düzeyinde otomatik filtre (asıl mekanizma):** SQLAlchemy'nin `do_orm_execute`
   olayında, `OkulaAitMixin` taşıyan bütün modellerin SELECT, UPDATE ve DELETE sorgularına
   `with_loader_criteria(OkulaAitMixin, okul_id == aktif_okul_id)` eklenir. Yeni kayıtlara
   `okul_id` flush öncesinde otomatik yazılır; başka bir okul_id elle verilirse hata fırlatılır.
   Bağlam yokken okula ait tabloya sorgu atılırsa hata fırlatılır ("okulsuz sorgu yasak"). Endpoint
   yazan kişinin unutabileceği bir şey kalmaz.
3. **Veritabanı düzeyinde güvenceler:**
   - bileşik yabancı anahtarlar (bölüm 4): okullar arası ilişki kurulamaz;
   - **seçenek:** PostgreSQL satır düzeyi güvenlik (Row Level Security, RLS). Her tabloda
     `okul_id = current_setting('app.okul_id')::uuid` politikası olur ve her işlemin başında
     `SET LOCAL app.okul_id = ...` çalıştırılır. Uygulama katmanında bir hata olsa bile
     veritabanı başka okulun satırını döndürmez. Bedeli: uygulama, tabloların sahibi olmayan ayrı
     bir veritabanı rolüyle bağlanmalı (sahip RLS'yi atlar) ve migration'lar sahip rolüyle
     çalışmalı.

   **Karar: RLS bu adımda eklenir.** Okul ayarı `SET LOCAL` ile işlem (transaction) kapsamında
   verilir; işlem bitince PostgreSQL ayarı kendisi siler. Böylece havuzdaki bir bağlantı sonraki
   isteğe başka okulun ayarıyla geçemez. Bu, ayrıca testle kanıtlanır (aşağıda).

Başka bir okula ait bir kayda erişim denemesi **404** döner, 403 değil: kaydın var olduğu bile
sızmasın.

**Kabul testi (`tests/test_izolasyon.py`):** A ve B okulları ve her birinde öğretmen, sınıf,
ders, ders ataması, müsaitlik, kısıt oluşturulur. Sonra şunlar denetlenir:
- A'nın bağlamıyla her listeleme endpoint'i yalnızca A'nın kayıtlarını döner;
- A'nın bağlamıyla B'nin her kaydına GET, PATCH ve DELETE 404 döner ve B'nin kaydı değişmez;
- A'nın ders atamasına B'nin öğretmenini bağlama denemesi reddedilir. Bu hem API (422/404) hem
  veritabanı (bileşik FK, ham SQL ile) düzeyinde sınanır;
- bağlam olmadan okula ait tabloya sorgu hata verir;
- RLS: ham SQL ile, uygulama rolüyle ve A'nın `app.okul_id` ayarıyla B'nin satırları görünmez;
  ayar yoksa hiçbir satır görünmez;
- **bağlantı havuzu taşması:** havuz tek bağlantıyla sınırlanır, aynı fiziksel bağlantı art arda
  A, B ve okulsuz istekler için kullanılır. Her istekte yalnızca o isteğin okulu görünür. Hata
  ve geri alma (rollback) ile biten bir istekten sonra da ayar taşmaz. Bağlantının aynı olduğu
  PostgreSQL'in `pg_backend_pid()` değeriyle doğrulanır.

Test, çekirdek ve modülün **bütün** okula ait modellerini `Base.metadata` üzerinden otomatik
dolaşır. Yeni bir modül eklendiğinde onun tabloları da izolasyon testine kendiliğinden girer.

## 6. Migration'lar (Alembic)

- Her modülün kendi Alembic **dalı** (branch) vardır: `cekirdek` ve `ders_programi`.
  `ders_programi` dalının ilk migration'ı `depends_on = cekirdek` ile çekirdeğin tablolarının önce
  oluşmasını garanti eder. Alembic `version_locations` ile her modülün `migrations/` klasörünü
  okur. `alembic upgrade heads` bütün dalları en son sürüme getirir.
- Migration'lar `--autogenerate` ile taslak olarak üretilir, ama **elle gözden geçirilir**.
  Otomatik üretim CHECK kısıtlarını, RLS politikalarını ve bazı tür değişikliklerini kaçırır.
- Uygulanmış bir migration değiştirilmez. Düzeltme için yeni migration yazılır.
- Her migration'ın `downgrade`'i yazılır ve testte sınanır: boş veritabanında upgrade, downgrade,
  upgrade çalıştırılır.
- Test veritabanı her test oturumunda migration'larla kurulur (`create_all` ile değil). Böylece
  migration'ların kendisi de test edilmiş olur.

## 7. Endpoint'ler (temel CRUD)

Yalnızca okul bağlamı içinde çalışır. Hepsi listeleme (`GET`), tek kayıt (`GET /{id}`), oluşturma
(`POST`), güncelleme (`PATCH`) ve silme (`DELETE`) içerir; okul hariç.

| Yol | Not |
|---|---|
| `POST /api/okullar`, `GET/PATCH /api/okul` | Okul oluşturma (4. adımda "okul kaydı" ile birleşir), aktif okulun ayarları |
| `/api/ogretmenler`, `/api/siniflar`, `/api/dersler` | Çekirdek |
| `/api/ders-programi/seviye-sablonlari`, `/atamalar`, `/musaitlikler`, `/kisitlar` | Modül |
| `GET /api/ders-programi/programlar`, `/programlar/{id}/yerlesimler` | Yalnızca okuma; üretim 3. adımda |
| `GET /api/saglik` | Docker sağlık kontrolü |

Kullanıcı tablosu bu adımda oluşur, endpoint'i 4. adımda gelir.

## 8. Testler

- pytest + FastAPI `TestClient`, **gerçek PostgreSQL** üzerinde. Docker Compose'daki `db`
  servisinde ayrı bir test veritabanı kullanılır. SQLite kullanılmaz, çünkü bileşik FK
  davranışı, JSONB, CHECK ve RLS PostgreSQL'e özgüdür ve testin bunları sınaması gerekir.
- Her test bir işlem (transaction) içinde çalışır ve sonunda geri alınır. Testler birbirini
  etkilemez ve hızlı kalır.
- Katman testleri: depo (filtre), servis (iş kuralları), API (durum kodları, şemalar).
- Mimari testi: çekirdek modülleri içe aktarmıyor.
- Migration testi: upgrade, downgrade, upgrade.
- Kabul testi: `test_izolasyon.py` (bölüm 5).

## 9. Alt adımlar

Her alt adım testler geçince commit edilir ve onay alınmadan sonrakine geçilmez.

1. **Altyapı:** `docker-compose.yml` (db, api), `api` paket iskeleti, ayarlar, `/api/saglik`,
   PostgreSQL'e bağlanan bir pytest düzeneği, boş Alembic ortamı (dallarla). ADR 0008 ve 0010.
2. **Çekirdek:** modeller ve migration, `KiraciBaglami`, otomatik filtre, `OkulaAitDepo`,
   çekirdek CRUD, mimari testi. İlk izolasyon testleri (çekirdek tabloları). ADR 0009.
3. **Ders programı modülü:** modül sözleşmesi, modeller ve migration (ayrı dal), CRUD, iş
   kuralları ("bir sınıf, bir ders, bir atama", atamanın öğretmeni ve sınıfı aynı okulda).
4. **İzolasyon kabul testi ve RLS:** bütün tabloları dolaşan kabul testi; RLS politikaları,
   uygulama rolü (tablo sahibi olmayan), ham SQL testleri, bağlantı havuzu taşma testi.
5. **Diyagramlar ve belgeler:** class, object ve deployment diyagramları (PlantUML kaynakları
   `docs/diyagramlar/` altında), README'de "tek komutla çalıştırma".

Not: modül sözleşmesi (`Modul`, kayıt defteri) 3. alt adımdan 1. alt adıma alındı, çünkü Alembic
dallarının sürüm klasörleri modül listesinden toplanır.

**Durum:**

| # | Alt adım | Durum |
|---|---|---|
| 1 | Altyapı | Bitti (2026-10-14) |
| 2 | Çekirdek | Bitti (2026-10-14) |
| 3 | Ders programı modülü | Bitti (2026-10-14) |
| 4 | İzolasyon kabul testi ve RLS | Bitti (2026-10-14) |
| 5 | Diyagramlar ve belgeler | Bitti (2026-10-14) |

Yapım sırası 2 tamamlandı (2026-10-14).

1. alt adımdan notlar:
- `docker compose up --build` ile db (PostgreSQL 17.11) ve api ayağa kalkıyor. API açılırken
  `python -m okulapi.migrasyon upgrade heads` çalışıyor, sonra `/api/saglik` gerçek bir sorguyla
  200 dönüyor. Temiz bir veri biriminden sıfırdan kurulum da denendi.
- `alembic.ini` yerine `python -m okulapi.migrasyon` sarmalayıcısı kullanılıyor (sürüm klasörleri
  modül listesinden). Günlük ayarı sarmalayıcıda, "Running upgrade" satırları konteyner
  kayıtlarında görünüyor.
- Bu makinede kapalı porta bağlanma hemen reddedilmiyor, zaman aşımına kadar bekliyor. Bütün
  bağlantılara `connect_timeout` (3 sn) eklendi; yoksa sağlık kontrolü ve testler takılıyordu.
- Öğrenilen bir Alembic davranışı: `alembic_version` dal başına değil, birbirini kapsamayan uç
  revizyon başına satır tutar (`depends_on` da kapsama sayılır). Testler uygulanmış revizyonları
  uçlardan geriye yürüyerek hesaplıyor; sıra garantisi çevrimdışı SQL çıktısıyla ayrıca sınanıyor.
- Makinede başka projelerin (vtys26-lab01, vtys26-lab02) PostgreSQL konteynerleri bilgisayarın
  5432 portunu kullanıyor. Karar: bu projenin `db` servisi bilgisayara **5433** üzerinden açılır
  (`5433:5432`); konteynerler arası bağlantı yine `db:5432`. Ayarların ve testlerin varsayılan
  adresi `localhost:5433`.

2. alt adımdan notlar:
- Modeller (`cekirdek/modeller.py`): `Okul` ve `OkulaAitMixin`'den türeyen `Kullanici`,
  `Ogretmen`, `Sinif`, `Ders`. Adlandırma kuralı (`ADLANDIRMA_KURALI`) kısıt adlarını öngörülebilir
  kılar. Migration `cekirdek_0002` autogenerate ile üretildi, elle gözden geçirildi.
- **Plandan sapma:** okul bağlamı `ContextVar` yerine veritabanı oturumuna bağlandı
  (`oturum.info["okul_id"]`). FastAPI senkron bağımlılıkları bağlam kopyasıyla ayrı iş parçacığında
  çalıştırır; ContextVar endpoint'e ulaşmayabilir. Gerekçe ADR 0009'da.
- Okul filtresi (`cekirdek/kiraci.py`): `do_orm_execute` + `with_loader_criteria`,
  `before_flush`. Testte bulunan açık: `select(func.count()).select_from(Model)` sorgusunda
  `all_mappers` boş olduğu için filtre atlanıyordu; okula aitlik artık FROM'daki tablolardan da
  belirleniyor. Ham SQL ve Core tablo nesneleri ORM filtresini atlar: uygulama kodunda tarama
  testiyle yasak, RLS (4. alt adım) kapatacak.
- Katmanlar: `OkulaAitDepo` → `CrudServisi` (işlem sınırı; servis commit eder; PostgreSQL hata
  kodları 23505/23503/23514 anlaşılır hatalara çevrilir) → `crud_router` fabrikası (modüller de
  kullanabilir). Servis istisnaları main.py'de 404/409/422'ye çevrilir.
- Test düzeneği: test başına dış işlem + oturumlar SAVEPOINT ile (`join_transaction_mode=
  "create_savepoint"`); servisler gerçekten commit etse de veritabanında iz kalmaz.
- Testler: 45/45 (altyapı 12, okul filtresi 16, çekirdek API 17). Gerçek API üzerinde elle de
  denendi: B okulu A'nın öğretmenini ne getirebiliyor ne silebiliyor (404).
- Windows notu: `curl -d` ile Türkçe karakterli gövde gönderilince komut satırı kod sayfası
  yüzünden bozuk UTF-8 gidiyor (API 400 döner). Gövdeyi dosyadan (`--data-binary @dosya`) gönderin.

3. alt adımdan notlar:
- Modeller ve migration `ders_programi_0002` (`depends_on = cekirdek_0002`). Bütün ilişkiler
  bileşik yabancı anahtar `(okul_id, x_id) -> x(okul_id, id)`. Silme davranışları: çekirdek
  kaydı bir atamada kullanılıyorsa RESTRICT; öğretmen -> müsaitlik CASCADE; program -> yerleşim
  CASCADE; ders ataması -> yerleşim CASCADE (RESTRICT olsaydı program üretilmiş bir atama bir daha
  silinemezdi); temel program silinince `ON DELETE SET NULL (temel_program_id)` (PostgreSQL 15+).
- `ders_atama.ogretmen_id` boş olabilir; bileşik anahtar MATCH SIMPLE olduğu için boşken
  denetlenmez.
- Yabancı anahtarın gösteren tarafına PostgreSQL indeks koymaz: `ders_atama(okul_id,
  ogretmen_id)` ve `yerlesim(okul_id, ders_atama_id)` indeksleri elle eklendi.
- Çekirdeğin `CrudServisi`'ne genişletme noktası eklendi: `_dogrula(alanlar, nesne)`. Modül
  servisleri iş kurallarını burada denetler (sınıf/ders/öğretmen bu okulda mı, müsaitlik okulun
  gün/saat aralığında mı). Kısıtlar çözücünün kendi kural kayıt defteriyle (`kural_olustur`)
  doğrulanıyor: API ile çözücü aynı kural listesini biliyor.
- Seviye şablonu: `POST /api/ders-programi/seviye-sablonlari/uygula {seviye}`. O seviyedeki her
  şubeye eksik (sınıf, ders) için öğretmeni boş atama oluşturur. Var olanları çoğaltmaz ve
  değiştirmez; saati şablondan farklı olanları raporlar.
- API çözücü paketine bağımlı oldu (`cozucu` bağımlılığı, Dockerfile önce çözücüyü kurar).
  Bağımlılık tek yönlü: çözücü API'yi bilmez.
- Dönüştürücü (`moduller/ders_programi/cozucu_donusturucu.py`): oturumun okulundan
  `CozumGirdisi` üretir; isteğe bağlı kilit programı (kilitli hücreler) ve temel program (en az
  değişiklik). Gidiş-dönüş testi: mini set API ile yüklenir, dönüştürülür, doğal anahtarlarla
  orijinaliyle birebir aynı çıkar; çözücü çözer, doğrulayıcıdan geçer.
- `test_modeller_ve_migrationlar_uyumlu` (`alembic check`'in test hali) eklendi.
- Testler: 63/63.

4. alt adımdan notlar:
- Roller: uygulama `okul_uygulama` (RLS'ye tabi), migration `okul_sahip`. Ayarlarda
  `veritabani_url` ve `migrasyon_url`. Rol ve parolası `docker/postgres/init/01-uygulama-rolu.sh`
  ile (yalnızca boş veri biriminde çalışır; `.gitattributes` ile LF satır sonu).
- RLS migration'ları: `cekirdek_0003` (rol, `aktif_okul_id()`, çekirdek politikaları) ve
  `ders_programi_0003` (`depends_on = cekirdek_0003`).
- `kiraci.py`: her işlemin başında `set_config('app.okul_id', ..., true)` (= SET LOCAL). Okul
  oluşturma servisi yeni okulun kimliğini işlemin bağlamına yazar.
- Testler artık uygulama rolüyle, RLS altında çalışıyor. Değişen beklentiler: okulsuz oturum hiçbir
  okulu görmez; ham SQL ve Core sorguları RLS ile filtrelenir.
- Kabul testi `tests/test_izolasyon.py`: 26 alt test (tablo kapsamı, tablo başına RLS, okul tablosu,
  API, bağlantı havuzu). Mutasyon denemesi havuz testinde bir boşluk buldu (istekler commit
  etmiyordu), düzeltildi; ayrıntılar ADR 0009'da.
- Testler: 89/89. Docker'da sıfırdan kurulum ve psql ile elle doğrulama yapıldı.

5. alt adımdan notlar:
- Diyagramlar `docs/diyagramlar/` altında, dokuz tane: genel bakış (01), çekirdek (02 modeller ve
  izolasyon, 03 katmanlar), ders programı modülü (04 tablolar, 05 katmanlar), çözücü (06, strategy
  deseni), nesne diyagramları (07 veri girişi, 08 program sonrası; mini setin gerçek çözümünden),
  dağıtım (09; redis, worker, web `<<planlanan>>`, gri ve kesik çizgili). Tek parça class
  diyagramı yerine bölündü; tek parça okunamıyordu. Bölüm 10'daki `KiraciBaglami` ve
  `ModulKayitDefteri` adları koddaki karşılıklarıyla çizildi (`kiraci` modülü, `modulleri_yukle`).
- Çıktılar tek komutla: `python scripts/diyagramlari_uret.py` (PlantUML `1.2026.8` imajı, Docker).
- `api/tests/test_diyagramlar.py`: diyagramdaki her sınıf, üye, metot parametresi ve nesne alanı
  kodda aranır (`' @kod <modül>` işaretleriyle). Mutasyonla denendi: yanlış üye, parametre ve
  nesne alanı yakalanıyor.
- PlantUML'de paket ile sınıf aynı adı taşıyamaz; `<<modül>>` sınıflarının paket etiketleri bu
  yüzden açıklamalı (ör. "kisitlar (paket: kayıt ve varsayılanlar)").
- README: tek komutla çalıştırma, testler, diyagramlar. `docker compose up --build` ile
  `/api/saglik` ve `/docs` yeniden doğrulandı.
- Testler: api 195/195 (diyagram testleri 106), çözücü 137/137.

## 10. Diyagramlar (ders için)

- **Class diyagramı:** iki paket (`cekirdek`, `moduller.ders_programi`) ve aralarındaki tek yönlü
  bağımlılık. Varlıklar ve çoklukları (bölüm 4). Katman sınıfları (`*Servisi`, `*Deposu`,
  `OkulaAitDepo<T>`, `KiraciBaglami`, `Modul`, `ModulKayitDefteri`). Çözücü tarafında
  `ProgramCozucu` ← `CpSatCozucu` ve `KisitKurali` hiyerarşisi (strategy).
- **Object diyagramları** (mini setteki somut verilerle, class diyagramıyla yan yana okunabilsin
  diye; en az iki tane):
  1. *Veri girişi sonrası anlık durum:* bir `Okul`, `Ayşe Yılmaz : Ogretmen`, `9-A : Sinif`,
     `Matematik : Ders`, `9-A Matematik : DersAtama` (haftalık 6), Ayşe'nin bir `Musaitlik`'i
     (Pazartesi gelemez), bir `Kisit` (günlük ders sınırı n=2).
  2. *Program üretildikten sonra:* aynı nesneler + `Program` (durum `hazir`) ve o atamanın birkaç
     `Yerlesim`'i (ör. Salı 1. saat kilitli, Çarşamba 2-3), ayrıca temel programı gösteren ikinci
     bir `Program` (en az değişiklikle güncelleme).
  3. (İsteğe bağlı) *İzolasyon:* iki `Okul` nesnesi ve A'nın atamasının B'nin öğretmenine
     bağlanamadığını gösteren not.
- **Deployment diyagramı:** Docker Compose düğümü içinde `web`, `api`, `worker`, `redis`,
  `postgres` konteynerleri, aralarındaki protokoller (HTTP, TCP/5432, Redis protokolü), kalıcı
  birim (volume). Bu adımda yalnızca `api` ve `postgres` gerçek; diğerleri "planlanan" olarak
  işaretlenir.
- Araç önerisi: **PlantUML.** Üç diyagram türünü de UML gösterimiyle çizer; Mermaid'de
  deployment ve object diyagramı yok. Kaynak dosyalar metin olduğu için depoda sürümlenir; görseller
  Docker'daki `plantuml` imajıyla üretilir.

## 11. Öğrenilecek PostgreSQL ve migration kavramları

Her biri ilgili alt adımda, kodla birlikte kısaca açıklanacak:

- **Tablo, satır, şema;** `uuid` birincil anahtar ve neden `serial` değil (tahmin edilemez,
  okullar arası birleşmede çakışmaz, istemci tarafında üretilebilir).
- **Yabancı anahtar ve bileşik yabancı anahtar;** `ON DELETE RESTRICT/CASCADE`.
- **UNIQUE ve CHECK kısıtları:** iş kuralının veritabanında da yaşaması.
- **İndeks:** `okul_id` ile başlayan indeksler; her sorgu okula göre süzüldüğü için.
- **İşlem (transaction):** servis katmanında başlayıp biten iş birimi; testlerde geri alma.
- **JSONB:** `kisit.parametreler` için. Esnek ama sorgulanabilir.
- **Satır düzeyi güvenlik (RLS):** politika, `current_setting`, tablo sahibi ile uygulama rolü
  farkı.
- **Migration:** revizyon, upgrade/downgrade, autogenerate ve sınırları, dallar ve `depends_on`,
  uygulanmış migration'ı değiştirmeme kuralı.
- **SQLAlchemy 2.0:** `Mapped[...]` ile tip ipuçlu modeller, oturum (session) ve unit of work,
  `with_loader_criteria`.

## 12. ADR'ler

| ADR | Konu | Neden gerekli |
|---|---|---|
| 0008 | Modüler monolit: çekirdek + modüller, bağımlılık yönü, modül sözleşmesi | Yeni modüllerin çekirdeği değiştirmeden eklenmesi temel bir mimari karar. Alternatifler: tek paket, mikro servisler |
| 0009 | Okul izolasyonu: kiracı bağlamı + ORM otomatik filtresi + bileşik FK (+ RLS) | CLAUDE.md mimari karar 5'in nasıl uygulandığı ve kabul kriteri. Alternatifler: okul başına şema, okul başına veritabanı, yalnızca depoda elle filtre, yalnızca RLS |
| 0010 | Migration stratejisi: modül başına Alembic dalı | Modülerliğin veritabanı tarafı. Alternatifler: tek doğrusal geçmiş, `create_all` |

Küçük kararlar (uuid anahtar, 404 dönme, gerçek PostgreSQL ile test) ilgili ADR'lerin içinde
"sonuçlar" olarak yer alır, ayrı ADR yazılmaz.

## 13. Onaylanan kararlar (2026-10-14)

1. RLS bu adımda eklenir; bağlantı havuzunda okul bilgisinin taşmadığı ayrıca test edilir.
2. Paket adı `okulapi`; endpoint önekleri `/api/...`, modül için `/api/ders-programi/...`.
3. Geçici `X-Okul-Id` başlığı uygun. Yapım sırası 4'ün kabul kriteri: başlık tamamen kaldırılmış,
   okul yalnızca oturumdan belirleniyor (CLAUDE.md bölüm 8'e yazıldı).
4. Diyagramlar PlantUML; object diyagramları mini set verisiyle, en az iki tane (bölüm 10).
5. PostgreSQL 17.

## 14. Ters yön: çözücü sonucu -> program ve yerleşim (tasarım; kodu yapım sırası 3'te)

Worker'ın akışı ve sonucu yazan parça (`moduller/ders_programi/sonuc_yazici.py`):

1. **İş:** kuyruğa `(okul_id, program_id)` girer. Worker `okul_oturumu(okul_id)` açar. Okul
   filtresi ve RLS worker'da da geçerlidir; worker başka okulun verisine dokunamaz.
2. **Başlatma (ayrı işlem):** `SELECT ... FOR UPDATE` ile program satırı kilitlenir. Durum
   `bekliyor` değilse iş bırakılır; aynı iş iki kez gelirse ikincisi bir şey yapmaz (idempotent).
   Durum `uretiliyor` yapılır ve commit edilir; arayüz bunu sorgulamayla görür.
3. **Girdi:** `cozum_girdisi_olustur(oturum, kilit_programi_id=..., temel_program_id=program.temel_program_id)`.
   Girdinin bir özeti (`girdi_ozeti`, kanonik JSON'un SHA-256'sı) programa yazılır.
4. **Çözüm:** `CpSatCozucu().coz(girdi, program.sure_siniri_sn)`; veritabanı bağlantısı çözüm
   boyunca açık tutulmaz.
5. **Yazma (tek işlem):**
   - program satırı yeniden `FOR UPDATE` ile kilitlenir; durum hâlâ `uretiliyor` olmalı;
   - girdi yeniden üretilir ve özeti karşılaştırılır. Veri çözüm sırasında değiştiyse (atama
     silindi, saati değişti) program `basarisiz` ve "Program üretilirken veriler değişti, yeniden
     üretin" olur; eski veriyle üretilmiş program yazılmaz;
   - başarılıysa çözücünün bağımsız doğrulayıcısı (`dogrula`) son bir kez çalışır (savunma);
   - programın varsa eski yerleşimleri silinir, yenileri toplu `INSERT` ile eklenir. Toplu ekleme
     ORM olaylarından geçmediği için `okul_id` açıkça oturumun okulundan yazılır; RLS'nin `WITH
     CHECK` koşulu ve bileşik yabancı anahtarlar yine korur;
   - program güncellenir: `durum` (`hazir`/`basarisiz`), `bitis`, ve yeni sütunlar `cozum_durumu`
     (optimal/uygun/cozumsuz/on_kontrol_hatasi/bilinmiyor), `toplam_ceza`, `olcumler` (JSONB:
     `kalite.olc` sonuçları), `celiskiler` (JSONB: tür, mesaj, ilgili kimlikler; arayüz ilgili
     hücreleri vurgulayabilsin), `sure_sn`, `girdi_ozeti`. Bunlar migration `ders_programi_0003`
     ile eklenecek;
   - `hata_mesaji`, çelişki mesajlarının kullanıcıya gösterilecek metnidir.
6. **Hata durumları:** çözücü istisna fırlatmaz (arayüz sözleşmesi). Worker'ın kendisi çökerse
   program `uretiliyor`da kalır; RQ iş zaman aşımı (süre sınırı + pay) dolunca bir temizleyici
   onu `basarisiz` ("üretim yarıda kaldı") yapar.
7. **Testler (o adımda):** mini set uçtan uca (istek -> kuyruk -> worker -> API'den yerleşimler,
   doğrulayıcıdan geçer); aynı işin iki kez işlenmesi; çözüm sırasında atama silinmesi; başarısız
   üretimde çelişkilerin yazılması; başka okulun programına yazma denemesi.


## 15. Sonraya

1. **Paylaşılan/yayınlanan programın dondurulması** (yapım sırası 8, öğretmen paylaşım linki
   adımında ele alınacak).
   - Sorun: ders ataması silinince yerleşimleri de siliniyor (`ON DELETE CASCADE`, bölüm 3. alt adım
     notları). Öğretmenlerle paylaşılmış bir programdan bir ders bu yüzden **sessizce kaybolabilir**.
     Silme davranışı şimdilik değiştirilmedi.
   - Fikir: bir program yayınlanınca (paylaşım linki oluşturulunca) **dondurulur**. Yayınlanan
     programın yerleşimleri, atamanın kendisine değil, yayın anındaki kopyasına (sınıf adı, ders adı,
     öğretmen adı, gün, saat) dayanan değişmez bir anlık görüntüde (snapshot) tutulur. Böylece
     atama silinse ya da değişse de yayınlanan program aynı kalır.
   - Veri değiştiğinde kullanıcıya "Bu program eski veriyle üretildi/yayınlandı" uyarısı gösterilir.
     Bunu anlamak için worker tasarımındaki **girdi özeti** (bölüm 14, adım 3) kullanılır: programın
     üretildiği girdinin özeti, okulun şu anki verisinden üretilen girdinin özetiyle
     karşılaştırılır. Farklıysa program "güncel değil" olarak işaretlenir; yönetici isterse en az
     değişiklikle yeniden üretir ve yeniden yayınlar.
   - Bu yaklaşım CASCADE'i taslak (yayınlanmamış) programlar için korur; yalnızca yayınlanan
     programlar korunur.

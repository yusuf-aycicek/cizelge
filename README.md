# Çizelge – Okul Ders Programı Oluşturma Sistemi

Okullar için çakışmasız haftalık ders programı üreten, çok okullu (multi-tenant) web uygulaması.
Kararların ve kapsamın tek doğruluk kaynağı [CLAUDE.md](CLAUDE.md).

## Tek komutla çalıştırma

Gerekenler: Docker (Docker Desktop ya da Docker Engine + Compose).

```bash
docker compose up --build
```

Bu komut:

1. `db`: PostgreSQL 17'yi başlatır. İlk açılışta uygulama rolünü (`okul_uygulama`) oluşturur
   (`docker/postgres/init/`). Veri `db_verisi` biriminde durur.
2. `redis`: iş kuyruğu (Redis 7.4, RQ). Bilgisayara port açılmaz; yalnızca api ve worker ulaşır.
3. `api`: imajı derler (çözücü paketi + API + worker). Veritabanı ve Redis sağlıklı olunca
   migration'ları uygular (`python -m okulapi.migrasyon upgrade heads`) ve API'yi başlatır.
4. `worker`: aynı imaj, `python -m okulworker`. Kuyruktaki program üretme işlerini çalıştırır.
   API sağlıklı olunca (migration'lar bitince) başlar. Birden fazla worker için:
   `docker compose up --scale worker=3`.
5. `web`: arayüz (React + TypeScript, Vite geliştirme sunucusu). İlk açılışta paketleri kurar
   (bir iki dakika sürebilir). `/api` isteklerini api konteynerine iletir.

| Adres | Ne |
|---|---|
| http://localhost:5173 | **Arayüz** (geliştirme). `/tasarim`: tasarım temeli vitrini |
| http://localhost:8000/docs | API belgeleri (Swagger), endpoint'leri buradan denemek mümkün |
| http://localhost:8000/api/saglik | Sağlık kontrolü (API ve veritabanı) |
| `localhost:5433` | PostgreSQL. Bilgisayardan erişim için 5433 kullanılır (5432 aynı makinedeki başka projelerde). |

Veritabanı rolleri (yalnızca geliştirme parolaları, `docker-compose.yml`):

| Rol | Kullanım |
|---|---|
| `okul_sahip` | Tabloların sahibi. Migration'lar bu rolle çalışır. |
| `okul_uygulama` | Uygulamanın bağlandığı rol. Satır düzeyi güvenliğe (RLS) tabidir, yalnızca kendi okulunun satırlarını görür. |
| `okul_giris` | Girişi olmayan (NOLOGIN) rol. Okul bilinmeden kullanıcı ve oturum arayan `SECURITY DEFINER` fonksiyonların sahibidir (ADR 0012). |

Kayıt ve giriş (ADR 0012). Aktif okul yalnızca oturumdan belirlenir:

1. `POST /api/kayit` `{"okul": {"ad": "..."}, "ad": "...", "email": "...", "sifre": "..."}`: okul, ilk
   müdür ve oturum oluşur. Oturum jetonu `HttpOnly` bir çerezde (`oturum`) döner.
2. `POST /api/giris` `{"email", "sifre"}` ve `POST /api/cikis`. `GET /api/ben`: giriş yapan kullanıcı
   ve okulu (yoksa 401).
3. Diğer bütün `/api/...` uçları oturum çerezi ister. Swagger sayfasında (`/docs`) önce
   `/api/kayit` ya da `/api/giris` çalıştırılır; tarayıcı çerezi sonraki isteklere kendisi ekler.
4. Müdür, yardımcı hesaplarını `/api/kullanicilar` uçlarıyla yönetir. Parola en az 12 karakterdir.

Müdür parolasını unutursa sistemi işleten kişi sunucuda (API'den erişilemez):

```bash
docker compose exec api python -m okulapi parola-sifirla mudur@okul.example
```

Yeni parola iki kez sorulur. `--rastgele` ile rastgele bir parola üretilip bir kez gösterilir.
Kullanıcının bütün oturumları kapanır, hatalı giriş kilidi kalkar.

### Örnek okul (demo ve ekran görüntüleri)

Geliştirme veritabanını temizleyip mini veri setiyle (`veri/mini.json`) örnek bir okul yükler.
Sistem `docker compose up` ile çalışırken bilgisayarda çalıştırılır:

```bash
cd api && OKULAPI_ORTAM=gelistirme .venv/Scripts/python -m okulapi ornek-okul --evet
```

PowerShell'de: `cd api; $env:OKULAPI_ORTAM="gelistirme"; .venv\Scripts\python -m okulapi ornek-okul --evet`

- **Veritabanındaki bütün okullar, kullanıcılar ve oturumlar silinir.** Bu yüzden iki koruması
  vardır:
  - `OKULAPI_ORTAM=gelistirme` açıkça verilmeden çalışmaz (çıkış kodu 3). Ayarın varsayılanı
    `yayin`dır; yayındaki bir sunucu bu değişkeni hiç tanımlamamalıdır.
  - `--evet` olmadan çalışmaz (çıkış kodu 2).
- Yüklenenler: 5 öğretmen, 3 şube, 7 ders, 18 ders ataması, 15 müsaitlik kaydı. Ayrıca her seviye
  için bir seviye şablonu, o seviyenin ilk şubesinin derslerinden üretilir.
- Giriş: `mudur@ornek.test` / `ornek-okul-parolasi` (http://localhost:5173).
- `--set gercekci`: mini set yerine gerçekçi set (42 öğretmen, 24 şube, 330 ders ataması). Program
  üretimi süre sınırını kullanır; bekleme ekranını görmek için.
- Veri, API'nin kendisinden geçerek yüklenir (süreç içinde, sunucuya istek atmadan); bütün
  doğrulamalar uygulanır. Kod: `api/src/okulapi/ornek_okul.py`.

### Geliştirme ortamı: arayüz ve API aynı kökenden (ADR 0013)

Tarayıcı arayüzü ve API'yi her zaman **aynı köken** (şema + alan adı + port) üzerinden görür.
Oturum çerezi `SameSite=Strict`'tir ve veri değiştiren isteklerde `Origin` başlığı denetlenir.
Ayrı kökenden yapılan istekler (CORS) bilerek desteklenmez.

- **Geliştirmede** arayüz Vite ile `http://localhost:5173`'te çalışır (yapım sırası 5). Vite'ın
  proxy'si `/api` isteklerini API'ye iletir. Arayüz kodu API'yi göreli adresle çağırır
  (`fetch("/api/ben")`). `web/vite.config.ts` şöyle olacak:

  ```ts
  export default defineConfig({
    plugins: [react()],
    server: { proxy: { "/api": "http://localhost:8000" } },
  })
  ```

- **Yayında** arayüzün derlenmiş dosyaları ve API aynı alan adının arkasındadır (ters vekil
  sunucu, ör. nginx ya da Caddy: `/` statik dosyalar, `/api` API).

Ayarlar (ortam değişkenleri, `docker-compose.yml`):

| Değişken | Geliştirme | Yayın |
|---|---|---|
| `OKULAPI_IZINLI_KOKENLER` | `["http://localhost:5173", "http://localhost:8000"]` (Vite ve `/docs`) | `["https://<alan adı>"]` |
| `OKULAPI_CEREZ_SECURE` | `false` (http) | verilmez; varsayılan `true` (yalnızca HTTPS) |

`OKULAPI_IZINLI_KOKENLER` verilmezse tarayıcıdan hiçbir yazma isteği kabul edilmez, giriş bile
yapılamaz (403, "köken denetimi"). Bu, güvenli bir varsayılandır. curl gibi tarayıcı dışı
istemciler `Origin` göndermez; onlar için yalnızca oturum çerezi gerekir.

Program üretme akışı (ADR 0011):

1. `POST /api/ders-programi/programlar` `{"ad": "Güz dönemi"}`: 202 ve `bekliyor` durumundaki
   program döner, iş kuyruğa konur.
2. `GET /api/ders-programi/programlar/{id}`: durum birkaç saniyede bir sorulur:
   `bekliyor` → `uretiliyor` → `hazir` (ya da `basarisiz` ve okunur bir `hata_mesaji`).
3. `GET /api/ders-programi/programlar/{id}/yerlesimler`: programın hücreleri.

Okulun devam eden bir üretimi varken yeni istek 409, kuyruğa ulaşılamazsa 503 alır.

Durdurmak için `docker compose down` kullanılır. Veritabanını da silmek için:

```bash
docker compose down -v
```

## Testler

Testler, gerçek PostgreSQL'e karşı çalışır (`localhost:5433`, `okul_test` veritabanı her
çalıştırmada sıfırdan migration'larla kurulur). Önce yalnızca veritabanını başlatın:

```bash
docker compose up -d db
```

Çözücü (veritabanı gerekmez):

```bash
cd cozucu && python -m venv .venv && .venv/Scripts/pip install -e ".[test]" && .venv/Scripts/python -m pytest
```

API (çözücü paketine bağımlıdır, önce o kurulur; worker paketi diyagram denetimi için):

```bash
cd api && python -m venv .venv && .venv/Scripts/pip install -e ../cozucu -e ".[test]" -e ../worker && .venv/Scripts/python -m pytest
```

Bu testler Redis gerektirmez: kuyruk bellek içi bir ikizle, RQ gerçeklemesi fakeredis ile
sınanır.

Uçtan uca kabul testleri, çalışan bütün sisteme (api, redis, worker, db) HTTP ile bağlanır:
- yapım sırası 3: mini seti yükler, program ister, durumun `bekliyor` → `uretiliyor` → `hazir`
  olduğunu denetler ve 9-A'nın haftalık çizelgesini yazdırır;
- yapım sırası 4: kayıt, çıkış ve giriş; `X-Okul-Id` başlığının işe yaramadığı; Vite kökeninin
  izinli, yabancı kökenin reddedildiği. Geliştirme veritabanına yeni bir okul eklediği için
varsayılan çalıştırmada yer almaz:

```bash
docker compose up -d --build --wait
```

```bash
cd api && .venv/Scripts/python -m pytest -m uctan_uca -s
```

Linux/macOS'ta `.venv/Scripts/` yerine `.venv/bin/` kullanılır. Uzun süren ölçüm testleri
`-m slow` ile ayrıca çalıştırılır.

## Arayüz (web/)

React + TypeScript + Vite. Plan ve kararlar: [docs/arayuz-plani.md](docs/arayuz-plani.md).
Docker olmadan, bilgisayarda (Node 22; API `localhost:8000`'de çalışıyor olmalı):

```bash
cd web && npm install && npm run dev
```

Denetimler: tip denetimi, lint ve testler (Vitest + Testing Library + MSW; API gerekmez):

```bash
cd web && npm run denetim
```

API değişince arayüzün tipleri yenilenir. Yenilenmezse iki test (api ve web) kırılır:

```bash
api/.venv/Scripts/python scripts/openapi_yaz.py
```

```bash
cd web && npm run api:tipler
```

Ekran görüntüleri, çalışan arayüzden bilgisayardaki Edge ile alınır ve `docs/ekranlar/<adım>/`
altına yazılır:

```bash
cd web && node scripts/ekran-goruntusu.mjs 5.1
```

## Çözücüyü komut satırından çalıştırma

```bash
cd cozucu && .venv/Scripts/python -m cozucu ../veri/mini.json --sinif 9-A
```

## Diyagramlar

UML diyagramlarının kaynakları `docs/diyagramlar/*.puml`, çıktıları `docs/diyagramlar/cikti/`
altındadır. PlantUML sürümü sabitlenmiş Docker imajıyla çalışır. Çıktıları yeniden üretmek için:

```bash
python scripts/diyagramlari_uret.py
```

Diyagramdaki sınıf, metot, parametre ve alan adlarının kodda var olduğunu
`api/tests/test_diyagramlar.py` denetler. Kod değiştiğinde bu test diyagramın da güncellenmesi
gerektiğini söyler.

| Diyagram | İçerik |
|---|---|
| 01 | Genel bakış: paketler ve bağımlılıklar |
| 02, 03 | Çekirdek: modeller ve okul izolasyonu; router → servis → depo katmanları |
| 04, 05 | Ders programı modülü: tablolar; servisler, depolar, dönüştürücü |
| 06 | Çözücü: `ProgramCozucu`, `CpSatCozucu`, kısıt kuralları (strategy deseni) |
| 07, 08 | Nesne diyagramları: mini set, veri girişinden ve program üretiminden sonra |
| 09 | Dağıtım: konteynerler (db, redis, api, worker), portlar, roller; planlanan web (Vite proxy) |
| 10 | Kimlik doğrulama: servisler, uçlar, köken denetimi, okul bilinmeden arama |

## Belgeler

- [CLAUDE.md](CLAUDE.md): kapsam, mimari, veri modeli, yapım sırası
- [docs/adr/](docs/adr/): mimari karar kayıtları
- [docs/cozucu-plani.md](docs/cozucu-plani.md), [docs/api-plani.md](docs/api-plani.md), [docs/kuyruk-plani.md](docs/kuyruk-plani.md): adım planları
- [docs/olcumler.md](docs/olcumler.md): çözücü süre ve kalite ölçümleri

## Klasörler

```
cozucu/    Saf Python çözücü paketi (OR-Tools CP-SAT) ve testleri
api/       FastAPI uygulaması (okulapi): çekirdek + modüller
worker/    Kuyruk işçisi (okulworker): modülleri bilmeyen genel çalıştırıcı
web/       Arayüz (React + TypeScript + Vite)
docker/    Konteyner başlangıç betikleri
docs/      Diyagramlar, ADR'ler, planlar, ölçümler
veri/      Test veri setleri (mini, gerçekçi, büyük)
scripts/   Deney ve yardımcı betikler
```

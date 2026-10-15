# Okul Ders Programı Sistemi

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

| Adres | Ne |
|---|---|
| http://localhost:8000/docs | API belgeleri (Swagger), endpoint'leri buradan denemek mümkün |
| http://localhost:8000/api/saglik | Sağlık kontrolü (API ve veritabanı) |
| `localhost:5433` | PostgreSQL. Bilgisayardan erişim için 5433 kullanılır (5432 aynı makinedeki başka projelerde). |

Veritabanı rolleri (yalnızca geliştirme parolaları, `docker-compose.yml`):

| Rol | Kullanım |
|---|---|
| `okul_sahip` | Tabloların sahibi. Migration'lar bu rolle çalışır. |
| `okul_uygulama` | Uygulamanın bağlandığı rol. Satır düzeyi güvenliğe (RLS) tabidir, yalnızca kendi okulunun satırlarını görür. |

Geçici not: 4. yapım adımına kadar aktif okul `X-Okul-Id` başlığıyla seçilir. Örnek akış:
`POST /api/okullar` ile bir okul oluşturulur, dönen `id` sonraki isteklerde `X-Okul-Id`
başlığında gönderilir.

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

Uçtan uca kabul testi, çalışan bütün sisteme (api, redis, worker, db) HTTP ile bağlanır, mini
seti yükler, program ister ve durumun `bekliyor` → `uretiliyor` → `hazir` olduğunu denetler.
Sonunda 9-A'nın haftalık çizelgesini yazdırır. Geliştirme veritabanına yeni bir okul eklediği için
varsayılan çalıştırmada yer almaz:

```bash
docker compose up -d --build --wait
```

```bash
cd api && .venv/Scripts/python -m pytest -m uctan_uca -s
```

Linux/macOS'ta `.venv/Scripts/` yerine `.venv/bin/` kullanılır. Uzun süren ölçüm testleri
`-m slow` ile ayrıca çalıştırılır.

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
| 09 | Dağıtım: konteynerler (db, redis, api, worker), portlar, roller; planlanan web |

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
docker/    Konteyner başlangıç betikleri
docs/      Diyagramlar, ADR'ler, planlar, ölçümler
veri/      Test veri setleri (mini, gerçekçi, büyük)
scripts/   Deney ve yardımcı betikler
```

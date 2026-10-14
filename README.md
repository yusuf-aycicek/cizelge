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
2. `api`: imajı derler (çözücü paketi + API). Veritabanı sağlıklı olunca migration'ları
   uygular (`python -m okulapi.migrasyon upgrade heads`) ve API'yi başlatır.

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

API (çözücü paketine bağımlıdır, önce o kurulur):

```bash
cd api && python -m venv .venv && .venv/Scripts/pip install -e ../cozucu -e ".[test]" && .venv/Scripts/python -m pytest
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
| 09 | Dağıtım: konteynerler, portlar, roller; planlanan bileşenler |

## Belgeler

- [CLAUDE.md](CLAUDE.md): kapsam, mimari, veri modeli, yapım sırası
- [docs/adr/](docs/adr/): mimari karar kayıtları
- [docs/cozucu-plani.md](docs/cozucu-plani.md), [docs/api-plani.md](docs/api-plani.md): adım planları
- [docs/olcumler.md](docs/olcumler.md): çözücü süre ve kalite ölçümleri

## Klasörler

```
cozucu/    Saf Python çözücü paketi (OR-Tools CP-SAT) ve testleri
api/       FastAPI uygulaması (okulapi): çekirdek + modüller
docker/    Konteyner başlangıç betikleri
docs/      Diyagramlar, ADR'ler, planlar, ölçümler
veri/      Test veri setleri (mini, gerçekçi, büyük)
scripts/   Deney ve yardımcı betikler
```

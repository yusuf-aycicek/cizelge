# ADR 0003: Çözücü girdi/çıktı formatı olarak düz dataclass ve JSON

Durum: Kabul edildi (2026-10-06)

## Bağlam

Çözücü veritabanından ve web'den habersiz olmalıdır (CLAUDE.md, mimari karar 3). Yine de
worker'ın veritabanından okuduğu veriyi çözücüye aktarabilmesi, test veri setlerinin dosyada
saklanabilmesi ve komut satırından çalıştırılabilmesi gerekir.

## Karar

- Girdi `CozumGirdisi`, çıktı `CozumSonucu`'dur. İkisi de `cozucu/model.py` içinde standart
  kütüphane dataclass'ı olarak tanımlıdır. Tek okul verisi taşırlar, `okul_id` içermezler.
- Kimlikler metindir (veritabanındaki uuid'ler metin olarak geçirilir).
- Alan adları veri modeliyle aynıdır (`ogretmen_id`, `haftalik_saat`, `gun`, `saat`). Böylece
  worker'daki dönüşüm birebir alan kopyalamasından ibarettir.
- Dosya formatı JSON'dur (`veri_io.py`). Veri setleri `/veri` altında bu formatta durur.
- Basit değer doğrulamaları (pozitif saat, gün aralığı) dataclass'ın kendisinde yapılır.
  Veriler arası tutarlılık (atamanın sınıfı var mı, kapasite aşılıyor mu) ön kontrolün işidir.

## Değerlendirilen alternatifler

- **SQLAlchemy modellerini doğrudan çözücüye vermek:** Çözücü veritabanına bağımlı hale gelir ve
  testlerde veritabanı gerekir. Reddedildi.
- **Pydantic modelleri:** Doğrulama ve JSON desteği güçlüdür, API tarafında zaten kullanılacak.
  Ancak çözücüye ek bir bağımlılık getirir ve ihtiyaç duyulan doğrulama azdır.
- **Ham sözlükler:** Bağımlılık yoktur ama alan adı hataları çalışma anında, geç ortaya çıkar.

## Sonuçlar

- Çözücü yalnızca standart kütüphane ve `ortools` ile çalışır.
- API'nin Pydantic şemaları ile çözücünün dataclass'ları ayrı tutulur. Worker'da küçük bir
  dönüşüm katmanı gerekir. Bu bilinçli bir bedeldir: iki taraf birbirinden bağımsız değişebilir.

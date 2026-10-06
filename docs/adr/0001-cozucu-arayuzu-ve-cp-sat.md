# ADR 0001: Çözücü arayüzü ve CP-SAT seçimi

Durum: Kabul edildi (2026-10-06)

## Bağlam

Haftalık ders programı üretmek bir kısıt sağlama ve optimizasyon problemidir. Bazı kurallar
ihlal edilemez (çakışma yok, gelemez saatleri), bazıları ise mümkün olduğunca az ihlal edilmelidir
(pencere saatleri, tercih edilmeyen saatler). Gerçekçi bir okulda 24 şube, 45 öğretmen ve 40 haftalık
saat vardır. Bu, binlerce ikili değişken ve on binlerce kısıt demektir. Çözüm dakikalar içinde
bulunmalıdır. İleride algoritmayı değiştirme ihtiyacı doğabilir.

## Karar

1. Çözücü `ProgramCozucu` soyut sınıfının arkasında durur: `coz(girdi, sure_siniri_sn) -> CozumSonucu`.
   Girdi ve çıktı düz dataclass'lardır (bkz. ADR 0003). Çağıran kod (worker) yalnızca arayüzü bilir.
2. İlk gerçekleme `CpSatCozucu`, Google OR-Tools'un CP-SAT çözücüsünü kullanır.
3. Çözücü hata durumunda istisna fırlatmaz. Durumu (`optimal`, `uygun`, `cozumsuz`,
   `on_kontrol_hatasi`, `bilinmiyor`) ve okunabilir mesajları sonuçta döner.

## Değerlendirilen alternatifler

| Seçenek | Artı | Eksi |
|---|---|---|
| **CP-SAT (seçildi)** | Boolean ve tam sayı kısıtlarda çok güçlü, çok çekirdekli arama, süre sınırında bulduğu en iyi çözümü verir, çözümsüzlük çekirdeği (assumption) desteği | Model kurma dili öğrenilmeli, ikili paket bağımlılığı |
| ILP (PuLP + CBC) | Klasik, iyi belgelenmiş | "En az bir/en çok bir" türü mantıksal kısıtlarda ve bu boyutta CP-SAT'tan belirgin şekilde yavaş, pencere gibi min/max ifadeleri zahmetli |
| Sezgisel / genetik algoritma | Bağımlılık yok, tam kontrol | Zorunlu kısıtların sağlandığını garanti etmez, çözüm yoksa bunu kanıtlayamaz, ayar yapmak zor |
| Hazır program yazılımları (aSc, FET) | Olgun | Kendi sistemimize gömülemez, çok kiracılı servis olarak sunulamaz |

## Sonuçlar

- Algoritma değişirse yalnızca yeni bir `ProgramCozucu` gerçeklemesi yazılır.
- Çözücü paketi yalnızca `ortools` paketine bağımlıdır. Veritabanı ya da web bağımlılığı yoktur ve
  tek başına test edilebilir.
- CP-SAT çözümün en iyi olduğunu her zaman kanıtlayamayabilir. Süre dolunca `uygun` durumu ve
  bulunan en iyi çözüm döner.

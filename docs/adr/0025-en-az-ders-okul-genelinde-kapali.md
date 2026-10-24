# ADR 0025: "Öğretmenin geldiği günde en az ders" okul genelinde kapalıdır

Durum: Kabul edildi (2026-10-24, K6 sonrası; kullanıcının koyduğu ölçüt ve ölçümle).

## Bağlam

ADR 0024 ile yayılım okul genelinde kapatıldıktan sonra gerçekçi sette öğretmen konforu K6
öncesine dönmedi: eski ölçülerin cezası 123 kaldı (K6 öncesi 69). K6'dan açık kalan tek yeni kural
"öğretmenin geldiği günde en az ders" (k = 2, "Önemli" = ağırlık 3) idi.

Kullanıcının ölçütü:

- Kural kapalıyken pencere ≤ 10 ve eksik boş gün ≤ 12 olursa fark bu kuraldan gelir.
- Bu durumda kuralın önemi önce "Önemsiz"e indirilip ölçülür.
- Önemsizken de K6 öncesine yakın değilse kural okul genelinde kapatılır.

## Ölçüm

Gerçekçi set, 120 sn, 3 tohum, sakin makine. Değerler 120. saniyede, üç tohumun ortalaması.
"Eski ölçüler" = pencere × 3 + tercih etmez × 5 + eksik boş gün × 4.

| Durum | Eski ölçüler | Pencere | Eksik boş gün | Az dersli gün | Art arda gün |
|---|---|---|---|---|---|
| K6 öncesi (P1) | 69 | 8,3 | 11 | — | — |
| Yayılım açık, en az ders "Önemli" | 156 | 23,3 | 19 | 1 | 62,7 |
| Yayılım kapalı, en az ders "Önemli" (ADR 0024) | 123 | 18,3 | 15,3 | 0,3 | 0 |
| Yayılım kapalı, en az ders kapalı | **69** | **8,7** | **10,7** | 2,7 | 0 |
| Yayılım kapalı, en az ders "Önemsiz" | 98 | 13 | 12,7 | 1,7 | 0 |

Ham sonuçlar: `scripts/sonuclar/k6-en-az-ders-kapali.md` ve `k6-en-az-ders-onemsiz.md`.

- Kural kapalıyken fark kapandı: pencere 8,7 ≤ 10, eksik boş gün 10,7 ≤ 12, eski ölçüler P1 ile
  aynı. Kalan farkın kaynağı bu kural.
- "Önemsiz" de yetmedi: pencere 13, eksik boş gün 12,7. Ağırlık 1'de bile çözücü kuralı
  sağlamaya çalışıyor. Az dersli gün 1,7 (kapalıyken 2,7) ile kural az bir kazanç getiriyor,
  karşılığında öğretmen konforundan çok şey alıyor.
- Neden: "en az 2 ders" bir günün bir derslik ucunu yasaklar. Boş gün hedefine ve penceresiz
  güne giden yollar çoğu zaman tek dersli bir günden geçer. Kural bu yolların bir kısmını kapatır.

## Karar

- Okul geneli varsayılan k = 1, yani kural kapalı (`tercihler.VARSAYILAN_GUNLUK_EN_AZ_DERS`).
  Önem seviyesi "Önemli" (3) kalır: kural açıldığında ölçüldüğü ağırlıkla çalışır.
- Okul "Gelişmiş" bölümünde ("Geldiği günde en az kaç ders") 2 ve üstü yazarak bütün okul için
  açabilir. Öğretmen sayfasında öğretmene özel açılabilir.
- Açıklama, kuralın öğretmenlerin boş gününü ve boş saatlerini zorlaştırabileceğini söyler.
- Kalite özeti "az dersli gün"ü yalnızca sıfırdan büyükse gösterir: kural kapalıyken "hiçbir öğretmen
  bir iki ders için gelmiyor" demek yanıltıcı olurdu.
- Yayılımdan (ADR 0024) farkı: yayılım okul genelinde açılamaz. Bu kural ise okul genelinde
  açılabilir, çünkü öğretmen bazlı bir tercihtir ve çoğu okulda birkaç öğretmen için değil, bütün
  kadro için konuşulur. Bedeli açıklamada yazılıdır.

## Değerlendirilen alternatifler

- **"Önemsiz" varsayılan.** Ölçüldü; kullanıcının ölçütünü karşılamadı.
- **Okul genelinde açılamaz (yayılım gibi).** "Bir saat için gelmem" okulun bütün öğretmenleri için
  verdiği bir karar olabilir. Kapatmak bu okulu her öğretmene tek tek özel ayar girmeye zorlardı.

## Sonuçları

- Varsayılan okulda K6'nın esnek kurallarından hiçbiri modele terim eklemez. Öğretmen konforu K6
  öncesiyle aynı.
- Migration gerekmez: k'yı açıkça kaydetmemiş okullar kapalıya geçer. k = 2 kaydetmiş okulun ayarı
  korunur.
- `cozucu.olcum` komutuna `--agirlik TUR=SAYI` eklendi. Bir kuralın okul geneli ağırlığını
  ölçüm için değiştirir.

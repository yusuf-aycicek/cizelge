# Çözücü ölçümleri

Ölçüm tarihi: 2026-10-14. Model: ADR 0007 sonrası (ceza terimleri pozitif değişken), ağırlıklar
CLAUDE.md bölüm 7.

**Ortam:** Windows 11 Pro, Intel 64 bit, 12 mantıksal çekirdek, Python 3.14.7, OR-Tools 9.15.6755,
CP-SAT 8 iş parçacığı (`CpSatCozucu` varsayılanı). Her ölçüm 3 tohumla (0, 1, 2) yapıldı, çünkü çok
iş parçacıklı CP-SAT deterministik değildir. Ölçüm sırasında makinede başka işlemci yükü yoktu.

**Gerçek ceza:** programın bağımsız `kalite.olc` ölçülerinin ağırlıklı toplamı (sınıf boşluğu ×30,
tercih etmez ×5, eksik boş gün ×4, pencere ×3, bölünmüş ders ×2). Her ara çözüm doğrulayıcıdan da
geçirildi.

Ham sonuçlar ve betikler: `scripts/sonuclar/`, `scripts/*.py`, `python -m cozucu.olcum`.

## Veri setleri

| Set | Şube | Öğretmen | Ders ataması | Ders saati | Öğretmen yükü | Müsaitlik kaydı |
|---|---|---|---|---|---|---|
| Mini (`veri/mini.json`) | 3 | 5 | 18 | 71 | 9-18 | 15 |
| Gerçekçi (`veri/gercekci.json`, tohum 1) | 24 | 42 | 330 | 936 | 15-30 | 163 |
| Büyük (`veri/buyuk.json`, tohum 1) | 40 | 75 | 550 | 1560 | 15-30 | 248 |

Gerçekçi ve büyük setlerde sınıflar haftada 38-40 saat (5 × 8 saatlik kapasitenin %95-100'ü).
Setler `cozucu/uretici.py` ile üretildi; çözümü olduğu gizli bir programla garanti edilir. Gizli
programın üretimi gerçekçi sette 34 sn, büyük sette 146 sn sürdü.

## Zamana göre kalite

### Gerçekçi set

| Saniye | Gerçek ceza (ort.) | Tohum 0 / 1 / 2 | Sınıf boşluğu | Pencere | Bölünmüş | Tercih etmez | Eksik boş gün |
|---|---|---|---|---|---|---|---|
| 60 | 448 | 483 / 394 / 466 | 0 | 91 | 36 | 0,3 | 26 |
| 120 | 285 | 282 / 267 / 306 | 0 | 50 | 20 | 0 | 24 |
| 300 | 150 | 139 / 134 / 178 | 0 | 18 | 5 | 0 | 21 |

İlk geçerli program 4,4-8,0 sn'de bulundu. 300. saniyede hiçbir çalıştırma en iyi olduğunu
kanıtlamadı (durum `uygun`).

### Büyük set

| Saniye | Gerçek ceza (ort.) | Tohum 0 / 1 / 2 | Sınıf boşluğu | Pencere | Bölünmüş | Tercih etmez | Eksik boş gün |
|---|---|---|---|---|---|---|---|
| 60 | 1419 | 1437 / 1295 / 1525 | **1,7** (2 / 3 / 0) | 267 | 185 | 11 | 35 |
| 120 | 897 | 874 / 830 / 988 | 0 | 155 | 135 | 4 | 35 |
| 300 | 427 | 354 / 439 / 487 | 0 | 54 | 69 | 1 | 30 |

İlk geçerli program 5,5-15,5 sn'de bulundu.

### Yorum

- Ceza 60 → 120 sn'de üçte bir, 120 → 300 sn'de yarı yarıya düşüyor. Çözücü 300 sn'de de
  yakınsamış değil.
- En öncelikli kural olan sınıf boşluğu gerçekçi sette 60. saniyede 0. Büyük sette 60. saniyede
  hâlâ 2-3 boş saat kalabiliyor, 120. saniyede her tohumda 0.
- Eksik boş gün süreyle çok az değişiyor (gerçekçide 26 → 21). Gerçekçi setteki 42 öğretmenin
  yaklaşık yarısı hedef boş gününe ulaşamıyor. Bunun ne kadarının yapısal olduğu (tam dolu sınıflar,
  15-30 saatlik yükler, gelemez saatleri) ne kadarının arama yetersizliği olduğu bilinmiyor; CP-SAT
  bir alt sınır kanıtlayamıyor (sınır 0'da kalıyor).

### Varsayılan süre sınırı önerisi

**Öneri: 120 sn** (şu an CLAUDE.md'de 60 sn; değişiklik proje sahibinin onayını bekliyor).

- 120 sn, iki sette de sınıf boşluğunu her tohumda sıfırlayan en kısa ölçülen süre.
- Gerçekçi sette ceza 60 sn'ye göre %36 daha düşük (pencere 91 → 50 saat, yani öğretmen başına
  haftada ~2,2 saatten ~1,2 saate).
- Program üretimi kuyruktan worker'da çalıştığı için (mimari karar 1-2) 2 dakikalık bekleme
  arayüzü kilitlemez. Dönem başında birçok okul aynı anda üretim yaparsa toplam süre worker
  sayısıyla ölçeklenir.
- 300 sn kaliteyi bir kez daha yarıya indiriyor. Bu bir "kapsamlı üretim" seçeneği olarak
  sunulabilir (bkz. plan, "Sonraya").

## Model düzeltmesinin etkisi (ADR 0007)

Gerçekçi set, 60 sn, 3 tohum ortalaması:

| Saniye | Önce | Sonra | Sonra: sınıf boşluğu | Sonra: pencere |
|---|---|---|---|---|
| 10 | 1406 | 999 | 0 | 233 |
| 30 | 952 | 667 | 0 | 154 |
| 60 | 703 | 469 | 0 | 99 |

Denenen ama getirisi olmayan iyileştirmeler (gerçekçi set, 120 sn, düzeltme öncesi model):
iki aşamalı çözüm (önce yalnızca zorunlu kısıtlar, ilk çözüm ipucu olarak), `linearization_level=2`,
12 iş parçacığı, pencere kısıtını güçlendirmek (varyant A) ve pencere yardımcılarını tam tanımlamak
(varyant B, %43 daha kötü). Ayrıntılar: `scripts/sonuclar/pencere_varyantlari.md`.

## Gerçekçi set gösterimleri

Tam çıktı: `scripts/sonuclar/gosterimler.md`. Haftalık program örnekleri (9-A ve bir öğretmen)
oradadır.

### En az değişiklikle güncelleme

60 sn'lik bir program temel alındı. Burak Çetin (Almanca) artık Çarşamba gelemiyor; temel programda
o gün 8 dersi var, yani en az 8 ders saati yer değiştirmek zorunda. Toplam 936 ders saati.

| Yöntem | Süre sınırı | Değişen ders saati | İlk çözüm | Durum | Sınıf boşluğu | Pencere | Eksik boş gün |
|---|---|---|---|---|---|---|---|
| Temel programla | 10 sn | 49 | 8,1 sn | uygun | 0 | 130 | 27 |
| Temel programla | 60 sn | **16** | 7,1 sn | **optimal** | 0 | 112 | 26 |
| Sıfırdan | 60 sn | 829 | 6,2 sn | uygun | 0 | 76 | 27 |

- Temel programla 60 sn'de çözücü en iyi güncellemeyi buldu ve en iyi olduğunu kanıtladı: 16 ders
  saati değişti (alt sınır 8). Sıfırdan üretim 936 saatin 829'unu değiştiriyor.
- 10 sn yetmiyor: güncelleme 49 değişiklikte kalıyor. Güncelleme için de varsayılan süre
  kullanılmalı.
- Sıfırdan üretimin penceresi daha düşük (76'ya karşı 112). Bu, "programı dağıtmama" kararının
  bilinçli bedeli (değişiklik ağırlığı 8, pencere 3).

### Bilerek çözümsüz örnek

9-A tam dolu (40 saat); 14 öğretmeninin hepsi Pazartesi 1. saatte gelemez. Ön kontrolden geçer
(her öğretmenin ve sınıfın kapasitesi tek tek yeter) ama o hücreyi kimse dolduramaz.

| Ölçüm | Sonuç |
|---|---|
| Ana çözücü (esnek hedefle, 60 sn) | `bilinmiyor`: ne çözüm ne çözümsüzlük kanıtı; çelişki analizi hiç çalışmadı |
| Yalnızca zorunlu kısıtlar (60 sn) | `cozumsuz`, **18,6 sn** |
| Çelişki analizi doğrudan (bütçe 30 sn) | **30,4 sn**, bütçe doldu; 690 maddelik küme döndü (30 gelemez, 330 günlük sınır, 330 haftalık saat). Gerçek çelişki ~29 kural (9-A'nın 14 öğretmeninin gelemez saatleri + 9-A'nın 15 dersinin haftalık saati). |

Sonuç: çözülemezlik açıklaması küçük setlerde ve mini sette doğru çalışıyor, ama gerçekçi
büyüklükte bu örnekte kullanıcıya bir açıklama üretemiyor. Önerilen düzeltmeler planda
("Sonraya" ve "Bilinen açıklar").

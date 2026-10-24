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

- Eksik boş gün yüksek kalmasının bir hata değil, ağırlık tercihi olduğuna karar verildi
  (2026-10-14): boş gün (4) sınıf boşluğundan (30), en az değişiklikten (8) ve tercih etmezden (5)
  hafif. Müdürün boş güne verdiği öneme göre ayarlanacak (CLAUDE.md bölüm 10, açık sorular).

### Varsayılan süre sınırı

**Karar (2026-10-14): 120 sn.** CLAUDE.md bölüm 7 ve `arayuz.VARSAYILAN_SURE_SINIRI_SN` güncellendi.
Gerekçe:

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

Sonuç (ilk ölçüm): çözülemezlik açıklaması küçük setlerde ve mini sette doğru çalışıyordu, ama
gerçekçi büyüklükte bu örnekte kullanıcıya bir açıklama üretemiyordu.

#### Düzeltmelerden sonra (2026-10-14)

İki düzeltme yapıldı: sınıf müsaitliği ön kontrolü ve `bilinmiyor` durumunda yalnızca zorunlu
kısıtlarla ikinci kontrol. Aynı örnek (`scripts/cozumsuz_teshisi.py`,
`scripts/sonuclar/cozumsuz_sonrasi.md`):

| Ölçüm | Sonuç |
|---|---|
| Kullanıcının göreceği | `on_kontrol_hatasi`, **0,10 sn** |
| Ön kontrol kapalıyken (ikinci kontrol yolunu sınamak için) | `cozumsuz`, toplam 164 sn = ana çözüm 120 sn (`bilinmiyor`) + ikinci kontrol 12,6 sn (çözümsüz) + çelişki analizi ~31 sn (690 maddelik küme) |

Kullanıcının gördüğü mesaj:

> 9-A'nın haftada 40 saat dersi var, ama öğretmenlerinden en az birinin gelebildiği yalnızca 39
> saat var. Şu saatlerde öğretmenlerinin hiçbiri gelemiyor: Pazartesi 1. saat.

İkinci kontrol, ön kontrolün yakalayamadığı (sınıflar arası etkileşimden doğan) çözümsüzlüklerde
"süre yetmedi" yerine doğru durumu (`cozumsuz`) bildiriyor. Ama çelişki analizi büyük çekirdekleri
30 sn içinde küçültemiyor; hızlandırılması sonraya bırakıldı (plan, "Sonraya").

## Blok dersler (K4, 2026-10-23)

Aynı makine ve ölçüm yöntemi (3 tohum, 8 iş parçacığı, 120 sn). Bloklu: okul önerisi açık
(gerçekçi sette 330 atamanın hepsi bloklu: 162 × "2", 66 × "2+2", 48 × "1", 30 × "2+2+2", 24 ×
"2+2+1"; büyükte 550/550). Bloksuz: `python -m cozucu.olcum <set> --bloksuz` (K4 öncesi davranış,
bugünkü modelle). Ham sonuçlar: `scripts/sonuclar/k4-*.md`.

| Set | Kip | İlk çözüm | 60 sn gerçek ceza (tohum 0/1/2) | 120 sn gerçek ceza (ort.) | 120 sn sınıf boşluğu | 120 sn pencere (ort.) | 120 sn bölünmüş (ort.) |
|---|---|---|---|---|---|---|---|
| Gerçekçi | bloksuz | 5,1-9,5 sn | 498 / 753 / 524 | 432 | 0 / 0 / 0 | 87 | 35 |
| Gerçekçi | bloklu | 4,3-20,4 sn | 168 / 263 / 126 | **88** | 0 / 0 / 0 | 15 | 0 |
| Büyük | bloksuz | 14,8-29,0 sn | 2638 / 2193 / 2024 | 1530 | 8 / 3 / 0 | 293 | 145 |
| Büyük | bloklu | **43,6-72,2 sn** | yok / 1483 / yok | 834 | 0 / 4 / 9 | 167 | 0 |

Yalnızca zorunlu kurallarla (bütün esnek ağırlıklar 0) büyük set, bloklu: ilk (ve en iyi) çözüm
24,7 / 57,3 / 10,9 sn.

**Yorum:**
- Kalite iki sette de belirgin biçimde iyi: blok, bölünmüş dersi sıfırlıyor ve arama uzayını
  daralttığı için pencere de azalıyor. Gerçekçi sette 120. saniyede ceza ~5 kat düşük.
- **Kötüleşme: büyük sette ilk çözüm geç geliyor.** Süre 60 sn olsaydı iki tohumda program
  çıkmazdı; 120 sn'de sınıf boşluğu iki tohumda sıfırlanmadı (4, 9). Neden: büyük sette şubeler
  kapasitenin %95-100'ü kadar dolu ve atamaların yarısı "2" (iki saat aynı gün art arda) olmak
  zorunda; zorunlu kısıtları sağlayan bir yerleşim bulmak bile 11-57 sn sürüyor (yalnızca
  zorunlu kurallarla ölçüldü). Amaç fonksiyonu bunu ayrıca yavaşlatıyor.
- Bloksuz büyük sette de 120 sn'de sınıf boşluğu iki tohumda sıfır değil (8, 3); 2026-10-14
  ölçümünde 0/0/0 idi. Arada model büyüdü (özel ayarlar, gün uzunluğu, iki yönlü boş gün).
  Aynı makinede tekrar ölçülerek ayrıca bakılmalı.
- Öneri (kullanıcıya soruldu, uygulanmadı): iki aşamalı çözüm. Önce yalnızca zorunlu
  kısıtlarla (süre bütçesinin bir kısmıyla) uygun bir yerleşim bulunur, sonra esnek kurallarla bu
  yerleşim başlangıç ipucu olarak verilip iyileştirilir (CLAUDE.md bölüm 7'de anılan
  iyileştirme). Ayrıca büyük okullarda (≥ 35 şube) varsayılan sürenin 180 sn olması ölçülerek
  değerlendirilebilir.

**Düzeltme (2026-10-24):** bu bölümdeki tek aşamalı sayılar sakin makinede tekrarlanamadı (aşağıda,
"İki aşamalı çözüm"). Bloksuz büyük setteki "kötüleşme" ve bloklu büyük setteki 44-72 sn'lik ilk
çözüm büyük olasılıkla ölçüm sırasında makinede çalışan başka işlerden (testler) geliyordu.

## Bloksuz büyük set: kötüleşme yok (2026-10-24)

K4b'de bloksuz büyük set 120. saniyede 1530 ceza ve 8 / 3 / 0 sınıf boşluğu vermişti (2026-10-14'te
897, 0 / 0 / 0). Neden aranırken her commit'in çözücüsü ayrı ayrı, aynı veriyle, sakin makinede
ölçüldü (3 tohum, 120 sn; `scripts/sonuclar/p1-bisect.md`):

| Commit | Değişiklik | İlk çözüm | 120 sn ceza (ort.) | 120 sn sınıf boşluğu |
|---|---|---|---|---|
| 6c66448 | 2026-10-14 ölçümü | 8,8-13,3 sn | 789 | 0 / 0 / 0 |
| d96e3e7 | K1 kapsam | 9,4-13,0 sn | 753 | 0 / 0 / 0 |
| 8f6ac07 | K2a iki yönlü boş gün | 9,0-14,3 sn | 742 | 0 / 0 / 0 |
| 0957d0b | K2e boş gün hedefi | 7,6-13,7 sn | 773 | 0 / 0 / 0 |
| b17d4f8 | K3a gün uzunluğu, öğle arası | 8,5-13,2 sn | 755 | 0 / 0 / 0 |
| 550323b | K4a blok (bloksuz kipte) | 8,8-11,9 sn | 805 | 0 / 0 / 0 |

Hiçbir model değişikliği kötüleştirmedi; 120 sn'de her commit her tohumda sınıf boşluğunu
sıfırlıyor. K4b'deki fark ölçüm ortamındandı. Ders: ölçüm sırasında makinede başka iş
çalıştırılmaz (CLAUDE.md bölüm 7'ye eklendi).

## İki aşamalı çözüm (P1, 2026-10-24)

Önce yalnızca zorunlu kısıtlarla, amaçsız ve ilk programda durarak bir program bulunur; sonra o
program tam ipucu olarak verilip esnek kurallarla kalan sürede iyileştirilir (ADR 0018). Aynı
makine, sakin; 3 tohum, 8 iş parçacığı. "Sınır" sütunları süre sınırı o değerle **ayrı ayrı**
çalıştırılarak ölçüldü (iki aşamalıda aşama 1'in payı süre sınırına göre olduğu için). Tek aşamalı
satırlarda 30 ve 60 sn, 120 sn'lik çalıştırmanın o anki durumudur (tek aşamalıda ikisi aynıdır).
Hücre: ortalama gerçek ceza (sınıf boşluğu, tohum 0 / 1 / 2). Ham sonuçlar: `scripts/sonuclar/p1-*.md`.

### İlk aşamanın payı

Büyük set, bloklu. Aşama 1 ilk programda durduğu için pay yalnızca ilk program geç gelirse sınırlar.

| Pay | Sınır 120 sn: ilk çözüm | 120 sn | Sınır 30 sn: ilk çözüm | 30 sn |
|---|---|---|---|---|
| 0,25 | 9,5-24,9 sn | 234 (0 / 0 / 0) | | |
| 0,5 | 10,1-23,6 sn | 242 (0 / 0 / 0) | 1 tohumda **program yok** | 1536 (16 / yok / 16) |
| 0,75 | | | 10,7-23,9 sn | 1927 (20 / 30 / 14) |
| 1 | 10,0-24,9 sn | 258 (0 / 0 / 0) | 10,1-24,4 sn | 1645 (12 / 30 / 0) |

**Karar: pay 1** (`cpsat.UYGUNLUK_PAYI`). 120 sn'de paylar arasında fark yok (aşama 1 her tohumda
25 sn içinde bitiyor); 30 sn'de 0,5 bir tohumda programsız bıraktı. Aşama 1 zaten ilk programda
durduğu için ona bütün süreyi tanımak, "hiç program yok" olasılığını en aza indirir; kalan süre
iyileştirmeye gider.

### Önceki ölçümlerle karşılaştırma

| Set | Kip | Yöntem | İlk çözüm | 30 sn | 60 sn | 120 sn |
|---|---|---|---|---|---|---|
| Gerçekçi | bloksuz | 2026-10-14 (tek) | 4,4-8,0 sn | | 448 (0) | 285 (0 / 0 / 0) |
| Gerçekçi | bloksuz | K4b (tek) | 5,1-9,5 sn | 869 (0 / 0 / 0) | 592 (0 / 0 / 0) | 432 (0 / 0 / 0) |
| Gerçekçi | bloksuz | **iki aşamalı** | **2,2-3,3 sn** | 617 (0 / 0 / 0) | 384 (0 / 0 / 0) | **240** (0 / 0 / 0) |
| Gerçekçi | bloklu | K4b (tek) | 4,3-20,4 sn | 473 (0 / 6 / 0) | 186 (0 / 0 / 0) | 88 (0 / 0 / 0) |
| Gerçekçi | bloklu | bugün, tek | 4,3-14,1 sn | 305 (0 / 2 / 0) | 140 (0 / 0 / 0) | 67 (0 / 0 / 0) |
| Gerçekçi | bloklu | **iki aşamalı** | 5,2-8,9 sn | 296 (3 / 0 / 0) | 161 (0 / 0 / 0) | 69 (0 / 0 / 0) |
| Büyük | bloksuz | 2026-10-14 (tek) | 5,5-15,5 sn | | 1419 (2 / 3 / 0) | 897 (0 / 0 / 0) |
| Büyük | bloksuz | K4b (tek) | 14,8-29,0 sn | 3077 (33 / 18 / 23) | 2285 (21 / 11 / 0) | 1530 (8 / 3 / 0) |
| Büyük | bloksuz | bugün, tek (K4a) | 8,8-11,9 sn | 2130 (13 / 16 / 0) | 1217 (1 / 0 / 0) | 805 (0 / 0 / 0) |
| Büyük | bloksuz | **iki aşamalı** | **3,9-5,2 sn** | 1812 (3 / 0 / 0) | 1299 (4 / 0 / 0) | **737** (0 / 0 / 0) |
| Büyük | bloklu | K4b (tek) | 43,6-72,2 sn | program yok | 1 tohumda: 1483 (16) | 834 (0 / 4 / 9) |
| Büyük | bloklu | bugün, tek | 23,5-29,2 sn | 1864 (24 / 18 / 18) | 749 (6 / 7 / 3) | 268 (0 / 2 / 0) |
| Büyük | bloklu | **iki aşamalı** | **9,2-25,5 sn** | 1889 (17 / 30 / 16) | **625** (1 / 5 / 0) | **253** (1 / 0 / 0) |

Büyük set, bloklu, iki aşamalı, sınır 180 sn: 120. saniyede 264 (0 / 0 / 0), 180. saniyede
**150** (0 / 0 / 0).

**Yorum:**
- K4b'nin kötü sayıları büyük ölçüde ölçüm ortamındandı: sakin makinede tek aşamalı çözüm de büyük
  bloklu sette 120 sn'de 268 ceza veriyor (K4b'de 834).
- İki aşamalı çözüm **ilk programı daha erken** verir: bloksuz büyük sette 9-12 sn → 4-5 sn, bloklu
  büyük sette 23-29 sn → 9-25 sn. Bu en çok kısa sürede önemli: 30 sn'lik sınırda tek aşamalıda
  ilk program 24-29 sn'de, yani sınırın hemen önünde geliyordu.
- **Kalite** 120 sn'de iki yöntemde benzer (gerçekçi bloklu 67 / 69, büyük bloklu 268 / 253);
  bloksuz setlerde iki aşamalı belirgin iyi (432 → 240, 805 → 737). Büyük bloklu sette 60 sn'de
  ceza 749 → 625.
- Pay 1 ile aşama 1 hiç bitmezse aşama 2'ye süre kalmaz. Bu durumda zaten hiç program yoktur;
  tek aşamalı model aynı sürede daha zor bir problemi çözmeye çalışırdı.

### Varsayılan süre

**Karar: 120 sn kalır, büyük okullar için de artırılmaz.** İki aşamalı çözümle büyük bloklu sette
120 sn'lik 15 çalıştırmanın (pay ölçümleri dahil) 14'ünde sınıf boşluğu 0; birinde 1 saat. Gerçekçi
sette hepsi 0. 180 sn cezayı yarıya yakın düşürüyor (264 → 150) ama sınıf boşluğu zaten 0; bu fark
öğretmen pencerelerindedir. Daha iyi sonuç isteyen büyük okul için "Uzun" (5 dk) seçeneği vardır.
Süre yetmezse arayüz tek tıkla daha uzun süreyle yeniden denemeyi önerir (ADR 0018).

### "Hızlı" uyarısının eşiği

Gerçekçi sette (24 şube, bloklu) 30 sn'lik sınırda ilk program her tohumda 9 sn içinde geldi; büyük
sette (40 şube) 10-25 sn'de, sınıf boşluğu 16-30 saatle. Arayüz **30 ve daha çok şubesi** olan
okulda "Hızlı" seçeneğinin yanında "bu süre program bulmaya yetmeyebilir" der
(`ProgramSayfasi.HIZLI_YETMEYEBILIR_SUBE`): ilk programın sürenin yarısını (15 sn) geçtiği yer
ölçülen iki noktanın arasındadır. Okulun sunucusu bu makineden yavaşsa sınır daha erken aşılır.

## İkincil kurallar (K6, 2026-10-24)

Gerçekçi set, bloklu, iki aşamalı, 3 tohum, sakin makine. Varsayılanla açık gelen iki yeni kural:
öğretmenin geldiği günde en az 2 ders (ağırlık 3) ve aynı dersin günlere yayılması (ağırlık 2).
Saat tercihi okul genelinde yoktur, ceza getirmez. Ham sonuç: `scripts/sonuclar/k6-gercekci-bloklu.md`.

| 120 sn | Toplam ceza | Sınıf boşluğu | Pencere | Tercih etmez | Eksik boş gün | Az dersli gün | Art arda gün |
|---|---|---|---|---|---|---|---|
| P1 (K6 öncesi) | 82 / 67 / 58 (ort. 69) | 0 / 0 / 0 | 10 / 9 / 6 | 0 / 0 / 0 | 13 / 10 / 10 | (ölçülmüyordu) | (ölçülmüyordu) |
| K6 | 337 / 269 / 247 (ort. 284) | 0 / 0 / 0 | 34 / 18 / 18 | 2 / 4 / 0 | 24 / 17 / 16 | 1 / 1 / 1 | 63 / 62 / 63 |

- İlk program 5,1-8,4 sn (P1: 5,2-8,9 sn); 60 sn'de de sınıf boşluğu her tohumda 0. Süre sınırı
  kararı (120 sn) değişmez.
- Toplam ceza yeni terimleri içerdiği için doğrudan karşılaştırılamaz. Eski ölçüler üzerinden
  (pencere × 3 + tercih etmez × 5 + eksik boş gün × 4): ortalama 69 → 156. **Öğretmen konforu
  kötüleşti:** pencere 8 → 23, eksik boş gün 11 → 19.
- Bunun nedeni yayılım kuralı: 120 sn sonunda bile 62-63 art arda gün çifti kalıyor (ceza ~125,
  toplamın yarısından fazlası). Kural boş gün ve pencereyle çatışıyor: öğretmeni dört güne
  sıkıştırmak aynı dersi art arda günlere iter; 3 bloklu (2+2+2, 2+2+1) bir ders 5 günlük haftada
  ancak pazartesi-çarşamba-cuma ile yayılabilir.
- "Günde en az ders" ucuz: her tohumda 1 gün kalıyor, boş gün hedefiyle aynı yönde çalışıyor.
- **Kullanıcı kararı:** yayılım okul genelinde kapalı, yalnızca derse özel açılır (ADR 0024).
  Yeniden ölçüm aşağıda.

### Yayılım okul genelinde kapalı (ADR 0024, 2026-10-24)

Aynı koşullar (gerçekçi set, bloklu, iki aşamalı, 3 tohum, sakin makine). Ham sonuç:
`scripts/sonuclar/k6-yayilim-kapali.md`. "Eski ölçüler" = pencere × 3 + tercih etmez × 5 + eksik
boş gün × 4 (üç ölçümde de aynı ağırlıklar, doğrudan karşılaştırılabilir).

| 120 sn | Toplam ceza | Eski ölçüler (ort.) | Sınıf boşluğu | Pencere | Tercih etmez | Eksik boş gün | Az dersli gün | Art arda gün |
|---|---|---|---|---|---|---|---|---|
| P1 (K6 öncesi) | 82 / 67 / 58 | 69 | 0 / 0 / 0 | 10 / 9 / 6 | 0 / 0 / 0 | 13 / 10 / 10 | — | — |
| K6 (yayılım açık) | 337 / 269 / 247 | 156 | 0 / 0 / 0 | 34 / 18 / 18 | 2 / 4 / 0 | 24 / 17 / 16 | 1 / 1 / 1 | 63 / 62 / 63 |
| ADR 0024 (yayılım kapalı) | 136 / 122 / 114 | 123 | 0 / 0 / 0 | 24 / 16 / 15 | 0 / 3 / 1 | 16 / 14 / 16 | 0 / 1 / 0 | 0 / 0 / 0 |

- Sınıf boşluğu her tohumda 60 ve 120 sn'de 0; ilk program 5,5-8,5 sn. Süre sınırı kararı değişmez.
- Eski ölçüler 156'dan 123'e indi, ama P1'in (69) üstünde kaldı: pencere ortalama 8 → 18,
  eksik boş gün 11 → 15. Açık kalan K6 kuralı "günde en az ders" (her tohumda 0-1 gün kalıyor,
  yani çözücü ona uyuyor). Farkın büyük olasılıkla bu kuraldan ve modelin büyümesinden geldiği
  düşünülüyor; kural kapatılarak ayrıca ölçülmedi.

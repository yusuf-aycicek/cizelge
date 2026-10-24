# Gece raporu (2026-10-24)

Kullanıcı yokken yapılan iş: Parça 1 (iki aşamalı çözüm) ve Parça 2 (K5: şube grupları ve
istisnalar). Her alt parça testleri geçince commit edildi; durum ayrıca `docs/arayuz-plani.md`
bölüm 7'de.

## Durum

| Parça | Durum | Commit |
|---|---|---|
| P1 İki aşamalı çözüm, "süre yetmedi" | Bitti | (bu commit) |
| K5 Şube grupları ve istisnalar | Sırada | |

## Parça 1: iki aşamalı çözüm

**Ne yapıldı:**
- Çözücü önce yalnızca zorunlu kısıtlarla, amaçsız, ilk programda durarak bir program arıyor; sonra
  o program tam ipucu olarak verilip esnek kurallarla kalan sürede iyileştiriliyor (ADR 0018).
- Aşama 1 çözümsüzlüğü kanıtlarsa doğrudan çelişki analizine geçiliyor. Aşama 2 daha iyisini
  bulamazsa aşama 1'in programı dönüyor.
- Temel program aşama 1'e de ipucu; kilitler iki aşamada da zorunlu (testli).
- Arayüz: süre yetmezse ("bilinmiyor") "Bu süre okulunuz için yetmedi" ve tek tıkla bir sonraki uzun
  süreyle yeniden deneme (aynı ad, aynı temel program); 30 ve daha çok şubede "Hızlı"nın yanında
  uyarı.

**Ölçüm** (sakin makine, 3 tohum; ayrıntı `docs/olcumler.md` "İki aşamalı çözüm"):

| Set | Kip | Önceki (K4b): ilk çözüm / 120 sn ceza (sınıf boşluğu) | Bugün tek aşamalı | İki aşamalı: ilk çözüm | 30 sn | 60 sn | 120 sn |
|---|---|---|---|---|---|---|---|
| Gerçekçi | bloksuz | 5-10 sn / 432 (0/0/0) | | 2-3 sn | 617 (0/0/0) | 384 (0/0/0) | 240 (0/0/0) |
| Gerçekçi | bloklu | 4-20 sn / 88 (0/0/0) | 4-14 sn / 67 | 5-9 sn | 296 (3/0/0) | 161 (0/0/0) | 69 (0/0/0) |
| Büyük | bloksuz | 15-29 sn / 1530 (8/3/0) | 9-12 sn / 805 | 4-5 sn | 1812 (3/0/0) | 1299 (4/0/0) | 737 (0/0/0) |
| Büyük | bloklu | 44-72 sn / 834 (0/4/9) | 23-29 sn / 268 | 9-25 sn | 1889 (17/30/16) | 625 (1/5/0) | 253 (1/0/0) |

## Benim yerime verdiğim kararlar

1. **Pay 1:** aşama 1 ilk programda durduğu için ona bütün süre tanındı. 120 sn'de 0,25 / 0,5 / 1
   aynı; 30 sn'de 0,5 büyük sette bir tohumda programsız bıraktı.
2. **Varsayılan süre 120 sn kaldı** (büyük okullar için de): iki aşamalıyla büyük bloklu sette 120
   sn'lik 15 çalıştırmanın 14'ünde sınıf boşluğu 0, birinde 1 saat. 180 sn cezayı 264 → 150
   düşürüyor (öğretmen pencereleri); bunun için "Uzun" seçeneği var.
3. **"Hızlı" uyarı eşiği 30 şube:** 24 şubede ilk program ≤ 9 sn, 40 şubede 10-25 sn.
4. **"Süre yetmedi"de önerilen süreler:** 30 sn → 2 dk → 5 dk → 10 dk (en uzun seçenekten sonra
   10 dk; API üst sınırı 1 saat).

## Bloksuz büyük setin "kötüleşmesi"

Kodda neden yok. 2026-10-14'ten bu yana çözücüye dokunan 6 commit sakin makinede ayrı ayrı ölçüldü;
hepsi 120 sn'de 742-805 ceza ve 0 / 0 / 0 sınıf boşluğu veriyor (K4a bloksuz kipte dahil). K4b'deki
1530 ve 8 / 3 / 0 ölçüm ortamındandı (büyük olasılıkla o sırada makinede testler çalışıyordu).
K4b'nin bloklu sayıları da aynı nedenle kötü çıkmıştı: sakin makinede tek aşamalı da 120 sn'de
268 (K4b'de 834). İki aşamalı çözüm bu yüzden "kötüleşmeyi gidermek" için gerekmedi; yine de ilk
programı daha erken veriyor. CLAUDE.md'ye "ölçüm sırasında makinede başka iş çalışmaz" eklendi.

## Ekran görüntüleri

- `docs/ekranlar/p1/01-sure-yetmedi.png`: süre yetmedi paneli ve 36 şubeli okulda "Hızlı" uyarısı
  (geçici deneme okulu; betik bitince silindi).

## Bilinen sorunlar ve onayını bekleyenler

- Yok (P1).

## Sıradaki adım

K5: şube grupları ve istisnalar (docs/kisisellestirme-plani.md bölüm 6).

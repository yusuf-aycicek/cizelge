# Gece raporu (2026-10-24)

Kullanıcı yokken yapılan iş: Parça 1 (iki aşamalı çözüm) ve Parça 2 (K5: şube grupları ve
istisnalar). Her alt parça testleri geçince commit edildi; durum ayrıca `docs/arayuz-plani.md`
bölüm 7'de. Git'e push yapılmadı.

> Not (teslim, 2026-10-24): geliştirme adımlarında alınan ekran görüntüleri (`docs/ekranlar/<adım>/`)
> teslimde depodan çıkarıldı; `a6c50df` ve önceki commit'lerde durur. Depoda yalnızca
> `docs/ekranlar/teslim/` kaldı.

## Durum

| Parça | Durum | Commit |
|---|---|---|
| P1 İki aşamalı çözüm, "süre yetmedi" | Bitti | eef0120 |
| K5a Şube grupları, gruba bağlı şablon, istisnalar, grup kapsamı (çözücü, API, arayüz) | Bitti | b20a31d |
| K5b Örnek okulda deneme, ekran görüntüleri, bu rapor | Bitti | (bu commit) |

Son denetimler (her commit'in kendi hâliyle): çözücü 252 test, API 591, web 296 (tip ve lint
0), taşma denetimi 0 (48 görünüm, yeni grup / şablon / istisna sayfaları dahil), kontrast testi
web testlerinin içinde (yeni uyarı rengi çiftleri eklendi). Mutasyon: P1 çözücü 8/8, arayüz 5/5;
K5 API 15/15, çözücü 1/1, arayüz 11/11 (ilk turda 2 mutasyon kaçtı, test eklendi).

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

**Ölçüm** (sakin makine, 3 tohum; ayrıntı `docs/olcumler.md` "İki aşamalı çözüm", ham sonuçlar
`scripts/sonuclar/p1-*.md`). 30 / 60 / 120 sn sütunları süre sınırı o değerle ayrı ayrı çalıştırılarak
ölçüldü; hücre: ortalama ceza (sınıf boşluğu, tohum 0 / 1 / 2).

| Set | Kip | Önceki (K4b): ilk çözüm / 120 sn | Bugün tek aşamalı: ilk çözüm / 120 sn | İki aşamalı: ilk çözüm | 30 sn | 60 sn | 120 sn |
|---|---|---|---|---|---|---|---|
| Gerçekçi | bloksuz | 5-10 sn / 432 (0/0/0) | | 2-3 sn | 617 (0/0/0) | 384 (0/0/0) | 240 (0/0/0) |
| Gerçekçi | bloklu | 4-20 sn / 88 (0/0/0) | 4-14 sn / 67 (0/0/0) | 5-9 sn | 296 (3/0/0) | 161 (0/0/0) | 69 (0/0/0) |
| Büyük | bloksuz | 15-29 sn / 1530 (8/3/0) | 9-12 sn / 805 (0/0/0) | 4-5 sn | 1812 (3/0/0) | 1299 (4/0/0) | 737 (0/0/0) |
| Büyük | bloklu | 44-72 sn / 834 (0/4/9) | 23-29 sn / 268 (0/2/0) | 9-25 sn | 1889 (17/30/16) | 625 (1/5/0) | 253 (1/0/0) |

Büyük bloklu, 180 sn: 150 ceza (0/0/0).

**Dürüst yorum:** K4b'nin kötü sayılarının çoğu ölçüm ortamındandı (aşağıda). Sakin makinede iki
aşamalı çözümün kazancı ilk programın erken gelmesi (büyük bloklu 23-29 → 9-25 sn, bloksuz 9-12 →
4-5 sn) ve 60 sn'de daha iyi program (büyük bloklu 749 → 625); 120 sn'de bloklu setlerde kalite aynı
düzeyde, bloksuz setlerde daha iyi.

## Bloksuz büyük setin "kötüleşmesi"

Kodda neden yok. 2026-10-14'ten bu yana çözücüye dokunan 6 commit sakin makinede ayrı ayrı ölçüldü;
hepsi 120 sn'de 742-805 ceza ve 0 / 0 / 0 sınıf boşluğu veriyor (K4a bloksuz kipte dahil). K4b'deki
1530 ve 8 / 3 / 0 ölçüm ortamındandı (büyük olasılıkla o sırada makinede testler çalışıyordu).
İki aşamalı çözüm bu yüzden "kötüleşmeyi gidermek" için gerekmedi; yine de bloksuz büyük sette 120
sn'de 805 → 737. CLAUDE.md'ye "ölçüm sırasında makinede başka iş çalışmaz" eklendi.

## Parça 2: K5 şube grupları ve istisnalar

- **Şube grupları:** Sınıflar sayfasında grup kartı (ekle, adını değiştir, sil) ve her şube
  satırında grup seçimi (yalnızca aynı seviyenin grupları).
- **Şablon seviyeye ya da gruba:** Seviye şablonu sayfasında "Şablon" seçimi ("9. sınıflar (1
  şube)", "9 Fen grubu (1 şube)"); şablonun kime ait olduğu ve hangi şubelerin kendi grubunun
  şablonunu kullandığı yazıyor. Var olan seviye şablonları migration'da olduğu gibi korunuyor (testli).
- **İstisnalar:** ders dağılımında şubeden ders kaldırılırken "9-B bu dersi hiç almasın (şablon
  yeniden uygulandığında geri gelmez)" kutusu; şablonda olmayan ders eklerken "ek ders olarak
  kaydet"; şube panelinde "Bu şubeye özel" listesi ve "Geri al". Şablon raporu atlanan ve ek
  dersleri, dokunulmayan şubeleri söylüyor.
- **Grup kapsamı:** günlük sınır (N) ve dağılım şekli gruba (ve ders + gruba) özel verilebiliyor;
  öncelik ders + şube > ders + grup > ders > şube > grup > okul, çözücüde ve API'de testli.
- **Örnek okulda deneme:** "9 Fen" grubu, grubun şablonu, 9-B'ye "Coğrafya almaz", şablon yeniden
  uygulandı (istisna korundu, raporda göründü), program üretildi (9-A Matematik gruba özel 3+3,
  9-B 2+2+2; ceza 0, en iyisi kanıtlandı). Önce `pg_dump` yedeği; sonra her şey geri alındı ve
  veritabanı yedekle tablo tablo birebir aynı çıktı.

## Ekran görüntüleri

- `docs/ekranlar/p1/01-sure-yetmedi.png`: süre yetmedi paneli ve 36 şubeli okulda "Hızlı" uyarısı
  (geçici deneme okulu; betik bitince silindi).
- `docs/ekranlar/k5/01-siniflar-gruplar.png`: grup sütunu ve "Şube grupları" kartı.
- `docs/ekranlar/k5/02-grup-sablonu-uygulandi.png`: 9 Fen grubunun şablonu ve uygulama raporu.
- `docs/ekranlar/k5/03-kaldirma-penceresi.png`: "9-B bu dersi hiç almasın" kutusu.
- `docs/ekranlar/k5/04-sube-istisnasi.png`: "Bu şubeye özel: Coğrafya almaz".
- `docs/ekranlar/k5/05-yeniden-uygulama-raporu.png`: yeniden uygulamada istisna korundu.
- `docs/ekranlar/k5/06-ozel-ayarlar.png`: okul ayarlarında "9 Fen grubu · Matematik" özel ayarları.
- `docs/ekranlar/k5/07-cizelge-9a.png`: 9-A çizelgesi, Matematik 3+3.

## Benim yerime verdiğim kararlar

**P1:**
1. **Pay 1:** aşama 1 ilk programda durduğu için ona bütün süre tanındı. 120 sn'de 0,25 / 0,5 / 1
   aynı; 30 sn'de 0,5 büyük sette bir tohumda programsız bıraktı.
2. **Varsayılan süre 120 sn kaldı** (büyük okullar için de): iki aşamalıyla büyük bloklu sette 120
   sn'lik 15 çalıştırmanın 14'ünde sınıf boşluğu 0, birinde 1 saat. 180 sn cezayı 264 → 150
   düşürüyor (öğretmen pencereleri); bunun için "Uzun" (5 dk) seçeneği var.
3. **"Hızlı" uyarı eşiği 30 şube:** 24 şubede ilk program ≤ 9 sn, 40 şubede 10-25 sn.
4. **"Süre yetmedi"de önerilen süreler:** 30 sn → 2 dk → 5 dk → 10 dk.

**K5** (ayrıntı: `docs/kisisellestirme-plani.md` bölüm 6, "K5'te netleşen ayrıntılar"):
5. **Grup şablonu seviyenin şablonunun yerine geçer**, üstüne eklenmez (tasarımdaki gibi); boş grup
   şablonunda grubun şubeleri seviyeninkini kullanır. Gerekçe: tek ve öngörülebilir kural.
6. **Şablon yalnızca onu kullanan şubelere uygulanır;** seviyenin şablonu gruplu şubelere dokunmaz
   (rapor adıyla söyler).
7. **İstisna ders dağılımını da değiştirir:** "almaz" dersi kaldırır, kalkınca şablondaki saatle geri
   ekler; "ek" dersi ekler, kalkınca ders şubede kalır (veri silinmesin). Ek ders dağılımdan
   silinirse "ek" istisnası da silinir. Gerekçe: kullanıcı iki ayrı iş yapmasın.
8. **"Hiç almasın" kutusu işaretli gelir** (ders şubenin şablonundaysa): şablondaki dersi bir şubeden
   kaldıran kullanıcı büyük olasılıkla şablon yeniden uygulanınca geri gelmesini istemez.
9. **Grubun seviyesi değiştirilemez;** gruptaki şubenin seviyesi de (önce gruptan çıkarılır).
10. **Grup silinince** şubeler grupsuz kalır, grubun şablonu ve gruba özel ayarlar silinir; arayüz
    silmeden önce söyler.
11. **Gruba özel kural ayarı için ayrı ekran yok** (K4'teki ders + şube kararı gibi): API'de ve okul
    ayarlarındaki özel ayarların özetinde var.
12. Migration adları: `cekirdek_0007_sube_grubu` (0006 K3'te kullanılmıştı) ve tek bir
    `ders_programi_0007_sube_gruplari`; kısıtın benzersizlik adı 63 karakter sınırı yüzünden
    `uq_kisit_kapsam`.

## Atladığım ya da onayını bekleyen konular

- **Gruba (ve ders + gruba) özel N / dağılım şekli için arayüzde seçim ekranı** yok (karar 11). İstersen
  Dersler sayfasındaki dağılım şekli hücresine "gruba göre" açılır bir bölüm eklenebilir.
- **Geri alınması zor bir karar gerekmedi;** veri silen bir migration yok (downgrade yalnızca gruba
  özel satırları siler, testli).

## Bilinen sorunlar

- K4b'nin `docs/olcumler.md`'deki tablosu yerinde bırakıldı, başına düzeltme notu eklendi (yanıltıcı
  sayılar silinmedi, neden yanlış olduğu yazıldı).
- Bu makinedeki ölçümler sakin ortamda; okulun sunucusu daha yavaşsa "Hızlı" eşiği erken aşılır
  (uyarı metni "yetmeyebilir" diyor, kesin değil).

## Sıradaki adım

5.6: kullanıcılar sayfası, telefon kontrolü (çizelgede gün gün görünüm, müsaitlikte "Toplu seç"
modu) ve Playwright ile uçtan uca test. Ardından K6 (ikincil esnek kurallar).

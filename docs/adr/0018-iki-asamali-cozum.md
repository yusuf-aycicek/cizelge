# ADR 0018: İki aşamalı çözüm ve "süre yetmedi" durumu

Durum: Kabul edildi (2026-10-24; kullanıcı yokken verildi, gerekçe aşağıda).

## Bağlam

Blok derslerle (ADR 0017) büyük sette (40 şube, şubeler haftalık kapasitenin %95-100'ü dolu,
atamaların yarısı "2 saat aynı gün art arda") ilk geçerli programın bulunması K4b ölçümünde
44-72 sn sürdü. Süre sınırı 60 sn olsaydı iki tohumda hiç program çıkmazdı. Yalnızca zorunlu
kurallarla (amaç yok) ilk program 11-57 sn'de bulunuyordu: yavaşlığın bir kısmı esnek kuralların
amaç fonksiyonundan geliyordu.

CLAUDE.md bölüm 7 bu iyileştirmeyi zaten anıyordu: "önce yalnızca zorunlu kısıtlarla çözüp sonucu
başlangıç ipucu olarak vermek". 2026-10-14'te (bloklar yokken) denenmiş, getirisi görülmemişti
(`docs/olcumler.md`, "Model düzeltmesinin etkisi").

## Karar

1. `CpSatCozucu` varsayılan olarak **iki aşamalı** çözer:
   - **Aşama 1:** yalnızca zorunlu kurallar, amaç yok, ilk çözümde durur
     (`stop_after_first_solution`). Süre sınırının en fazla `UYGUNLUK_PAYI` kadarını kullanır.
     Temel program varsa (en az değişiklikle güncelleme) ona ipucu olarak verilir: ilk program
     temel programa yakın başlar.
   - **Aşama 2:** bütün kurallar ve amaç; aşama 1'in programı **tam ipucu** olarak verilir
     (her hücre değişkeni). Kalan bütün süreyi kullanır (aşama 1 erken biterse kalan ona geçer).
2. Aşama 1 çözümsüzlüğü kanıtlarsa aşama 2 çalışmaz; doğrudan çelişki analizine geçilir
   (eskiden bunun için ayrıca "ikinci kontrol" yapılıyordu).
3. Aşama 2 süre içinde aşama 1'in programından daha iyisini bulamazsa (ipucunu da
   tamamlayamazsa) **aşama 1'in programı döner** (`uygun`); cezası bağımsız kalite ölçümüyle
   hesaplanır ("iyileştirmeye süre kalmadı" mesajıyla). Kullanıcı, kurallara uyan bir program
   bulunduysa hiçbir zaman eli boş dönmez.
4. Aşama 1 süre içinde ne program ne çözümsüzlük kanıtı bulursa aşama 2 kalan süreyle bütün
   modeli dener; o da bulamazsa davranış eskisi gibidir (ikinci kontrol, "süre yetmedi").
5. Kilitler aşama 1'de de zorunlu kuraldır; temel program aşama 1'e ipucu, aşama 2'ye hem ipucu
   (aşama 1'in programı üzerinden) hem değişiklik cezası olarak girer.
6. **Pay: 1.** Aşama 1 ilk programda durduğu için pay yalnızca ilk program geç gelirse sınırlar.
   120 sn'de 0,25 / 0,5 / 1 arasında fark yok; 30 sn'de 0,5 büyük sette bir tohumda programsız
   bıraktı, 1 hiçbirinde.
7. **Arayüz:** sonuç `bilinmiyor` ise (süre içinde ne program ne çözümsüzlük) program sayfası
   "Bu süre okulunuz için yetmedi" der ve tek tıkla bir sonraki uzun süreyle (aynı ad, aynı temel
   program) yeniden üretmeyi önerir: 30 sn → 2 dk → 5 dk → 10 dk. Okulun şube sayısı 30 ve
   üstündeyse "Hızlı" seçeneğinin yanında yetmeyebileceği yazar (24 şubede ilk program ≤ 9 sn,
   40 şubede 10-25 sn).
8. **Varsayılan süre 120 sn kalır**, büyük okullar için de: iki aşamalı çözümle büyük bloklu sette
   120 sn'lik 15 çalıştırmanın 14'ünde sınıf boşluğu 0 (birinde 1 saat). 180 sn cezayı 264'ten
   150'ye indiriyor ama fark öğretmen pencerelerinde; "Uzun" (5 dk) seçeneği bunun için var.

## Ölçüm

Sakin makine, 3 tohum, 120 sn (ayrıntı ve 30 / 60 sn: `docs/olcumler.md`, "İki aşamalı çözüm").

| Set | Kip | Tek aşamalı: ilk çözüm | Tek: 120 sn ceza | İki aşamalı: ilk çözüm | İki: 120 sn ceza |
|---|---|---|---|---|---|
| Gerçekçi | bloksuz | 5,1-9,5 sn (K4b) | 432 (K4b) | 2,2-3,3 sn | 240 |
| Gerçekçi | bloklu | 4,3-14,1 sn | 67 | 5,2-8,9 sn | 69 |
| Büyük | bloksuz | 8,8-11,9 sn | 805 | 3,9-5,2 sn | 737 |
| Büyük | bloklu | 23,5-29,2 sn | 268 | 9,2-25,5 sn | 253 |

İki aşamalı çözüm ilk programı daha erken veriyor; 120 sn'de kalite bloklu setlerde aynı düzeyde,
bloksuz setlerde daha iyi. K4b'deki 44-72 sn'lik ilk çözüm büyük ölçüde ölçüm ortamındandı (o
sırada makinede başka işler çalışıyordu); sakin makinede tek aşamalı da 23-29 sn. Yine de 30 sn'lik
sınırda tek aşamalı ilk programı sınırın hemen önünde buluyordu; iki aşamalı en geç 25 sn'de.

## Değerlendirilen alternatifler

- **Tek aşama (eski):** büyük bloklu sette ilk program geç geliyordu; 60 sn'de iki tohumda program yoktu.
- **Aşama 1'e bütün süre (pay 1):** aşama 1 hiç bitmezse aşama 2'ye süre kalmaz; ölçümde ayrıca
  karşılaştırıldı.
- **Aşama 1'de de amaç (ör. yalnızca sınıf boşluğu):** daha iyi bir başlangıç verebilir ama aşama
  1'i yavaşlatır; asıl sorun ilk programın geç gelmesiydi.
- **`fix_variables_to_their_hinted_value` / ipucunu zorlamak:** aşama 2'nin aramasını aşama 1'in
  programına kilitlerdi; ipucu yalnızca başlangıçtır.
- **Büyük okullarda yalnızca süreyi artırmak:** kullanıcıyı bekletir; iki aşamalı çözüm aynı sürede
  daha erken program verir. Süre önerisi ölçüme göre ayrıca verildi.

## Sonuçlar

- `CpSatCozucu(iki_asamali=False)` eski davranışı korur (ölçüm ve karşılaştırma için;
  `python -m cozucu.olcum ... --tek-asamali`, `--pay`).
- Ölçümlerde ara çözümler gözlemciye aşama 1'den de bildirilir (aşama 1'in programı ilk çözümdür).
- K4b ölçümündeki "bloksuz büyük set Ekim ortasından beri kötüleşti" gözlemi ölçüm ortamından
  kaynaklanıyordu (bkz. `docs/olcumler.md`, "Bloksuz büyük set: kötüleşme yok").

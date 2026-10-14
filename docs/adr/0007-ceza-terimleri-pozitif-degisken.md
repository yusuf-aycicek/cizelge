# ADR 0007: Ceza terimleri amaca yalnızca negatif olamayan tek bir değişken olarak girer

Durum: Kabul edildi (2026-10-14)

## Bağlam

Gerçekçi sette (24 şube, 42 öğretmen) 60. saniyedeki kalite yetersizdi: öğretmen başına haftada
~4 pencere saati vardı. CP-SAT'ın raporladığı alt sınır da negatifti (−2229 ile −4248 arası).
Oysa cezaların hepsi 0 ya da pozitiftir. İlk teşhis (pencere formülündeki `okulda ≥ once + sonra
− 1` kısıtının gevşetilmiş halinin zayıflığı) yanlış çıktı: bu kısıtı güçlendiren iki varyant da
negatif sınırı düzeltmedi (`scripts/sonuclar/pencere_varyantlari.md`).

`scripts/amac_teshisi.py`, her kuralın amaç fonksiyonuna yazdığı katsayıları listeledi:

| Kural | Amaçtaki değişken | Negatif katsayı | Alan sınırı |
|---|---|---|---|
| Öğretmen penceresi | 14 880 | 13 200 | −39 600 |
| Sınıf boşluğu | 14 160 | 13 200 | −396 000 |
| Diğerleri | – | 0 | 0 |

Nedeni: pencere cezası `okulda − dolu`, sınıf boşluğu cezası `sonra − dolu` biçiminde doğrudan
amaca yazılıyordu. `dolu` o saatteki ders değişkenlerinin toplamı olduğundan, bütün ders
değişkenleri amaçta negatif katsayı alıyordu (her biri −33). Değişken alanlarında ya da sabitte
sorun yoktu. Tamsayı çözümlerde her terim 0 ya da 1 olduğu için en iyi çözüm doğru bulunuyor ve
testler bunu yakalamıyordu. Ama CP-SAT'ın amaç üzerinden yaptığı akıl yürütmeler zayıflıyordu.

## Karar

Her ceza terimi amaca yalnızca negatif olamayan tek bir değişken (çoğunlukla 0/1) ile girer.
Fark ifadesi bu değişkene bir kısıtla bağlanır:

- pencere: `pencere ≥ okulda − dolu`
- sınıf boşluğu: `bosluk ≥ sonra − dolu`
- en az değişiklik: `degisti ≥ 1 − dolu`

Amaç bu değişkenleri aşağı ittiği için en iyi çözümde değerleri farkın kendisine eşittir. Ölçüm
anlamı değişmez; mini setteki çapraz kontrol testi (model cezası = bağımsız ölçüm) bunu
denetlemeye devam eder. Yeni bir esnek kural yazılırken de bu kurala uyulur.

## Değerlendirilen alternatifler

- **Pencere kısıtını güçlendirmek** (A: `okulda ≥ dolu`; B: `max`/`min` eşitlikleriyle tam
  tanım). Ölçüldü. A'nın getirisi tohum dalgalanmasının içinde kaldı, B %43 daha kötüydü. İkisinde
  de alt sınır negatif kaldı.
- **Sabiti amaçtan çıkarmak.** Bir öğretmenin haftalık toplam `dolu`'su sabittir (yükü). Pencere
  = Σ okulda − yük biçiminde yazılabilir. Katsayılar pozitif olur ama amaçta büyük bir negatif
  sabit kalır. CP-SAT'ın bu sabiti karşılayacak alt sınırı yine kendisinin bulması gerekir.
  Denenmedi; seçilen yöntem daha basit ve daha geneldir.

## Sonuçlar

Gerçekçi set, 60 sn, 3 tohum ortalaması:

| Saniye | Önce (gerçek ceza) | Sonra (gerçek ceza) | Sonra: sınıf boşluğu | Sonra: pencere |
|---|---|---|---|---|
| 10 | 1406 | 999 | 0 | 233 |
| 30 | 952 | 667 | 0 | 154 |
| 60 | 703 | 469 | 0 | 99 |

- 60. saniyede ceza %33 düştü. Sonrasının en kötü tohumu, öncesinin en iyi tohumundan iyi. Alt
  sınır artık 0'dan başlıyor. Mini sette en iyi çözüme ulaşma ve test takımı da hızlandı (takım 20-30
  sn'den 12 sn'ye).
- Model ~2700 ek 0/1 değişken aldı (pencere ve sınıf boşluğu hücre başına bir tane).
- Alt sınır hâlâ 0'da kalıyor, yani en iyi çözüme ne kadar uzak olduğumuzu CP-SAT kanıtlayamıyor.
  Daha güçlü sınırlar ileride düşünülebilir.

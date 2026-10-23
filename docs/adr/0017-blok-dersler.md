# ADR 0017: Blok dersler: zorunlu kural, okul önerisi uygulanamazsa düşer

Durum: Kabul edildi (2026-10-23).

## Bağlam

Okullar bir dersin haftalık saatlerini bloklar halinde ister: 5 saatlik Matematik "2+2+1" (iki gün
ikişer saat art arda, bir gün bir saat). Önceden yalnızca esnek "aynı dersin günlük saatleri arka
arkaya" kuralı vardı; bloğun boyunu ve blokların farklı günlere düşmesini garanti etmiyordu.

Kullanıcı istekleri (K4): varsayılan şekil haftalık saatten önerilsin (1: 1, 2: 2, 3: 2+1, 4: 2+2,
5: 2+2+1, 6: 2+2+2), okul değiştirebilsin ya da kapatabilsin, derse ve ders + şubeye özel şekil
verilebilsin (ADR 0016 kapsam yapısıyla), ön kontrol uygulanamayan şekli anlaşılır söylesin.

Sorun: öneri **her** derse varsayılan olarak uygulanınca, bazı atamalarda uygulanamaz olabilir
(öğretmen yalnızca iki gün geliyor ama ders 2+2+1 üç gün ister; okulun günlük sınırı 1; kilitli
hücreler şekle uymuyor). Kullanıcı hiçbir şey seçmediği halde program çözümsüz olurdu.

## Karar

1. **Blok deseni zorunlu bir kuraldır** (`blok_deseni`). Model: `bas[g, s, b]` = "b saatlik blok g
   günü s saatinde başlıyor"; yalnızca bloğun sığdığı başlangıçlar için değişken üretilir (gün
   uzunluğu ve öğle arası böylece ayrı kısıt gerektirmez). Her ders saati tam bir bloğa ait, günde
   en çok bir blok, her boydan desendeki kadar blok.
2. **Okul geneli şekil bir öneridir.** Bir atamada uygulanamıyorsa o atama bloksuz kalır. Bunlara
   bakılır: blok sayısı ≤ gün sayısı, en büyük blok ≤ N, her blok bir güne sığar, öğretmenin
   müsaitliğiyle her bloğa ayrı gün eşleşir (iki parçalı eşleştirme), kilitli hücreler uyar.
3. **Açıkça seçilen şekil (derse ya da ders + şubeye özel) düşmez.** Uygulanamıyorsa ön kontrol
   nedenini kullanıcının diliyle söyler; program üretilmez.
4. Hangi atamaya hangi şeklin uygulanacağının **tek kaynağı** `cozucu/blok.py`'dir. Çözücü, ön
   kontrol, çelişki açıklaması, bağımsız doğrulayıcı ve API (`/dagilim-sekilleri`) oradan okur.
   Arayüz düşen öneriyi ve nedenini ders listesinde gösterir.

## Değerlendirilen alternatifler

- **Esnek kural (ihlali ceza):** her zaman çözüm verir, ama "Beden Eğitimi 2 saat art arda" gibi
  kesin istekleri garanti etmez; ceza ağırlığı diğer kurallarla yarışır. Kullanıcı şekli zorunlu
  istedi.
- **Öneri de düşmesin, ön kontrol söylesin:** kullanıcı hiçbir ayar yapmadan karşısına "9-A Fizik
  2+2 dağılımı Ali Çelik'in müsaitliğine sığmıyor" çıkardı ve bunu düzeltmek için bir ayar
  (derse özel "blok yok") yapması gerekirdi. Varsayılan ayarlar tek başına çözümsüzlük
  üretmemeli.
- **Öneriyi uyarlamak (ör. 2+2+1 yerine 3+2 denemek):** daha akıllı, ama okulun beklemediği
  şekiller ortaya çıkardı ve nedenini açıklamak zorlaşırdı. Bloksuz bırakmak öngörülebilir ve ders
  listesinde görünür.

## Sonuçlar

- Öneri yalnızca **tek atamaya bakan** denetimlerle düşer. Başka atamalarla birlikte ortaya çıkan
  çözümsüzlük (ör. aynı şubenin iki bloklu dersi öğleden sonraya sığmıyor) çelişki analizinde
  "9-A Matematik'in 2+2+1 dağılımı" grubu olarak görünür.
- Gerçekçi ve büyük sette ölçülen etki `docs/olcumler.md`'de ("Blok dersler").
- `ardisik_ders` bütün atamaları bloklu (sınıf, ders) çiftinde modele eklenmez (ceza zaten 0).

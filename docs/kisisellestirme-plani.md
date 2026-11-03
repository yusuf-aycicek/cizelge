# Kişiselleştirme katmanı: tasarım

Durum: **Onaylandı**, uygulanıyor (sıra bölüm 10'da). Karar kaydı:
`docs/adr/0016-kural-kapsami.md` (kabul edildi).

## 1. Sorun

Gerçek okullarda kuralların çoğunun istisnası var:
- "Bu öğretmen günde en fazla 6 saat";
- "Beden Eğitimi hep 2 saatlik blok";
- "11-A sayısal, 11-C sözel";
- "9-B Din almıyor".

Bugün her kural okul genelidir: kısıt tablosunda her `tur` için tek satır, çözücüde tek örnek.

**Genel ilke:** her kuralın okul geneli bir varsayılanı vardır. Bu değer şube grubu, şube,
öğretmen ya da ders kapsamında ezilebilir; **en özel kapsam kazanır**.

## 2. Kapsam kavramı

### 2.1 Kapsam türleri

| Kapsam | Ne | Örnek |
|---|---|---|
| `okul` | Varsayılan (bugünkü durum) | "Aynı ders günde en fazla 2 saat" |
| `sube_grubu` | Bir grup şube | "11 Sayısal şubelerinde Matematik günde en fazla 3 saat" |
| `sube` | Tek şube | "9-A'da Fizik günde en fazla 1 saat" |
| `ogretmen` | Tek öğretmen | "Ayşe Yılmaz günde en fazla 6 saat", "boş gün hedefi 2" |
| `ders` | Bir ders (bütün şubelerde) | "Beden Eğitimi 2 saatlik blok", "Matematik sabah" |

Bazı kurallar iki ekseni birlikte kullanır: dersin günlük sınırı hem derse hem şubeye bağlıdır
(ör. "11 Sayısal'da Matematik"). Bu yüzden bir kapsam **eksenlerin birleşimidir**: her eksen boş
olabilir.

```
Kapsam = (ders_id?, sinif_id? | sube_grubu_id?, ogretmen_id?)
okul    = (—, —, —)
```

### 2.2 Çözümleme kuralı: hangi değer nereden gelir

Her kural hangi eksenleri desteklediğini bildirir (`kapsamlar`). Bir varlık için değer şöyle
bulunur:
1. Kuralın bu varlığa uyan bütün tanımları alınır. Bir tanım, belirttiği her eksende varlıkla
   eşleşiyorsa uyar. Boş eksen her şeye uyar.
2. **Özgüllük puanı** en yüksek olan kazanır. Puan: `ders` 4, `sube` 2, `sube_grubu` 1,
   `ogretmen` 1; doldurulmuş eksenlerin toplamı.
   - Ders ve şube ailesi: (ders + şube) 6 > (ders + şube grubu) 5 > ders 4 > şube 2 > şube
     grubu 1 > okul 0.
   - Öğretmen ailesi: öğretmen 1 > okul 0.
   - Ders, şubeden önce gelir: dersin doğası (Beden Eğitimi bloğu) şubenin genel ayarından daha
     özeldir.
3. **Öğretmen kapsamı, ders ve şube kapsamıyla hiçbir kuralda çakışamaz.** Kurallar iki ayrık
   aileye ayrılır:
   - öğretmenin kendisiyle ilgili kurallar (M, boş gün hedefi, günde en az ders): yalnızca
     `ogretmen` ekseni;
   - dersin ve şubenin yerleşimiyle ilgili kurallar (N, blok deseni, saat tercihi, yayılım):
     yalnızca `ders`, `sube`, `sube_grubu` eksenleri.

   Bir kural sınıfı ikisini birden bildirirse `kaydet` onu **kayıt anında reddeder** (testle
   denetlenir). Öğretmen eksenli bir tanım ders ya da şube ekseni de taşırsa `Kapsam` daha
   oluşturulurken (`ValueError`), API (422) ve veritabanı CHECK'i (`ck_kisit_kapsam_ailesi`)
   reddeder. Böylece "Ayşe Yılmaz'a özel" bir değerle "Matematik'e özel" bir değer
   aynı kuralda karşılaşamaz; hangisinin kazanacağı sorusu doğmaz. İleride iki ekseni birlikte
   isteyen bir kural gerekirse (ör. "Ayşe Yılmaz'ın Matematik dersleri sabah"), öncelik yeni bir
   ADR kararıyla tanımlanır.
4. **Eşitlik olmaz:** aynı kapsamda bir kural için tek tanım vardır (benzersiz indeks); kalan
   puanlar ailelerin içinde farklıdır.
5. Hiç tanım yoksa kuralın kod içindeki varsayılanı kullanılır (bugünkü davranış).

Örnek, aynı dersin günlük sınırı (N), "11-A Matematik" için:

| Tanım | Puan | Uyar mı |
|---|---|---|
| okul: N = 2 | 0 | evet |
| sube_grubu = 11 Sayısal: N = 3 | 1 | evet (11-A bu grupta) |
| ders = Matematik: N = 2 | 4 | evet |
| ders = Matematik, sube_grubu = 11 Sayısal: N = 3 | 5 | evet, **kazanır** |

Çözümleme tek bir saf fonksiyondur (`cozucu/kapsam.py: cozumle(tanimlar, varlik)`). Çözücü, ön
kontrol, API (ayarların "nereden geldiği" gösterimi) ve arayüz aynı sonucu bu fonksiyondan alır
(ADR 0015'teki tek kaynak ilkesi).

### 2.3 Strategy deseni nasıl korunur

Bugün `kural_olustur(tanim)` her `tur` için bir örnek üretir, `CpSatCozucu` hepsine
`uygula(baglam)` der. Bu değişmez.

- `KisitTanimi`'ne bir alan eklenir: `kapsam: Kapsam = OKUL`.
- `kurallari_hazirla` aynı `tur`un tanımlarını gruplar:
  - **bir** kural örneği oluşturur; parametreleri okul geneli tanımdan, yoksa varsayılandan
    alır;
  - geri kalan tanımları örneğe `ozel_tanimlar` olarak verir.
- Kural, değeri doğrudan alanından okumak yerine taban sınıftaki yardımcıdan ister:
  `self.deger(baglam, "n", ders=..., sinif=...)`.
  Yardımcı `cozumle`'yi çağırır.
- Taban sınıfa bir sınıf özniteliği eklenir: `kapsamlar: ClassVar[frozenset[str]] =
  frozenset()`. Boşsa kural yalnızca okul genelidir. `kural_olustur` desteklenmeyen kapsamı
  `GirdiHatasi` ile reddeder ("'sinif_boslugu' öğretmene özel ayarlanamaz").

Sonuç:
- Bir kurala kapsam desteği eklemek yalnızca o sınıfı değiştirir: `kapsamlar` bildirimi ve
  değer okuma.
- Yeni kural eklemek yine yeni bir sınıftır (açık/kapalı ilkesi).
- `CpSatCozucu` ve kayıt defteri değişmez.

**K1'de netleşen ayrıntılar** (uygulama ve testlerle):
- **Kip ve ağırlık okul tanımından gelir;** özel ayar yalnızca parametreleri değiştirir. Okul bir
  kuralı esnek yaptıysa ona ait özel ayarlar da esnektir. (`kural_olustur` özel örneğe okulun
  kipini ve ağırlığını verir.)
- Özel ayarda bulunmayan parametre, kural sınıfının kurucusundaki varsayılanı alır (çözücüdeki
  örnek ile `CozumGirdisi.parametre` aynı sonucu verir).
- Okul tanımı yoksa özel ayar, kuralın varsayılan tanımının üzerine kurulur. Varsayılanı da
  olmayan bir türün özel ayarı `GirdiHatasi`dır.
- Çözücünün dışındaki okuyucular (yük, ön kontrol, doğrulama, kalite, çelişki açıklaması, boş gün
  kuralının M'si) değeri `CozumGirdisi.parametre(..., ogretmen_id=…)` / `sinif_id=, ders_id=` ile
  varlık başına okur; hepsi `cozumle`yi kullanır.
- Ön kontrol mesajı değer okul değerinden farklıysa bunu söyler: "bu ders bu şubeye günde en
  fazla 1 saat konabildiği (özel ayar)". Çelişki açıklaması her öğretmenin ve dersin kendi
  değerini yazar ("Ayşe Yılmaz günde en fazla 6 saat derse girebilir"). Ayrı bir
  `("ozel", tur, kapsam)` çelişki grubu henüz yok; mevcut gruplar değeri doğru söylediği için
  gerekmedi.
- API: `GET /kurallar` her kural için `kapsamlar` (destekleri, çözücünün sınıfından) ve
  `ozel_ayarlar` (`kapsam`, `ad`, `parametreler`) döner; `PUT/DELETE /kurallar/{tur}/ozel`.
  Okul değerini "varsayılana döndürmek" özel ayarlara dokunmaz.

**Neden "her kapsam için ayrı kural örneği" değil:**
- Öyle olsaydı okul geneli N = 2 ve Matematik N = 3 tanımları aynı (şube, ders, gün) için iki
  kısıt ekleyip **ikisini birden** uygulardı: Matematik fiilen 2'de kalırdı.
- "En özel kazanır" için her örneğin ötekilerin kapsamını bilmesi gerekirdi.
- Esnek kurallarda ise aynı ceza iki kez yazılırdı.

## 3. Veri modeli ve migration'lar

Bütün yeni tablolarda `id`, `okul_id` ve bileşik yabancı anahtarlar (okul_id, …) bulunur. RLS
politikası mevcut kalıpla eklenir (ADR 0009); okul izolasyonu bozulmaz.

| Migration | Değişiklik |
|---|---|
| `cekirdek_0006_sube_grubu` | `sube_grubu` (ad, seviye; UNIQUE (okul_id, ad)); `sinif.sube_grubu_id` (boş olabilir; grubun seviyesi şubeninkiyle aynı olmalı: servis denetler) |
| `cekirdek_0007_okul_zaman` | `okul`: `gun_saatleri int[]` (boşsa her gün `gunluk_ders_saati`), `ogle_arasi_sonra int` (boş = yok; ör. 4 = 4. dersten sonra), `ilk_ders_baslangic time` (08:30), `ders_suresi_dk` (40), `teneffus_dk` (10), `ogle_arasi_dk` (40), `maas_karsiligi_saat` ve `ek_ders_ust_siniri` (boş = uyarı yok). `gunluk_ders_saati` en uzun gün olarak kalır: mevcut kod ve kapasite hesabı kırılmaz |
| `ders_programi_0006_kisit_kapsami` | `kisit`: `ders_id`, `sinif_id`, `sube_grubu_id`, `ogretmen_id` (hepsi boş olabilir, bileşik FK, `ON DELETE CASCADE`: öğretmen silinince özel ayarları da gider). CHECK: `sinif_id` ile `sube_grubu_id`'den en çok biri dolu; `ogretmen_id` doluysa öteki üçü boş. Mevcut `UNIQUE (okul_id, tur)` kalkar; yerine `UNIQUE NULLS NOT DISTINCT (okul_id, tur, ders_id, sinif_id, ogretmen_id)` (PostgreSQL 15+: boş sütunlar eşit sayılır, okul geneli satır da tek kalır; uygulamada `coalesce` ifade indeksinden daha okunur). **K1'de yapılan:** `ders_id`, `sinif_id`, `ogretmen_id`; `sube_grubu_id` tablosuyla birlikte K5'te eklenir. **Var olan satırlar** dört boş sütunla `okul` kapsamında kalır; veri taşıması gerekmez |
| `ders_programi_0007_sablon_grubu` | `seviye_sablonu.sube_grubu_id` (boş = seviyenin şablonu). UNIQUE (okul_id, seviye, sube_grubu_id, ders_id) |
| `ders_programi_0008_sube_istisnasi` | `sube_ders_istisnasi` (sinif_id, ders_id, tur `almaz`/`ek`, haftalik_saat: yalnızca `ek` için). UNIQUE (okul_id, sinif_id, ders_id) |

**Neden kural ezmeleri ayrı tablolarda değil de `kisit`te** (ADR 0016'da alternatifler):
- tek çözümleme yolu;
- tek API ucu;
- yeni bir kural yeni bir tablo istemez;
- yabancı anahtarlar sayesinde silinen öğretmenin ayarı yetim kalmaz.

**Blok deseni** de bir kuraldır: `tur = blok_deseni`, kapsam `ders` (ya da ders + şube grubu),
parametre `{"desen": [2, 2, 1]}`. Desen tanımlanmamış derste okul geneli varsayılan işlev
uygulanır: 1 → [1], 2 → [2], 3 → [2, 1], 4 → [2, 2], 5 → [2, 2, 1], 6 → [2, 2, 2]. Okul bu
varsayılanı kapatabilir: `blok_deseni` okul kapsamında `{"otomatik": false}` olursa yalnızca
açıkça tanımlanan derslere uygulanır.

## 4. Çözücü: yeni ve değişen kurallar

| # | Kural | Tür | Kapsamlar | Değişiklik |
|---|---|---|---|---|
| e | `gunluk_ders_siniri` (N) | zorunlu | ders, şube, şube grubu | Değer `deger(…)` ile; davranış aynı |
| — | `ogretmen_gunluk_siniri` (M) | zorunlu | öğretmen | Aynı |
| d | `bos_gun` | esnek | öğretmen | Hedef öğretmene özel olabilir; **iki yönlü** (aşağıda) |
| c | `gun_uzunlugu` (yeni) | zorunlu, okul | — | `s >= gun_saatleri[g]` olan hücreler 0. `Baglam.saatler` en uzun gün olarak kalır |
| c | `ogle_arasi_bolunmez` (yeni) | zorunlu, okul | — | Bir blok öğle arasının iki yanına yayılamaz (blok kuralının parçası; ayrı tanım gerekmez) |
| b | `blok_deseni` (yeni) | zorunlu | ders, ders + şube grubu | Aşağıda |
| b | `ardisik_ders` | esnek | — | Blok deseni olan atamalarda uygulanmaz (blok zaten bitişik) |
| f | `ders_saat_tercihi` (yeni) | esnek | ders | `{"saatler": [0, 1, 2, 3]}` tercih edilen saatler, ya da `{"kacin": [4]}`. Dışına düşen her saat ceza |
| g | `gunluk_en_az_ders` (yeni) | esnek | öğretmen | Öğretmenin geldiği bir günde ders sayısı 1..k-1 ise ceza (okul geneli varsayılan k = 1, yani kapalı; açılınca önerilen 2. ADR 0025) |
| h | `ders_yayilimi` (yeni) | esnek | ders (zorunlu), şube, grup | Aynı (şube, ders) art arda iki günde varsa ceza. Okul genelinde kapalı, derse özel açılır (ADR 0024) |
| i | `haftalik_yuk` (yeni, K6d) | uyarı | öğretmen | `{"alt", "ust"}`, 0 = yok; modele etkisi yok, dağılımda ve ön kontrolde uyarı (ADR 0023; plandaki `okul` sütunlarının yerine) |

### 4.1 Blok deseni (b)

Her atama için desen ([2, 2, 1] gibi) toplamı haftalık saate eşit olmalıdır (ön kontrol denetler).
Değişkenler:
- `bas[a, g, s, b]`: atama `a`, gün `g`'de, saat `s`'den başlayan `b` uzunlukta bir blok;
  yalnızca desende geçen `b` boyları için üretilir.

Kısıtlar:
1. `x[a, g, s] = Σ_b Σ_{s' ∈ (s-b, s]} bas[a, g, s', b]`: her ders saati tam olarak bir bloğa ait;
   bloklar bitişik.
2. `Σ_s Σ_b bas[a, g, s, b] ≤ 1`: bir günde en çok bir blok. Aynı dersin blokları farklı günlere
   düşer.
3. `Σ_g Σ_s bas[a, g, s, b] = desendeki b sayısı`: desen tam olarak gerçekleşir.
4. `bas` yalnızca bloğun günün içine sığdığı ve öğle arasını kesmediği başlangıçlar için üretilir
   (`s + b <= gun_saatleri[g]`, öğle arası `[s, s+b)` aralığının içinde değil). Böylece c
   maddesindeki kısıt ayrı bir kural gerektirmeden, değişken üretilmeyerek uygulanır.

N ile ilişkisi: desen N'den büyük blok içeriyorsa ön kontrol uyarır. Dersin günlük ders sayısı
zaten bloğun boyudur.

**K4'te verilen kararlar:**
- Parametreler: okul geneli `{"otomatik": true, "varsayilanlar": {"4": [2, 1, 1]}}` (`otomatik:
  false` = okulda blok yok); derse ya da ders + şubeye özel `{"desen": [2, 2, 1]}`, `[]` = blok
  yok. Özel ayarda ders ekseni zorunludur (kurala `zorunlu_eksenler` eklendi: şubenin bütün
  derslerine tek desen anlamsız). Desen büyükten küçüğe sıralanır: "1+2" ile "2+1" aynıdır.
- Okul geneli desen bir **öneridir**: o atamada uygulanamıyorsa (blok sayısı > gün sayısı, en
  büyük blok > N, blok hiçbir güne sığmıyor, öğretmenin müsaitliğine sığmıyor, kilitli hücreler
  uymuyor) atama bloksuz kalır. Böylece varsayılan ayar tek başına programı çözümsüz yapmaz.
  Açıkça seçilen şekil düşmez; ön kontrol nedenini söyler. Okul önerisinin yine de başka
  atamalarla birlikte çözümsüzlüğe yol açtığı durumda çelişki analizi "9-A Matematik'in 2+2+1
  dağılımı" grubunu gösterir.
- **Kilitli hücre:** bir bloğun parçası sayılır; bloğun geri kalanını çözücü yanına yerleştirir.
  Uyması için aynı gündeki kilitli saatler tek bir bloğa sığmalı (öğle arasını kesmeden,
  öğretmenin gelemez saatlerine taşmadan) ve her kilitli güne ayrı bir blok düşmeli.
- **Temel program:** değişiklik cezası ve ipucu aynen çalışır; bloklara uyan temel program
  korunur, uymayan temel programda blok kuralı (zorunlu) kazanır.
- `ardisik_ders` bütün atamaları bloklu (sınıf, ders) çiftinde modele eklenmez (ceza hep 0).
- Doğrulayıcı (`dogrulama.py`) blokları bağımsız denetler: her gün tek kesintisiz parça, öğle
  arasını kesmeden, parça boyları desene eşit.

Performans: değişken sayısı kabaca atama × gün × saat × (farklı blok boyu ≤ 2) kadar artar.
CLAUDE.md bölüm 7'deki gibi gerçekçi ve büyük sette 10/30/60/120 sn kalite ölçümüyle doğrulanır.
Blok kısıtı arama uzayını daraltır; daha hızlı çözüm beklenir, ama bu ölçülecek.

### 4.2 İki yönlü boş gün (d)

Bugün: `ceza = max(0, gün − hedef_gün)`; yalnızca fazla gelmek cezalı.

Yeni:
- `hedef_gun = max(⌈yük / günlük sınır⌉, gün sayısı − hedef_boş_gün)`, sonra `min(…, yük,
  gelebildiği gün)` ile sınırlanır: 3 saat dersi olan öğretmen 4 gün gelemez; bütün günü
  "gelemez" olan gün zaten boştur. (Gelebildiği gün sınırı K2'de örnek okuldaki denemede
  eklendi: pazartesi gelemeyen öğretmene "0 boş gün" verilince kaçınılmaz ceza yazılıyordu.)
- Tek kaynak: `cozucu/yuk.py: bos_gun_hedefi`; çözücüdeki kural ve kalite ölçümü onu kullanır.
- `fazla = max(0, gün − hedef_gun)` → mevcut ağırlıkla ceza (bugünkü davranış).
- `eksik = max(0, hedef_gun − gün)` → yalnızca **öğretmene özel** hedef tanımlıysa cezalanır.

Neden yalnızca öğretmene özelde:
- Okul geneli hedef 1 iken iki boş günü olan öğretmeni cezalandırmak, onu daha fazla güne
  yaymak demektir: pencereyi artırır ve öğretmenin de istemediği bir sonuç doğurur.
- "Boş günüm olmasın" bir öğretmenin açık isteğidir (hedef 0); ancak o zaman eksik gün cezası
  anlamlıdır.
- Ders saati yetmiyorsa (yük < gün sayısı) hedef zaten yüke indirildiği için ceza doğmaz.

Belirli bir günün boş olması isteği müsaitlik çizelgesiyle karşılanır ("cuma gelemez"); ayrıca
modellenmez.

### 4.3 Günlere göre ders saati ve öğle arası (c)

- `OkulAyari`na `gun_saatleri: tuple[int, ...]` (varsayılan: her gün `gunluk_ders_saati`) ve
  `ogle_arasi_sonra: int | None` eklenir.
- `haftalik_kapasite = Σ gun_saatleri`.
- `yuk.py` (ADR 0015) kapasiteyi ve öğretmenin günlük müsait saatini gün uzunluğuyla hesaplar;
  ön kontrol ve dağılım özeti kendiliğinden uyar.
- Sınıf boşluğu ve pencere kuralları günün kendi uzunluğunu kullanır.
- **K3'te yapılan:** değişkenler en uzun güne göre kurulur, kısa günün sonundaki hücreler temel
  kural `gun_uzunlugu` ile 0'a sabitlenir (öteki kurallar değişmedi; sınıf boşluğu ve pencere
  zaten yalnızca dolu saatlerin arasına bakar). Öğle arasının iki yanındaki saatler bitişik
  sayılmaz: öğle arasıyla bölünen ders "bölünmüş ders" cezası alır (blok dersler K4'te
  öğle arasına hiç yayılamayacak). Boş gün hedefindeki en az gün, en uzun günlerden başlanarak
  hesaplanır.

## 5. Ön kontrol ve çelişki analizi

Yeni ön kontroller. Mesajlar kullanıcının diliyle ve adlarla yazılır.

| Durum | Örnek mesaj |
|---|---|
| Desen toplamı haftalık saate eşit değil | "9-A Matematik haftada 5 saat, ama dağılım şekli 2+2 (4 saat). Şekli ya da saati düzeltin." |
| Desende N'den büyük blok | "Beden Eğitimi 3 saatlik blok istiyor, ama bir ders bir şubeye günde en fazla 2 saat konabiliyor." |
| Blok sayısı uygun gün sayısından fazla | "9-A Matematik 3 blok (2+2+1), ama Ayşe Yılmaz yalnızca 2 gün müsait." |
| Blok müsaitliğe sığmıyor | "Beden Eğitimi 2 saatlik blok istiyor, ama Ali Çelik'in hiçbir gün art arda 2 saat müsaitliği yok (öğle arası da bölüyor)." |
| Blok hiçbir güne sığmıyor | "11-A Fizik 3 saatlik blok istiyor, ama öğle arası günü 4+4'e bölüyor ve cuma 2 saat sonra öğle arası var." |
| Gün uzunluğu kapasitesi | Mevcut sınıf kapasitesi mesajı gün uzunluklarıyla: "haftalık kapasite 39 saat (4 gün × 8, cuma 7)" |
| Şube istisnası tutarsız | "9-B için 'Din almaz' istisnası var, ama 9-B'ye Din atanmış." (bilgi; otomatik düzeltilmez) |

Çelişki analizinde yeni grup anahtarları:
- `("blok", atama_id)`: "9-A Matematik'in 2+2+1 dağılımı";
- `("gun_uzunlugu", gun)`: "Cuma 7 saat".

Bunların `anlatim.py`'de Türkçe karşılıkları olur. Çelişen grupların açıklamasında kullanıcı hangi
özel ayarın sorun çıkardığını görür. Özel ayarlar kendi grubunu alır (`("ozel", tur, kapsam)`):
"Ayşe Yılmaz'a özel günlük sınır (6)".

## 6. Şube grupları ve şube istisnaları (a)

- **Şube grubu:** "11 Sayısal", "11 Sözel", "11 Eşit Ağırlık", "11 Dil". Şubeye grubu
  atanabilir; grubu olmayan şube seviyesinin şablonunu kullanır.
- **Şablon:** seviyeye **ya da** gruba bağlanır. Uygulanırken önce grubun şablonu, yoksa
  seviyenin şablonu kullanılır.
- **İstisna (`sube_ders_istisnasi`):**
  - `almaz`: şablon bu şubeye bu dersi eklemez. Şablon yeniden uygulansa da geri gelmez
    (istenen davranış).
  - `ek` (haftalık saatle): şablonda olmasa da eklenir.
- **İstisna nasıl oluşur:** ders dağılımında şablondan gelen bir ders şubeden kaldırılınca
  pencere sorar: "9-A bu dersi hiç almasın mı? (Şablon yeniden uygulandığında geri gelmez)".
  "Evet" bir `almaz` istisnası yazar. Şube sayfasında istisnalar listelenir ve geri alınabilir.
- **Şablon raporu (5.4):** "atlanan (istisna)" sayısını da gösterir.

**K5'te netleşen ayrıntılar** (kullanıcı yokken verilen kararlar):
- **Hangi şube hangi şablonu kullanır** tek kuraldır (`servisler.sablon_kaynaklari`, arayüzde aynısı
  `kullananSubeler` / `subeninSablonu`): şubenin grubunun şablonunda en az bir ders varsa grubunki,
  yoksa seviyesininki. Grup şablonu seviye şablonunun **yerine** geçer (üstüne eklenmez); ortak dersler
  grubun şablonuna da yazılır. Boş grup şablonu bir şeyi değiştirmez.
- **Uygulama:** `POST /seviye-sablonlari/uygula {seviye, sube_grubu_id?}` şablonu yalnızca onu kullanan
  şubelere uygular. Seviyenin şablonu, kendi grubunun şablonunu kullanan şubelere dokunmaz; rapor
  bunları `baska_sablonlu` olarak adıyla söyler. Rapor ayrıca `istisna_atlanan` ("almaz" yüzünden
  eklenmeyen) ve `istisna_ek` (şubenin ek dersleri; eksikse eklenir) listelerini verir.
- **İstisna ders dağılımını da değiştirir** (kullanıcı iki iş yapmasın): "almaz" konunca şubenin o
  dersi kaldırılır; "almaz" kaldırılınca ders şubenin şablonundaysa şablondaki saatle (öğretmeni
  boş) geri eklenir. "Ek" konunca ders yoksa eklenir; "ek" kaldırılınca ders şubede kalır (veri
  silinmez). Şubenin ek dersi ders dağılımından silinirse "ek" istisnası da silinir (şablon
  uygulanınca geri gelmesin). İstisna ile dağılım tutarsızsa (ör. "almaz" ama elle eklenmiş) liste
  uyarır, otomatik düzeltmez.
- **Arayüz:** kaldırma penceresinde "9-A bu dersi hiç almasın" kutusu (ders şubenin şablonundaysa
  görünür, işaretli başlar); şablonda olmayan ders eklenirken "ek ders olarak kaydet" kutusu; şube
  panelinde "Bu şubeye özel" listesi ("Geri al" / "İşareti kaldır"); ders satırında "Ek ders" rozeti.
- **Grubun seviyesi değiştirilemez** (`PATCH /sube-gruplari` yalnızca ad): seviye, şubelerinin ve
  şablonunun seviyesidir; değiştirmek için yeni grup açılır. Şube başka seviyedeki bir gruba
  alınamaz; gruptaki şubenin seviyesi değiştirilemez (önce gruptan çıkarılır).
- **Grup silinince** şubeler grupsuz kalır (`SET NULL`), grubun şablonu ve gruba özel ayarlar silinir
  (CASCADE); arayüz silmeden önce bunu söyler.
- **Gruba özel kural ayarı** (N, dağılım şekli; ders + grup dahil) çözücüde, API'de ve özel ayarların
  özetinde ("11 Sayısal grubu · Matematik") var; ayrı bir seçim ekranı yok (K4'teki ders + şube
  kararıyla aynı). `dagilim-sekilleri` kaynağı `ders_grup` olabilir.
- **Migration'lar:** `cekirdek_0007_sube_grubu` (0006 K3'te kullanıldı) ve tek bir
  `ders_programi_0007_sube_gruplari` (şablon grubu, kısıt kapsamı, istisna tablosu). Kısıtın yeni
  benzersizlik kuralının adı, kuraldan üretilen ad 63 karakteri aşacağı için `uq_kisit_kapsam`.

## 7. API

| Uç | Ne |
|---|---|
| `GET/POST/PATCH/DELETE /api/sube-gruplari` | Çekirdek; şube grupları |
| `PATCH /api/siniflar/{id}` | `sube_grubu_id` alanı |
| `GET /api/ders-programi/kurallar` | Her kural için okul değeri ve **özel ayarlar** listesi: `[{kapsam: {ders, sinif, sube_grubu, ogretmen}, parametreler, seviye, ad: "Ayşe Yılmaz"}]` |
| `PUT /api/ders-programi/kurallar/{tur}/ozel` | `{kapsam, parametreler?, seviye?}`: özel ayarı ekler ya da günceller. Desteklenmeyen kapsam 422 |
| `DELETE /api/ders-programi/kurallar/{tur}/ozel?ogretmen_id=…` | Özel ayarı kaldırır: okul değerine döner |
| `GET /api/ders-programi/ayar-kaynagi?ogretmen_id=…` | Bir varlık için her kuralın geçerli değeri ve **nereden geldiği** ("okul geneli", "11 Sayısal grubu", "bu öğretmene özel"); `cozumle` ile |
| `/api/ders-programi/istisnalar` | Şube ders istisnaları CRUD |
| `PATCH /api/okul` | `gun_saatleri`, `ogle_arasi_sonra`, zaman alanları, yük eşikleri (etki önizlemesi ADR 0014'teki gibi: gün kısalınca kalan müsaitlik ve kilitler) |
| `GET /api/ders-programi/dagilim-ozeti` | Öğretmen satırına `yuk_uyarisi` (i): "maaş karşılığının altında (12/15)", "ek ders üst sınırını aşıyor" |

Kapsamdaki kimliklerin bu okula ait olduğunu hem servis (anlaşılır 422) hem bileşik FK denetler.

## 8. Arayüz: teknik olmayan yönetici için

İlke: ayar **ilgili olduğu yerde** yapılır, ayrı bir "kurallar matrisi" yok. Her özel alanın ilk
seçeneği "Okul varsayılanı (2)"dır. Özel değer verilmiş alanın yanında küçük bir "özel" rozeti
çıkar.

| Nerede | Ne ayarlanır |
|---|---|
| Okul ayarları | Günlere göre ders saati (beş kutu, "hepsi aynı" kısayolu); öğle arası ("4. dersten sonra" seçimi); zil saatleri (başlangıç, ders süresi, teneffüs, öğle arası süresi: önizlemeyle "1. ders 08.30–09.10"); yük eşikleri |
| Öğretmenler: satırda "Özel ayarlar" çekmecesi | Boş gün hedefi (Okul varsayılanı / 0 / 1 / 2); günlük en çok ders; geldiği gün en az ders |
| Dersler: satırda "Özel ayarlar" | Dağılım şekli (otomatik, 2+2, 2+2+1, 3+2, tek tek...: yalnızca toplamı tutan seçenekler); günlük en çok saat; saat tercihi (sabah / öğleden sonra / farketmez); günlere yayılsın |
| Sınıflar | Şube grupları (ekle, adlandır); şube satırında grup seçimi; "Bu şubeye özel dersler" (almaz / ek alır) |
| Seviye şablonu | Seviye ya da grup seçimi ("11. sınıflar" / "11 Sayısal") |
| Okul ayarları > "Özel ayarların özeti" | Okuldaki bütün özel ayarlar tek listede ("Ayşe Yılmaz: günde en çok 6 saat"); her biri kaldırılabilir. Şeffaflık: hiçbir istisna gizli kalmaz |
| Haftalık çizelge | Satır başlığında zil saatleri ("1. saat · 08.30–09.10"); öğle arası satırı |

## 9. Testler

- **`cozumle` (saf):** puan sırası, eksik eksen her şeye uyar, öğretmen ekseniyle karışık kapsam
  reddi, hiç tanım yoksa varsayılan. Tablo güdümlü, çözücü paketinde.
- **Her yeni kural:**
  - mini senaryoda kuralın sağlandığı (doğrulama, `dogrulama.py`ya yeni denetimler eklenir:
    blok bitişik mi, gün uzunluğu aşılmış mı);
  - ihlal edilmesi gereken durumda çözümsüzlük ya da ceza;
  - mutasyon denemesi.
- **İki yönlü boş gün:** okul geneli hedefte eksik gün cezası yok; öğretmene özel 0'da var; yük
  yetmezse yok.
- **Ön kontrol:** her yeni mesaj için senaryo ve tam metin.
- **Çelişki analizi:** blok + müsaitlik çelişkisi doğru gruplarla ve adlarla açıklanır.
- **Migration:**
  - var olan kısıtlar okul kapsamında kalır;
  - var olan okullarda `gun_saatleri` boş, davranış değişmez;
  - upgrade/downgrade/upgrade.
- **API:**
  - özel ayar ekle, güncelle, sil;
  - başka okulun öğretmenine özel ayar reddedilir (izolasyon);
  - öğretmen silinince özel ayarı da silinir (CASCADE);
  - şablon yeniden uygulanınca `almaz` dersi geri gelmez.
- **Arayüz:** "Okul varsayılanı" seçeneği, özel rozeti, özet listesi, istisna penceresi.
- **Ölçüm:** gerçekçi ve büyük sette blok desenleriyle 10/30/60/120 sn kalite, `docs/olcumler.md`'ye.

## 10. Uygulama sırası (kullanıcının belirlediği)

Her alt adım kendi başına çalışır ve test edilir; öncelikli ihtiyaçlar önce gelir.

| # | Alt adım | Karşıladığı |
|---|---|---|
| K1 | Kapsam temeli: `kisit` kapsam sütunları, `KisitTanimi.kapsam`, `cozumle`, taban sınıfta `deger()`; N ve M kapsamlı; API özel ayar uçları; okul ayarlarında "özel ayarların özeti" | e, temel |
| K2 | Öğretmene özel boş gün hedefi, iki yönlü ceza **ve 5.5 müsaitlik çizelgesi birlikte**: tek bir öğretmen detay sayfası (üstte kişisel ayarlar, altta müsaitlik çizelgesi) | d |
| K3 | Günlere göre ders saati, öğle arası, zil saatleri; `gun_uzunlugu`; `yuk.py`; çizelgede saat başlıkları | c, j |
| K4 | Blok deseni: kural, varsayılan desen işlevi, ön kontrol ve çelişki mesajları, ders "dağılım şekli" seçimi; ölçüm | b |
| K5 | Şube grupları, gruba bağlı şablon, şube istisnaları ve kaldırma penceresi | a |
| 5.6 | Kullanıcılar sayfası, telefon kontrolü (çizelgenin telefonda gün gün görünümü dahil), Playwright ile uçtan uca test | — |
| K6 | İkincil esnek kurallar: saat tercihi, günde en az ders, yayılım; yük uyarısı | f, g, h, i |
| — | Çarşaf liste | k: yapım sırası 7'de (çıktı) |

K1 diğerlerinin önkoşuludur. K3, K4'ten önce gelir: blok kuralı öğle arasını ve gün uzunluğunu
kullanır.

# Okul Ders Programı Sistemi

Okullar için çakışmasız haftalık ders programı üreten çok okullu (multi-tenant) web uygulaması.
Bu dosya projenin tek doğruluk kaynağıdır. Bir karar değişirse önce burası güncellenir.

## 1. Proje özeti

Okul yöneticisi öğretmenleri, sınıfları, dersleri ve kimin hangi sınıfa hangi dersi haftada kaç saat
verdiğini girer. Kısıtları tanımlar. Sistem arka planda, hiçbir öğretmenin ve sınıfın aynı saatte iki
yerde olmadığı bir haftalık program üretir. Yönetici sonucu görür, elle düzeltir, çıktı alır.

- Belirli bir okul için değil, bütün okullar için genel bir sistemdir (dönem projesi). Okuldan
  okula değişen her şey ayarlanabilir olmalı; makul varsayılanlarla çalışmalıdır (bkz. bölüm 10).
- Hedef: birden fazla okulun birbirinden bağımsız kullanabilmesi.
- Hedef kademe: lise ve ortaokul.
- Proje aynı zamanda bir yazılım tasarımı ve mimarisi dersinde sunulacak. Mimari kararların
  gerekçeli ve belgelenmiş olması, kodun çalışması kadar önemli.

## 2. Roller

| Rol | Yetki |
|---|---|
| Yönetici (müdür, müdür yardımcısı) | Okulun tüm verisini düzenler, program üretir |
| Öğretmen | Sadece kendi programını görüntüler (paylaşılan link ile, hesap gerekmez) |

## 3. Kapsam

### İlk sürümde var
- Okul kaydı ve yönetici girişi
- Okul ayarları: haftadaki gün sayısı, günlük ders saati sayısı
- Öğretmen, sınıf (şube), ders listeleri: elle giriş ve Excel'den içe aktarma
- Seviye şablonu: bir seviyenin dersleri ve haftalık saatleri bir kere tanımlanır, o seviyedeki
  tüm şubelere uygulanır
- Ders atama: şube görünümü (her derse öğretmen seç) ve öğretmen görünümü (toplam ders yükü)
- Öğretmen müsaitliği: gelemez (zorunlu) ve tercih etmez (esnek)
- Okul geneli kısıtlar (bkz. bölüm 7)
- Öğretmenin günlük ders sınırı: bir öğretmen günde en fazla M saat derse girer (zorunlu,
  varsayılan 8, okul değiştirebilir)
- Öğretmene boş gün: her öğretmene hedeflenen sayıda (varsayılan 1) boş gün kazandırılır (esnek,
  ağırlığı ayarlanabilir). Amaç en fazla sıkıştırma değil, hedefe ulaşmaktır
- Program üretme: kuyruk üzerinden, durum takibiyle
- Çözülemezlik açıklaması: çözüm yoksa nedeni kullanıcının diliyle söylenir (ör. "Ayşe Yılmaz'ın
  24 saat dersi var, müsait olduğu 20 saat var"), ön kontrolün yakalayamadığı durumlarda da
  çelişen kısıtlar bulunur
- En az değişiklikle güncelleme: mevcut bir program temel alınarak yeniden üretilir, ondan farklı
  her yerleşim ceza getirir (öğretmen değişikliği gibi durumlarda program baştan dağılmaz)
- Sonucu sınıf ve öğretmen bazında görüntüleme
- Elle düzeltme: dersi sürükleyip taşıma, çakışma uyarısı, hücre kilitleme
- PDF ve Excel çıktısı

### Kapsam dışı (planlanmıyor)
- Mekan takibi ve mekan çakışması (laboratuvar, spor salonu)
- Bölünen ya da birleşen şube, bir derse birden fazla öğretmenin girmesi. Model kalıcı olarak
  "bir sınıf, bir ders, bir öğretmen"dir: her (sınıf, ders) çifti için tek bir ders ataması vardır.

### İlk sürümde yok (model buna açık kalmalı)
- Dönem ve yıl yönetimi
- İkili öğretim
- Öğretmen hesapları

Bu listedeki maddelerin önceliği değişebilir; okullar arasında değişen konular bölüm 10'dadır.

## 4. Mimari

Dört çalışan parça ve bir veritabanı:

```
Tarayıcı (React)
     |
     v
API (FastAPI)  ---->  PostgreSQL
     |                    ^
     v                    |
Kuyruk (Redis)  ---->  Worker (Python)  -->  Çözücü modülü (OR-Tools CP-SAT)
```

- **Web arayüzü:** React. Sadece API ile konuşur.
- **API:** Kimlik doğrulama, okul verisinin yönetimi, program üretme isteklerinin kuyruğa atılması.
  Çözücüyü kendisi çalıştırmaz.
- **Kuyruk:** Program üretme istekleri burada sıraya girer.
- **Worker:** Kuyruktan iş alır, veriyi okur, çözücüyü çalıştırır, sonucu veritabanına yazar.
- **Çözücü modülü:** Veritabanından ve web'den habersiz saf Python paketi. Girdi olarak düz veri
  yapıları alır, çıktı olarak yerleşim listesi döner.

### Temel mimari kararlar ve gerekçeleri

1. **Çözücü API'den ayrı çalışır.** Program üretmek saniyelerden dakikalara kadar sürebilir ve
   işlemciyi tüketir. API içinde çalışsaydı diğer kullanıcıların istekleri beklerdi.
2. **Kuyruk kullanılır.** Aynı anda birçok okul program üretirse (dönem başı) istekler sıraya girer,
   sistem çökmez. Gerekirse worker sayısı artırılır.
3. **Çözücü bir arayüzün arkasındadır.** `ProgramCozucu` arayüzü ve onun `CpSatCozucu`
   gerçeklemesi. Başka bir algoritmaya geçmek geri kalan kodu etkilemez.
4. **Her kısıt ayrı bir sınıftır.** Yeni kural eklemek mevcut kodu değiştirmeyi gerektirmez
   (strategy deseni, açık/kapalı prensibi).
5. **Çok kiracılı yapı satır düzeyindedir.** Her tabloda `okul_id` bulunur ve her sorgu oturumdaki
   okula göre filtrelenir. Bu filtre tek bir yerde (veri erişim katmanında) uygulanır, endpoint
   yazarken unutulabilecek bir şey olmamalıdır. Veritabanı da ayrıca korur: bileşik yabancı
   anahtarlar okullar arası ilişkiyi, PostgreSQL satır düzeyi güvenliği (RLS) başka okulun
   satırlarını görmeyi engeller (bkz. ADR 0009).
6. **Durum takibi sorgulama (polling) ile yapılır.** Arayüz, program durumunu birkaç saniyede bir
   sorar. WebSocket bu ölçek için gereksiz karmaşıklık.
7. **API modüler bir monolittir.** Çekirdek (okul, kullanıcı, öğretmen, sınıf, ders) ile modüller
   (ders programı; ileride ders notları, kütüphane) ayrı paketlerdir. Modül çekirdeğe bağımlı
   olabilir, çekirdek modülleri bilmez, modüller birbirini doğrudan kullanmaz. Yeni modül eklemek
   çekirdeği değiştirmeyi gerektirmez (bkz. ADR 0008, 0010).
8. **Kimlik doğrulama sunucu taraflı oturumladır.**
   - Jeton `HttpOnly`, `SameSite=Strict` bir çerezde taşınır; veritabanında jetonun özeti saklanır.
   - Parola özeti argon2id'dir.
   - Aktif okul yalnızca oturumdan belirlenir.
   - Girişte okul bilinmediği için kullanıcı, RLS altında dar kapsamlı `SECURITY DEFINER`
     fonksiyonlarla aranır.
   - Arayüz ile API tarayıcıya hep aynı kökenden görünür (geliştirmede Vite proxy'si); CORS
     kullanılmaz.

   Bkz. ADR 0012, 0013.

Her önemli karar için `docs/adr/` altına kısa bir karar kaydı (ADR) yazılır: bağlam, karar,
değerlendirilen alternatifler, sonuçları.

## 5. Teknoloji yığını

| Katman | Teknoloji |
|---|---|
| Arayüz | React, TypeScript, Vite |
| API | Python, FastAPI, SQLAlchemy, Alembic (migration) |
| Veritabanı | PostgreSQL |
| Kuyruk | Redis + RQ |
| Çözücü | Google OR-Tools (CP-SAT) |
| Test | pytest |
| Çalıştırma | Docker Compose (tek komutla tüm sistem) |

### Klasör yapısı

```
/cozucu      Saf Python çözücü paketi ve testleri
/api         FastAPI uygulaması
/worker      Kuyruk işçisi
/web         React uygulaması
/docs        Diyagramlar ve ADR kayıtları
/veri        Test veri setleri (mini, gerçekçi, büyük)
docker-compose.yml
```

## 6. Veri modeli

Alan (domain) terimleri Türkçe ve ASCII yazılır (ogretmen, sinif, ders_atama). Bu terimler
kullanıcının diliyle aynı tutulur. Teknik isimler (fonksiyon önekleri, altyapı kodu) İngilizce
olabilir.

Tüm tablolarda `id` (uuid) ve `okul_id` (FK) bulunur. Aşağıda yalnızca diğer alanlar listelenir.

| Tablo | Alanlar | Açıklama |
|---|---|---|
| `okul` | ad, gun_sayisi, gunluk_ders_saati | Kök kayıt (okul_id yok) |
| `kullanici` | email, sifre_hash, ad, rol | Yönetici hesapları (rol: mudur / mudur_yardimcisi). E-posta bütün sistemde, büyük/küçük harf ayrımsız tektir. Her okulda en az bir müdür bulunur |
| `oturum` | kullanici_id, jeton_ozeti, son_kullanim, hareketsizlik_siniri, bitis_mutlak | Giriş oturumları. Kullanıcı silinince silinir |
| `ogretmen` | ad, brans | |
| `sinif` | ad, seviye | Şube, ör. 9-A |
| `ders` | ad, kisa_ad | |
| `seviye_sablonu` | seviye, ders_id, haftalik_saat | Seviyenin ders listesi |
| `ders_atama` | sinif_id, ders_id, ogretmen_id (boş olabilir), haftalik_saat | Çözücünün asıl girdisi |
| `musaitlik` | ogretmen_id, gun, saat, durum (gelemez / tercih_etmez) | |
| `kisit` | tur, parametreler (JSON), zorunlu, agirlik, ders_id, sinif_id, ogretmen_id (kapsam; boş olabilir) | Okul geneli kurallar; kapsam doluysa o derse, şubeye ya da öğretmene özel ayar (ADR 0016) |
| `program` | ad, durum, hata_mesaji, temel_program_id (boş olabilir), sure_siniri_sn, olusturma, bitis | Her üretim denemesi bir kayıt. `temel_program_id` doluysa en az değişiklikle güncellemedir |
| `yerlesim` | program_id, ders_atama_id, gun, saat, kilitli | Programın hücreleri |

`giris_denemesi` (email, hata_sayisi, pencere_basi, kilit_bitis) okula ait **olmayan** tek tablodur.
Kaba kuvvet sayacıdır; uygulama rolünün bu tabloya doğrudan yetkisi yoktur (ADR 0012).

`program.durum` değerleri: `bekliyor`, `uretiliyor`, `hazir`, `basarisiz`.

Gün ve saat tam sayı olarak tutulur (gun: 0 = pazartesi, saat: 0 = ilk ders).

## 7. Çözücü

### Model
Her ders ataması, gün ve saat üçlüsü için bir boolean değişken: "bu atama bu saatte yapılıyor mu".

### Zorunlu kısıtlar (ihlal edilemez)
- Her atama tam olarak haftalık saati kadar yerleşir.
- Bir sınıf aynı saatte en fazla bir derste olur.
- Bir öğretmen aynı saatte en fazla bir sınıfta olur.
- Öğretmen "gelemez" işaretli saatlere yerleştirilmez.
- Kilitli hücreler yerinde kalır.
- Aynı ders bir sınıfa günde en fazla N saat konur (varsayılan 2, kısıt parametresi).
- Bir öğretmen günde en fazla M saat derse girer (varsayılan 8, kısıt parametresi).

### Esnek kısıtlar (ihlali ceza puanı getirir, toplam ceza en aza indirilir)
- Öğretmenin "tercih etmez" saatlerinden kaçınma.
- Öğretmenin gün içindeki boş (pencere) saatlerini azaltma.
- Aynı dersin günde iki saati varsa arka arkaya olması.
- Sınıfın programında boş saat bırakmama (dersler günün başından itibaren dolsun).
- Öğretmene boş gün: parametre hedef boş gün sayısıdır (varsayılan 1).
  Hedef gün = max(⌈toplam saat / günlük sınır⌉, gün sayısı − hedef boş gün). Burada günlük sınır =
  min(M, okulun günlük ders saati). Ceza = max(0, ders verilen gün − hedef gün). Hedefe ulaşan
  öğretmen daha fazla sıkıştırılmaz. Yükü yüzünden boş günü mümkün olmayan öğretmene ceza
  yazılmaz.
- En az değişiklik (yalnızca temel program verildiğinde): temel programdaki bir yerleşim yeni
  programda yoksa ceza.

Her esnek kısıtın ağırlığı okul tarafından ayarlanabilir, 0 kuralı kapatır. Varsayılan ağırlıklar
ve öncelik sırası:

| Kural | Ağırlık | Gerekçe |
|---|---|---|
| Sınıf boşluğu | 30 | Gün ortasında boş kalan sınıf kabul edilemez, diğer bütün esnek kurallardan baskındır |
| En az değişiklik | 8 | Öğretmen konforu kurallarından ağır, sınıf boşluğundan hafif |
| Tercih etmez | 5 | |
| Öğretmene boş gün | 4 | |
| Öğretmen penceresi | 3 | |
| Bölünmüş (ardışık olmayan) ders | 2 | |

### Davranış
- Süre sınırı parametredir (varsayılan 120 saniye). Süre dolunca bulunan en iyi çözüm döner.
  120 sn, ölçülen süreler içinde iki test setinde de sınıf boşluğunu her tohumda sıfırlayan en
  kısa süredir (`docs/olcumler.md`). Üretim kuyrukta çalıştığı için arayüzü bekletmez.
- Ana çözüm süre içinde ne çözüm ne de çözümsüzlük kanıtı bulursa, yalnızca zorunlu kısıtlarla
  ikinci bir kontrol yapılır. Çözüm yoksa çelişkiler açıklanır, varsa "süre yetmedi" denir.
- Çözücü çağrılmadan önce ön kontroller yapılır ve anlaşılır hata verilir: öğretmeni seçilmemiş
  atama, bir sınıfın toplam saati haftalık kapasiteyi aşıyor, bir öğretmenin toplam saati müsait
  olduğu saatlerden fazla (her gün için müsait saat ile M'nin küçüğü sayılır), bir sınıfın
  dersleri öğretmenlerinin müsait olduğu saatlere sığmıyor. Mesajlar kimlik değil ad kullanır.
- Ön kontrolden geçip çözüm yine yoksa, çelişen zorunlu kısıt grupları bulunur ve kullanıcının
  diliyle açıklanır.
- İsteğe bağlı olarak temel bir program girdi alınır. Bu durumda değişiklik cezası devreye girer ve
  temel program çözücüye başlangıç ipucu olarak da verilir.

### Test veri setleri
- **Mini:** 3 sınıf, 5 öğretmen. Hata ayıklama için, sonucu gözle kontrol edilebilir.
- **Gerçekçi:** yaklaşık 24 şube, 45 öğretmen, 5 gün, günde 8 saat, öğretmen müsaitlik kısıtlarıyla.
- **Büyük:** yaklaşık 40 şube, 80 öğretmen. Süre ölçümü için.

Gerçek bir okulun verisi elde edilirse gerçekçi setin yanına eklenir. Veriler uydurma üretilirken her sınıfın
ve öğretmenin toplam saati kapasiteyi aşmayacak şekilde, çözümü olan setler üretilir.

Her çözüm için otomatik doğrulama testi yazılır: çakışma yok, tüm saatler yerleşmiş, zorunlu
kısıtların hepsi sağlanmış.

Gerçekçi ve büyük setlerde yalnızca toplam süre değil, zamana göre kalite de ölçülür: 10, 30, 60
ve 120. saniyede toplam ceza ve her esnek ölçü. 60 saniyedeki kalite yetersizse iyileştirmeler
(ör. önce yalnızca zorunlu kısıtlarla çözüp sonucu başlangıç ipucu olarak vermek) ölçülerek
değerlendirilir.

## 8. Yapım sırası

Her adımın sonunda çalışan ve test edilen bir şey olmalı. Bir adım bitmeden sonrakine geçilmez.

1. **Çözücü.** Saf Python paketi, üç veri seti, doğrulama testleri. Komut satırından çalışır ve
   programı tablo olarak yazdırır. Çözülemezlik açıklaması ve temel programla güncelleme dahil.
   Kabul: gerçekçi set süre sınırı içinde çözülür, testler geçer, zamana göre kalite ölçülmüştür.
2. **Veritabanı ve API temeli.** Docker Compose, tablolar, migration, okul izolasyonu (ORM filtresi,
   bileşik yabancı anahtarlar ve PostgreSQL satır düzeyi güvenliği), temel CRUD endpoint'leri.
   Çekirdek (okul, kullanıcı, öğretmen, sınıf, ders) ders programı modülünden ayrıdır. Plan:
   `docs/api-plani.md`. Kabul: iki okul oluşturulur, biri diğerinin verisine erişemez (testle
   kanıtlanır); bağlantı havuzunda aynı bağlantı art arda farklı okullar için kullanıldığında okul
   bilgisi bir istekten diğerine taşmaz (testle kanıtlanır).
3. **Kuyruk ve worker.** Program üretme isteği, durum takibi, sonucun kaydedilmesi.
   Kabul: API'den istek atılır, durum `bekliyor` → `uretiliyor` → `hazir` olarak değişir.
4. **Kimlik doğrulama.** Okul kaydı, giriş, oturum. Kabul: 2. adımdaki geçici `X-Okul-Id`
   başlığı tamamen kaldırılmıştır; aktif okul yalnızca oturumdan belirlenir. Başlık gönderilse
   bile yok sayıldığı ve oturumsuz isteklerin okula ait veriye erişemediği testle kanıtlanır.
5. **Arayüz: veri girişi.** Okul ayarları, listeler, seviye şablonu, ders atama, müsaitlik çizelgesi.
6. **Arayüz: program.** Üretme, durum göstergesi, sınıf ve öğretmen görünümü, çözülemezlik
   açıklamasının gösterilmesi, mevcut programı temel alarak yeniden üretme.
7. **Elle düzeltme ve çıktı.** Sürükle bırak, çakışma uyarısı, kilitleme, PDF ve Excel.
8. **Excel'den içe aktarma ve öğretmen paylaşım linki.** Paylaşılan (yayınlanan) program dondurulur:
   veri değişse de aynı kalır, veri değiştiğinde "eski veriyle üretildi" uyarısı gösterilir
   (bkz. docs/api-plani.md bölüm 15).

**Sıra değişikliği (kullanıcı kararı):** 5. adımın son iki alt adımı (müsaitlik çizelgesi;
kullanıcılar ve uçtan uca) ertelendi. Sistemin ekranda uçtan uca kullanılabilmesi için önce 6.
adımın ilk iki alt adımı (program üretme, haftalık çizelge) yapılır. Örnek okulda müsaitlik verisi
olduğu için bu sıra çözücüyü eksik veriyle çalıştırmaz. Ayrıntı ve durum: docs/arayuz-plani.md.

## 9. Çalışma kuralları

- Küçük adımlarla ilerle. Her adımda ne yapılacağını önce kısaca söyle, sonra yap.
- Proje sahibi yazılım mühendisi ama React ve PostgreSQL'i bu projeyle öğreniyor. Bu ikisinde
  önemli kavramları ve neden öyle yapıldığını kısaca açıkla.
- Mimari bir karar verirken alternatifi ve gerekçeyi belirt, `docs/adr/` altına kaydet.
- Çözücü paketine veritabanı ya da web bağımlılığı ekleme.
- Okul izolasyonunu atlayan sorgu yazma.
- Her özellik için test yaz. Testler geçmeden iş bitmiş sayılmaz.
- Test, lint ve tip denetimi komutlarının çıktısı asla `tail`, `head`, `grep` ya da başka bir
  komuta borulanmaz (boru, komutun çıkış kodunu son komutunkiyle değiştirir; başarısızlık
  görünmez olur). Başarı her zaman komutun kendi çıkış koduyla denetlenir; çıktı gerekiyorsa
  önce dosyaya yazılır, çıkış kodu ayrıca okunur. Commit ancak bütün denetimlerin çıkış kodu 0
  ise yapılır. (Bu kural, başarısız bir testin iki kez commit edilmesinden sonra eklendi.)
- Kapsam dışı bir özelliği sormadan ekleme.
- Bu dosyadaki bir kararın yanlış olduğunu düşünürsen uygulamadan önce söyle.

## 10. Okuldan okula değişen konular (ayarlanabilir olmalı)

Sistem genel olduğu için aşağıdakiler bir okulun kararıdır, kodun değil. Her biri ayarlanabilir
olmalı ve okul hiçbir şey girmese de makul bir varsayılanla çalışmalıdır. "Durum" sütunu bugün
ne yapıldığını söyler. Öğretmen, ders ve şube bazında istisnalar için tasarım:
`docs/kisisellestirme-plani.md` (harfler oradaki ihtiyaç listesidir).

| Konu | Önerilen varsayılan | Durum |
|---|---|---|
| Haftadaki gün sayısı | 5 | Var (okul ayarı) |
| Günlük ders saati | 8 (ortaokulda çoğunlukla 7) | Var (okul ayarı) |
| Günlere göre farklı ders saati (ör. cuma 7) | Her gün aynı | Tasarımda (c) |
| Öğle arasının yeri | Tanımsız (blokların bölünmesi denetlenmez) | Tasarımda (c) |
| Ders saatlerinin başlangıç ve bitiş saatleri (yalnızca gösterim) | 08.30'da başlar, 40 dk ders, 10 dk teneffüs | Tasarımda (j) |
| Aynı dersin bir şubeye günlük sınırı (N) | 2 | Okul geneli var; derse, şubeye özel çözücüde ve API'de var (K1), arayüzü K4'te (e) |
| Öğretmenin günlük ders sınırı (M) | 8 | Okul geneli var; öğretmene özel çözücüde ve API'de var (K1), arayüzü K2'de |
| Öğretmene boş gün hedefi | Okul geneli 1; öğretmene özel 0, 1 ya da 2 | Okul geneli var; öğretmene özel tasarımda (d) |
| Dersin bloklara bölünmesi | 1 saat: 1; 2: 2; 3: 2+1; 4: 2+2; 5: 2+2+1; 6: 2+2+2 | Tasarımda (b) |
| Şube grupları (alanlar: sayısal, sözel, eşit ağırlık, dil) | Grup = seviye | Tasarımda (a) |
| Şubeye özel "bu dersi almaz / ek alır" | Yok | Tasarımda (a) |
| Dersin saat tercihi (ör. Matematik sabah) | Yok | Tasarımda (f) |
| Öğretmenin geldiği günde en az ders | 2, esnek ("bir saat için gelmem") | Tasarımda (g) |
| Aynı dersin günlere yayılması | Açık, "Önemli" | Tasarımda (h) |
| Öğretmenin haftalık yük eşikleri (maaş karşılığı, ek ders üst sınırı) | Kapalı; okul girerse uyarı | Tasarımda (i) |
| Esnek kuralların önemi | "Önemli" = bölüm 7'deki ağırlıklar | Var ("Önemsiz / Önemli / Çok önemli") |
| Program üretme süre sınırı | 120 sn | Var |
| Başka okulda da görevli öğretmen | Müsaitlik çizelgesiyle ("gelemez" günler) | Var |
| İkili öğretim | Tekli | İlk sürümde yok (bölüm 3) |

Notlar:
- Gerçekçi test setinde öğretmenlerin yaklaşık yarısı hedef boş gününe ulaşamıyor. Bu bir hata
  değil, varsayılan ağırlık tercihi: boş gün (4) sınıf boşluğundan (30), tercih etmezden (5) ve
  değişiklikten (8) hafif. Okul önemini "Çok önemli" yaparak değiştirebilir.
- Önem seviyelerinin sayısal karşılıkları API'de tek yerde tanımlıdır (docs/arayuz-plani.md
  2.3); ölçümlerle ayarlanabilir.

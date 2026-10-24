# Yapım sırası 5 (arayüz: veri girişi) ve 6 (arayüz: program) planı

Durum: **onaylandı (2026-10-15).** Kararlar bölüm 8'de. Alt adım durumu bölüm 7'de.

Kabul (CLAUDE.md bölüm 8, yapım sırası 5): okul ayarları, listeler, seviye şablonu, ders atama ve
müsaitlik çizelgesi arayüzden girilebilir. Ek hedef: mini set baştan sona yalnızca arayüz
kullanılarak girilebilir ve bunu bir uçtan uca test kanıtlar.

Kullanıcılar okul müdürleri ve müdür yardımcılarıdır, teknik kişiler değildir. İlkeler:
- **Sade ve Türkçe.** Her ekranda tek bir ana iş. Teknik terim yok ("atama" yerine "Kim hangi
  dersi veriyor").
- **Hatalar anlaşılır ve yerinde.** Hata, ilgili alanın altında, ne yapılacağını söyleyerek
  gösterilir. "Hata 422" asla görünmez.
- **Öncelik masaüstü, telefonda da kullanılabilir.** Okul bilgisayarında, geniş tablolarla çalışılır.
  Telefonda listeler karta dönüşür, menü alta iner.
- **Erişilebilirlik:**
  - klavyeyle kullanılabilir;
  - renk tek başına anlam taşımaz (müsaitlik çizelgesinde renk + simge + yazı);
  - `lang="tr"`.

## 1. Teknoloji ve kütüphaneler

Temel: **React + TypeScript + Vite** (CLAUDE.md). Kütüphane sürümleri kurulumda sabitlenir
(`package-lock.json`).

| İhtiyaç | Öneri | Gerekçe | Alternatif ve neden seçilmedi |
|---|---|---|---|
| Yönlendirme (sayfalar, adres çubuğu) | **React Router** | React'in fiilen standart yönlendiricisi. Belgesi ve örneği bol. Korumalı sayfa ("giriş yapılmamışsa giriş sayfasına") kolay. | TanStack Router: tür güvenliği daha iyi, ama kavramları daha çok. React'i öğrenirken ikinci bir öğrenme yükü. |
| Sunucu verisi (çekme, önbellek, yenileme) | **TanStack Query** | Verinin çoğu sunucuda. Yükleniyor, hata ve yeniden deneme durumlarını; bir kayıt eklenince listenin tazelenmesini; yapım sırası 6'daki durum sorgulamasını (`refetchInterval`) hazır verir. | `useEffect` + `fetch` ile elle yapmak: her ekranda aynı yükleme ve hata kodu tekrarlanır, yarış durumları ve eski veri hataları çıkar (React'te en sık yapılan hata). SWR: benzer ama daha az özellikli; Query'nin "mutation" desteği daha olgun. |
| İstemci durumu (global) | **Kütüphane yok.** Sunucu verisi Query'de, sayfa içi durum `useState`'te. Giriş yapan kullanıcı Query'deki `/api/ben` sorgusundan okunur. | Redux ya da Zustand gibi bir global durum deposu, bu uygulamada çözülecek bir sorun olmadan karmaşıklık ekler. | Redux Toolkit, Zustand: ihtiyaç doğarsa (ör. yapım sırası 7'de sürükle-bırak taslağı) yeniden değerlendirilir. |
| Formlar | **Kütüphane yok.** Kontrollü form bileşenleri ve küçük bir `useForm` kancası (hook). Doğrulama sunucudadır; arayüz yalnızca bariz olanı önceden söyler (boş alan, parola 12 karakter). | Formlar küçük (en fazla 5 alan). Asıl kurallar sunucuda ve sunucunun Türkçe hata mesajları alanların altına yerleşir: kural iki yerde yazılmaz. Kontrollü form, React'in temel kavramlarından biri; öğrenmek için de değerli. | React Hook Form + Zod: büyük ve çok kurallı formlarda iyi, burada iki ek bağımlılık ve kuralların ikinci kopyası. |
| API çağrıları ve tipler | **openapi-typescript** (yalnızca geliştirmede: API'nin OpenAPI şemasından TypeScript tipleri üretir) ve **openapi-fetch** (~6 KB, bu tiplerle `fetch` sarmalayıcısı) | API'deki bir alan adı değişirse arayüz derlenmez: hata kullanıcıda değil derlemede görünür. Tipler elle yazılmaz, API ile arayüz ayrışmaz. | Tipleri elle yazmak: zamanla API'den ayrışır. axios: `fetch` yeterli, gereksiz bağımlılık. |
| Görsel stil | **Bölüm 3'te iki seçenek, öneri ve karar sizde.** | | |
| Test | **Vitest**, **Testing Library**, **MSW**, **Playwright** | Bölüm 5. | |

Toplam çalışma zamanı bağımlılığı: react, react-dom, react-router, @tanstack/react-query,
openapi-fetch. Bölüm 3'teki seçime göre bir bileşen kütüphanesi eklenebilir.

## 2. Ekranlar ve akış

```
Giriş ──► (ilk kez) Kayıt ──► Ana sayfa (kurulum adımları)
                                  │
     ┌──────────┬──────────┬──────┴─────┬──────────────┬───────────────┬───────────────┐
 Okul ayarları  Öğretmenler  Sınıflar   Dersler   Seviye şablonu   Ders dağılımı   Müsaitlik
                                                                   (şube / öğretmen)
     Kullanıcılar (müdür) · Hesabım (parola) · [yapım sırası 6: Programlar]
```

**Çerçeve:**
- Masaüstünde solda menü, üstte okul adı ve kullanıcı adı (çıkış düğmesi).
- Telefonda menü altta, sık kullanılan 4 sayfa ve "Daha fazla".
- Oturum süresi dolarsa (401) giriş sayfasına gidilir: "Oturumunuzun süresi doldu, yeniden giriş
  yapın". Giriş sonrası kalınan sayfaya dönülür.

### 2.1 Giriş ve kayıt
- **Giriş:** e-posta ve parola. "E-posta ya da parola hatalı" ve kilitte "15 dakika sonra yeniden
  deneyin" (sunucunun mesajları). Kayıt sayfasına bağlantı.
- **Kayıt:** tek sayfa, iki bölüm:
  - "Okulunuz": ad, haftada kaç gün, günde kaç ders saati. Varsayılanlar 5 ve 8, kısa
    açıklamalarla.
  - "Hesabınız": ad, e-posta, parola. Yazarken "en az 12 karakter" göstergesi.
  
  E-posta kullanılıyorsa alanın altında sunucunun mesajı görünür.

### 2.2 Ana sayfa: kurulum adımları
Teknik olmayan kullanıcı için yol gösterici bir kontrol listesi. Her satır tıklanınca ilgili
sayfaya gider; sayılar sunucudan:

```
✓ Okul ayarları             5 gün, günde 8 ders
✓ Öğretmenler               45 öğretmen
✓ Sınıflar                  24 şube
✓ Dersler                   14 ders
! Ders dağılımı             3 dersin öğretmeni seçilmedi   [Tamamla]
· Öğretmen müsaitliği       isteğe bağlı
```

Yapım sırası 6'da altına "Program üret" düğmesi gelir. Eksik varsa düğme neden pasif olduğunu
söyler.

### 2.3 Okul ayarları
- Okulun adı, gün sayısı, günlük ders saati.
- "Kurallar" bölümü (okul geneli kısıtlar) sade dille:
  - "Aynı ders bir sınıfa günde en fazla [2] saat";
  - "Bir öğretmen günde en fazla [8] saat";
  - "Her öğretmene haftada [1] boş gün kazandırmaya çalış".
- "Gelişmiş" katlanır bölümünde esnek kurallar. Her kural için sade Türkçe bir açıklama
  ("Sınıfların gün ortasında boş saati olmasın") ve üç seviyeli bir seçim: **Önemsiz / Önemli /
  Çok önemli**. Ham sayı ya da kaydırıcı gösterilmez (kullanıcı kararı, 2026-10-15).
  - Varsayılan kurallarda kuralın ağırlığı farklıdır (30, 8, 5, 4, 3, 2). Bu yüzden her kuralın
    kendi üç sayısı vardır ve **"Önemli" = bugünkü varsayılan ağırlık**.
  - Karşılıklar **tek bir yerde** tanımlanır: API'de, ders programı modülünde, çözücünün
    varsayılanlarının yanında. Arayüz bunları API'den okur, kendisi sayı bilmez. Bir test
    "Önemli = çözücünün varsayılan ağırlığı" eşitliğini denetler.
  - Kayıtlı ağırlık hiçbir seviyeye denk gelmiyorsa (ör. elle girilmiş) "Özel" gösterilir.
  - Okul müdüründen cevap gelince karşılıklar ayarlanacak (CLAUDE.md bölüm 10).

  İlk karşılıklar (önemsiz / **önemli** / çok önemli):

  | Kural | Önemsiz | Önemli (varsayılan) | Çok önemli |
  |---|---|---|---|
  | Sınıf boşluğu | 10 | **30** | 60 |
  | En az değişiklik | 3 | **8** | 20 |
  | Tercih etmez | 2 | **5** | 12 |
  | Öğretmene boş gün | 1 | **4** | 10 |
  | Öğretmen penceresi | 1 | **3** | 8 |
  | Bölünmüş ders | 1 | **2** | 5 |
- Gün ya da saat sayısı düşürülürse ve bu yüzden bazı müsaitlik kayıtları dışarıda kalacaksa
  uyarı.

### 2.4 Öğretmenler, sınıflar, dersler
Üç ekran aynı ortak liste bileşenini kullanır:
- Tablo: ada göre Türkçe sıralı (`localeCompare('tr')`: Ç, Ğ, İ, Ö, Ş, Ü doğru yerde). Üstte
  arama kutusu.
- Ekleme: tablonun altında satır içi form ("+ Öğretmen ekle"). Enter ile kaydedilir, odak bir
  sonraki boş satıra geçer. Uzun listeyi hızlı girmek için.
- Düzenleme: satıra tıklayınca satır düzenlenebilir olur.
- Silme: onay penceresi. Kayıt kullanılıyorsa sunucunun mesajı gösterilir ("Bu öğretmenin ders
  atamaları var...").
- Alanlar:
  - öğretmen: ad, branş;
  - sınıf: ad (9-A), seviye;
  - ders: ad, kısa ad.
- Telefonda tablo kartlara dönüşür.
- Excel'den içe aktarma yapım sırası 8'de; şimdilik yer ayrılmaz.

### 2.5 Seviye şablonu
- Üstte seviye seçimi: okulda var olan seviyeler, ör. "9. sınıflar (3 şube)".
- Tablo: ders ve haftalık saat, satır içi düzenleme. Altında toplam: "Haftalık 32 saat, okulun
  kapasitesi 40 saat".
- "Bu seviyedeki şubelere uygula" düğmesi. Sonuç özeti sunucudan gelir: "9-A, 9-B, 9-C: 12 ders
  eklendi. 9-B'de Matematik'in saati şablondan farklı (5 / 6), değiştirilmedi."

### 2.6 Ders dağılımı (ders atama)
İki görünüm, üstte sekme ile:
- **Şube görünümü:**
  - solda şube listesi; yanında toplam saat ve eksik öğretmen işareti, ör. "9-A ⚠ 2";
  - sağda seçili şubenin tablosu: ders, haftalık saat, öğretmen (aranabilir açılır liste). Açılır
    listede her öğretmenin yanında güncel yükü görünür, ör. "Ayşe Yılmaz, 18/24 saat";
  - altta "Toplam 38 saat, kapasite 40". Aşınca kırmızı ve açıklama.
  - Öğretmen seçmek anında kaydedilir.
- **Öğretmen görünümü:**
  - her öğretmen için toplam ders yükü bir çubukla: verdiği saat / müsait olduğu saat (günlük
    sınırla birlikte, sunucunun ön kontrolüyle aynı hesap);
  - yükü müsaitliğini aşan öğretmen en üstte ve kırmızı: "Ayşe Yılmaz'ın 24 saat dersi var,
    müsait olduğu 20 saat var";
  - satıra tıklayınca o öğretmenin dersleri açılır (hangi şube, hangi ders, kaç saat).
  
  **Değişti (5.4, kullanıcı isteği, ADR 0015):** hesap arayüzde yapılmaz. Çözücü paketindeki
  `cozucu.yuk` hem ön kontrolün hem de API'nin `GET /api/ders-programi/dagilim-ozeti` ucunun
  kaynağıdır; arayüz yalnızca gösterir. İlk plan ("hesap arayüzde, ortak örnek dosyayla iki
  tarafta test") aynı kuralı iki dilde iki kez yazmak demekti.

### 2.7 Öğretmen müsaitlik çizelgesi
- Üstte öğretmen seçimi (önceki/sonraki okları ile hızlı geçiş).
- Çizelge: sütunlar günler, satırlar ders saatleri. Her hücre tıklandıkça döner:
  **müsait** (boş) → **gelemez** (koyu, ✕) → **tercih etmez** (açık, ~) → müsait.
- Gün ya da saat başlığına tıklayınca bütün satır/sütun değişir ("pazartesi bütün gün gelemez").
- Her tıklama anında kaydedilir. İyimser güncelleme (optimistic update): hücre hemen değişir,
  sunucu reddederse geri döner ve mesaj gösterilir.
- Altta özet: "Müsait 34 saat, ders yükü 24 saat". Yük müsaitliği aşarsa uyarı.
- Klavye: oklarla hücre seçimi, boşlukla değiştirme.
- Telefonda hücreler parmak boyutunda (en az 44 px); çizelge gerekirse yatay kaydırılır.

### 2.8 Kullanıcılar (müdür) ve Hesabım
- **Kullanıcılar:**
  - liste: ad, e-posta, rol;
  - müdür için: "Müdür yardımcısı ekle", "Parolasını yeniden belirle" (uyarı: "Açık oturumları
    kapanacak"), "Müdür yap / yardımcı yap", "Sil";
  - son müdür kuralında sunucunun mesajı gösterilir;
  - yardımcı aynı listeyi düğmeler olmadan görür.
- **Hesabım:** parola değiştirme (mevcut + yeni + yeni tekrar). "Diğer cihazlardaki oturumlarınız
  kapandı" bilgisi.

### 2.9 Hatalar ve yükleniyor durumları
- **Tek bir hata biçimi.** API'nin hata yanıtı arayüzde tek bir yerde (`api/hata.ts`) çözülür:
  - alan hatası ilgili alanın altına;
  - genel hata formun üstüne;
  - bağlantı hatası ekranın üstünde bir şerit: "Sunucuya ulaşılamıyor, bağlantınızı kontrol
    edin".
- **Backend değişikliği gerekiyor:** şu an pydantic'in doğrulama hataları İngilizce ve liste
  biçiminde (`{"detail": [{"loc": [...], "msg": "String should have at least 1 character"}]}`).
  5.1'de API'ye bir hata işleyicisi eklenecek: `{"detail": "Bazı alanlar hatalı",
  "alanlar": {"okul.ad": "Boş bırakılamaz", "email": "Geçerli bir e-posta adresi girin"}}`.
  Türkçe mesajlar hata türünden üretilir. Servislerin kendi hataları zaten Türkçe ve tek
  metindir.
- **Yükleniyor:** ilk yüklemede iskelet satırlar, kaydederken düğmede "Kaydediliyor...". Çift
  tıklama ikinci isteği göndermez.

## 3. Görsel tasarım: iki seçenek

| | **A. Kendi sade stilimiz** (öneri) | **B. Hazır bileşen kütüphanesi** (Mantine) |
|---|---|---|
| Ne | Doğal HTML öğeleri (`<table>`, `<dialog>`, `<select>`, `<form>`), düz CSS ve CSS değişkenleriyle tasarım belirteçleri (renk, boşluk, yazı boyu). Bileşen başına CSS modülü. | Hazır, erişilebilir bileşenler: tablo, pencere, açılır liste, bildirim, sekme. |
| Artıları | Sıfır ek bağımlılık. React'in kendisi görünür; kütüphanenin API'si değil React öğrenilir. Doğal HTML öğeleri erişilebilirliği tarayıcıdan bedava alır (`<dialog>` odak yönetimi, `<select>` klavye). Görünüm tamamen bizim: sade, okul ortamına uygun. Paket küçük. | Hız: aranabilir açılır liste, bildirimler, sekmeler hazır. Tutarlı ve olgun görünüm. Karanlık tema ve telefon uyumu hazır. |
| Eksileri | Birkaç parçayı kendimiz yazarız: aranabilir öğretmen seçici, bildirim (toast), sekme. Her biri birkaç düzine satır, ama erişilebilirliğini kendimiz test etmeliyiz. Görsel cila için daha çok emek. | Kütüphanenin kavramları React'in üstüne ikinci bir öğrenme yükü. Paket büyür. Görünümün dışına çıkmak zorlaşır. Sürüm yükseltmeleri kırıcı olabilir. |

**Karar: A** (kullanıcı, 2026-10-15). Ek istek: 5.1'de ortak bir tasarım temeli kurulur.
- Renkler, boşluklar, yazı boyutları ve köşe yuvarlaklıkları CSS değişkenleri (tasarım
  belirteçleri) olarak tek dosyada tanımlanır. Bütün bileşenler yalnızca bunları kullanır.
- Ortak temel bileşenler: düğme, form alanı (etiket + açıklama + hata), tablo, bildirim, onay
  penceresi.
- Erişilebilirlik:
  - her şey klavyeyle kullanılabilir;
  - odak her zaman görünür (`:focus-visible` halkası);
  - metin/arka plan kontrastı en az WCAG AA (4.5:1). Bunu belirteç dosyasından hesaplayan bir
    test denetler.

Gerekçeler:
- Ekranlar az sayıda ve çoğu tablo ile formdan oluşuyor. En özel parça olan müsaitlik çizelgesi
  zaten hiçbir kütüphanede hazır değil.
- Proje bir ders projesi ve React'i öğrenmek de amaçlardan biri. Bileşenleri kendimiz yazmak
  React'i öğretir.
- "Gereksiz bağımlılıktan kaçın" isteğinize uyar.

Aranabilir seçici yazılırken zorlanırsak yalnızca o parça için başsız (headless) bir yardımcı
eklemek seçenek olarak kalır.

## 4. React'i öğrenme sırası

Her alt adımda yeni kavramlar, o adımın kodu üzerinden, küçük örneklerle anlatılır:

| Alt adım | Kavramlar |
|---|---|
| 5.1 | Bileşen ve JSX (HTML'e benzeyen ama JavaScript olan sözdizimi); props (bileşene dışarıdan verilen değerler); TypeScript ile props tipleri; Vite'ın geliştirme sunucusu ve proxy; `StrictMode`'un geliştirmede her şeyi iki kez çalıştırması ve nedeni. |
| 5.2 | `useState` ve yeniden çizim (state değişince bileşen fonksiyonu yeniden çalışır); kontrollü form; olay işleyicileri; React Router (sayfa, bağlantı, korumalı sayfa); TanStack Query'ye giriş: sorgu (`useQuery`) ve değişiklik (`useMutation`). |
| 5.3 | Liste çizimi ve `key` (React hangi satırın hangisi olduğunu nasıl bilir); bileşen bileşimi (ortak liste bileşeni + sayfaya özel sütunlar); sorgu geçersiz kılma (bir öğretmen eklenince liste nasıl tazelenir); türetilmiş değerler (ayrı state yerine hesaplamak). |
| 5.4 | Durumu yukarı taşımak (iki bileşenin aynı veriye ihtiyacı); `useMemo` ne zaman gerekir, ne zaman gerekmez; özel kanca (custom hook): `useOgretmenYukleri`. |
| 5.5 | İyimser güncelleme ve geri alma; klavye olayları ve odak yönetimi (`useRef`); erişilebilirlik (ARIA rolleri, `aria-pressed`). |
| 5.6 | Context (bağlam): oturum bilgisini derinlere taşımak ve ne zaman gereksiz olduğu; `useEffect`'in doğru kullanımı (dış dünyayla senkronizasyon) ve yanlış kullanımı (veri çekmek). |

## 5. Testler

- **Bileşen ve sayfa testleri: Vitest + Testing Library + MSW.**
  - Testing Library, sayfayı kullanıcının gördüğü gibi sorgular: `getByRole("button", { name:
    "Kaydet" })`. CSS sınıfına ya da iç yapıya bağlı değildir. Bu, erişilebilirliği de zorlar:
    düğmenin erişilebilir bir adı yoksa test onu bulamaz.
  - `user-event` gerçek tıklama ve klavye girişini taklit eder.
  - MSW (Mock Service Worker) ağ düzeyinde sahte API'dir: bileşen gerçek `fetch` yapar, MSW cevap
    verir. Hata durumları (409, 422, 401, bağlantı hatası) kolayca kurulur.
  - Her ekran için:
    - mutlu yol;
    - sunucu hatasının doğru yerde gösterilmesi;
    - yükleniyor durumu;
    - yetki farkı (müdür / yardımcı).
- **Saf hesap testleri:** öğretmen yükü ve müsait saat hesabı arayüzde değil, çözücü paketinde
  (`cozucu/tests/test_yuk.py`). Özetin ön kontrolle aynı mesajları verdiğini
  `api/tests/test_dagilim.py` gerçek veritabanıyla denetler (5.4'te değişti, ADR 0015). Arayüzde
  saf fonksiyon testi olarak branş eşleştirmesi kalır (Vitest).
- **Uçtan uca: Playwright**, çalışan gerçek sisteme karşı (docker compose + Vite):
  - kayıt → mini setin arayüzden girilmesi (ayarlar, listeler, şablon, dağılım, müsaitlik) →
    ana sayfadaki kontrol listesinin tamamlanması;
  - veritabanının API ile aynı veriyi gösterdiği denetlenir.
  - Masaüstü ve telefon görünüm boyutunda.
  - Yapım sırası 6'da bu test programı üretip bir şubenin çizelgesini ekranda doğrular.
- **Tip denetimi ve lint:** `tsc --noEmit` ve ESLint (React kanca kuralları: `rules-of-hooks`,
  `exhaustive-deps`) her test çalıştırmasında.
- **API tipleri güncel mi:** OpenAPI şemasından üretilen tipler depoda durur. Bir test şemayı
  yeniden üretip farkı denetler: API değişip tipler yenilenmezse test kırılır. Bu, diyagram
  denetimindeki fikrin aynısı.

## 6. Çalıştırma ve Docker

- `web/` klasörü (CLAUDE.md klasör yapısı). Geliştirme: `cd web && npm install && npm run dev`;
  Vite `localhost:5173`'te açılır, `/api`'yi `localhost:8000`'e iletir (ADR 0013).
- docker-compose'a `web` servisi (node imajı, Vite geliştirme sunucusu). Proxy hedefi ortam
  değişkeniyle `http://api:8000`. `docker compose up` ile her şey tek komutla kalkar; kaynak kod
  bağlanır, değişiklik anında görünür.
- Yayın derlemesi (`npm run build`, statik dosyalar + ters vekil sunucu) yayına alma adımında.

## 7. Alt adımlar

### Yapım sırası 5 (veri girişi)

Her alt adım testler geçince commit edilir, onayınız olmadan sonrakine geçilmez.

1. **Altyapı:**
   - `web/` (Vite, React, TypeScript), Vite proxy'si, API tipleri ve `api/` istemci katmanı;
   - test düzeneği (Vitest, Testing Library, MSW, Playwright iskeleti), ESLint;
   - docker-compose `web` servisi;
   - **backend:** Türkçe ve tek biçimli doğrulama hataları (`detail` + `alanlar`);
   - sade stil temeli (tasarım belirteçleri, düğme, alan, tablo) ve çerçeve (menü, üst çubuk).
   
   Kabul: boş bir sayfa ve menü açılır, `/api/saglik` arayüzden okunur, testler geçer.
2. **Kimlik:** giriş, kayıt, çıkış; korumalı sayfalar; 401'de giriş sayfası; Hesabım (parola).
3. **Okul ayarları ve listeler:** okul ayarları ve kurallar; öğretmen, sınıf, ders listeleri
   (ortak liste bileşeni).
4. **Seviye şablonu ve ders dağılımı:** şube, öğretmen ve ders görünümü; yük özeti sunucudan
   (ön kontrolle aynı hesap, ADR 0015); toplu öğretmen atama.
5. **Müsaitlik çizelgesi.**
6. **Kullanıcılar, ana sayfa kontrol listesi ve uçtan uca:** Playwright ile mini setin arayüzden
   girilmesi; telefon görünümü ve erişilebilirlik kontrolü; README, diyagram 09'da web artık
   gerçek.

**Durum:**

| # | Alt adım | Durum |
|---|---|---|
| 5.1 | Altyapı | Bitti (2026-10-16) |
| 5.2 | Kimlik | Bitti (2026-10-16) |
| 5.3 | Okul ayarları ve listeler | Bitti (2026-10-16) |
| 5.4 | Seviye şablonu ve ders dağılımı | Bitti (2026-10-16) |
| 5.5 | Müsaitlik çizelgesi | K2 ile birlikte yapılacak (öğretmen detay sayfası) |
| 5.6 | Kullanıcılar, telefon kontrolü, uçtan uca | K5'ten sonra (kontrol listesi tasarım 3e'de yapıldı). Müsaitlik çizelgesinde dokunmatik: kaydırma serbest, dokunma tek hücre, sürükleme "Toplu seç" modunda (K2 notlarında) |
| 6.1 | Program üretme ekranı ve durum takibi | Bitti: `/program`; engeller (öğretmensiz, aşım) düğmeyi pasif yapar; süre seçimi; sorgulama `refetchInterval` fonksiyonuyla (etkin program yoksa durur); bekleme paneli (mini çizelge animasyonu, süre çubuğu, aşamalar); başarısızlıkta çelişkiler türüne göre ve ilgili şube/öğretmene bağlantıyla; panoda program adımı ve son programa bağlantı; API şemasında `CeliskiYanit` tipli |
| 6.2 | Haftalık çizelge görünümü ve kalite özeti | Bitti: `/program/:id`; şube ve öğretmen sekmeleri, seçim adres çubuğunda; hücrede ders çipi ve öğretmen rozeti ya da şube adı; boş saat sade; hücreler gün gün sırayla yerleşir (en çok 0,6 sn); çizelge boyutu okul ayarı ile programın büyüğü; kalite özeti sade Türkçe |
| 6.3 | Programlar listesi ve temel alarak yeniden üretme | Bitti (2026-10-24). API: `PATCH /programlar/{id}` (ad), `DELETE /programlar/{id}` (üretimi süren program 409; bu programı temel alanların bağı kopar), `GET /programlar/{id}/fark?ile=` (verilmezse temel program; hücreler şube + ders + gün + saat ile karşılaştırılır; `degisen` kalite ölçüsündeki "değişen yerleşim"le aynı tanım; şube başına sayı ve değişen hücreler). "Eski verilerle üretildi": migration `ders_programi_0008` ile `program.veri_ozeti` (yalnızca okulun verisi, temel program ve kilitler hariç; `girdi_ozeti` temel program silinince de değişirdi, yanlış uyarı verirdi); `ProgramYanit.eski_veri` (hazır programda; eski programlarda bilinmiyor). Arayüz: Programlar tablosu (durum ve kısa kalite "3 konu iyileştirilebilir", ayrıntı `title`'da; "Temel: …"; "Eski verilerle" rozeti; satır içi ad değiştirme; onaylı silme; "Temel al"); hazır panelinde eski veri uyarısı (tek tıkla temel alarak yeniden üret), temel programa göre fark özeti ("“Eylül” programına göre 3 ders saati yer değiştirdi: 9-A (2), 9-B (1)") ve "Bu programı temel alarak yeniden üret"; oluşturma kartında "“X” temel alınıyor" ve "Temel almadan üret"; çizelgede `?fark=1` / "Temel programdan değişen dersleri vurgula" (kesik çerçeve ve nokta, ekran okuyucuya "Temel programa göre değişti"), masaüstü ve gün gün görünümde. Geliştirme veritabanından 23 Ekim tarihli iki başarısız program (kullanıcı isteği) silindi. |
| 7.1 | Elle düzeltme: taşıma, kilit, geri alma | Bitti (2026-10-24, ADR 0019). Çözücü: `dogrulama.ihlaller` (tür, karşılaştırma anahtarı, kullanıcı dilinde mesaj; `dogrula` aynı metinleri döner); `cozucu/tasima.py`: blok bütün taşınır, kilitli ders taşınmaz, **yer değiştirme** (hedefte aynı şubenin dersi varsa boşalan saatlere geçer; takassız ilk sürümde gerçekçi sette 40 dersin 38'inin hedefi yoktu, takasla 6), yalnızca yeni zorunlu ihlal engeller, ağırlığı > 0 esnek ölçü kötüleşirse uyarı; `BlokHesabi.desen` önbelleği (harita 3 sn → 0,6 sn). API: `GET /programlar/{id}/tasima` (her başlangıç hücresi uygun / uyarı / engel, nedenler, takas edilen dersler), `POST /tasi` (422 engel, 409 onaysız uyarı), `PUT /kilit` (bütün blok), `POST /geri-al` (sondan başa; 409 yoksa); `program_islemi` (migration `ders_programi_0009`, RLS, bileşik FK, CASCADE); `ProgramYanit.elle_duzeltme`; kalite ölçümü ve toplam ceza her değişiklikte yeniden hesaplanır; program satırı FOR UPDATE. Arayüz: çizelgede masaüstünde sürükle bırak (bırakmadan biterse iptal), tıklayarak ya da telefonda dokunarak seç → "Taşı" → hedef; hedefler renk + desenle (uygun yeşil, uyarı kesik sarı, engel çizgili), üzerine gelince nedeni (aria-live) ve kimle yer değiştireceği; uyarıda onay penceresi; "Kilitle / Kilidi aç" (kilit simgesi, kalın kenar, ekran okuyucuya "Kilitli"); "Geri al (n)"; elle düzeltilmiş programda kalite özeti "en iyisi kanıtlandı" demez. Mutasyon: 24/24 (ilk turda 18; kapalı kural, takas konumu, aynı günde kaydırma, onaysız uyarı, geri alma sırası ve temel programın kilidi için test eklendi). Tarayıcıda denemede bulunan: blok hücresinde düğme içeriği ortaya kayıyordu (düzeltildi); elle düzeltilmiş programda "kanıtlandı" yazıyordu (düzeltildi). Denemedeki taşıma geri alındı. Ekran: docs/ekranlar/7.1/ (6 görüntü; geçici "gelemez" günü ve onu temel alan program API ile açılıp silindi, veritabanı başlangıçla aynı). Uçtan uca test yeni kodla yeniden geçti. Not: 0008 migration'ından önce üretilen programın veri özeti yok, "eski veri" uyarısı onda gösterilmez (bilinmiyor). |
| 7.2 | PDF ve Excel çıktı | Bitti (2026-10-24, ADR 0020). Alt parçalar aşağıda ("7.2 çıktı planı"). |

6.1-6.2 uçtan uca denemesi (örnek okulda gerçek üretim):
- Mini set: program 1 saniyeden kısa sürede hazır (en iyisi kanıtlandı); bütün kalite ölçüleri sıfır.
- Gerçekçi set (`ornek-okul --set gercekci`, 24 şube): 2 dk 1 sn; 59 pencere saati, 26 eksik boş gün,
  26 bölünmüş ders; sınıf boşluğu 0. Bekleme ekranı burada görüntülendi.
- Hata örneği: günlük ders sınırı 1 iken ön kontrol "Günlere sığmayan dersler" olarak, şubeye bağlantıyla.
- Görüntüler: `docs/ekranlar/6/`, `docs/ekranlar/6-bekleme/`. Taşma denetimi 22/22 temiz.
- Gözlem: gerçekçi sette 17 ders var, palet 14 renk; üç renk iki derste tekrar ediyor.
- Telefonda çizelge kendi kutusunda yatay kayıyor; gün gün görünüm 5.6'daki telefon kontrolüne.
- Testler: web 218, api 482, çözücü 149.
- Yük altında kararsız testler için Vitest işçileri çekirdeklerin yarısıyla sınırlandı.
| K | Kişiselleştirme katmanı (`docs/kisisellestirme-plani.md`, ADR 0016 kabul edildi) | Onaylandı, uygulanıyor |

Uygulama sırası (kullanıcı kararı; her alt adımın sonunda kullanıcıya sorulur):

| # | Alt adım | Durum |
|---|---|---|
| R | Ders paleti en az 20 renk; renkler tükenirse tekrar eden derslerin çipinde ayırt edici işaret | Bitti: 20 renk (ilk 14 yerinde; 6 yeni, CIELAB ΔE ile seçildi; en yakın çift 18,8); testler: her renk beyaz yazıyla ≥ 4.5:1, her çift ΔE ≥ 15; tekrar eden renkte çipin başında ◆ ▲ ● (eklenme sırasıyla, aria-hidden) |
| K1 | Kapsam temeli (öğretmen kapsamının ders ve şube kapsamıyla çakışmaması kodda zorlanır) | Bitti |
| D1 | Program sayfasındaki ön kontrol üretimdekiyle aynı (özel ayarlar dahil); hata varsa düğme pasif | Bitti: `GET /on-kontrol` worker'ın girdisi ve `cozucu.on_kontrol` ile; engeller ondan; test: özet temizken özel ayar hatası iki yerde aynı. K1 deneme özel ayarları geliştirme veritabanından silindi |
| D2 | Çizelge hücrelerinde dar alanda kısa ders adı ve kısaltılmış öğretmen adı | Bitti: `useDarAlan` adın doğal genişliğini ölçer (ResizeObserver), sığmazsa kısa biçim ("TDE", "Z. Demir"); tam ad `title` ve ekran okuyucuda. Ekran: docs/ekranlar/duzeltmeler/ |
| D3 | Sol menü masaüstünde yapışkan (sticky) | Bitti: menü listesi `position: sticky`, üst çubuğun altında; ekrandan uzunsa kendi içinde kayar; telefonda değişmedi |
| D4 | Programlar tablosu 800 px'te sığar; taşma denetimine 800 px | Bitti: oluşturma ve süre tek sütunda, uzun ad kırılır. Taşma denetimi 800 px'i de dener ve artık **kutu içi yana kaymayı** da yakalar (eski sürüm yalnızca sayfa taşmasına bakıyordu, bu hatayı göremezdi). Yeni denetim 800 px'te öğretmenler, dersler, şablon ve ders dağılımı tablolarında da kayma buldu; düzeltildi: tablo kutusu container query ile dar alanda sıkışır, tablo hücresindeki çip satır kırar, ders dağılımında 64rem altında şube listesi üste alınır. Bilerek kayan haftalık çizelge `data-kaydirilabilir` ile işaretli. Denetime hazır bir program ve çizelgesi de eklendi |
| D5 | Uygulamanın adı "Çizelge" | Bitti: ad tek yerde (`web/src/urun.ts`); üst çubuk, giriş/kayıt sayfası (altında "Okul Ders Programı Oluşturma Sistemi"), sekme başlığı, API başlığı, README ve CLAUDE.md |
| D6 | Program sayfası: hazır program öne, son başarısız deneme sade ve açılabilir | Bitti: en yeni hazır program önde; ondan sonraki başarısız deneme sade uyarı, nedeni `<details>` ile açılır; hiç hazır program yoksa büyük panel |
| D7 | Deneme verisi temizliği: betiklerin (taşma, ekran görüntüsü) açtığı deneme okulları silinir | Bitti: `python -m okulapi deneme-temizle` (geliştirme ortamı koruması; yalnızca bütün kullanıcıları `tasma-/ekran-/bos-…@ornek.test` olan okullar; örnek okul kalır); iki betik iş bitince kendiliğinden çağırır. Geliştirme veritabanından 11 deneme okulu silindi |
| K2 + 5.5 | Öğretmene özel boş gün ve müsaitlik çizelgesi: öğretmen detay sayfası | Bitti. K2a çözücü bitti: boş gün öğretmene özel, iki yönlü ceza yalnızca özel hedefte; hedef gün tek yerde (`yuk.bos_gun_hedefi`); kalite ölçüsü `fazla_bos_gun`. K2b bitti: `GET/PUT /ogretmenler/{id}/musaitlik` (toplu, ya hep ya hiç; cevapta yük ve ön kontrolle aynı aşım mesajı). K2c+K2d bitti: `/ogretmenler/:id` (kişisel ayarlar: "Okul varsayılanı" ve "özel" rozeti; müsaitlik çizelgesi: döngü, iyimser güncelleme, klavye, başlıkla ve sürükleyerek toplu işaretleme, ikon + desen + lejant, kısa animasyon, kapasite uyarısı; önceki/sonraki/seçim ile hızlı geçiş); öğretmen listesinde ad bağlantı; menüden "Öğretmen müsaitliği" kaldırıldı, eski adres ilk öğretmene yönlenir. Ekran: docs/ekranlar/k2/. K2e bitti: örnek okulda deneme (aşağıda). Hepsi geri alındı. |
| K3 | Günlere göre ders saati, öğle arası ve zil saatleri | Uygulanıyor. K3a çözücü bitti: `OkulAyari.gun_saatleri` ve `ogle_arasi_sonra`; kısa günün sonundaki hücreler temel kural `gun_uzunlugu` ile 0 (çelişkide "Cuma 4 saat"); kapasite, öğretmenin müsait saati, sınıf müsaitliği ve boş gün hedefi gün uzunluğuyla (tek kaynak `yuk.py`); kapasite mesajı "4 gün × 6 saat, Cuma 4 saat"; öğle arasının iki yanındaki saatler bitişik sayılmaz (bölünmüş ders), kalite ölçüsü de aynı. Mutasyon denetimi 10/10. K3b API bitti: migration `cekirdek_0006_okul_zaman` (`gun_saatleri int[]`, `ogle_arasi_sonra`, zil saatleri: `ilk_ders_baslangic`, ders/teneffüs/öğle arası süresi); tek gösterim (bütün günler aynıysa liste boş, en uzun gün `gunluk_ders_saati`) servisle ve dizi üzerinde CHECK'lerle (`= ANY`, `>= ALL`); bir günü kısaltmak ADR 0014 akışından geçer (kanca artık her günün yeni uzunluğunu alır: `okul_ayari_etkisi(oturum, gun_saatleri, uygula)`); müsaitlik girişi kısa günün dışını reddeder; çözücü girdisi gün uzunluklarını ve öğle arasını taşır. Mutasyon denetimi 8/8. K3c arayüz bitti: okul ayarlarında varsayılan tek "günde kaç ders saati" alanı, "Günlere göre farklı" işaretlenince gün kutuları; öğle arası seçimi ("n. dersten sonra", en uzun günün son dersinden önce); "Zil saatlerini göster" işaretlenince başlangıç ve süreler, canlı önizleme; bir gün kısalınca ADR 0014 penceresi. Haftalık çizelge ve müsaitlik çizelgesi: satır başlığında "1. saat" altında saat aralığı, öğle arası iki ders arasında ince ayraç (hücresiz satır), kısa günün sonundaki saatler çizgili "ders yok" alanı (müsaitlikte tıklanamaz; toplu işlem ve oklar atlar). Zil hesabı saf `okul/zaman.ts`. Mutasyon denetimi 6/6. K3d bitti: örnek okulda deneme (aşağıda), hepsi geri alındı. Ekran: docs/ekranlar/k3/. **Bitti** |
| K4 | Blok dersler | Uygulanıyor. K4a çözücü bitti: `cozucu/blok.py` tek kaynak (otomatik desen, okul önerisi uygulanamazsa düşer, ders ve ders + şube özel desen, kilit uyumu, eşleştirme); `blok_deseni` zorunlu kuralı (`bas[g,s,b]` değişkenleri; öğle arası ve gün uzunluğu değişken üretilmeyerek); ön kontrol altı mesaj (toplam, N, gün sayısı, öğle arası/gün uzunluğu, müsaitlik, kilit); çelişki grubu "9-A Matematik'in 2+2+1 dağılımı"; doğrulayıcı blokları bağımsız denetler. Mutasyon denetimi 14/14. K4b ölçüm bitti (docs/olcumler.md "Blok dersler"): gerçekçi sette 120 sn ceza 432 → 88; büyük sette 1530 → 834, ama ilk çözüm 15-29 sn → 44-72 sn ve 120 sn'de sınıf boşluğu iki tohumda sıfırlanmıyor. Öneri (iki aşamalı çözüm) kullanıcıya soruldu. ADR 0017. K4c API bitti: `blok_deseni` kuralı kurallar listesinde (okul: `otomatik`, `varsayilanlar`; özel: `desen`, tek gösterime getirilir); parametre tipi sayıdan genişledi (`bool | int | list[int] | dict`); `GET /dagilim-sekilleri` (her atamanın şekli, kaynağı ders / ders_sube / okul / yok, düşen öneri ve nedeni, açık şeklin sorunları). Mutasyon denetimi 7/7. K4d arayüz bitti: Dersler listesinde "Dağılım şekli" sütunu (okul önerisi / blok yok / hazır bölünüşler / "Başka bir şekil…" ile elle "2+2+1"; "özel" rozeti; uygulanamayan şeklin sorunu ve düşen öneri nedeniyle); Okul ayarlarında "Dağılım şekli (blok dersler)": "Dersleri bloklara böl" ve 1-6 saat için önerilen şekil tablosu (yalnızca öneriden farklı olanlar kaydedilir); haftalık çizelgede bir dersin art arda saatleri tek hücre (`rowSpan`, "2 saat", ekran okuyucuya "1.-2. saat, 2 saat art arda"), öğle arasını geçmez. Dar tabloda düzenle/sil yalnızca ikon (taşma denetimi 800 px). Mutasyon denetimi 8/8. K4e bitti: örnek okulda deneme (aşağıda), hepsi geri alındı. Ekran: docs/ekranlar/k4/. **Bitti** |
| P1 | İki aşamalı çözüm ve "süre yetmedi" (gece çalışması, kullanıcı isteği 2026-10-24) | **Bitti.** Çözücü: önce yalnızca zorunlu kısıtlarla ilk programda durarak, sonra o program tam ipucuyla esnek kurallar (`CpSatCozucu(iki_asamali=True)`, pay 1); aşama 1 çözümsüzlüğü kanıtlarsa doğrudan çelişki analizi; aşama 2 bulamazsa aşama 1'in programı; temel program aşama 1'e ipucu, kilitler iki aşamada zorunlu. Ölçüm (docs/olcumler.md "İki aşamalı çözüm", ADR 0018): ilk program daha erken (büyük bloklu 23-29 → 9-25 sn, bloksuz 9-12 → 4-5 sn), 120 sn kalitesi bloklu setlerde aynı, bloksuz setlerde iyi; varsayılan süre 120 sn kalır. Bloksuz büyük setin "kötüleşmesi" ölçüm ortamındandı (6 commit sakin makinede yeniden ölçüldü, hepsi 0 sınıf boşluğu). Arayüz: `bilinmiyor` sonucunda "Bu süre okulunuz için yetmedi" ve tek tıkla bir sonraki uzun süreyle yeniden deneme (aynı ad ve temel program); 30+ şubede "Hızlı"nın yanında uyarı. Ekran: docs/ekranlar/p1/. Sırada: K5 |
| K5 | Şube grupları ve istisnalar | Uygulanıyor. K5a bitti: `sube_grubu` (çekirdek, migration cekirdek_0007; şube satırında grup, seviyesi aynı olmalı; silinince şubeler grupsuz), şablon seviyeye ya da gruba (`seviye_sablonu.sube_grubu_id`, var olan satırlar seviyenin şablonu olarak korunur; migration testli), şube istisnaları `almaz` / `ek` (`sube_ders_istisnasi`; istisna dağılımı da değiştirir, şablon yeniden uygulanınca "almaz" geri gelmez, raporda atlanan / ek / başka şablonlu şubeler), kural kapsamında şube grubu (N, dağılım şekli; öncelik ders + şube > ders + grup > ders > şube > grup testli). Arayüz: Sınıflar'da grup sütunu ve "Şube grupları" kartı (ekle, ad değiştir, sil); Seviye şablonu'nda "Şablon" seçimi (seviye ya da grup) ve kime ait olduğu; Ders dağılımı şube görünümünde "bu şube bu dersi hiç almasın" (kaldırma penceresi), "ek ders" (ekleme formu), "Bu şubeye özel" listesi ve "Geri al". Mutasyon: API 15/15, çözücü 1/1, arayüz 11/11. Kararlar docs/kisisellestirme-plani.md bölüm 6 "K5'te netleşen ayrıntılar". K5b bitti: örnek okulda deneme (aşağıda), hepsi geri alındı. Ekran: docs/ekranlar/k5/. **Bitti** |
| 5.6 | Kullanıcılar, özel ayar ekleme, telefon kontrolü (çizelgede gün gün görünüm), Playwright uçtan uca | Uygulanıyor. 5.6a bitti: `/kullanicilar` (müdür: yardımcı ekle, parolayı yeniden belirle, müdür yap / yardımcı yap, sil; yardımcı listeyi düğmesiz görür). Son müdür kuralı önceden: tek müdürün "Yardımcı yap" ve "Sil" düğmeleri pasif, altında nedeni ("Okulda tek müdür var: …"); yarışta sunucunun 409 mesajı bildirimde. Kendi parolası Hesabım'dan; kendini silen müdür giriş sayfasına döner. 5.6b bitti: Okul ayarları > Özel ayarlar'da "Özel ayar ekle": kural (yalnızca kapsamı olanlar) → "Nerede geçerli" (kuralın `kapsamlar` ve yeni `zorunlu_eksenler` alanından süzülür: dağılım şekli ders ister, öğretmen kuralları yalnızca öğretmen; okulda grubu yoksa grup seçenekleri gizli) → kayıt → değer (sayı, boş gün 0/1/2, dağılım şekli "2+2+1"/"blok yok"). Kaydetmeden önce `GET /kurallar/{tur}/ozel/etki` hangi özel ayarları ezdiğini ve hangilerinin altında kaldığını söyler; puan ve örtüşme çözücünün `kapsam.py`'sinden (`ortusur`, testli), arayüz yalnızca cümle kurar. Öğretmen sayfası ve ders listesi kendi alanlarını kullanmaya devam ediyor. Bulunan hata: özetteki "Kaldır" gruba özel ayarın `sube_grubu_id`'sini göndermiyordu (ders + grup ayarı yerine ders ayarını silebilirdi); düzeltildi, testli. 5.6c bitti (telefon): müsaitlik çizelgesinde hücrelerde `touch-action: manipulation` (parmakla sayfa kayar); dokunuş tek hücreyi "click"te değiştirir (kaydırma click üretmediği için hücre değişmez); sürükleyerek seçim yalnızca "Toplu seç" modunda (düğme `aria-pressed`, açıkken çizelge kesik çerçeveli, "Bu çizelgede sayfa kaymaz" bilgisi, hücrelerde `touch-action: none`); fareyle sürükleme moddan bağımsız, düğme yalnızca dokunmatik ekranda görünür. Haftalık çizelge 40rem altında gün gün: gün düğmeleri (Pzt…Cum, bugün seçili gelir), o günün saatleri alt alta, blok tek satır ("1.-2. saat" ve zil aralığı), boş saat "Boş", öğle arası ayraç; seçim `useMedya` (useSyncExternalStore + matchMedia) ile, iki görünüm birden DOM'a konmaz. Ortak tablo dar kutuda (30rem) karta dönüşür: hücreler alt alta, solunda sütun adı (`data-etiket`), roller açıkça yazılı; ders dağılımında öğretmen sütunu artık kaydırmadan görünüyor (3. adımdan ertelenen not). Gün kısaltmaları tek yerde (`GUN_KISA_ADLARI`): müsaitlik çizelgesindeki "Paz" (Pazartesi; Pazar'la karışır) "Pzt" oldu. Taşma denetimine /kullanicilar eklendi, 51/51 temiz. **Karar:** telefonda menü açılır menü olarak kaldı (plandaki alt çubuk yapılmadı): bütün sayfalar iki dokunuşla erişilebilir, düğmeler 44 px; alt çubuk gün gün çizelgenin dikey alanını daraltırdı. 5.6d bitti: Playwright uçtan uca (`web/e2e/akis.spec.ts`, `npm run e2e`; `@playwright/test`, bilgisayardaki Edge, çalışan docker compose + Vite'a karşı). Örnek okulla giriş → adına göre ilk öğretmene boş gün hedefi 2 ve başlangıçta müsait olan ilk saate "gelemez" (telefonda `tap`) → "Hızlı" program → çizelgede öğretmen görünümü: o saat "Boş" (masaüstünde tablo hücresi, telefonda gün gün liste, tablo yok). Masaüstü ve telefon (Pixel 7: dokunmatik, 412 px) sırayla (aynı okulda aynı anda tek üretim). Geri alma test kırılsa da `finally`de: müsaitlik ve özel ayar API'yle, üretilen program veritabanından (silme ucu yok); test sonunda müsaitlik, boş gün ayarı ve program listesi başlangıçla aynı mı diye denetlenir. Vitest yalnızca `src/**/*.test.*`. Plan 5'teki "mini setin arayüzden girilmesi" akışı yapılmadı: örnek okul zaten kurulu, kullanıcının istediği akış (müsaitlik, boş gün, üretim, çizelge) kapsandı. Ekran: docs/ekranlar/5.6/ (5 görüntü). Ekran görüntüsü sırasında yakalanan: docker'daki API imajı eskiydi (kod imaja kopyalanıyor, `--build` gerekir); yeni arayüz `zorunlu_eksenler` alanını bulamayınca "Özel ayar ekle" sayfayı boşaltıyordu. İmaj yenilendi, README'ye not düşüldü. Uçtan uca testin ilk sürümü yeni program hazır olmadan sayfadaki eski programın bağlantısına tıklayabiliyordu (yavaş üretimde kırıldı); artık üretim isteğinin cevabındaki kimliği bekliyor. **Bitti** |
| K6 | İkincil kurallar (f, g, h, i) | Uygulanıyor; alt parçalar aşağıdaki "K6 planı"nda |

K1'den notlar (kapsam temeli; tasarım: docs/kisisellestirme-plani.md, ADR 0016):
- **Çözücü:** `cozucu/kapsam.py` (`Kapsam`, `cozumle`); her tür için tek kural örneği ve özel
  ayarları; N derse, şubeye (şube grubuna, K5'te veriyle) özel; M öğretmene özel. Yük, ön kontrol,
  doğrulama, kalite, çelişki açıklaması ve boş gün kuralı değeri varlık başına okur.
- **Öğretmen kapsamı ile ders/şube kapsamı aynı kuralda çakışamaz:** `Kapsam` oluşturulurken,
  `kaydet` (iki aileyi bildiren kural sınıfı), API (422) ve veritabanı CHECK'i reddeder. Testli.
- **API:** migration `ders_programi_0006_kisit_kapsami` (kapsam sütunları, bileşik FK + CASCADE,
  CHECK, `UNIQUE NULLS NOT DISTINCT`); `GET /kurallar` → `kapsamlar`, `ozel_ayarlar`;
  `PUT/DELETE /kurallar/{tur}/ozel`. Başka okulun öğretmenine özel ayar reddedilir; öğretmen,
  ders, şube silinince özel ayarı da silinir.
- **Arayüz:** okul ayarlarında "Özel ayarlar" özeti (kaldırma ile). Özel ayar **ekleme** ekranları
  ilgili yerlerde gelecek: öğretmene özel K2'de (öğretmen detay sayfası), derse özel K4'te.
- Ekran görüntüleri: docs/ekranlar/k1/. Testler: çözücü 189, API 510, web 224. Mutasyon denemesi
  7/7 (biri ilk denemede kaçtı: boş gün kuralının öğretmene özel M'yi okuması; ceza toplamını
  denetleyen test eklendi).

K2 + 5.5'ten notlar:
- **Boş gün denemesi (örnek okul, mini set, 30 sn):** önce bütün öğretmenler okul varsayılanında
  (1 boş gün): hepsi 4 gün geliyor, ceza 0. Mehmet Kaya'ya 0 (her gün), Ayşe Yılmaz'a 2 boş gün:
  Mehmet 4 → 5 gün, Ayşe 4 → 3 gün; ceza yine 0, öteki öğretmenler 4 gün. Deneme ayarları ve iki
  deneme programı silindi.
- **Denemenin bulduğu hata:** ilk denemede "0 boş gün" pazartesi bütün gün gelemeyen Ayşe'ye
  verilmişti; hedef 5 gün kalıyor, kaçınılmaz 1 günlük ceza yazılıyordu. Hedef artık
  öğretmenin gelebildiği gün sayısıyla da sınırlı (test eklendi).
- Müsaitlik toplu API'si ya hep ya hiç; arayüz iyimser günceller, hata olursa geri alır.
- Sürükleme dokunmatikte de çalışsın diye işaretçi yakalaması (pointer capture) bırakılır;
  hücrelerde `touch-action: none` (çizelgenin üstünde parmakla sayfa kaydırılamaz; 5.6'da
  telefon kontrolünde yeniden bakılacak).
- **5.6 için karar (kullanıcı, K2 onayı):** dokunmatik ekranda çizelgenin üstünde sayfa kaydırma
  engellenmeyecek (`touch-action: none` kalkar). Dokunmak tek hücreyi değiştirir; toplu seçim
  (sürükleme) yalnızca açıkça açılan bir **"Toplu seç"** modunda yapılır (mod açıkken kaydırma o
  çizelgede durur, mod göstergesi ve kapatma düğmesi görünür). Masaüstünde fareyle sürükleme
  olduğu gibi kalır (`pointerType === "mouse"`).

K3'ten notlar (günlere göre ders saati, öğle arası, zil saatleri):
- **Deneme (örnek okul, mini set, 5 gün × 6 saat, 30 sn):** cuma 5 saate indirildi. Önizleme
  tek etkiyi söyledi ("1 müsaitlik kaydı ... silinecek (1 öğretmen: Fatma Şahin; ör. Fatma Şahin,
  Cuma 6. saat)"); onaysız kayıt 409; onaylı kayıtta kayıt aynı işlemde silindi. Haftalık
  kapasite 30 → 29 (şubeler 24/29, 24/29, 23/29), ön kontrol temiz. Üretilen programda üç
  şube de cumaya tam 5 ders aldı, en geç ders cuma 5. saat; ceza 0 (en iyisi kanıtlandı).
- **Geri alma:** okul ayarı eski haline (her gün 6 saat, öğle arası ve zil yok); silinen
  müsaitlik kaydı önceden alınan yedekten geri yüklendi (15 kayıt yedekle birebir aynı);
  deneme programı silindi.
- Ekran görüntüleri için `ekran-goruntusu.mjs k3` hiçbir şeyi kaydetmez (kısaltma penceresinde
  "Vazgeç"); okul önceden deneme ayarına getirilir, sonra geri alınır.
- Müsaitlik çizelgesinde olmayan saat çizgili değil sade ve soluk ("—"): çizgili desen
  "gelemez"in deseniyle karışıyordu (ekran görüntüsünde görüldü).
- Zil saatleri yalnızca arayüzde hesaplanır (`okul/zaman.ts`). **Karar (kullanıcı, K3 onayı):**
  PDF çıktısı adımında (7) hesap tek kaynağa taşınacak (API'de hesaplanıp arayüze ve PDF'e
  verilecek; arayüzdeki önizleme de onu kullanacak).

K4'ten notlar (blok dersler):
- **Deneme (örnek okul, mini set, 5 gün × 6 saat, 30 sn):** okul önerisiyle 9-A'da her ders
  önerilen şeklinde (Matematik 2+2+2: salı 3-4, çarşamba 1-2, cuma 1-2; TDE 2+2+1; İngilizce 2+2;
  Fizik, Kimya, Tarih 2+1), ceza 0 (en iyisi kanıtlandı). Derse özel TDE 2+1+1+1 ve Matematik
  "blok yok" ile ikinci program: TDE 2+1+1+1, Matematik bloksuz (2+2+1+1), ceza 0. Ön kontrol:
  TDE 3+3 için "haftada 5 saat, ama dağılım şekli 3+3 (6 saat)", 3+2 için "3 saatlik blok
  istiyor, ama ... günde en fazla 2 saat" (üç şube için ayrı ayrı).
- **Geri alma:** `kisit` tablosu ve program listesi önceden yedeklendi; deneme özel ayarları
  silindi, iki deneme programı silindi; ikisi de yedekle birebir aynı.
- Çizelgede blok hücresi `rowSpan`; bir satırın bütün hücreleri birleşince satır çöküyordu
  (ekran görüntüsünde görüldü), satır başlığına sabit yükseklik verildi.
- Ders listesi 800 px'te taşıyordu (yeni sütun); dar tablo kutusunda düzenle/sil yalnızca ikon.
- **Açık soru (kullanıcıya):** büyük sette ilk çözüm 44-72 sn (docs/olcumler.md "Blok
  dersler"); öneri iki aşamalı çözüm.

K5'ten notlar (şube grupları ve istisnalar):
- **Deneme (örnek okul, 5 gün × 6 saat):** "9 Fen" grubu (9-A), grubun şablonu 9. sınıflarınki +
  Coğrafya 2; gruba özel Matematik günlük sınırı 3 ve dağılım şekli 3+3. Grubun şablonu uygulandı
  (9-A'ya Coğrafya eklendi). 9. sınıfların şablonuna Coğrafya 2 eklenip uygulandı (yalnızca 9-B'ye;
  rapor 9-A'yı "kendi şablonunu kullanıyor" diye söyledi). Ders dağılımında 9-B'nin Coğrafya'sı
  "bu şube bu dersi hiç almasın" ile kaldırıldı; şablon yeniden uygulanınca Coğrafya 9-B'ye geri
  gelmedi, rapor "Şubenin almadığı 1 ders eklenmedi (istisna): 9-B Coğrafya" dedi. "Hızlı" ile üretilen
  programda 9-A Matematik 3+3, 9-B ve 10-A 2+2+2; en iyisi kanıtlandı, ceza 0.
- **Geri alma:** veritabanı denemeden önce `pg_dump` ile yedeklendi; akış bütün değişiklikleri tersine
  aldı ve başlangıçla karşılaştırdı; deneme programı silindi; okul, şube, ders, öğretmen, şablon,
  atama, müsaitlik, kural, program ve yerleşim tabloları yedekle birebir aynı (grup ve istisna yok).
- Grup kartında tablo ile ekleme formu yapışıktı (ekran görüntüsünde görüldü), araya boşluk kondu.

### Sonraya: tasarım rötuşu

Şimdi uygulanmayacak (kullanıcı notu, K1 sonrası). Zemin ve kartlar çok açık olduğu için arayüz sade
görünüyor. Sona doğru denenecekler:
- koyu ve sıcak tonda yan menü;
- sayfa başlıklarında kiremitten turuncuya hafif degrade bant;
- zeminin bir ton koyulaştırılması;
- panodaki sayı kartlarına farklı yumuşak renk tonları.

Uygulamadan önce iki seçenek ekran görüntüsüyle gösterilecek.

Sıra değişikliği (kullanıcı kararı): sistemin ekranda uçtan uca kullanılabilmesi için 5.5 ve 5.6
ertelendi, önce yapım sırası 6'nın ilk iki alt adımı yapılır. Örnek okulda müsaitlik verisi var.

5.1'den notlar:
- **Backend:**
  - doğrulama hataları Türkçe ve tek biçimli: `{"detail", "alanlar": {yol: mesaj}}`;
  - OpenAPI şemasındaki 422 tanımı da buna uyduruldu;
  - pydantic'in "a or b" seçenek metnindeki İngilizce "or" testte yakalandı, "ya da" yapıldı;
  - `/api/saglik` tipli yanıt modeli aldı; veritabanı yoksa 503 + `detail`.
- **web/:**
  - Vite 8, React 19, TypeScript 5.9;
  - TypeScript 6, openapi-typescript'in desteklediği aralıkta olmadığı için 5.9'a sabitlendi;
  - çalışma zamanı bağımlılıkları: react, react-dom, react-router, @tanstack/react-query,
    openapi-fetch.
- **Tasarım temeli:**
  - `src/stil/belirtecler.css` (renk, boşluk, yazı, köşe); `temel.css` (odak halkası
    `:focus-visible`, azaltılmış hareket);
  - ortak bileşenler: `Dugme`, `Alan`/`MetinAlani`/`SecimAlani`, `Tablo`, `Bildirim`
    (Context + iki canlı bölge), `OnayPenceresi` (doğal `<dialog>`);
  - vitrin sayfası `/tasarim`.
- **Kontrast testi:** belirteç dosyasını okuyup 16 metin çiftinin 4.5:1, 3 sınır çiftinin 3:1
  olduğunu hesaplar.
- **API tipleri:** `scripts/openapi_yaz.py` → `web/openapi.json` → `npm run api:tipler` →
  `src/api/sema.d.ts`. İki tazelik testi var: pytest (json = API) ve vitest (tipler = json).
- **Çerçeve:** "İçeriğe geç" bağlantısı, `aria-current`, dar ekranda menü düğmesi
  (`aria-expanded`). Plandaki "telefonda alt menü" yerine şimdilik açılır menü; 5.6'da telefon
  kontrolünde yeniden bakılacak.
- **docker-compose `web` servisi:**
  - node:22-alpine, kendi `node_modules` birimi, Windows için dosya izleme yoklaması;
  - ilk açılışta konteynerin içinden npm'e ağ zaman aşımı oldu, yeniden başlatınca geçti.
- **Ekran görüntüleri:** `web/scripts/ekran-goruntusu.mjs` (playwright-core + bilgisayardaki
  Edge), `docs/ekranlar/5.1/`.
- **Testler:** web 52 (tasarım ve kontrast, bileşenler, hata çözümü, uygulama ve çerçeve, tip
  tazeliği); api 406.

5.2'den notlar:
- **Oturum durumu:** global depo yok; giriş yapan kullanıcı `/api/ben` sorgusunun önbelleğinde.
  `null` = giriş yok. Giriş, kayıt ve çıkış önbelleği elle günceller (`setQueryData`).
- **Korumalı alan (`KorumaliAlan`):** girişsiz kullanıcıyı gelinen adresle birlikte giriş
  sayfasına gönderir; girişten sonra o adrese dönülür.
- **Oturum süresi dolunca:** herhangi bir sorgu ya da değişiklik 401 alırsa sorgu istemcisinin
  hata dinleyicisi kullanıcıyı `null` yapar. Giriş sayfası "Oturumunuzun süresi doldu"
  mesajını gösterir.
- **Formlar:** `useFormDegerleri` (kontrollü form kancası), `sunucuHatalari` (sunucu hatasını
  alanlara dağıtır), `useIlkHatayaOdaklan` (gönderimden sonra ilk hatalı alana odak),
  `FormHatasi` (genel hata).
  - Alan listesi olmayan bilinen sunucu hataları ilgili alana bağlanır: kayıtta 409 → e-posta,
    "Parola..." → parola; hesabımda "Mevcut parola hatalı" → mevcut parola.
- **Ekranlar:** giriş, kayıt (okul + müdür hesabı, yazarken parola uzunluğu göstergesi), hesabım
  (bilgiler + parola değiştirme); üst çubukta okul, kullanıcı ve rol, Çıkış.
- **Çıkış:** sunucuya ulaşılamasa da kullanıcı çıkmış sayılır (önbellek temizlenir).
- **Ekran görüntüsünde yakalanan düzen hatası:** telefonda gizli menünün ızgara satırı boş alanı
  kaplıyordu (üç satıra iki satırlık yükseklik tanımı). jsdom testleri düzeni görmez.
  Düzeltildi.
- **Ekran görüntüsü betiği:**
  - akış kipi eklendi: tek tarayıcı oturumunda giriş → kayıt → hesabım → çıkış → telefon;
  - liste kipi artık önce geçici bir okul kaydediyor (sayfalar giriş istiyor);
  - her çalıştırma geliştirme veritabanına bir okul ekler.
- **Mutasyon denemesi:** sekiz bozmanın hepsi yakalandı:
  - korumalı alan yönlendirmez;
  - 401'de oturum kapanmaz;
  - girişten sonra hep ana sayfa;
  - 409 alana bağlanmaz;
  - odak yok;
  - istemci denetimi yok;
  - form temizlenmez;
  - çıkış hatada kalır.
- **Testler:** web 67 (kimlik 18).

5.3'ten notlar:
- **API davranışı değişti (ADR 0014):** çekirdekten modüle iki isteğe bağlı kanca.
  - Gün ya da ders saati azaltılırsa `PATCH /api/okul` etkileri onaylanmadan 409 + `etkiler`
    döner; `etkileri_onayla: true` ile aralık dışındaki müsaitlik kayıtları aynı işlemde silinir.
    Programlar değişmez, yeniden üretilmeleri gerektiği söylenir. `POST /api/okul/ayar-etkisi`
    önizlemedir.
  - Kullanımdaki öğretmen, sınıf ya da ders silinemeyince 409 mesajı nerede kullanıldığını ve ne
    yapılacağını söyler ("Şule Kaya silinemez: 2 derste öğretmen olarak seçili (9-A Matematik,
    9-B Matematik). Önce Ders dağılımı sayfasında..."). Kancası olmayan modülde genel mesaj kalır.
- **Kurallar:** `GET/PUT/DELETE /api/ders-programi/kurallar[/{tur}]`. Önem seviyelerinin sayısal
  karşılıkları `kurallar.py`'de tek yerde (`ONEM_KARSILIKLARI`); "Önemli" çözücünün varsayılanına
  eşit (testle denetlenir). Seviyelerden birine denk gelmeyen ağırlık "özel" olarak gösterilir.
- **Ortak liste bileşeni (`ListeSayfasi`):** öğretmen, sınıf ve ders sayfaları yalnızca alan
  tanımı ve metin verir. Türkçe sıralama (`Intl.Collator("tr")`), arama (`toLocaleLowerCase("tr")`),
  boş durum (açıklama + ilk kaydı ekleme düğmesi), satır içi düzenleme (Enter/Escape), onaylı
  silme. Silinemeyen kayıtta API'nin mesajı kalıcı hata bildirimi olur.
- **Okul ayarları:** okul bilgileri (azaltırken önceden uyarı, kaydetmeden önce önizleme ve etki
  listeli onay penceresi), kurallar (N, M, boş gün hedefi), "Gelişmiş: kuralların önemi"
  (`<details>`, kural başına radyo grubu, varsayılana dönüş).
- **Çıkışta bildirimler temizlenir** (5.2'nin 7 numaralı görüntüsündeki sorun).
- **Erişilebilir ad çakışması:** satır içi düzenleme kutusu ekleme formundaki alanla aynı adı
  taşıyordu; testte yakalandı, "(düzenleme)" eklendi.
- **Diyagram denetimi** `KurallarServisi`'nin diyagramda yanlış pakette olduğunu yakaladı.
- **Ertelenen:** telefonda tablo yerine kart düzeni. Tablo 375 px'te sığıyor (görüntü 11); uzun
  sütunlu listelerde 5.6'da yeniden bakılacak.
- **Mutasyon denemesi:** on iki bozmanın hepsi yakalandı:
  - api: onaysız azaltma uygulanır; onayda silme atlanır; silmede modüle sorulmaz; "Önemli"
    karşılığı kayar;
  - web: çıkışta bildirim kalır; JS'nin varsayılan sıralaması; Türkçe olmayan küçük harf; önizleme
    yok; uyarı yok; 409 mesajı gösterilmez; boş durum yok; değişmeyen önem seviyeleri de gönderilir.
- **Testler:** web 101 (metin 12, listeler 12, okul ayarları 9); api 432; çözücü 137.

5.4'ten notlar:
- **Yük hesabının tek kaynağı (ADR 0015):**
  - `cozucu/yuk.py` (`YukHesabi`) öğretmen ve sınıf yükünü, kapasiteyi ve aşım mesajını üretir;
  - ön kontrolün kapasite kontrolleri artık bunu kullanır;
  - API'de `GET /api/ders-programi/dagilim-ozeti`; arayüz hiç hesap yapmaz;
  - aynılığı `test_yuk.py` (çözücü) ve `test_dagilim.py` (gerçek veritabanı, ön kontrolle birebir
    mesaj karşılaştırması) denetler.
  - Ölçüm: hesap gerçekçi sette 0,3 ms, büyük sette 0,5 ms.
- **Toplu öğretmen atama:** `POST /api/ders-programi/atamalar/toplu-ogretmen`. Tek işlemdir:
  atamalardan biri okulda yoksa hiçbiri değişmez (404); başka okulun öğretmeni 422.
- **Ders dağılımı sayfası, üç sekme:**
  - şubelere göre: şube listesinde toplam saat ve öğretmensiz sayısı; tabloda saat, öğretmen,
    kaldırma, ders ekleme;
  - öğretmenlere göre: yük çubuğu; aşanlar en üstte, ön kontrolün mesajıyla; dersinden şubesine
    gidilir;
  - derslere göre: işaretle, öğretmen seç, tek istekle ver; "Öğretmeni seçilmemişleri işaretle".
  - Seçili sekme, şube ve ders adres çubuğunda (`?gorunum=&sinif=&ders=`), sayfanın durumudur.
- **Erken uyarılar:**
  - sayfanın üstünde öğretmensiz ders sayısı, kapasitesi aşılan öğretmen ve şube sayısı
    (`aria-live`);
  - bir seçim öğretmenin kapasitesini aştırırsa sunucunun mesajı hemen uyarı bildirimi olarak
    gelir;
  - öğretmen seçicide her öğretmenin yükü ("18 / 24 saat · kapasite aşıldı") yazar.
- **Öğretmen seçici:**
  - doğal `<select>`; branşı uyanlar `<optgroup>` ile üstte, diğerleri altta, kimse gizlenmez;
  - plandaki "aranabilir liste" yerine doğal seçici kullanıldı: harf yazınca atlıyor, telefonda
    sistemin seçicisi açılıyor;
  - branş eşleşmesi: kelime başında ve en az 4 harf; kısa ad birebir. Test "MA"nın her şeye
    uyduğunu yakaladı, kural sıkılaştırıldı. Bilinen sınır: 3 harfli branş ("Din") eşleşmez,
    yalnızca sıralamayı etkiler.
- **Seviye şablonu:**
  - seviye seçimi, satırda saat düzenleme, toplam ve kapasite;
  - uygulama raporu: eklenen ve zaten olan dersler, saati farklı olanlar tablosu ve "Şablondaki
    saati kullan"; rapor açılınca odak başlığına gider.
- **Ekran görüntüsünde ve tarayıcı ölçümünde yakalanan eski düzen hataları** (jsdom düzeni
  görmez):
  1. Çerçeve ızgarası `1fr` kullanıyordu: alt sınırı içerik olduğu için geniş bir tablo
     telefonda öğretmen, ders ve şablon sayfalarını yana kaydırıyordu (5.3'ün 11 numaralı telefon
     görüntüsü de 495 px'ti). `minmax(0, 1fr)` yapıldı.
  2. `Tablo`daki görünmez sütun başlığı (`position: absolute`) kaydırma kutusundan kaçıp sayfayı
     genişletiyordu. Kutuya `position: relative` verildi.
  - Bunun için `web/scripts/tasma-denetimi.mjs` eklendi: bütün sayfaları masaüstü ve telefonda
    açar, taşan varsa çıkış kodu 1. Geri alınan düzeltmeyle denendi: 4 taşma buldu.
- **Ertelenen (5.6):** telefonda şube tablosu yatay kayıyor, öğretmen sütunu kaydırmadan
  görünmüyor. Kart düzeni orada yeniden değerlendirilecek.
- **Ana sayfa kontrol listesi (5.6)** öğretmensiz ders sayısını aynı özetten (`ogretmensiz_atama`)
  alacak.
- **Mutasyon denemesi:** 19 bozmanın 19'u yakalandı (ilk turda 18; "şubeye git şubeyi seçmez"
  kaçtı, çünkü varsayılan şube de 9-A'ydı; test başka şube seçiliyken başlayacak şekilde
  düzeltildi).
  - web: branş gruplaması, seçicide aşım, özetin tazelenmesi, aşım uyarısı, Enter'da çift kayıt,
    toplu atamada işaretsizler, öğretmensiz sayısı, aşanın üstte olması, şubeye git, rapordaki
    farklı saatler, rapora odak, yarı dolu kutu, sekmede ok tuşu;
  - çözücü: "tercih etmez"in düşülmesi, günlük sınır, ön kontrolün yük hesabını kullanması;
  - api: özetin kendi mesajı, toplu atamanın yarıda kalması, öğretmenin okul denetimi.
- **Testler:** web 144 (branş 20, ders dağılımı 17, şablon 6); api 447; çözücü 149.

### Tasarım yenileme (5.4 ile 5.5 arası, kullanıcı isteği 2026-10-16)

Arayüz işlevsel ama fazla sade; daha modern, canlı ve akıcı olacak. Kullanıcının kullanım limiti
azaldığı için **her parça bitince testler çalışır, geçerse commit edilir ve bu tablo güncellenir**.
Yarıda kalırsa sonraki oturum buradan devam eder.

| # | Parça | Durum |
|---|---|---|
| 0 | Örnek okul komutu (`python -m okulapi ornek-okul --evet`, README) | Bitti |
| 1 | İki tasarım yönü, beşer masaüstü ekran görüntüsü (giriş, ana sayfa, öğretmenler, okul ayarları, ders dağılımı); **kullanıcının seçimi beklenir** | Bitti. **Seçim: A (sıcak ve yumuşak)**, kullanıcı 2026-10-23 |
| 2 | (1 ile birlikte, iki yönde ortak) animasyonlar, ikonlar, kartlar, yazı tipi | Bitti (2a, 2b) |
| 3 | A'nın tek tasarım olarak uygulanması ve zenginleştirilmesi (alt parçalar aşağıda); 5.5'ten önce kullanıcıya sorulur | Bitti (2026-10-23), kullanıcı onayladı |

Parça 3'ün alt parçaları (kullanıcı isteği 2026-10-23: "yalnızca renk değişikliği gibi durmasın"):

| # | Alt parça | Durum |
|---|---|---|
| 3a | A'yı belirtecler.css'e taşı; B temasını, Inter'i, `?tema` ve ara yapıyı kaldır | Bitti. Ayrıca kararsız testler: bekleme süreleri uzatıldı (`asyncUtilTimeout` 3 sn, `testTimeout` 15 sn) |
| 3b | İkonlu sayfa başlık alanı; kartlarda üzerine gelince yükselme ve gölge | Bitti (`SayfaBasligi`; `<header>` değil `<div>`: test ikinci bir "banner" yakaladı) |
| 3c | Ders renkleri: otomatik atanır, değiştirilebilir, API'de saklanır; çip biçiminde (liste, dağılım, şablon, ileride çizelge); metin kontrastı testle | Bitti (aşağıda) |
| 3d | Öğretmenler için baş harfli renkli rozetler (listeler, seçiciler) | Bitti: `OgretmenRozeti`; renk kimlikten kararlı (8 belirteç, kontrast testli); baş harfler CSS `attr()` ile çizilir, metne karışmaz; seçicide seçili öğretmenin rozeti solda |
| 3e | Ana sayfa panosu: karşılama bandı, kurulum ilerleme halkası (kontrol listesiyle aynı veriden), sayı kartları | Bitti: `kurulumDurumu` (saf, testli) halkayı ve kontrol listesini besler; dağılım adımı sunucu özetinden; sayı kartları (öğretmen, şube, ders, haftalık saat); 5.6'daki kontrol listesi böylece öne alındı |
| 3f | Boş durumlar için özgün SVG illüstrasyonlar (tema renkleriyle) | Bitti: `Illustrasyon` (öğretmen, şube, ders, takvim); satır içi SVG, renkler CSS sınıflarından; liste boş durumları, şube, dağılım ve şablon ön koşulları; test sabit renk olmadığını denetler |
| 3g | Masaüstü ve telefon ekran görüntüleri, taşma denetimi, bütün testler; özet ve 5.5'ten önce soru | Bitti: `docs/ekranlar/tasarim-a/` (12 masaüstü, 4 telefon); taşma 20/20 temiz; web 185, api 481, çözücü 149 |

Hepsi tasarım belirteçleri üzerinden yapılır; animasyonlar hareketi azaltma ayarına uyar.

3c notları (ders renkleri):
- **API:**
  - palet `cekirdek/ders_renkleri.py`'de tek yerde: 14 renk, her biri çipteki beyaz yazıyla en az
    4.92:1;
  - `ders.renk` sütunu (migration cekirdek_0005; var olan derslere okul başına ada göre sırayla,
    CHECK `#rrggbb`);
  - servis yeni derse okulda en az kullanılan rengi verir; paletin dışı 422;
  - `GET /api/ders-renkleri` (oturum ister).
- **Arayüz:**
  - `DersCipi` (zemin `--ders-rengi`, yazı `--renk-cip-metin`) ders listesinde, ders dağılımında,
    öğretmen görünümünde, şablonda ve şablon raporunda;
  - `RenkSecici`: `<details>` ile açılan, radyo grubu olarak bir renk paleti; seçince hemen kaydeder.
- Ortak liste bileşenine iki genişletme noktası: `gorunum` (alanın görünümü) ve `ekSutunlar`.
- **Testler:**
  - API'de palet kontrastı, biçim, sıralı atama, okullar arası bağımsızlık, değiştirme, reddetme,
    oturum ve migration'ın doldurması (ayrı veritabanında);
  - arayüzde çip, renk seçici, ve belirteçteki çip yazı renginin API'nin `CIP_METNI`'siyle aynı
    olduğu.

İstekler (parça 2, iki yönde de):
- **Animasyonlar** (150-250 ms, abartısız):
  - düğme ve satırlarda üzerine gelme ve tıklama geçişleri;
  - bildirimlerin kayarak gelip gitmesi;
  - onay penceresinin yumuşak açılıp kapanması;
  - sayfa geçişlerinde hafif solma;
  - listeye eklenen ve silinen satırlar;
  - sekme geçişleri;
  - "Yükleniyor..." yerine iskelet görünüm.
- `prefers-reduced-motion` açıksa animasyonlar kapanır.
- **Görünüm:**
  - düğmelerde ve menüde ikon;
  - belirgin kartlar, hafif gölgeler;
  - Türkçe karakterleri iyi gösteren modern bir yazı tipi.
- **Yöntem:**
  - mümkün olduğunca CSS ile; kütüphane gerekirse küçük ve yaygın olanı, gerekçesiyle;
  - tasarım belirteçleri üzerinden; kontrast testi ve taşma denetimi geçmeye devam eder.

Parça 2a (bitti):
- Belirteçler: sayfa zemini, çerçeve renkleri (`--renk-ust-*`, `--renk-menu-*`), kart gölgesi,
  hareket süreleri (`--sure-kisa/--sure/--sure-uzun`, `--egri`).
- `stil/temalar.css`: `[data-tema="sicak"]` ve `[data-tema="kurumsal"]`. Seçim `?tema=`
  parametresiyle ya da localStorage'dan yapılır (main.tsx; geçici).
- Kontrast testi üç temayı ayrı ayrı denetler.
- Yazı tipleri (Nunito, Inter; @fontsource-variable) ve ikonlar (lucide-react).
- `Iskelet` bileşeni "Yükleniyor..." yazısının yerine geçti.
- `hareket.ts`: çıkış animasyonları; hareket azaltılmışsa ve jsdom'da gecikme yoktur.
- Animasyonlar: bildirim kayarak girer ve çıkar; onay penceresi `@starting-style` ile açılır;
  tablo satırı girer, silinen satır çıkar (liste sayfaları); düğmede basma ve dönen yüklenme
  ikonu.
- Hareketi azaltma kuralı `::backdrop`'u da kapsar.

Parça 2b (bitti):
- çerçeve: menü ikonları, temaya göre üst çubuk ve menü renkleri, sayfa geçişinde solma
  (`key={konum.pathname}`);
- sekme geçişi: çizgi ve renk geçişi, panel solarak gelir;
- düğmelerde ikonlar (`ikon` prop'u);
- kartlar daha belirgin;
- giriş ve kayıt sayfaları: temanın renginden türeyen zemin, ürün işareti, kart girişi.

Parça 1 notları:
- Görüntüler: `node scripts/ekran-goruntusu.mjs tasarim`. Örnek okulla alınır; iki tema, beşer
  ekran.
- Görüntüler sırasında yapılan düzeltmeler:
  - ana sayfaya karşılama bandı eklendi;
  - ders dağılımı tablosu sıkılaştırıldı (Inter'de "Kaldır" kesiliyordu).
- Taşma denetimi tema seçebiliyor (`TEMA=sicak`); iki temada da temiz.
- **Seçimden sonra (parça 3):**
  - seçilen bloğu `belirtecler.css`'e taşı;
  - `temalar.css`'i, main.tsx'teki tema seçimini ve kullanılmayan yazı tipi paketini kaldır;
  - kontrast testini tek dosyaya döndür;
  - bütün ekranların masaüstü ve telefon görüntülerini al, taşma denetimini çalıştır;
  - 5.5'ten önce kullanıcıya sor.

Parça 0 notları: `api/src/okulapi/ornek_okul.py`.
- Bütün okulları `TRUNCATE okul, giris_denemesi CASCADE` ile siler; `--evet` olmadan hiçbir şey
  yapmaz.
- Mini seti API'den geçirerek, süreç içinde (`TestClient`) yükler. Testlerin mini yükleyicisi de
  artık aynı fonksiyonu (`veri_setini_yukle`) kullanır.
- Her seviyenin şablonu ilk şubesinden üretilir.
- Giriş: `mudur@ornek.test` / `ornek-okul-parolasi`. Test: `api/tests/test_ornek_okul.py`.
- **Geliştirme ortamı koruması (2026-10-23, bitti):** `Ayarlar.ortam` alanı eklendi; varsayılanı
  `yayin`. Komut yalnızca `OKULAPI_ORTAM=gelistirme` ile çalışır (yoksa çıkış 3). Koruma
  `ornek_okul_kur`'un kendisinde de var. 7 test; iki koruma ayrı ayrı kaldırılarak denendi, ikisi de
  yakalandı.

### Yapım sırası 6 (program)

**Animasyonlara özellikle özen gösterilecek** (kullanıcı isteği, 2026-10-16):
- "program hazırlanıyor" beklemesi;
- ilerleme göstergesi;
- çizelgenin yerleşmesi (hücrelerin sırayla yerine oturması).

1. **Program üretme ve durum (6.1):**
   - "Programı oluştur" düğmesi; öncesinde dağılım özetindeki uyarılar (öğretmensiz ders,
     kapasite aşımı) gösterilir;
   - durum takibi (`refetchInterval` ile sorgulama; bekliyor → üretiliyor → hazır);
   - bekleme ekranı: canlı ama sakin ilerleme göstergesi ve aşamaların görünmesi;
   - başarısızlıkta ön kontrol ve çelişki mesajları anlaşılır biçimde;
   - ana sayfa panosuna "Programı oluştur" adımı ve son programa bağlantı.
2. **Haftalık çizelge görünümü (6.2):**
   - şube ya da öğretmen seçilir, o haftalık program gösterilir;
   - hücrede ders çipi ve ders adı; şube görünümünde öğretmen rozeti, öğretmen görünümünde şube
     adı; boş saatler sade;
   - program hazır olunca hücreler kısa ve yumuşak bir sırayla yerleşir (hareket azaltmaya uyar);
   - altında kalite özeti sade Türkçe (boş gün, pencere saati, sınıf boşluğu).
3. **Programlar ve yeniden üretme:**
   - program listesi;
   - kalite ölçümlerinin sade dille gösterimi ("2 öğretmenin penceresi var, sınıflarda boş saat
     yok");
   - "Bu programı temel alarak yeniden üret" ve kaç hücrenin değiştiğinin gösterimi;
   - uçtan uca: arayüzden program üretilip bir şubenin çizelgesi doğrulanır.

### 7.2 çıktı planı (PDF ve Excel)

Kullanım limiti dolabileceği için her alt parça ayrı commit edilir; yarıda kalırsa buradan devam edilir.

| # | Alt parça | Durum |
|---|---|---|
| 7.2a | Zil saati hesabı tek kaynakta: `api cekirdek/zil.py`; `OkulYanit.zil_saatleri` ve `ogle_arasi_zili` hesaplanmış alanlar; ayar ekranının önizlemesi `POST /api/okul/zil-onizleme` (kaydetmez); arayüzdeki hesap (`zaman.ts`) kaldırıldı | Bitti |
| 7.2b | Kütüphane seçimi (ReportLab, openpyxl, DejaVu Sans gömülü) ve ADR 0020; çıktı modeli `cikti/model.py`, veritabanından dolduran `cikti/veri.py` (blok birleştirme arayüzdekiyle aynı kural) | Bitti |
| 7.2c | Şube ve öğretmen PDF'i: `GET /programlar/{id}/cikti/subeler.pdf` (`sinif_id`, `imza`), `.../ogretmenler.pdf` (`ogretmen_id`, `imza`); A4 yatay, her biri ayrı sayfa, okul/program/tarih başlığı, zil saatleri, öğle arası satırı, blok birleşik hücre, öğretmende haftalık toplam; 409 hazır olmayan program | Bitti |
| 7.2d | Çarşaf liste PDF'i `.../carsaf.pdf?satir=` (ogretmen ya da sube): A3 yatay; satırlar bölünür, başlık tekrarlanır; günler sığmazsa gün gruplarına ayrılır | Bitti |
| 7.2e | Excel `.../program.xlsx`: Şubeler, Öğretmenler (sayfa sonlarıyla), iki çarşaf (filtre, dondurulmuş bölme, başlık tekrarı, A3), Liste (her ders saati bir satır, filtre); adlandırılmış stiller (büyük okulda 4,2 → 2,1 sn) | Bitti |
| 7.2f | İzolasyon testi (başka okul her uçta 404, oturumsuz 401); bir kez bozuldu (yabancı programa boş çıktı): yakalandı. Büyük okul ölçümü ADR 0020'de (hepsi 2,5 sn altında; istek içinde üretim yeterli) | Bitti |
| 7.2g | Arayüz: `IndirMenusu` (açılır kutu, disclosure deseni: `aria-expanded`, Escape ve dışarı tıklama kapatır) program sayfasının "hazır" panelinde ve çizelgede; seçili şube/öğretmenin tek sayfalık PDF'i, "Okul Müdürü" imza alanı seçeneği. Satır başlığı arayüzle aynı: "1. saat". Ekran: docs/ekranlar/7.2/ (menü ve 3 PDF sayfası; akış `node scripts/ekran-goruntusu.mjs 7.2` menüden gerçekten indirir ve dosya adını denetler, örnek okula geçici açılan zil saatleri geri yazılır; PDF sayfaları pypdfium2 ile PNG'ye çevrildi, proje bağımlılığı değil) | Bitti |

### 8 planı (içe aktarma, yayın ve paylaşım linki)

Kullanım limiti dolabileceği için her alt parça ayrı commit edilir; yarıda kalırsa buradan devam edilir.

| # | Alt parça | Durum |
|---|---|---|
| 8.0 | Öğretmen PDF'inde aynı dersin farklı şubelerdeki art arda saatleri ayrı görünür: şube adı her hücrede kalın ve üstte, hücreler arasında koyu ayraç | Bitti |
| 8a | Excel'den içe aktarma (ADR 0021): `GET /ice-aktarma/sablon.xlsx` (4 sayfa; açıklama, başlık, "(örnek)" işaretli örnek satır, seviye/saat doğrulaması), `POST /ice-aktarma/onizleme` (kaydetmez; sayfa başına eklenecek / güncellenecek / hatalı (satır no + neden) / değişmeyen), `POST /ice-aktarma?ozet=` (plan yeniden hesaplanır; hatalı satır 422, veri arada değiştiyse 409; tek işlem). Ad eşleştirme Türkçe anahtarla (İ/ı, boşluk, tire çevresi); boş hücre değiştirmez; gruplar şube satırından açılır. Sınırlar: 2 MB (akışta 413), açık 40 MB, 2000 kayıt/sayfa. Testler: 9 API (izolasyon dahil), 3 web. Arayüz: menüde "Excel'den aktar" (`/ice-aktarma`) | Bitti |
| 8b-1 | Yayın (ADR 0022): `yayin` tablosu (migration `ders_programi_0010`, okul başına tek satır, RLS); içerik çıktı modelinin JSON'u (`cikti/anlik.py`), atamalara bağlı değil. `GET/PUT/DELETE /yayin`; uyarılar: eski veri (programın `veri_ozeti`), yayından sonra program değişti (hücre karşılaştırması), program silindi. Test: atama ve öğretmen silinince taslak program eksilir (CASCADE), yayın aynı kalır ("Sonraya" 1 kapandı) | Bitti |
| 8b-2 | Paylaşım linkleri (ADR 0022): `paylasim_linki` (migration `ders_programi_0011`; kapsam CHECK, kapsam başına tek link, öğretmen/şube silinince CASCADE), jeton 256 bit. Yönetici: `GET/POST /paylasim-linkleri`, `/toplu`, `/{id}/yenile`, `DELETE`. Girişsiz: `GET /paylasim/{jeton}` ve `/program.pdf`, okulsuz oturumla `paylasim_icerigi` (SECURITY DEFINER, sahibi `okul_paylasim`: NOLOGIN, süper değil, yalnızca iki tablonun gereken sütunları; kapsam süzmesi SQL'de). Yanıtlar no-store, no-referrer, noindex; kimlik taşımaz. Güvenlik testleri 8; mutasyon: 12 mutasyonun 12'si yakalandı (ilk turda kaçan ikisi: uydurma jeton yalnızca başka link yokken denenmişti, test linkler varken de deniyor; kimlik mutasyonu eşdeğerdi, yerine şemaya alan ekleyen mutasyon kondu) | Bitti |
| 8b-3 | Arayüz: girişsiz `/p/:jeton` sayfası (menüsüz; masaüstünde haftalık tablo, telefonda gün düğmeleri ve o günün listesi, blok tek satır; okul linkinde şube/öğretmen seçici; seçilenin PDF'i; geçersiz link ve "yayında program yok" iletileri; no-referrer). Menüde "Yayın ve paylaşım" (`/yayin`): yayınla / yeniden yayınla / kaldır (onaylı), güncel olmama nedenleri; okul, öğretmen, şube linkleri (kopyala, yenile, iptal onaylı; "Linki olmayanlara oluştur"). Program sayfasında "Yayınla ve paylaş" bağlantısı. Testler: 7 web. Ekran: docs/ekranlar/8/ | Bitti |

**Sıradaki:** 8. adım bitti (kullanıcı onayladı). Sırada K6.

### K6 planı (ikincil kurallar; kullanıcı isteği 2026-10-24)

Kullanım limiti dolabileceği için her alt parça ayrı commit edilir; yarıda kalırsa buradan devam edilir.

| # | Alt parça | Durum |
|---|---|---|
| K6a-c | Çözücü: `ders_saat_tercihi` (esnek, ders / ders + şube / ders + grup; `saatler` tercih edilen, `kacin` kaçınılan; okul genelinde tercih yok), `gunluk_en_az_ders` (esnek, okul ve öğretmen; k=2; öğretmenin yükü ve en iyi günü yetmezse k küçülür, 1'de kural yok), `ders_yayilimi` (esnek, ders/şube/grup; art arda iki gün dolu → ceza; `yayilsin: false` ile kapanır). Değerler tek kaynakta (`cozucu/tercihler.py`), kalite ölçüleri `saat_tercihi`, `az_dersli_gun`, `art_arda_gun` (eski programlarda 0). Ağırlıklar 3 / 3 / 2. API: metinler, önem karşılıkları, parametre doğrulaması (saat listesi, `yayilsin`). Mutasyon 14/14. Eski testlerden üçü yeni kuralları kapattı (konuları değil), mini setteki "en az değişiklik" payı 4 → 6 | Bitti |
| K6d | Öğretmen haftalık yük uyarısı (ADR 0023): eşikler `haftalik_yuk` uyarı kuralı (`alt`, `ust`; 0 = kapalı; okul ve öğretmene özel; modele bir şey eklemez; alt > üst reddedilir). Metin tek yerde (`YukHesabi.ogretmen_yuk_uyarisi`): dağılım özetinde `yuk_uyarisi`, `GET /on-kontrol` yanıtında ayrı `uyarilar` listesi (üretimi engellemez). Arayüz: öğretmen kartında turuncu uyarı, program sayfasında "Uyarılar (programı engellemez)". Mutasyon 5/5 (ilk turda eşiğe eşit yük kaçtı, sınır testi eklendi) | Bitti |
| K6e | Arayüz: "Özel ayar ekle"de dört yeni kural (saat tercihi: "yalnızca seçilen saatlerde olsun" / "seçilen saatlerde olmasın" ve saat kutuları, öğle arasından hemen sonraki saat adıyla, "sabah saatlerini seç" kısayolu; en az ders: sayı; yayılım: açık/kapalı; yük: alt ve üst eşik). Özel ayarların özetinde sade cümleler ("5., 6. saatlerde olmasın", "haftada en az 15 saat"). Okul ayarları "Gelişmiş: kuralların önemi ve ikincil kurallar": yeni kuralların önemi, "geldiği günde en az kaç ders", "bütün derslerde açık" kutusu, yük eşikleri; tek "Gelişmiş ayarları kaydet". Kalite özetinde "az dersli gün", "art arda gün" ve (yalnızca sıfırdan büyükse) "saat tercihi". Testler: 5 yeni web testi | Bitti |
| K6f | Örnek okulda deneme ve gerçekçi sette ölçüm (aşağıda "K6'dan notlar"; docs/olcumler.md "İkincil kurallar") | Bitti |
| K6g | Yayılım okul genelinde kapalı, yalnızca derse (ders + şube/grup) özel açılır (ADR 0024). "Gelişmiş"te kutu yerine yönlendirme ve çatışma cümlesi; API okul geneli açmayı reddeder; kalite özetinde "art arda gün" yalnızca sıfırdan büyükse. Yeniden ölçüm: docs/olcumler.md | Bitti |
| T | Tasarım rötuşu: iki seçenek gösterildi, kullanıcı A'yı seçti. Koyu espresso menü, seçili öğede kiremitten turuncuya geçiş, sayfa başlığında ve karşılamada dolu geçişli bant ve beyaz yazı, #efe4d6 zemin, pastel sayı kartları. Hepsi belirteçlerle (stil/belirtecler.css), kontrast testi yeni çiftlerle | Bitti |

Tasarım rötuşundan notlar:
- Önizlemedeki bandın sarı-turuncu ucu (#f59e0b) ve seçili menünün açık turuncu ucu (#ea580c)
  beyaz yazıyla 4.5:1'i tutmuyordu (2.1 ve 3.6). Uçlar koyulaştırıldı (#b44c0b, #c44c0e; bandın açık ikincil yazısı da 4.5:1 tutsun diye).
- Zemin #efe4d6'ya koyulaşınca eski birincil renk (#c2410c) bu zeminde bağlantı yazısı olarak 4.1:1
  kalıyordu; birincil renk bir ton koyulaştırıldı (#b53c0b).
- Bant içindeki ikincil metin, rengini CSS değişkeninin yerel olarak yeniden tanımlanmasıyla alır
  (`--renk-metin-ikincil` bant içinde açık ton); bileşenler değişmedi. Yazdırırken bant düz zemine
  döner. PDF ve Excel sunucuda üretildiği için bu değişiklikten etkilenmez.

K6'dan notlar:
- **Deneme (örnek okul, mini set, 5 gün × 6 saat, "Hızlı" 30 sn; API ve worker yeni imajla):**
  kurallar kapalıyken (k = 1, yayılım kapalı) 13 art arda gün çifti, öğretmenin 1 saatlik bir günü;
  varsayılanla 3 çift, 1 saatlik gün yok (her öğretmen gününde en az 2 ders). k = 3 ile en az 3.
  Kimya "yalnızca 4.-6. saat": 8 saatin hepsi 4.-6. saatte (önce 6'sı 1.-2. saatteydi); Tarih
  "1.-2. saatte olmasın": hepsi 3.-6. saatte (önce 3'ü). Matematik "1.-3. saat" yalnızca kısmen
  (12/18): tek öğretmenin 18 saati var, sabah 15 yer. Yük eşikleri 16-20: ön kontrolde 3 uyarı
  ("Fatma Şahin haftada 9 saat derse giriyor, alt eşik 16 saat (7 saat eksik)."), çelişki 0,
  program üretildi; dağılım özetinde aynı 3 öğretmen.
- **Geri alma:** veritabanı önce `pg_dump` ile yedeklendi; betik özel ayarları ve okul değerlerini
  kaldırdı, 5 deneme programını sildi; kurallar ve program listesi başlangıçla birebir aynı.
- **Ölçüm:** sınıf boşluğu her tohumda 0, ama yayılım kuralı öğretmen konforunu kötüleştiriyor
  (pencere 8 → 23, eksik boş gün 11 → 19). Kullanıcı kararıyla yayılım okul genelinde kapatıldı
  (K6g, ADR 0024); yeniden ölçümde eski ölçüler 156 → 123 (P1: 69). Kalan fark için "günde en az
  ders" kuralının ayrıca ölçülmesi açık bir soru.

## 8. Açık sorular

Kararlar (kullanıcı, 2026-10-15):
1. **Görsel tasarım: A**, kendi sade stilimiz, ortak tasarım temeliyle (bölüm 3).
2. **Esnek kural ağırlıkları:** "Gelişmiş" bölümünde, üç seviyeli sade seçimle; sayısal
   karşılıklar API'de tek yerde (bölüm 2.3).
3. **Karanlık tema:** ilk sürümde yok.

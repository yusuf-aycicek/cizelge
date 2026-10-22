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
| 5.5 | Müsaitlik çizelgesi | **Sıradaki** |
| 5.6 | Kullanıcılar, kontrol listesi, uçtan uca | |

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
| 1 | İki tasarım yönü, beşer masaüstü ekran görüntüsü (giriş, ana sayfa, öğretmenler, okul ayarları, ders dağılımı); **kullanıcının seçimi beklenir** | Görüntüler alındı (`docs/ekranlar/tasarim/`); **kullanıcının seçimi bekleniyor** |
| 2 | (1 ile birlikte, iki yönde ortak) animasyonlar, ikonlar, kartlar, yazı tipi | Bitti (2a, 2b) |
| 3 | Seçilen yönün bütün ekranlara uygulanması; masaüstü ve telefon görüntüleri, taşma denetimi; 5.5'ten önce kullanıcıya sorulur | |

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

1. **Program üretme ve durum:**
   - "Program üret" (ad, süre; temel program seçimi);
   - durum göstergesi (`refetchInterval` ile sorgulama; bekliyor → üretiliyor → hazır);
   - başarısızlıkta çelişkilerin anlaşılır gösterimi, ilgili öğretmen ya da şubeye bağlantıyla.
2. **Haftalık çizelge görünümü:** şube ve öğretmen bazında çizelge bileşeni (gün × saat), program
   seçimi, yazdırmaya uygun sade görünüm.
3. **Programlar ve yeniden üretme:**
   - program listesi;
   - kalite ölçümlerinin sade dille gösterimi ("2 öğretmenin penceresi var, sınıflarda boş saat
     yok");
   - "Bu programı temel alarak yeniden üret" ve kaç hücrenin değiştiğinin gösterimi;
   - uçtan uca: arayüzden program üretilip bir şubenin çizelgesi doğrulanır.

## 8. Açık sorular

Kararlar (kullanıcı, 2026-10-15):
1. **Görsel tasarım: A**, kendi sade stilimiz, ortak tasarım temeliyle (bölüm 3).
2. **Esnek kural ağırlıkları:** "Gelişmiş" bölümünde, üç seviyeli sade seçimle; sayısal
   karşılıklar API'de tek yerde (bölüm 2.3).
3. **Karanlık tema:** ilk sürümde yok.

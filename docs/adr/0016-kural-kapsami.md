# ADR 0016: Kural kapsamı: en özel kapsam kazanır

Durum: **Kabul edildi** (kullanıcı onayladı). Ayrıntılı tasarım:
`docs/kisisellestirme-plani.md`.

## Bağlam

Kurallar bugün okul genelidir: `kisit` tablosunda her `tur` için tek satır, çözücüde tek kural
örneği (ADR 0002, strategy deseni). Gerçek okullarda kuralların istisnası vardır:
- öğretmene özel günlük sınır ve boş gün;
- derse özel blok yapısı ve günlük sınır;
- şube grubuna (alan) ya da tek şubeye özel değerler.

Sistem bütün okullar için genel olduğundan bu istisnalar kodla değil, ayarla karşılanmalıdır.

## Karar

- **Kapsam:** bir kural tanımı, eksenlerin birleşimi olan bir kapsam taşır: `(ders?, şube? |
  şube grubu?, öğretmen?)`. Boş eksen her şeye uyar; dört eksen de boşsa kapsam okul genelidir.
- **En özel kapsam kazanır.** Özgüllük puanı: ders 4, şube 2, şube grubu 1, öğretmen 1.
- **Öğretmen kapsamı ders ve şube kapsamıyla çakışamaz.** Kurallar iki ayrık aileye ayrılır:
  öğretmenin kendisiyle ilgili olanlar (M, boş gün, günde en az ders) yalnızca öğretmen ekseni;
  yerleşimle ilgili olanlar (N, blok, saat tercihi, yayılım) yalnızca ders, şube ve şube grubu
  eksenleri. İkisini birden bildiren kural sınıfı kayıt anında reddedilir (testle denetlenir).
  İki ekseni birlikte isteyen bir kural gerekirse öncelik yeni bir ADR ile tanımlanır.
- **Çözümleme tek bir saf fonksiyondur** (`cozucu/kapsam.py: cozumle`). Çözücü, ön kontrol, API
  (değerin nereden geldiği) ve arayüz aynı fonksiyonu kullanır (ADR 0015'teki tek kaynak ilkesi).
- **Strategy deseni korunur:**
  - her `tur` için yine tek kural örneği vardır;
  - özel tanımlar örneğe verilir, kural değeri `self.deger(baglam, ad, varlik…)` ile ister;
  - kural desteklediği eksenleri `kapsamlar` ile bildirir, desteklenmeyen kapsam
    `kural_olustur`'da reddedilir;
  - `CpSatCozucu` ve kayıt defteri değişmez.
- **Depolama:** özel tanımlar da `kisit` tablosundadır:
  - dört boş olabilir kapsam sütunu (`ders_id`, `sinif_id`, `sube_grubu_id`, `ogretmen_id`);
  - bileşik yabancı anahtar ve `ON DELETE CASCADE`;
  - kapsam üzerinde benzersizlik.
  Var olan satırlar okul kapsamında kalır.

## Değerlendirilen alternatifler

- **Her kapsam için ayrı kural örneği:** okul geneli ve özel tanım aynı varlık için ikisi birden
  uygulanırdı (ör. N = 2 ve Matematik N = 3: Matematik fiilen 2'de kalır). Esnek kurallarda ceza
  iki kez yazılırdı. "En özel kazanır" için her örneğin ötekileri bilmesi gerekirdi.
- **Her ezme türü için ayrı tablo** (`ogretmen_ayari`, `ders_ayari`…): her kural kendi tablosunu
  ve okuma yolunu ister. Kapsam çözümlemesi kurallara dağılır; yeni bir kural yeni tablo ve
  migration ister.
- **Okul satırının içinde JSON ezmeler:** yabancı anahtar yok. Silinen öğretmenin ayarı yetim
  kalır, başka okulun kimliği yazılabilir; veritabanı izolasyonu korumaz (ADR 0009).
- **Öncelik sırasını kullanıcıya seçtirmek:** teknik olmayan kullanıcı için anlaşılmaz. Sabit ve
  belgelenmiş bir sıra ("en özel kazanır") ile "değer nereden geliyor" gösterimi yeterli.

## Sonuçlar

- Yeni kurallar (blok deseni, saat tercihi, günde en az ders…) baştan kapsamlı yazılır.
- Arayüz her özel alanda "Okul varsayılanı (2)" seçeneği ve değerin kaynağını gösterir.
  Okuldaki bütün özel ayarlar tek bir özet listede görünür.
- Çelişki analizi özel ayarları kendi gruplarında adlandırır ("Ayşe Yılmaz'a özel günlük sınır").
  Kullanıcı hangi istisnanın sorun çıkardığını görür.
- Bedeli:
  - kural kodu değeri doğrudan alanından değil, çözümleyiciden okur (küçük bir dolaylılık);
  - `kisit` tablosunun benzersizliği kapsam sütunlarını da kapsar: `UNIQUE NULLS NOT DISTINCT`
    (PostgreSQL 15+); boş sütunlar eşit sayılır, okul geneli satır yine tektir.

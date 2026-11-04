# ADR 0029: Branş, okulun derslerinden çoklu seçimdir (aynı metin sütununda)

Durum: Kabul edildi (2026-11-04, okul müdürü gibi yapılan deneme sonrası kullanıcının isteğiyle).

## Bağlam

Öğretmenin branşı serbest metindi. Denemede bu yavaş ve tutarsız kaldı ("Mat.", "Matematik
Öğretmeni"). Branş, ders dağılımında öğretmen seçicinin sıralamasında kullanılıyor (`brans.ts`):
dersle eşleşen öğretmenler üstte çıkıyor. Bazı öğretmenler birden fazla derse giriyor (Fizik ve
Kimya). Eski serbest metin verisi bozulmamalı.

## Karar

- Arayüzde branş okulun derslerinden **çoklu seçimdir** (`listeler/BransSecici.tsx`). Ekleme
  formunda ve satır içi düzenlemede açılır bir onay kutusu listesi olarak görünür.
- Değer yine `ogretmen.brans` metin sütununda saklanır. Seçilen derslerin adları okulun ders
  sırasıyla, virgülle birleştirilir: `"Fizik, Kimya"`. Veritabanı, API ve migration değişmez.
- Bir ders adıyla eşleşmeyen eski parça ("Fen Bilimleri Öğretmeni") listede işaretli bir
  "(eski yazım)" seçeneği olarak kalır. Kullanıcı isterse işaretini kaldırıp siler; dokunmazsa
  metin olduğu gibi korunur. Tabloda metin eskisi gibi gösterilir.
- Eşleştirme (`bransUyar`) virgülle ayrılmış parçaların her birine ayrı bakar. Biri uyarsa
  öğretmen o dersin grubunda çıkar.

## Değerlendirilen alternatifler

- **`ogretmen_brans` (öğretmen, ders) ara tablosu.** İlişkisel olarak en doğrusu ve ders
  silinince temizlenir. Ama migration, yeni CRUD, okul izolasyonu (bileşik FK, RLS) ve Excel
  içe aktarmada değişiklik gerektirir. Eski serbest metin de bir yere taşınmalı. Branş yalnızca
  sıralamayı etkilediği için, hiçbir kısıtın girdisi değil, bu bedel karşılanmaya değmez.
- **Tek seçim.** Birden fazla derse giren öğretmeni karşılamaz.

## Sonuçlar

- Dersin adı değişirse öğretmenin branşındaki eski ad "(eski yazım)" olarak kalır. Kullanıcı yeni
  adı seçip eskisini kaldırır. Eşleştirme kelime başı benzerliğine baktığı için çoğu durumda
  sıralama yine çalışır.
- Sütun en fazla 100 karakterdir. Çok sayıda uzun adlı ders seçilirse sunucu 422 döner ve mesaj
  alanın altında görünür. Pratikte 4-5 ders sığar.
- Excel'den içe aktarma serbest metni olduğu gibi yazar. Virgüllü metin ("Fizik, Kimya")
  seçicide doğrudan iki ders olarak görünür.

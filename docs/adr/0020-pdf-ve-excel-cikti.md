# ADR 0020: PDF ve Excel çıktısı sunucuda, ReportLab ve openpyxl ile

Durum: Kabul edildi (2026-10-24, 7.2).

## Bağlam

Yönetici programı kâğıda basar ve paylaşır: şube programları (sınıf kapısına), öğretmen
programları (haftalık toplam ders saatiyle), bütün okulun çarşaf listesi (müdür odası panosu,
A3) ve düzenlenebilir bir Excel dosyası. Türkçe harfler doğru basılmalı; renkli olmalı ama
siyah-beyaz yazıcıda da okunmalı. Zil saatleri hem ekranda hem çıktıda aynı olmalı.

## Karar

1. **Çıktı sunucuda üretilir** (`moduller/ders_programi/cikti/`). Tarayıcıda yazdırma
   (`window.print`) sayfa bölmeyi, A3'ü ve yazı tipini tarayıcıya bırakır; okuldan okula sonuç
   değişir. Excel zaten sunucuda üretilmeli; iki biçim aynı veriyi aynı yerden okusun.
2. **Üç katman:** `model.py` biçimden bağımsız düz yapılar (çizelge, hücre, hafta); `veri.py`
   onları oturumun okulundan doldurur (okul filtresi depolarda); `pdf.py` ve `excel.py` yalnızca
   modeli okur. Blok birleştirme kuralı arayüzdekiyle aynıdır (aynı atamanın art arda saatleri,
   öğle arası böler).
3. **PDF: ReportLab.** Yaygın, saf Python (yalnızca Pillow'a bağımlı), tablo hücre birleştirme
   (SPAN), başlığın her sayfada tekrarı ve satırlardan bölme hazır; TrueType yazı tipini alt küme
   olarak gömer. Yazı tipi **DejaVu Sans** (serbest lisans, Türkçe harfler tam), depoda
   `cikti/yazitipi/` altında; Docker imajında sistem yazı tipine gerek kalmaz.
4. **Excel: openpyxl.** Yaygın; birleşik hücre, filtre, bölmeleri dondurma, yazdırma ayarı
   (yatay, sayfa genişliğine sığdır, başlık satırlarını tekrarla, sayfa sonu) destekli; testte
   aynı kütüphaneyle dosya okunur. Stiller adlandırılmış stil olarak bir kez kaydedilir.
5. **Zil saati hesabı tek yerde** (`cekirdek/zil.py`); okul yanıtı, ayar önizlemesi ve
   çıktılar oradan okur. Arayüzdeki hesap kaldırıldı.
6. **Çarşaf liste sayfalara bölünür:** satırlar sığmazsa tablo bölünür, iki başlık satırı her
   sayfada tekrarlanır; sütunlar (gün × saat) en az 7,5 mm'ye sığmazsa günler gruplara ayrılır.
7. **Renk:** hücre zemini dersin renginin açık tonu, solda dersin renginde kalın şerit; yazı
   siyah. Siyah-beyaz baskıda zemin açık gri olur, metin okunur. Kısa günün olmayan saati gri.

## Değerlendirilen alternatifler

- **WeasyPrint (HTML → PDF):** şablonu HTML/CSS ile yazmak kolay, ama Pango/Cairo sistem
  kütüphanelerine bağımlı (Windows'ta ve ince Docker imajında kurulumu ağır) ve büyük okulda
  belirgin yavaş.
- **fpdf2:** küçük ve saf Python; ama dikey hücre birleştirme ve sayfa bölünmesinde başlık
  tekrarı ReportLab kadar olgun değil.
- **XlsxWriter:** hızlı, ama yalnızca yazar; testte okumak için yine openpyxl gerekirdi.
- **Tarayıcıda PDF (jsPDF vb.):** çıktı üretimi arayüze taşınırdı; Excel ile tek kaynak kalmazdı.

## Sonuçlar

- Bağımlılık: `reportlab`, `openpyxl` (API); `pypdf` yalnızca test (PDF metnini okumak için).
- Depoya ~1,4 MB yazı tipi eklendi (iki dosya ve lisansı).
- Süre (büyük okul: 40 şube, 80 öğretmen, 5 × 8 saat, bütün saatler dolu; geliştirme makinesi,
  üç denemenin en iyisi): şube PDF'i (40 sayfa) 2,1 sn, öğretmen PDF'i (80 sayfa) 2,2 sn, çarşaf
  liste 1,0–1,5 sn, Excel 2,1 sn (adlandırılmış stillerden önce 4,2 sn). Veritabanından okuma
  mini sette 0,2 sn. İstek içinde üretmek yeterli; kuyruğa almak gereksiz karmaşıklık.
- Daha büyük okulda süre sorun olursa sırayla: (1) programın son değişikliğine (elle düzeltme
  sırası, okul ayarı) bağlı önbellek: aynı dosya yeniden üretilmez; (2) çıktıyı da program
  üretimi gibi kuyruğa alıp hazır olunca indirme bağlantısı vermek.

# ADR 0006: En az değişiklikle güncelleme: değişiklik cezası ve başlangıç ipucu

Durum: Kabul edildi (2026-10-06)

## Bağlam

Program dönem içinde de değişir: bir öğretmen ayrılır, müsaitliği değişir, bir dersin saati
artar. Program sıfırdan üretilirse çözücü kalite bakımından eşit derecede iyi ama tamamen
farklı bir program bulabilir. Mini sette tek bir öğretmenin bir günü kapandığında, sıfırdan
üretim 71 hücrenin 54'ünü değiştirdi. Öğrenci, öğretmen ve veli için bu kabul edilemez. Hedef:
gereken değişikliği yapıp gerisini yerinde bırakmak.

## Karar

- Çözücü isteğe bağlı olarak temel bir program alır: `CozumGirdisi.temel_yerlesimler`.
  Veritabanında `program.temel_program_id` hangi programın temel alındığını kaydeder.
- **Eşleştirme (sınıf, ders, gün, saat) ile yapılır, atama kimliğiyle yapılmaz.** Temel program
  bu yüzden `TemelYerlesim(sinif_id, ders_id, gun, saat)` olarak verilir. Öğretmeni değişen ya
  da silinip yeniden oluşturulan atama da "aynı ders" sayılır. "Bir sınıf, bir ders, bir öğretmen"
  modeli kalıcı olduğundan (CLAUDE.md bölüm 3) bu eşleştirme belirsiz değildir. Worker, eski
  programın yerleşimlerini `temel_program(...)` ile bu biçime çevirir.
- **Değişiklik cezası** (`degisiklik`, esnek, varsayılan ağırlık 8; ilk sürümde 20): temel programdaki her hücre
  yeni programda yoksa 1 puan. Birimi "yer değiştiren ders saati"dir. Ölçüsü
  `kalite.degisen_yerlesim`'dir. Temel programda olup artık var olmayan dersler sabit ceza
  olarak eklenir. Bu, en iyi programı değiştirmez ama toplam cezayı ölçümle tutarlı tutar.
- **Başlangıç ipucu:** temel program CP-SAT'a `add_hint` ile de verilir. Arama oradan başlar,
  ama sonuç zorlanmaz. Mini sette güncelleme 0,3-1 sn sürdü, sıfırdan üretim 6-10 sn.

## Değerlendirilen alternatifler

- **Değişmeyen dersleri kilitlemek.** Hangi derslerin değişmesi gerektiğini önceden bilmek
  gerekir. Çoğu zaman bilinmez: Mehmet'in perşembe dersleri kaymak zorundadır, ama nereye
  kayacakları başka dersleri de yerinden oynatabilir. Fazla kilit çözümsüzlüğe, eksik kilit
  dağılmaya yol açar.
- **Yalnızca ipucu vermek (ceza olmadan).** Arama temel programa yakın başlar, ama amaç
  fonksiyonu yakınlığı ödüllendirmez. Çözücü kalite için programı yine serbestçe dağıtabilir.
- **Kimlikle eşleştirme.** Basittir, ama atama yeniden oluşturulunca (öğretmen değişikliğinin
  bazı akışları, Excel'den yeniden içe aktarma) bütün eşleşmeler kaybolur.

## Sonuçlar

- Değişiklik ağırlığı, diğer esnek kurallarla bir takas belirler. Mini set ölçümünde Mehmet'in
  bir günü kapandığında alt sınır 5 değişiklikti:

  | Ağırlık | Değişen hücre | Sınıf boşluğu |
  |---|---|---|
  | 20 | 5 | 3 |
  | 10 | 6 | 2 |
  | 8 | 7 | 1 |
  | 2 | 9 | 0 |

  (Bu tablo sınıf boşluğu ağırlığı 10 iken ölçüldü.) Ağırlık bir sınıf boşluğunun cezasından
  büyükse çözücü bir dersi daha kaydırmak yerine sınıfta boş saat bırakmayı seçer.
- **Karar (2026-10-13):** değişiklik 8, sınıf boşluğu 30. Değişiklik öğretmen konforu
  kurallarından ağır, sınıf boşluğundan hafif. Aynı senaryoda yeni ağırlıklarla 8 hücre değişti,
  sınıf boşluğu 0 kaldı ve bir öğretmen boş gününü kaybetti (eksik boş gün 1, ceza 4 < 8). Sıfırdan
  üretim aynı senaryoda 71 hücrenin 58'ini değiştirdi.
- Ağırlık okul bazında ayarlanabilir. Arayüz bunu "mevcut programa bağlılık" gibi anlaşılır
  bir ayar olarak sunabilir.

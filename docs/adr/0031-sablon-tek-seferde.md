# ADR 0031: Seviye şablonu tek seferde kaydedilir ve hepsi birden uygulanır

Durum: Kabul edildi (2026-11-04, okul müdürü gibi yapılan deneme sonrası kullanıcının isteğiyle).

## Bağlam

Şablona ders tek tek ekleniyordu: ders seç, saat yaz, Ekle. Satırdaki saat de alandan çıkınca
ayrı bir istekle kaydediliyordu. Bir seviyenin 12-15 dersi için bu çok yavaştı. Komşu seviyeler
çoğunlukla aynı dersleri alıyor ama kopyalamanın yolu yoktu. "Şubelere uygula" da her seviye için
ayrı ayrı basılıyordu.

## Karar

- **Tablo + tek kayıt.** Şablon sayfası okulun bütün derslerini alt alta, saat kutularıyla
  gösterir. Yazılanlar sayfada taslaktır, toplam ve kapasite yazdıkça güncellenir. "Şablonu
  kaydet" hepsini tek istekle gönderir: `PUT /api/ders-programi/seviye-sablonlari/toplu`.
  Gövde şablonun **tamamıdır**: saati 0 olan ya da listede olmayan ders şablondan çıkar,
  değişen güncellenir, yeni ders eklenir. Tek işlemde yapılır: bir satır geçersizse (başka okulun
  dersi, aynı ders iki kez) hiçbiri yazılmaz.
- **Kopyalama arayüzde yapılır.** "Başka şablondan kopyala" kaynak şablonun saatlerini tabloya
  doldurur ama kaydetmez. Kullanıcı düzeltip kaydeder. Hedefte saat varsa önce onay istenir.
  Ayrı bir sunucu ucu gerekmez: kopya, kaydedilmeden önce zaten taslaktır.
- **Tüm seviyelere uygula:** `POST /api/ders-programi/seviye-sablonlari/uygula-hepsi`. Dolu her
  şablon (seviye ve şube grubu) kendi şubelerine, tek tek uygulamayla aynı kurallarla uygulanır.
  Rapor şablon şablondur. Tek işlemdir. Şablonların şubeleri ayrık olduğundan
  (`sablon_kaynaklari`) sıra sonucu değiştirmez.
- Kaydedilmemiş değişiklik varken uygulama düğmeleri kapalıdır. Uygulama kaydedilmiş şablonu
  kullanır; kullanıcının ekranda gördüğüyle uygulanan farklı olmasın.

## Değerlendirilen alternatifler

- **Satır başına istek, eşzamanlı.** Var olan CRUD uçlarıyla yapılabilirdi, ama yarıda kalan bir
  kayıt şablonu yarım bırakır ve hata mesajı satırlara dağılır.
- **Sunucuda kopyala ucu.** Kopyayı doğrudan kaydederdi. Kullanıcı kopyayı görüp düzeltmeden
  hedefin üzerine yazılırdı; taslak yaklaşımı daha güvenli ve daha basit.

## Sonuçlar

- Eski satır uçları (`POST`, `PATCH`, `DELETE /seviye-sablonlari`) kalır: API kullanıcıları ve
  testler için. Arayüz artık yalnızca toplu kaydı kullanır.
- Okulda çok ders varsa tablo uzar. Saati boş satırlar soluk görünmez, sıralama Türkçe
  alfabetiktir. Gerekirse ileride "yalnızca şablondakiler" süzgeci eklenir.

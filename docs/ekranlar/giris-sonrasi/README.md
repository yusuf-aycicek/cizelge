# Giriş sonrası ekranlar (yeniden tasarım öncesi, 2026-10-30)

Demo okulla dolu, 1440 px genişlikte, tam sayfa. Yeniden almak için (yerel API'de
`OKULAPI_DEMO_PAROLA` tanımlı olmalı):

    cd web && node scripts/ekran-goruntusu.mjs giris-sonrasi

Bütün ekranlar aynı çerçevede durur: üstte logo, okul adı, kullanıcı ve "Çıkış"; solda koyu
menü; içerikte turuncu başlık bandı (ikon, başlık, açıklama).

| # | Yol | Ne işe yarar | Ana parçalar |
|---|---|---|---|
| 01 | `/` | Ana sayfa: kurulumun neresinde olunduğu | Karşılama, ilerleme halkası (%, adım sayısı), sayı kartları (öğretmen, şube, ders, haftalık saat), kurulum adımları listesi, sistem durumu |
| 02 | `/okul` | Okul ayarları | Okul bilgileri (ad, gün sayısı, günlük ders saati, günlere göre saat, öğle arası), zil saatleri, kuralların önemi (Önemsiz / Önemli / Çok önemli), özel ayarlar ve "Özel ayar ekle" |
| 03 | `/ogretmenler` | Öğretmen listesi | Arama, tablo (ad, branş, yük), satır işlemleri, "Yeni öğretmen" formu |
| 04 | `/ogretmenler/:id` | Tek öğretmenin ayarları | Önceki / sonraki gezinme ve öğretmen seçici, kişisel ayarlar (boş gün hedefi, günde en çok ders), müsaitlik çizelgesi (müsait / gelemez / tercih etmez), müsait saat ve ders yükü özeti |
| 05 | `/siniflar` | Şube listesi | Arama, şube tablosu, şube grupları, "Yeni şube" formu |
| 06 | `/dersler` | Ders listesi | Arama, ders tablosu (ad, kısa ad, renk, dağılım şekli), "Yeni ders" formu |
| 07 | `/seviye-sablonu` | Seviyenin ders listesi ve saatleri | Şablon seçici (seviye ya da şube grubu), ders + haftalık saat tablosu, "Şubelere uygula", şablondan farklı dersler |
| 08 | `/ders-dagilimi` | Hangi şubeye hangi dersi kimin verdiği | Durum bildirimi, sekmeler (şubelere / öğretmenlere / derslere göre), solda şube listesi (doluluk), ders tablosu (saat, öğretmen seçici, "Bütün şubeler", "Kaldır"), toplam, "Ders ekle" |
| 09 | `/ice-aktarma` | Excel'den toplu veri girişi | 1. şablonu indir, 2. dosya seç, 3. önizleme (eklenecek, güncellenecek, hatalı satırlar) |
| 10 | `/program` | Program üretme ve geçmiş | Son programın kartı (hazır, kalite özeti, çizelgeyi aç / indir / yayınla, "temel alarak yeniden üret"), yeni program formu (ön kontrol, ad, süre seçimi Hızlı / Dengeli / Uzun), programlar tablosu |
| 11 | `/program/:id` | Haftalık çizelge ve elle düzeltme | Program sayfasına dönüş, "İndir" menüsü, sekmeler (şubeye / öğretmene göre), şube seçici, sürükle-bırak çizelgesi (ders çipi, öğretmen rozeti, blok süresi, boş hücreler), programın kalitesi |
| 12 | `/yayin` | Öğretmenlerle paylaşma | Yayındaki program (değiştir, yayından kaldır), paylaşım linkleri (okul linki, öğretmen linkleri, kopyala / sil) |
| 13 | `/kullanicilar` | Okulun yönetici hesapları | Yöneticiler tablosu (rol, parola belirle, sil), "Müdür yardımcısı ekle" formu |
| 14 | `/hesabim` | Giriş yapan kullanıcının hesabı | Bilgilerim, "Parolamı değiştir" formu |

Listede olmayanlar:

- `/p/:jeton`: öğretmene paylaşılan program. Girişsizdir ve menüsü yoktur; linki 12'deki
  "Paylaşım linkleri"nden açılır.
- `/tasarim`: geliştirme sırasında bileşenleri görmek için iç sayfa, menüde yok.
- `/musaitlik`: eski adres, öğretmen sayfasına yönlendirir.
- Bulunamadı (404) sayfası.

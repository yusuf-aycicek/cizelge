# ADR 0012: Kimlik doğrulama: oturum çerezi, argon2id, okul bilinmeden arama

Durum: Kabul edildi (2026-10-15). Ayrıntılı plan: `docs/kimlik-plani.md`.

## Bağlam

2\. adımdaki geçici `X-Okul-Id` başlığı kaldırılacak; aktif okul yalnızca oturumdan
belirlenecek (CLAUDE.md bölüm 8, yapım sırası 4). Kullanıcılar okul yöneticileridir (müdür,
müdür yardımcısı). Giriş e-posta ve parolayla, okul seçmeden yapılır. Bu iki şeyi gerektirir:
- e-posta bütün sistemde tek olmalı;
- e-postayla arama, okul bağlamına dayanan RLS'nin altında yapılabilmeli.

## Karar

1. **Sunucu taraflı oturum.**
   - Girişte 32 baytlık rastgele bir jeton üretilir ve bir çerezde tarayıcıya verilir. Çerez
     özellikleri:
     - `HttpOnly`: JavaScript okuyamaz, XSS ile çalınamaz;
     - `SameSite=Strict`: başka sitelerden gelen isteklere eklenmez;
     - `Secure`: üretimde yalnızca HTTPS.
   - Veritabanında (`oturum` tablosu) jetonun kendisi değil SHA-256 özeti saklanır. Veritabanı
     sızsa bile oturumlar ele geçirilemez.
   - Süre: 12 saat hareketsizlik, en fazla 7 gün. Çıkışta oturum satırı silinir; oturum anında
     geçersiz olur.
2. **Parola özeti argon2id.** `argon2-cffi`, kütüphanenin önerdiği parametrelerle. En az 10
   karakter. Parametreler ileride değişirse eski özetler girişte yeniden özetlenir.
3. **E-posta bütün sistemde ve büyük/küçük harf ayrımsız tektir.** Küçük harfle saklanır (CHECK),
   benzersizlik `lower(email)` üzerindedir. CHECK kaldırılsa bile ikinci hat korur (testle
   kanıtlandı).
4. **Okul bilinmeden arama:** dar kapsamlı `SECURITY DEFINER` fonksiyonlar. Sahibi `okul_giris`
   rolüdür: `NOLOGIN`, süper kullanıcı değil, yalnızca gereken sütunlarda yetkili. Ayrıntılar
   ADR 0009 ve migration `cekirdek_0004`'te.
5. **Bilgi sızdırmama (giriş):** yanlış e-posta ve yanlış parola aynı mesajı ve yaklaşık aynı
   süreyi alır: kullanıcı yoksa da sahte bir özet doğrulanır.
6. **Kaba kuvvet koruması, e-postaya göre.**
   - Bir e-postayla 15 dakika içinde 5 hatalı denemeden sonra o e-postaya 15 dakika giriş
     yapılamaz (429).
   - Kayıtlı olmayan e-postalar da aynı şekilde sayılır: kilit, e-postanın kayıtlı olup
     olmadığını söylemez.
   - Başarılı giriş sayacı siler.
   - Sayaç okula ait olmayan `giris_denemesi` tablosundadır. Uygulama rolünün bu tabloya yetkisi
     yoktur, yalnızca fonksiyonlarla erişir.
7. **CSRF:** `SameSite=Strict` ve veri değiştiren isteklerde `Origin` başlığı denetimi.
8. **Yönetim.**
   - Okulun tek müdürü vardır, kayıtta oluşur.
   - Müdür yardımcı ekler, siler ve parolasını yeniden belirler. Yeniden belirlenen parolada
     yardımcının oturumları kapanır. Müdür yardımcısı yönetim uçlarına 403 alır.
   - Müdür parolasını unutursa sistemi işleten kişi sunucuda `python -m okulapi parola-sifirla
     <email>` çalıştırır. Bu işin API'de karşılığı yoktur.

## Bilinen ödünleşimler

- **E-postaya göre kilitleme, kasıtlı dışarıda bırakmaya izin verir.** Bir kullanıcının
  e-postasını bilen biri, bilerek yanlış parola deneyerek onu 15 dakika dışarıda bırakabilir; bunu
  tekrarlayarak sürekli yapabilir. IP adresine göre kilitleme bunu önlerdi. Ama okuldaki bütün
  bilgisayarlar aynı dış IP'yi paylaşabilir (bir öğrencinin denemesi bütün okulu kilitlerdi) ve
  vekil sunucu (proxy) arkasında gerçek IP'ye güvenilemez. Sorun gerçekleşirse:
  - kilit süresi kısaltılabilir;
  - IP + e-posta birleşik sayaç eklenebilir;
  - işletmeci `parola-sifirla` ile kilidi kaldırabilir.
- **Kayıt, e-postanın kayıtlı olup olmadığını söyler.** Kayıtta ve yardımcı eklerken e-posta başka
  bir hesapta kullanılıyorsa anlaşılır bir hata (409) döner. Bu, kayıt formu üzerinden bir
  e-postanın sistemde olup olmadığını öğrenmeye izin verir. Kullanıcıya anlaşılır hata vermek
  için kabul edildi. Giriş tarafında aynı bilgi verilmez (madde 5).
- **Oturum her istekte veritabanından çözülür.** JWT'deki gibi imza doğrulaması değil, bir
  fonksiyon çağrısıdır. Son kullanım zamanı en çok dakikada bir yazılır. Bu ölçekte maliyeti
  önemsiz.

## Değerlendirilen alternatifler

- **JWT (imzalı, durumsuz jeton):**
  - sunucuda oturum tutmaz, ama çıkışta ya da hesap silindiğinde süresi dolana kadar geçerli
    kalır (iptal listesi gerekir);
  - `localStorage`'da tutulursa XSS ile çalınabilir.
  - Tek API ve tek veritabanı olan bu sistemde durumsuzluğun getirisi yok.
- **bcrypt:** iyi bir seçenek, ama 72 bayt sınırı var ve güncel öneri argon2id.
- **Okul bilinmeden arama için:**
  - ayrı giriş bağlantısı (RLS'yi atlayan `LOGIN` rolü): bütün `kullanici` tablosunu okuyabilen
    bir bağlantı;
  - RLS dışında global hesap tablosu: uygulama rolü bütün özetleri görür;
  - girişte okul kodu istemek: sorunu kullanıcıya yükler;
  - parolayı veritabanında doğrulamak (pgcrypto): parola SQL parametresiyle gider, bcrypt'e
    bağlanılır.

  Ayrıntılar `docs/kimlik-plani.md` bölüm 2'de.
- **CSRF jetonu (double-submit):** aynı korumayı daha çok kodla verir; arayüz ve API aynı sitede.

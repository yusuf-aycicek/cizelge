# Yapım sırası 4: kayıt, giriş, oturum (plan)

Durum: **onaylandı (2026-10-15)**: (a)-(h) kabul. Açık soruların cevapları bölüm 4'te. Alt adım durumu bölüm 7'de.

Kabul (CLAUDE.md bölüm 8): 2. adımdaki geçici `X-Okul-Id` başlığı tamamen kaldırılmıştır. Aktif
okul yalnızca oturumdan belirlenir. Başlık gönderilse bile yok sayıldığı ve oturumsuz isteklerin
okula ait veriye erişemediği testle kanıtlanır.

## 1. Akış

```
Kayıt:  POST /api/kayit {okul: {ad, gun_sayisi, gunluk_ders_saati}, ad, email, sifre}
        -> okul + müdür (kullanici) + oturum, tek işlemde; 201 + Set-Cookie
Giriş:  POST /api/giris {email, sifre} -> 200 + Set-Cookie   |  401 (aynı mesaj, ayrım yok)
Çıkış:  POST /api/cikis -> oturum silinir, çerez temizlenir
Ben:    GET  /api/ben -> {kullanici, okul}  (arayüz açılışta "giriş yapılmış mı" diye sorar)
Yönetim (yalnızca müdür):
        GET    /api/kullanicilar            okulun hesapları
        POST   /api/kullanicilar            müdür yardımcısı ekler {ad, email, sifre}
        PUT    /api/kullanicilar/{id}/sifre yardımcının parolasını yeniden belirler (oturumları kapanır)
        DELETE /api/kullanicilar/{id}       yardımcıyı siler (oturumları da silinir)
Diğer bütün /api/... uçları: geçerli oturum yoksa 401.
```

İsteğin okulu: çerezdeki jeton → oturum → `okul_id`. `bagimliliklar.aktif_okul_id` artık başlığa
değil oturuma bakar. Okulun belirlendiği tek yer yine bu fonksiyondur (2. adımda böyle
tasarlanmıştı). Aşağıdaki katmanlar değişmez: servisler, depolar, ORM filtresi, RLS.

## 2. RLS altında e-postayla kullanıcı arama sorunu

**Sorun.** Girişte okul henüz bilinmez. `kullanici` tablosu RLS'ye tabidir: uygulama rolü
`app.okul_id` ayarı olmadan hiçbir satır görmez. Dolayısıyla "bu e-postanın kullanıcısı kim, hangi
okulda, parola özeti ne" sorusu sorulamaz. Aynı sorun oturum çözmede de vardır: çerezdeki jetonun
hangi okula ait olduğu, okul bilinmeden bulunmalıdır.

**Önerilen çözüm: dar kapsamlı `SECURITY DEFINER` fonksiyonlar ve onlara sahip, girişi olmayan
bir rol.**

- Yeni rol: `okul_giris`. Özellikleri:
  - `NOLOGIN`: kimse bu rolle bağlanamaz;
  - yalnızca `kullanici(id, okul_id, email, sifre_hash)` ve `oturum` üzerinde gereken en az
    yetki (SELECT; oturum için ayrıca son kullanım zamanını güncelleme);
  - bu iki tabloda yalnızca bu role tanımlı bir RLS politikası: `FOR SELECT TO okul_giris USING
    (true)`. Diğer roller için politika aynen kalır.
- İki fonksiyon. Sahipleri `okul_giris`, `SECURITY DEFINER` oldukları için sahiplerinin
  yetkisiyle çalışırlar:
  - `giris_bilgisi(email text) RETURNS TABLE (kullanici_id uuid, okul_id uuid, sifre_hash text)`:
    **tam eşleşen** tek e-postanın satırını döner, yoksa boş. Joker, liste, sayfalama yok:
    e-postayı bilmeyen kimseyi bulamaz.
  - `oturum_coz(jeton_ozeti text) RETURNS TABLE (oturum_id uuid, kullanici_id uuid, okul_id uuid)`:
    süresi geçmemiş oturumu döner, son kullanım zamanını ilerletir.
- Uygulama rolü (`okul_uygulama`) bu fonksiyonlara yalnızca `EXECUTE` yetkisi alır. Tablolara
  okul bağlamı dışında hâlâ erişemez.
- Güvenlik ayrıntıları:
  - `SET search_path = pg_catalog, public`: SECURITY DEFINER fonksiyonun bilinen açığı; çağıranın
    arama yoluna koyduğu sahte bir tablo ya da fonksiyon çağrılamasın;
  - `REVOKE EXECUTE ... FROM PUBLIC`: yalnızca uygulama rolü çağırabilsin.
- Fonksiyon okulu bulduktan sonra uygulama, normal yoldan (`okul_oturumu`, `SET LOCAL
  app.okul_id`, RLS) devam eder.

**Neden ayrı bir sahip rol?** `okul_sahip` bu imajda süper kullanıcıdır ve RLS'yi zaten atlar. Ama
üretimde tablo sahibi süper kullanıcı olmamalı. `FORCE ROW LEVEL SECURITY` açık olduğu için o
zaman sahibin fonksiyonu da hiçbir satır göremezdi. Ayrı ve dar yetkili `okul_giris` rolü, süper
kullanıcı olmadan da çalışır. Ayrıca fonksiyonun yapabildiklerini yetkilerle sınırlar: fonksiyonda
bir hata olsa bile `okul_giris` başka bir tabloya dokunamaz.

**Değerlendirilen alternatifler:**

| Seçenek | Neden seçilmedi |
|---|---|
| Giriş için ayrı bir veritabanı bağlantısı (RLS'yi atlayan, `LOGIN` yetkili bir rol) | API'de ikinci bir motor ve bağlantı havuzu gerekir. O bağlantı `kullanici` tablosunun tamamını okuyabilir: bir hata ya da SQL enjeksiyonu bütün parola özetlerini açığa çıkarır. Fonksiyonda ise yüzey tek bir e-posta sorgusudur. |
| Kimlik bilgilerini RLS dışındaki global bir `hesap` tablosuna taşımak | Uygulama rolü bütün e-postaları ve özetleri görebilir hale gelir. Kullanıcı iki tabloya bölünür. |
| Girişte okul kodu da istemek (e-posta + okul + parola) | Sorunu kullanıcıya yükler. Ayrıca e-posta bütün sistemde zaten tektir. |
| Parola doğrulamayı da veritabanında yapmak (pgcrypto `crypt`) | Özet veritabanından hiç çıkmazdı. Ama parola düz metin olarak SQL parametresiyle gider (sorgu günlüklerine düşebilir) ve argon2 yerine bcrypt'e bağlanılır. |

## 3. Önerilen kararlar (onayınız gerekiyor)

| # | Karar | Öneri | Alternatif ve neden seçilmedi |
|---|---|---|---|
| a | Oturum biçimi | **Sunucu taraflı oturum.** Rastgele jeton (32 bayt) bir `HttpOnly`, `SameSite=Strict` çerezde (üretimde `Secure`). Veritabanında jetonun kendisi değil SHA-256 özeti saklanır. | JWT: oturum sunucuda tutulmaz, ama çıkış ya da hesabı kapatma anında geçersiz kılınamaz (iptal listesi gerekir). `localStorage`'da tutulursa XSS ile çalınabilir. Tek API ve tek veritabanı olan bu sistemde JWT'nin getirisi yok. |
| b | Parola özeti | **argon2id** (`argon2-cffi`, kütüphanenin önerdiği parametreler). En az 10 karakter. | bcrypt: iyi ama 72 bayt sınırı var ve güncel öneri argon2id. |
| c | Oturum süresi | 12 saat hareketsizlik, en fazla 7 gün. Çıkışta oturum satırı silinir. | Sonsuz oturum: paylaşılan okul bilgisayarlarında risk. |
| d | CSRF (siteler arası istek sahteciliği) | `SameSite=Strict` çerez, ayrıca veri değiştiren isteklerde `Origin` başlığı denetimi. | CSRF jetonu (double-submit): aynı korumayı daha çok kodla verir. Arayüz ile API aynı sitede olacak (Vite proxy, yapım sırası 5). |
| e | E-posta | Küçük harfe çevrilip saklanır (CHECK `email = lower(email)`) ve **bütün sistemde** tektir: `lower(email)` üzerinde benzersiz indeks. Kayıtta ya da yardımcı eklerken e-posta başka bir okulda kullanılıyorsa anlaşılır hata (409). | Büyük/küçük harfe duyarlı: "Ayse@..." ile "ayse@..." iki ayrı hesap olurdu. Okul içinde benzersiz: giriş okul bilinmeden yapıldığı için hangi hesabın kastedildiği belirsiz kalırdı. |
| f | Bilgi sızdırmama | Yanlış e-posta ve yanlış parola aynı mesajı ve aynı süreyi alır: kullanıcı yoksa da sahte bir özet doğrulanır. | Ayrı mesajlar: hangi e-postaların kayıtlı olduğunu dışarıya söylerdi. |
| g | `POST /api/okullar` | **Kaldırılır,** yerini `POST /api/kayit` alır: okul, ilk yönetici ve oturum tek işlemde oluşur. | İkisini ayrı tutmak: sahipsiz okullar oluşabilirdi. |
| h | Worker | Değişmez. İş `okul_id` taşır; kuyruk iç ağdadır (Redis dışarı açık değil). İş, onu kuyruğa koyan oturumun okuluyla oluşturulur. | |

## 4. Açık soruların cevapları (2026-10-15)

1. **Kullanıcı yönetimi bu adımda, en küçük haliyle.**
   - Yalnızca müdür yardımcı ekler, siler ve parolasını yeniden belirler.
   - Müdür yardımcısı bu uçlara 403 alır, okulun geri kalan verisini müdür gibi düzenler
     (CLAUDE.md bölüm 2).
   - Müdür kendini silemez. Okulun tek müdürü vardır: kayıtta oluşur, API'den ikincisi
     eklenmez.
2. **Kaba kuvvet koruması bu adımda.**
   - E-posta başına: 15 dakikada 5 hatalı denemeden sonra o e-postaya 15 dakika giriş yok (429,
     "Çok fazla hatalı deneme, 15 dakika sonra yeniden deneyin").
   - Kayıtlı olan ve olmayan e-postalar aynı şekilde sayılır ve kilitlenir. Kilit mesajı bu yüzden
     e-postanın kayıtlı olup olmadığını söylemez.
   - Sayaç, okula ait olmayan `giris_denemesi` tablosundadır. Uygulama rolünün bu tabloya
     doğrudan yetkisi yoktur, yalnızca `okul_giris` rolünün fonksiyonlarıyla erişir (bölüm 2'deki
     yöntem).
   - **Bilinen ödünleşim (ADR 0012'ye yazılacak):** e-postaya göre kilitleme, birinin bir
     kullanıcının e-postasıyla bilerek yanlış deneyip onu 15 dakika dışarıda bırakmasına izin
     verir. IP'ye göre kilitleme bunu önlerdi, ama okulda bütün bilgisayarlar aynı dış IP'yi
     paylaşabilir ve vekil sunucu (proxy) arkasında gerçek IP güvenilir değildir.
3. **Parola sıfırlama e-postası kapsam dışı.** Müdür parolasını unutursa sistemi işleten kişi
   sunucuda bir komut çalıştırır:

   ```
   python -m okulapi parola-sifirla <email>
   ```

   - Yeni parola etkileşimli sorulur, iki kez, ekranda görünmez. İstenirse rastgele üretilip bir
     kez gösterilir.
   - Kullanıcının bütün oturumları kapanır, kaba kuvvet kilidi kaldırılır.
   - API'de karşılığı yoktur. Bunu bir test denetler: hiçbir uç bu işi yapmaz.
   - Docker'da: `docker compose exec api python -m okulapi parola-sifirla <email>`. README'ye
     yazılacak.

**Kayıt sırasında e-postanın kullanılıyor olması:** "Bu e-posta adresi başka bir hesapta
kullanılıyor" (409). Bu, kayıt formu üzerinden bir e-postanın sistemde kayıtlı olup olmadığını
öğrenmeye izin verir. Kullanıcının istediği anlaşılır hata için kabul edilen bir ödünleşimdir,
ADR 0012'ye yazılacak. Giriş tarafında aynı bilgi verilmez (karar f).

## 5. Değişiklikler

**Migration `cekirdek_0004`:**
- `kullanici.email`:
  - var olan e-postalar küçük harfe çevrilir;
  - `UNIQUE (email)` kaldırılır, yerine `lower(email)` üzerinde benzersiz indeks gelir;
  - CHECK `email = lower(email)`.
- `oturum` tablosu: id, okul_id, kullanici_id, jeton_ozeti (UNIQUE), olusturma, son_kullanim,
  bitis_mutlak. Bileşik yabancı anahtar `(okul_id, kullanici_id)`, okula ait (RLS). Kullanıcı
  silinince oturumları da silinir (CASCADE).
- `giris_denemesi` tablosu: email, zaman. Okula ait değildir; uygulama rolünün yetkisi yoktur.
- `okul_giris` rolü, politikalar ve yetkiler. Fonksiyonlar:
  - `giris_bilgisi`, `oturum_coz`;
  - `giris_kilitli_mi(email)`, `giris_hatasi_kaydet(email)`, `giris_denemelerini_sil(email)`.

**Çekirdek:** `okulapi/cekirdek/kimlik/` paketi:
- `parola.py`: argon2id;
- `servis.py`: `KimlikServisi` (kayit, giris, cikis, oturum_coz) ve `KullaniciServisi` (yardımcı
  ekle/sil, parola yeniden belirle);
- `api.py`: router;
- `bagimliliklar.py` değişir: `aktif_okul_id` oturumdan okur, `X-Okul-Id` kodu silinir.

`okulsuz_oturum` yalnızca kayıt ve giriş içindir.

**Komut satırı:** `okulapi/__main__.py`: `python -m okulapi parola-sifirla <email>`.

**Belgeler:**
- ADR 0012 (kimlik doğrulama: oturum çerezi, argon2id, CSRF);
- ADR 0009'a giriş araması bölümü (sonraki adım notunun yerine karar);
- diyagramlar 02/03 (kimlik paketi, oturum tablosu), 09 (`okul_giris` rolü);
- README (örnek akış artık kayıt ve giriş).

## 6. Testler

- **Kabul (CLAUDE.md):**
  - `X-Okul-Id` başlığı gönderilse bile yok sayılır: A'nın oturumu ve B'nin başlığıyla gelen
    istek A'nın verisini görür, B'ninkini görmez;
  - başlık tek başına hiçbir şey açmaz (401);
  - kaynak kodunda `X-Okul-Id` / `x_okul_id` geçmez (tarama testi);
  - oturumsuz istek, okula ait **her** uçta 401 alır. Liste uygulamanın router'larından otomatik
    çıkarılır; yeni bir uç eklenip korunmayı unutursa test kırılır.
- **RLS altında arama:**
  - uygulama rolü okul bağlamı olmadan `kullanici` ve `oturum` tablolarını hâlâ okuyamaz;
  - `giris_bilgisi` yalnızca tam eşleşen e-postayı döner;
  - joker (`%`), boş ya da büyük harfli girdiyle liste dönmez;
  - fonksiyonun `search_path`'i sabittir;
  - `PUBLIC`'in yetkisi yoktur;
  - `okul_giris` rolüyle bağlanılamaz.
- **Oturum:**
  - süresi geçen oturum 401 alır;
  - çıkıştan sonra aynı çerez 401 alır;
  - jeton veritabanında düz durmaz;
  - başka okulun oturumu o okulun verisine erişir, ötekine erişemez;
  - bağlantı havuzu taşma testleri oturumla da geçer.
- **E-posta benzersizliği:**
  - iki farklı okulda aynı e-posta (büyük/küçük harf farkıyla bile) kaydedilemez, 409 ve
    anlaşılır mesaj;
  - veritabanı düzeyinde de: servis atlanıp doğrudan eklense bile benzersiz indeks reddeder;
  - büyük harfli e-posta CHECK'e takılır.
- **Kaba kuvvet:**
  - 5 hatalı denemeden sonra doğru parola da 429 alır;
  - süre geçince açılır;
  - kayıtlı olmayan e-posta da aynı şekilde kilitlenir;
  - başarılı giriş sayacı sıfırlar;
  - uygulama rolü `giris_denemesi` tablosunu doğrudan okuyamaz ve yazamaz.
- **Kullanıcı yönetimi:**
  - müdür yardımcı ekler, siler ve parolasını yeniden belirler;
  - yeniden belirlenen parolada yardımcının eski oturumları kapanır;
  - yardımcı bu uçlara 403 alır;
  - başka okulun kullanıcısına 404.
- **Komut satırı aracı:**
  - parolayı değiştirir, oturumları kapatır, kilidi kaldırır;
  - bilinmeyen e-postada anlaşılır hata ve sıfırdan farklı çıkış kodu;
  - API'de karşılığı yoktur.
- **Giriş:**
  - yanlış e-posta ve yanlış parola aynı yanıtı alır;
  - e-posta büyük/küçük harf duyarsızdır;
  - parola özeti argon2id'dir;
  - kayıt tek işlemdir (yarıda kalırsa ne okul ne kullanıcı kalır).
- **Mevcut testler:** 31 yerde kullanılan `okul_basligi(okul_id)` yardımcısı, o okul için gerçek
  bir oturum açıp çerez döndüren bir yardımcıyla değiştirilir. Testlerin geri kalanı değişmez.
  Uçtan uca kabul testi kayıt ve girişle başlar.
- **Mutasyon denemesi:**
  - `aktif_okul_id` başlığa geri döner;
  - fonksiyonun `SECURITY DEFINER`'ı kaldırılır;
  - süre denetimi kaldırılır;
  - `SameSite` kaldırılır.

## 7. Alt adımlar

Her alt adım testler geçince commit edilir, onayınız olmadan sonrakine geçilmez.

1. **Şema ve veritabanı tarafı:**
   - migration `cekirdek_0004` (oturum, `okul_giris` rolü, fonksiyonlar, politikalar);
   - RLS altında arama testleri;
   - ADR 0012 ve ADR 0009 güncellemesi.
2. **Kimlik servisi:**
   - parola, kayıt, giriş, çıkış, oturum çözme, süre;
   - kaba kuvvet sayacı, kullanıcı yönetimi servisi;
   - `parola-sifirla` komutu;
   - servis testleri.
3. **API'ye bağlama:**
   - `aktif_okul_id` oturumdan okunur, `X-Okul-Id` silinir;
   - kayıt, giriş, çıkış, ben ve kullanıcı yönetimi uçları;
   - kaba kuvvet yanıtı (429);
   - mevcut testlerin geçişi;
   - CLAUDE.md kabul testleri.
4. **Belgeler ve uçtan uca:** uçtan uca kabul testi, diyagramlar, README.

**Durum:**

| # | Alt adım | Durum |
|---|---|---|
| 1 | Şema ve veritabanı tarafı | **Sıradaki** |
| 2 | Kimlik servisi | |
| 3 | API'ye bağlama | |
| 4 | Belgeler ve uçtan uca | |

## 8. Kapsam dışı (bu adımda)

- Öğretmen hesapları (CLAUDE.md: ilk sürümde yok). Öğretmen paylaşım linki yapım sırası 8'de.
- Parola sıfırlama e-postası, iki adımlı doğrulama, harici kimlik sağlayıcılar (Google ile
  giriş).
- Bir kullanıcının birden fazla okulda hesabı (e-posta bütün sistemde tektir).

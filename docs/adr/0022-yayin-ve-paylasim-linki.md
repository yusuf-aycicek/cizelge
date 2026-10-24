# ADR 0022: Yayın (dondurulmuş program) ve girişsiz paylaşım linkleri

Durum: Kabul edildi (2026-10-24, 8b).

## Bağlam

Yönetici bitmiş programı öğretmenlere ve şubelere duyurur. Öğretmenlerin hesabı yoktur (bölüm 2):
program bir linkle, girişsiz ve salt okunur görülmelidir. İki sorun var:

1. **Sessiz kayıp.** Ders ataması silinince yerleşimleri `ON DELETE CASCADE` ile silinir
   (api-plani bölüm 15, "Sonraya" 1). Paylaşılmış bir programdan bir ders bu yüzden kimse fark
   etmeden kaybolabilirdi.
2. **RLS altında girişsiz okuma.** Her tablo satır düzeyi güvenliğe tabidir; uygulama rolü
   `app.okul_id` olmadan hiçbir satır görmez. Linkle gelen istekte oturum yoktur, okul bilinmez.
   Okulu linkten bulup bağlamı açmak, o istekte okulun **bütün** verisini uygulama koduna açardı:
   kodda bir hata başka bir öğretmenin ya da okulun verisini sızdırabilirdi.

## Karar

### Yayın

1. **Yayın, çıktı modelinin dondurulmuş JSON'udur** (`yayin.icerik`, `cikti/anlik.py`): okul, program
   adı, hafta (gün adları, gün uzunlukları, öğle arası, zil saatleri) ve her şube ile öğretmenin
   hücreleri (ders adı, kısa ad, renk, şube adı, öğretmen adı). Atamaya, öğretmene, derse ya da
   yerleşime yabancı anahtarla bağlı değildir: onlar silinse de yayın değişmez. Taslak programlarda
   CASCADE aynen kalır (en az değişiklikle güncellemede "kaldırılmış ders" doğru işlenir, ADR 0006).
2. **Okul başına tek yayın** (`UNIQUE (okul_id)`); yeniden yayınlamak satırı günceller. Program
   silinince yayın kalır (`program_id` boşalır).
3. **Güncel olmama nedenleri** her okumada hesaplanır ve yöneticiye söylenir: programın üretildiği
   verinin özeti (`veri_ozeti`) şimdikinden farklıysa "eski verilerle üretildi"; programın şimdiki
   hücreleri yayınınkinden farklıysa (elle düzeltme, silinen atama, ad değişikliği) "yayından sonra
   değişiklik var"; program silindiyse o da. Yayın kendiliğinden değişmez; yönetici yeniden yayınlar.

### Paylaşım linki

4. **Kapsam:** bütün okul, tek öğretmen ya da tek şube (`paylasim_linki.tur`). Kapsam başına tek link
   (`UNIQUE NULLS NOT DISTINCT`). Öğretmen ya da şube silinince linki de silinir (CASCADE).
5. **Link yayına değil okula bağlıdır:** program yeniden yayınlanınca öğretmenin elindeki link aynı
   kalır, yeni programı gösterir. Yayın kaldırılırsa link "yayında program yok" der.
6. **Jeton:** `secrets.token_urlsafe(32)` (256 bit); tahmin edilemez, sayaç ya da hız sınırı
   gerekmez. İptal satırı siler; yenileme yeni jeton verir, eskisi o anda çalışmaz.
7. **Jeton düz saklanır** (oturum jetonu gibi özeti değil). Yönetici linki sonradan da kopyalayıp
   yeniden gönderebilmeli; yalnızca özet saklansaydı her seferinde yenilemek, öğretmenin elindeki
   linki bozmak gerekirdi. Linkin açtığı içerik (program) zaten aynı veritabanındadır; jetonu
   okuyabilen, içeriği de okuyabilir. Uygulama rolü jetonları yalnızca kendi okulunun bağlamında
   görür (RLS).
8. **Okuma tek bir dar `SECURITY DEFINER` fonksiyonuyla** (`paylasim_icerigi(jeton)`), giriş
   adımındaki yaklaşımla (ADR 0012):
   - sahibi `okul_paylasim` rolüdür: `NOLOGIN`, süper kullanıcı değil, BYPASSRLS yok; yalnızca
     `paylasim_linki` ve `yayin`'ın gereken sütunlarını okur, ikisinde yalnızca kendisine tanımlı
     birer okuma politikası vardır;
   - **süzme veritabanındadır:** öğretmen linki yalnızca o öğretmenin, şube linki yalnızca o şubenin
     çizelgesini döner; uygulama kodu başka bir şeyi istese de alamaz;
   - `SET search_path = pg_catalog, public`; `PUBLIC`'in çalıştırma yetkisi kaldırılır.
   API bu fonksiyonu **okulsuz** bir oturumla çağırır: istek boyunca hiçbir okul bağlamı açılmaz,
   bütün tablolar RLS ile kapalı kalır.
9. **Yanıtlar:** `Cache-Control: no-store`, `Referrer-Policy: no-referrer` (jeton adreste; başka
   siteye giden bağlantıda sızmasın), `X-Robots-Tag: noindex`. Geçersiz ve iptal edilmiş link aynı
   yanıtı alır (404): hangisi olduğu söylenmez.

## Değerlendirilen alternatifler

- **Yerleşimleri RESTRICT yapmak:** program üretilmiş bir atama bir daha silinemezdi.
- **Yayın için yerleşimlerin kopyası (ilişkisel):** atamaya bağlı kalır; ad ve renk yine canlı
  tablolardan gelir, öğretmen silinince yine eksilir. JSON anlık görüntü kendi kendine yeter.
- **Linkten okulu bulup bağlamı açmak:** basit ama istek boyunca okulun bütün verisi açık olur.
  Kapsam süzmesi uygulama koduna kalır; tek bir eksik `where` sızıntıdır.
- **İmzalı (HMAC) link, tabloya gerek yok:** iptal için yine bir liste gerekir; anahtar yönetimi
  eklenir.

## Sonuçları

- Yayınlanan program, veriler değişse ya da silinse de aynı kalır; yönetici neden güncel olmadığını
  görür. Bu, api-plani "Sonraya" 1'i kapatır (testle: atama, öğretmen silinir; yayın aynı).
- Paylaşım sayfası ve PDF'i yayının içeriğinden, yönetici çıktısıyla aynı kodla üretilir.
- Bütün okul linki öğretmen adlarını da gösterir; yönetici bunu bilerek paylaşır.

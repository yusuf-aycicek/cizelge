# ADR 0009: Okul izolasyonu: oturuma bağlı ORM filtresi, bileşik yabancı anahtar, RLS

Durum: Kabul edildi ve uygulandı (2026-10-14): ORM katmanı 2. alt adımda, bileşik yabancı
anahtarlar 3. alt adımda, RLS 4. alt adımda.

## Bağlam

Sistem çok okulludur. Okulların verisi aynı tablolarda, satır düzeyinde ayrılır (CLAUDE.md mimari
karar 5). Bir okulun başka bir okulun verisini görmesi, değiştirmesi ya da ona bağlanması en ağır
hata türüdür ve 2. yapım adımının kabul kriteridir. Filtre tek bir yerde uygulanmalı: endpoint
yazan kişinin unutabileceği bir şey olmamalı.

## Karar

Üç katman (derinlemesine savunma):

1. **Oturuma bağlı okul bağlamı.** Her HTTP isteği, tek bir okula bağlı bir veritabanı oturumu
   (Session) kullanır: `oturum.info["okul_id"]`. Okul, 4. yapım adımına kadar geçici `X-Okul-Id`
   başlığından, sonra yalnızca oturumdan (token) belirlenir. Bunun yapıldığı tek yer
   `bagimliliklar.aktif_okul_id`'dir.
2. **ORM otomatik filtresi** (`cekirdek/kiraci.py`, asıl mekanizma). SQLAlchemy olaylarıyla:
   - okula ait tablolara dokunan her ORM SELECT/UPDATE/DELETE'e `okul_id = <oturumun okulu>`
     koşulu eklenir (`with_loader_criteria`). Okula aitlik hem sorgunun ORM varlıklarından hem de
     FROM'daki tablolardan belirlenir;
   - yeni kayda `okul_id` otomatik yazılır. Başka okulun okul_id'siyle eklemek ya da kaydın okulunu
     değiştirmek hata verir;
   - okul bağlamı olmayan oturumla okula ait tabloya erişmek hata verir (sessizce boş sonuç değil).
3. **Veritabanı güvenceleri.**
   - Okula ait her tabloda `UNIQUE (okul_id, id)`. Diğer tablolar ona bileşik yabancı anahtarla
     `(okul_id, x_id) → x(okul_id, id)` bağlanır. Böylece veritabanı okullar arası ilişkiyi
     kendisi reddeder (modül tablolarında, 3. alt adım).
   - PostgreSQL satır düzeyi güvenliği (RLS), 4. alt adım. Her okula ait tabloda
     `okul_id = current_setting('app.okul_id')::uuid` politikası olur. Okul ayarı işlem başında
     `SET LOCAL` ile verilir; işlem bitince PostgreSQL ayarı kendisi siler. Böylece havuzdaki bir
     bağlantı sonraki isteğe başka okulun ayarıyla geçemez (bu ayrıca test edilecek). Uygulama,
     tabloların sahibi olmayan ayrı bir rolle bağlanır, çünkü tablo sahibi RLS'yi atlar.

Başka bir okulun kaydına erişim denemesi 404 döner, 403 değil: kaydın var olduğu bile sızmasın.

## Değerlendirilen alternatifler

- **Okul başına şema** (her okula ayrı PostgreSQL şeması) ya da **okul başına veritabanı:**
  İzolasyon çok güçlüdür. Ama her yeni okulda migration'ların her şemaya ayrı ayrı uygulanması
  gerekir; okul sayısı arttıkça bakım ve bağlantı sayısı büyür. Bu ölçek (onlarca, belki yüzlerce
  okul) için satır düzeyi yeterlidir ve CLAUDE.md'de karar zaten satır düzeyidir.
- **Depoda elle filtre** (her sorguya `where(okul_id == ...)` yazmak): basittir, ama unutulabilir.
  Kararın "tek yerde" şartını karşılamaz.
- **Yalnızca RLS:** Veritabanı düzeyinde güçlüdür. Ama hatalar geç ve anlaşılması zor biçimde
  ortaya çıkar (boş sonuç). Yeni kayıtlara okul_id yazmak yine uygulamanın işidir. ORM katmanı
  hataları erken ve açık verir; RLS ikinci güvencedir.
- **Okul bağlamını `ContextVar` ile taşımak:** İlk plan buydu. FastAPI senkron bağımlılıkları ayrı
  bir iş parçacığında bağlam kopyasıyla çalıştırdığı için bağımlılıkta yazılan değer endpoint'e
  ulaşmayabilir. Oturuma bağlamak hem bu sorunu çözer hem de iş birimi (unit of work) ile okul
  sınırını aynı nesnede toplar.

## Sonuçlar

- Servis ve endpoint kodu okul filtresini hiç yazmaz. Testler (`test_kiraci.py`) sayım,
  `select_from`, alt sorgu ve birleştirme dahil 6 sorgu biçiminde, toplu güncelleme ve silmede
  filtrenin uygulandığını denetler. İlk sürümdeki `all_mappers`'a dayalı tespit,
  `select(func.count()).select_from(Model)` sorgusunda filtreyi atlıyordu; bu açık testle
  yakalandı ve düzeltildi.
- Ham SQL (`text(...)`) ve Core tablo nesneleri (`Model.__table__`) ORM filtresinden geçmez.
  Uygulama kodunda ikisi de bir kaynak kod tarama testiyle yasaktır (izinli yerler: sağlık
  kontrolündeki `SELECT 1` ve `kiraci.py`'deki `SET LOCAL`). RLS geldiğinden beri veritabanı onları
  da filtreler; ilgili test tersine döndü (A yalnızca kendi satırlarını görür).
- Bir oturum yalnızca tek bir okula aittir. Birden çok okulu birlikte işleyen işlemler (ör. sistem
  yöneticisi raporları) ileride gerekirse açık ve ayrı bir yolla yapılmalıdır.

## Uygulama ayrıntıları (RLS, 4. alt adım)

- **Roller:** `okul_sahip` tabloların sahibidir ve migration'ları çalıştırır (Docker imajında süper
  kullanıcıdır, RLS'yi her zaman atlar). Uygulama `okul_uygulama` rolüyle bağlanır: süper kullanıcı
  değil, tablo sahibi değil, `BYPASSRLS` yetkisi yok; yalnızca tablo yetkileri (GRANT) var. Rol ve
  parolası altyapıda oluşturulur (`docker/postgres/init/01-uygulama-rolu.sh`); yetkiler ve
  politikalar migration'larla verilir. Ayarlar iki adres tutar: `veritabani_url` (uygulama),
  `migrasyon_url` (sahip).
- **Politika:** okula ait her tabloda `USING (okul_id = aktif_okul_id()) WITH CHECK (okul_id =
  aktif_okul_id())`; okul tablosunda `id = aktif_okul_id()`. `aktif_okul_id()` =
  `nullif(current_setting('app.okul_id', true), '')::uuid`: ayar yoksa ya da boşsa NULL döner ve hiçbir
  satır geçmez (güvenli tarafta kalarak reddetme). `FORCE ROW LEVEL SECURITY` tablo sahibini de
  politikaya tabi kılar.
- **Modülerlik:** her dal kendi tablolarının politikalarını getirir (`cekirdek_0003`,
  `ders_programi_0003`, `depends_on = cekirdek_0003`). Bu migration'lar uygulama kodunu içe
  aktarmaz (uygulanmış migration değişmemeli).
- **Okul bağlamının veritabanına bildirilmesi:** `kiraci._veritabanina_okulu_bildir` (SQLAlchemy
  `after_begin`), her işlemin başında `set_config('app.okul_id', <okul ya da ''>, true)` çalıştırır.
  `true` = `SET LOCAL`: işlem bitince ayar silinir, bağlantı havuza temiz döner. Okulsuz oturumda da
  açıkça boş değer yazılır; önceki değere hiç güvenilmez.
- **Okul oluşturma:** okulsuz oturum hiçbir okulu göremez ve ekleyemez. `OkulServisi.olustur` yeni
  okulun kimliğini istemci tarafında üretir ve işlemin bağlamına yazar (`INSERT ... RETURNING` de
  SELECT politikasından geçmek zorundadır).
- **Kanıtlar** (`tests/test_izolasyon.py`, kabul testi): okula ait bütün tablolar `Base.metadata`'dan
  otomatik bulunur; her tablo için ORM ve ham SQL okuma, başka okulun satırına UPDATE/DELETE (0
  satır), kendi satırını başka okula taşıma (`42501` RLS ihlali), okulsuz bağlam (0 satır) ve tablo
  sahibinin ikisini de gördüğü (filtrenin RLS'den geldiği) denetlenir. API'de her listeleme ve tek
  kayıt endpoint'i denetlenir.
- **Bağlantı havuzu:** havuz tek bağlantıyla sınırlanır, art arda A, B, okulsuz, A, okulsuz, B
  istekleri aynı fiziksel bağlantıda (aynı `pg_backend_pid()`) çalışır; her biri yalnızca kendi
  okulunu görür. İstekler bittikten sonra aynı bağlantıda, işlem dışında ayar boştur. Hatayla biten
  istekten sonra da taşma yoktur. Karşı örnek: bağlantı düzeyinde `SET` (`set_config(..., false)`)
  commit edilen bir işlemden sonra bağlantıda kalır ve bir sonraki kullanıcıya taşar.
- **Mutasyon denemesi:** `SET LOCAL` bilerek `SET` yapıldığında havuz testinin ilk sürümü bunu
  yakalayamadı, çünkü testteki istekler yalnızca okuyup geri alınıyordu (geri alınan işlemdeki SET
  de geri alınır). İstekler servisler gibi commit edecek şekilde düzeltildi; mutasyon artık
  yakalanıyor. Ayarın hiç bildirilmemesi mutasyonu da yakalanıyor.

## Okul bilinmeden arama: giriş ve oturum çözme (yapım sırası 4, 2026-10-15)

Girişte kullanıcı e-postasıyla, okul bilinmeden aranır. Her istekte oturum, okul bilinmeden
çerezdeki jetondan çözülür. RLS ikisini de engeller: okulsuz bağlamda `kullanici` ve `oturum`
tabloları boş görünür.

**Karar:** dar kapsamlı `SECURITY DEFINER` fonksiyonlar (`giris_bilgisi`, `oturum_coz` ve kaba
kuvvet sayacı fonksiyonları, migration `cekirdek_0004`). Sahipleri girişi olmayan (`NOLOGIN`), süper
kullanıcı olmayan, RLS'yi atlayamayan `okul_giris` rolüdür:
- yalnızca gereken sütunlarda yetkisi vardır;
- `kullanici` ve `oturum` tablolarında yalnızca bu role tanımlı birer politika vardır;
- fonksiyonların arama yolu sabittir, `PUBLIC` çağıramaz.

Uygulama rolü bu fonksiyonları çağırabilir ama tablolara okul bağlamı dışında hâlâ erişemez.
Fonksiyon okulu bulduktan sonra istek normal yoldan devam eder: `okul_oturumu`, `SET LOCAL`, RLS.
Gerekçe ve değerlendirilen alternatifler: ADR 0012 ve `docs/kimlik-plani.md` bölüm 2.

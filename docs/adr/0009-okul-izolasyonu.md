# ADR 0009: Okul izolasyonu: oturuma bağlı ORM filtresi, bileşik yabancı anahtar, RLS

Durum: Kabul edildi (2026-10-14). ORM katmanı ve bileşik anahtar altyapısı 2. alt adımda; RLS
4. alt adımda.

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
- **Bilinen sınır:** ham SQL (`text(...)`) ve Core tablo nesneleri (`Model.__table__`) ORM
  filtresinden geçmez. Uygulama kodunda ikisi de bir kaynak kod tarama testiyle yasaktır (izin
  verilen tek yer sağlık kontrolündeki `SELECT 1`); veritabanı düzeyinde RLS ile kapanır (4. alt
  adım). İlgili test, RLS geldiğinde beklentisi tersine dönecek biçimde yazılmıştır.
- Bir oturum yalnızca tek bir okula aittir. Birden çok okulu birlikte işleyen işlemler (ör. sistem
  yöneticisi raporları) ileride gerekirse açık ve ayrı bir yolla yapılmalıdır.

# ADR 0010: Migration stratejisi: modül başına Alembic dalı

Durum: Kabul edildi (2026-10-14)

## Bağlam

Veritabanı şeması Alembic migration'larıyla yönetilir (CLAUDE.md bölüm 5). Modüler yapıda
(ADR 0008) her modülün tabloları o modüle aittir. Yeni bir modül eklemek, çekirdeğin migration
geçmişini değiştirmeyi gerektirmemelidir. Ama modül tabloları çekirdek tablolarına yabancı
anahtarla bağlandığı için uygulanma sırası garanti edilmelidir: `ders_atama` tablosu `ogretmen`
tablosundan önce oluşamaz.

## Karar

- Her modülün (ve çekirdeğin) kendi `migrations/` klasörü ve kendi Alembic **dalı** vardır. Dalın
  kök revizyonu `branch_labels=("<modül adı>",)` taşır (`cekirdek`, `ders_programi`).
- Modül dalının kök revizyonu `depends_on = "cekirdek_0001"` der. Alembic, bir revizyonu
  uygulamadan önce `depends_on`'daki revizyonları da uygular. Sıra böyle garanti edilir. Modülün
  sonraki bir migration'ı çekirdeğin daha yeni bir tablosuna ihtiyaç duyarsa, o migration da
  ilgili çekirdek revizyonuna `depends_on` ile bağlanır.
- Sürüm klasörleri (`version_locations`) elle yazılmaz, etkin modül listesinden toplanır.
  `alembic.ini` yerine `python -m okulapi.migrasyon <komut>` sarmalayıcısı kullanılır.
- `upgrade heads` bütün dalları yükseltir. `alembic_version` tablosu dal başına değil,
  birbirini kapsamayan uç revizyon başına bir satır tutar. `depends_on` da "kapsama" sayılır:
  `ders_programi_0001` uygulandığında Alembic `cekirdek_0001` satırını günceller
  (`UPDATE ... SET version_num='ders_programi_0001'`) ve tabloda tek satır kalır. Hangi
  revizyonların uygulandığını anlamak için tablodaki uçlardan atalar ve bağımlılıklar boyunca
  geriye yürünür (testlerde `_uygulanmis_revizyonlar`).
- Migration'lar `--autogenerate` ile taslak olarak üretilir, ama elle gözden geçirilir.
  Uygulanmış bir migration değiştirilmez, düzeltme için yenisi yazılır. Her migration'ın
  `downgrade`'i yazılır.
- Test veritabanı her test oturumunda migration'larla kurulur. Testler ayrıca şunları denetler:
  her modülün tek bir kök revizyonu olduğu, kökün etiketinin modül adı olduğu, kökün çekirdeğe
  bağımlı olduğu, yalnızca modül dalı istense bile çekirdeğin önce uygulandığı ve
  upgrade → downgrade → upgrade'in çalıştığı.

## Değerlendirilen alternatifler

- **Tek doğrusal geçmiş:** Basittir, `alembic history` tek bir zincirdir. Ama her modülün
  migration'ları aynı zincire karışır; bir modülü kapatmak ya da yeni bir modül eklemek ortak
  zinciri değiştirir. İki geliştirici aynı anda farklı modüllerde migration yazarsa birleştirme
  (merge) revizyonu gerekir.
- **`Base.metadata.create_all`:** migration yoktur, tablolar uygulama açılışında oluşur. Var olan
  tabloları değiştiremez (sütun ekleme, tür değiştirme), veri taşıyamaz, geri alınamaz. Üretim
  için uygun değildir.
- **Modül başına ayrı `alembic_version` tablosu ve ayrı ortam:** modüller tamamen bağımsız olur,
  ama çekirdekle aradaki sıra garantisi kaybolur ve elle yönetilmesi gerekir.

## Sonuçlar

- Yeni bir modül için yapılacaklar: `okulapi/moduller/<ad>/migrations/` klasörünü açmak, ilk
  revizyonunu `branch_labels=("<ad>",)` ve `depends_on=("cekirdek_0001",)` ile yazmak (ya da
  `python -m okulapi.migrasyon revision -m "..." --head base --branch-label <ad> --depends-on
  cekirdek_0001 --version-path src/okulapi/moduller/<ad>/migrations`), modülü `etkin_moduller`'e
  eklemek. Testler bu kuralları otomatik denetler.
- Yeni bir migration'ı doğru dala eklemek için `--head <dal>@head` ve `--version-path` verilmelidir.
  Bu, tek doğrusal geçmişe göre biraz daha fazla dikkat ister.
- `alembic history` dalları ayrı ayrı gösterir. Ders sunumunda modül sınırlarının veritabanında da
  sürdüğünün somut bir örneğidir.

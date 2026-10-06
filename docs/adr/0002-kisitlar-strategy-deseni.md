# ADR 0002: Kısıtların strategy deseniyle modellenmesi

Durum: Kabul edildi (2026-10-06)

## Bağlam

Kural listesi sabit değildir. Okul müdüründen gelecek cevaplara göre yeni kurallar eklenecektir
(boş gün talebi, blok ders, başka okulda görevli öğretmen gibi). Okullar kuralları açıp
kapatabilmeli, esnek kuralların ağırlığını değiştirebilmelidir. Tüm kurallar tek bir büyük
fonksiyonda olursa her yeni kural, mevcut ve test edilmiş kodu değiştirmeyi gerektirir.

## Karar

- Her kural, `KisitKurali` taban sınıfından türeyen ayrı bir sınıftır ve tek metodu vardır:
  `uygula(baglam)`. `baglam` CP-SAT modelini, `x[atama, gun, saat]` değişkenlerini ve
  girdiye hızlı erişim için hazırlanmış dizinleri taşır.
- Zorunlu kurallar modele kısıt ekler. Esnek kurallar ceza ifadeleri döndürür. `CpSatCozucu`
  bunları ağırlıklarıyla toplar ve toplamı en aza indirir.
- Bir kayıt defteri `tur` adını sınıfa eşler (ör. `"gunluk_ders_siniri"` → `GunlukDersSiniri`).
  Veritabanındaki `kisit` satırı (tur, parametreler, zorunlu, agirlik) bu yolla bir sınıf
  örneğine dönüşür.
- Programın anlamını oluşturan temel kurallar (haftalık saat, sınıf ve öğretmen çakışması,
  gelemez, kilitli hücre) her zaman uygulanır ve kapatılamaz. Okul geneli kurallar varsayılan
  parametrelerle eklenir. `kisit` tablosu bunları geçersiz kılar.

## Değerlendirilen alternatifler

- **Tek fonksiyon, if/else ile kural seçimi:** Başta basittir ama her kural mevcut kodu değiştirir.
  Kurallar ayrı ayrı test edilemez.
- **Kuralları veri olarak tanımlayan bir DSL:** Esnektir ama bu ölçekte gereksiz karmaşıklık getirir.
  Pencere gibi kurallar yardımcı değişken ister ve bir DSL ile ifade etmek zordur.

## Sonuçlar

- Yeni kural eklemek için yeni bir sınıf ve bir kayıt satırı yeterlidir. Mevcut kod değişmez
  (açık/kapalı prensibi).
- Her kural küçük bir senaryoyla tek başına test edilir.
- Kurallar aynı `baglam` üzerinde çalıştığı için yardımcı değişkenler (ör. "öğretmen o saatte
  meşgul mü") bağlamda bir kez oluşturulur ve paylaşılır.

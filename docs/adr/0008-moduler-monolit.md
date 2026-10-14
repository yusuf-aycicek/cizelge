# ADR 0008: API modüler bir monolittir: çekirdek + modüller

Durum: Kabul edildi (2026-10-14)

## Bağlam

İlk özellik ders programıdır, ama okula ileride başka modüller (ders notları ve dosya paylaşımı,
kütüphane) eklenebilir. Bunların hepsi aynı temel varlıklara ihtiyaç duyar: okul, kullanıcı,
öğretmen, sınıf, ders. Yeni bir modül eklemek mevcut, test edilmiş çekirdeği değiştirmeyi
gerektirmemelidir (açık/kapalı prensibi; CLAUDE.md mimari karar 4'ün sistem düzeyindeki karşılığı).
Proje bir yazılım mimarisi dersinde sunulacağı için paketler arası bağımlılıkların class
diyagramında açıkça görülebilmesi de istenir.

## Karar

- API tek süreçtir, tek dağıtım birimidir. İçeride `okulapi.cekirdek` ve `okulapi.moduller.<ad>`
  paketleri vardır.
- Bağımlılık kuralları:
  - **modül → çekirdek:** serbest (yabancı anahtar, depo, kiracı bağlamı, modül sözleşmesi);
  - **çekirdek → modül:** yasak;
  - **modül → modül:** yasak. Ortak ihtiyaç çekirdeğe taşınır.
  İki kural da testle denetlenir: kaynak kod `ast` ile taranır, yasak bir içe aktarma bulunursa
  test kırılır.
- Modül sözleşmesi `Modul(ad, onek, router, migration_dizini, modeller)`. Modül bunu kendi
  paketinde `MODUL` adıyla tanımlar. Çekirdek modülleri adlarıyla yükler (`importlib`), hiçbirini
  doğrudan içe aktarmaz. Etkin modüller ayardadır (`OKULAPI_ETKIN_MODULLER`).
- Her modülün API yolları `/api/<onek>/...` altındadır ve kendi Alembic dalı vardır (ADR 0010).
- Bütün modeller tek bir `Base.metadata`'yı paylaşır. Böylece modül tabloları çekirdek tablolarına
  yabancı anahtarla bağlanabilir ve izolasyon testi bütün tabloları tek yerden dolaşabilir.

## Değerlendirilen alternatifler

- **Tek paket (modülsüz):** Başta en basit yol. Ama ders programına özgü kod çekirdeğe karışır ve
  ikinci modül eklenirken çekirdek yeniden düzenlenmek zorunda kalır.
- **Mikro servisler** (çekirdek ve her modül ayrı servis): bağımsız dağıtım ve ölçekleme sağlar.
  Ama okul izolasyonu, kimlik doğrulama ve yabancı anahtar bütünlüğü servis sınırları arasında
  dağıtık hale gelir; tek bir okul müdürünün kullanacağı bu ölçek için gereksiz karmaşıklık.
  Modüler monolit, ihtiyaç doğarsa bir modülün servise ayrılmasını kolaylaştıracak sınırları
  şimdiden çizer.
- **Eklenti sistemi (entry points):** modüller ayrı paketler olarak kurulur ve kendilerini
  kaydeder. Gereğinden esnek; aynı depoda geliştirildikleri için ad listesi yeterli.

## Sonuçlar

- Yeni modül eklemek: `okulapi/moduller/<ad>/` paketini sözleşmeye uygun yazmak, kendi migration
  dalını açmak (ADR 0010) ve adını `etkin_moduller` listesine eklemek. Çekirdekte değişiklik yoktur.
- Modül sözleşmesi ilk sürümünde küçük tutuldu. Modüller çoğaldıkça ihtiyaç duyulursa (ör. silme
  engeli mesajları, olaylar) genişletilir; bu, sözleşmenin kendisinin değişmesi demektir ve dikkat
  ister.
- Paket sınırları class diyagramındaki paketlerle birebir aynıdır.

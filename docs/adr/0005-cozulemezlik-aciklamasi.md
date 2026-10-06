# ADR 0005: Çözülemezlik açıklaması: ön kontrol ve en küçük çelişen kural kümesi

Durum: Kabul edildi (2026-10-06)

## Bağlam

Okul yöneticisi çoğu zaman çözümü olmayan bir veri girer: öğretmenin yükü müsait saatlerinden
fazladır, kilitler birbiriyle çelişir, iki öğretmen aynı dar zaman aralığına sıkışır. CP-SAT
yalnızca "çözüm yok" der. Yönetici neyi değiştireceğini bilmezse sistem kullanılamaz. Hedef,
nedeni kullanıcının diliyle söylemektir: "Ayşe Yılmaz'ın 24 saat dersi var, müsait olduğu 20
saat var."

## Karar

İki katman:

1. **Ön kontrol** (`on_kontrol.py`). Çözücüden önce çalışan, hızlı ve kesin hesaplar: veri
   tutarlılığı, öğretmensiz atama, sınıf ve öğretmen kapasitesi, dersin gün kapasitesi, kilit
   çelişkileri. Bulunan bütün sorunlar birlikte döner. Durum `on_kontrol_hatasi` olur.
2. **Çelişki analizi** (`celiski.py`). Ön kontrolden geçen ama çözümsüz girdiler için:
   - Zorunlu kısıtlar anlamlı gruplara bağlanır: atamanın haftalık saati, öğretmenin gelemez
     saatleri, tek bir kilit, (sınıf, ders) günlük sınırı, öğretmen günlük sınırı. Kurallar
     kısıtlarını `baglam.grupla(...)` ile etiketler. Analiz kural mantığını kopyalamaz.
   - CP-SAT'ın varsayım çekirdeği bir aday küme verir. Küme, gruplar teker teker çıkarılarak
     en küçük hale getirilir. Sonuç Türkçe maddeler olarak döner (`Celiski`, durum `cozumsuz`).
   - Küçültme denemelerinde grup literalleri varsayım olarak değil sabit olarak verilir (aşağıya
     bakın).
- Sonuç yapılandırılmıştır: `CozumSonucu.celiskiler` her sorun için tür, mesaj ve ilgili
  kimlikleri taşır. Arayüz ilgili satır ve hücreleri vurgulayabilir.
- Çakışma kuralları gruplanmaz. Bunlar programın tanımıdır, gevşetilecek bir kural değildir.

## Değerlendirilen alternatifler

- **Yalnızca ön kontrol.** Basit ve hızlıdır, ama birden fazla kuralın etkileşiminden doğan
  çelişkileri (iki öğretmen aynı dar aralıkta, kilit + gelemez zinciri) yakalayamaz. Kullanıcı
  "çözüm yok" mesajıyla baş başa kalır.
- **Zorunlu kısıtları çok büyük cezalı esnek kısıtlara çevirmek ("en az ihlalli program").**
  Kullanıcıya her zaman bir program ve ihlal listesi verir. Ama hangi kısıtın ihlal edileceğini
  ağırlıklar keyfi olarak belirler ("Ayşe'nin gelemez saati" mi, "haftalık saat" mi?). Ayrıca
  model büyür. Sonuç "neden çözüm yok" sorusuna değil, "en ucuz ihlal hangisi" sorusuna cevap
  olur. İleride "bu kuralı gevşetirsem ne olur" özelliği için düşünülebilir.
- **Yalnızca varsayım çekirdeği (küçültme olmadan).** Hızlıdır, ama çekirdek en küçük değildir.
  Mini sette 7 gerekli kuralın yanında gereksiz maddeler de içeriyordu ve kullanıcıyı yanlış
  yere yönlendirir.
- **Küçültmede de varsayım kullanmak.** İlk gerçekleme buydu. Varsayımlar CP-SAT'ın ön
  işlemesine görünmez. Kısıtlar koşullu kalır, gevşek model zayıflar ve basit bir sayma
  argümanının kanıtı uzar: mini sette deneme başına 4,4 sn, toplamda 30 sn'lik bütçe doldu.
  Literalleri sabit olarak verip modeli yeniden kurmak deneme başına 0,07 sn'ye indirdi.

## Sonuçlar

- Yönetici çoğu hatayı ön kontrolden anında ve kesin bir mesajla alır.
- Çelişki analizi en kötü durumda aday grup sayısı kadar çözüm denemesi yapar. Bu yüzden ayrı
  bir süre bütçesi vardır (`CELISKI_ANALIZ_SURESI_SN`, en fazla 30 sn). Süre dolarsa o ana kadarki
  küme raporlanır. Bu küme doğrudur ama en küçük olmayabilir. Büyük setlerdeki süre 6. alt adımda
  ölçülecek.
- Yeni bir zorunlu kural eklenirken kısıtları `grupla` ile etiketlenmeli ve `_anlat`'a bir cümle
  kalıbı eklenmelidir. Etiketlenmeyen kısıt her zaman açık sayılır, analiz yine çalışır ama o kuralı
  suçlayamaz.

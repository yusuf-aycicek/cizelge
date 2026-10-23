# ADR 0014: Çekirdekten modüle kancalar: okul ayarı değişikliği ve silinemeyen kayıtlar

Durum: Kabul edildi (2026-10-16).

## Bağlam

Çekirdek modülleri bilmez (ADR 0008). Ama iki çekirdek işi modül verisini etkiliyor:

1. **Okulun gün/saat ayarının azaltılması.** Okul çekirdektedir; müsaitlik ve programlar ders
   programı modülündedir. Önceki davranışta API azaltmayı sessizce kabul ediyordu. Aralık dışında
   kalan müsaitlik kayıtları yerinde kalıyor, sorun ancak bir sonraki program üretiminde ön
   kontrol hatası olarak ("müsaitlik okulun aralığı dışında") ortaya çıkıyordu. Kullanıcıdan
   ayarı değiştirmeden önce sonucunu bilmesi istendi.
2. **Kullanımda olan öğretmen, sınıf ya da dersin silinmesi.** Veritabanı silmeyi reddeder
   (yabancı anahtar, RESTRICT). Ama çekirdeğin tek söyleyebildiği "Bu kayıt başka kayıtlar
   tarafından kullanılıyor, silinemez" idi: nerede kullanıldığı ve ne yapılacağı söylenmiyordu.

## Karar

**Modül sözleşmesine (`Modul`) isteğe bağlı kancalar eklenir.** Çekirdek, yüklü modüllerin
listesini (uygulamanın durumunda) dolaşır ve kancası olana sorar. Modülü içe aktarmaz; bağımlılık
yönü değişmez: modül → çekirdek. Kancası olmayan modül etkilenmez.

- `okul_ayari_etkisi(oturum, gun_saatleri, uygula) -> list[str]`: bu ayara geçilirse modül
  verisine ne olur, kullanıcının diliyle. `uygula=True` ise yapar. `gun_saatleri` her gün için
  yeni ders saati sayısıdır (K3'te günlere göre ders saati gelince `gun_sayisi,
  gunluk_ders_saati` çiftinin yerini aldı; uzunluğu gün sayısıdır). Bir günü kısaltmak da (ör.
  cuma 8 → 5) aynı akıştan geçer.
- `kullanim_aciklamasi(oturum, tablo, kayit_id) -> list[str]`: bu çekirdek kaydı modülde
  nerede kullanılıyor ve ne yapılmalı, kullanıcının diliyle.

**Ders programı modülünün cevapları:**
- Gün/saat azalınca aralık dışında kalan **müsaitlik kayıtları silinir**: artık var olmayan bir
  saat için "gelemez" anlamsızdır.
- **Programlar değişmez**: eski ayarlarla üretilmiş birer kayıttır. Kullanıcıya hangi programlarda
  kaç ders saatinin aralık dışında kaldığı ve programın yeniden üretilmesi gerektiği söylenir.
- Silinemeyen kayıt için mesaj: "Ayşe Yılmaz silinemez: 2 derste öğretmen olarak seçili (9-A
  Matematik, 9-B Matematik). Önce Ders dağılımı sayfasında bu derslere başka bir öğretmen
  seçin." En fazla beş örnek, fazlası "ve N tane daha".

**Okul ayarı değişikliği açık onay ister:**
- `POST /api/okul/ayar-etkisi` önizlemedir, hiçbir şeyi değiştirmez.
- `PATCH /api/okul` etkisi olan bir değişikliği yalnızca `etkileri_onayla: true` ile yapar. Onay
  yoksa 409 döner, yanıtta `etkiler` listesi vardır. Onaylanırsa ayar ve etkileri tek işlemde
  kaydedilir.
- Arayüz önce önizler, etkileri bir onay penceresinde listeler, ancak onaydan sonra kaydeder.
  Önizleme ile kayıt arasında veri değişirse sunucunun 409'u aynı pencereyi açar.
- API'nin kendisi de korur: arayüzü kullanmayan bir istemci de onaysız veri kaybına yol açamaz.

## Değerlendirilen alternatifler

- **Azaltmayı reddetmek** (önce kayıtları elle silin): kullanıcı onlarca müsaitlik kaydını tek
  tek silmek zorunda kalırdı; sonuç aynı.
- **Sessizce silmek:** kullanıcı veri kaybettiğini bilmezdi.
- **Kayıtları bırakıp üretimde yok saymak:** kullanıcı artık var olmayan saatler için kayıtlar
  görmeye devam ederdi; hata ancak sonra ortaya çıkardı (önceki davranışın sorunu).
- **Çekirdeğin modül tablolarını doğrudan sorgulaması:** ADR 0008'i bozar; her yeni modül
  çekirdeği değiştirmeyi gerektirirdi.
- **Olay yayını (event bus):** aynı ayrıştırmayı sağlar, ama iki kanca için gereksiz bir altyapı.
  Kanca sayısı artarsa yeniden değerlendirilir.

## Sonuçlar

- Çekirdek, modül olmadan da çalışır: kanca yoksa genel mesaj döner (testle denetlenir).
- Programlar eski ayarlarla kalır. Yapım sırası 8'deki "eski veriyle üretildi" uyarısı (girdi
  özeti) bu durumu da kapsayacak.
- Yeni bir modül, kendi verisi etkileniyorsa aynı kancaları sağlar.

# ADR 0023: Öğretmenin haftalık yük eşikleri bir "uyarı kuralı"dır

Durum: Kabul edildi (2026-10-24, K6d).

## Bağlam

Okullar öğretmenin haftalık ders saatini iki eşikle izler: altta maaş karşılığı (ör. 15 saat), üstte
ek ders sınırı. Eşiklerin dışındaki öğretmen bir **hata** değildir (program yine üretilir), ama
yönetici dağılımı yaparken bunu görmek ister (kişiselleştirme planı, madde i). Eşik okuldan okula
değişir; bazı öğretmenlerde de farklıdır (ör. idari görevi olan öğretmenin maaş karşılığı daha az).

Kişiselleştirme planı (bölüm 3) eşikleri `okul` tablosunda iki sütun olarak öngörmüştü.

## Karar

Eşikler `kisit` tablosunda `haftalik_yuk` türünde bir kuraldır: `{"alt": 0, "ust": 0}`, 0 = eşik yok
(varsayılan: ikisi de kapalı). Kural öğretmen kapsamını destekler.

- Çözücüde `HaftalikYuk` sınıfı kayıt defterindedir ama modele hiçbir şey eklemez (`uygula` boş
  döner). Bir "uyarı kuralı"dır.
- Uyarının metni tek yerde: `cozucu/yuk.py: YukHesabi.ogretmen_yuk_uyarisi`. Ders dağılımı özeti
  (`yuk_uyarisi` alanı) ve ön kontrol (`GET /on-kontrol` yanıtındaki `uyarilar`, çözücüde
  `on_kontrol.uyarilar`) bunu kullanır; ADR 0015'teki gibi aynı sonuç iki yerde.
- Uyarılar `celiskiler`den ayrı listededir: üretim düğmesini pasifleştirmez.

## Değerlendirilen alternatifler

- **`okul` tablosunda iki sütun (plandaki).** Okul geneli için yeterli, ama öğretmene özel eşik için
  ayrı bir yer (öğretmen tablosunda sütun ya da yeni tablo) gerekirdi. "Özel ayar ekle" ekranı,
  özel ayarların özeti, "en özel kazanır" çözümlemesi ve silinen öğretmenin ayarının CASCADE ile
  gitmesi ikinci kez yazılırdı. Migration da gerekirdi.
- **Yalnızca API'de bir ayar, çözücüde değil.** Çözücü `kisit` satırlarını kayıt defterinden
  doğrular; bilinmeyen tür girdi hatasıdır. Kuralı çözücüden saklamak her okuyucuya bir istisna
  eklerdi.

## Sonuçları

- Migration yok; mevcut okullar eşiksiz başlar (davranış değişmez).
- Kural listesinde "zorunlu" kipte görünür; arayüz onu önem seviyeleriyle değil, iki sayıyla gösterir.
- Kayıt defterinde modele etkisi olmayan bir kural bulunur. Sınıfın belgesi bunu açıkça söyler; ileride
  başka uyarı kuralları da aynı yolu kullanabilir.

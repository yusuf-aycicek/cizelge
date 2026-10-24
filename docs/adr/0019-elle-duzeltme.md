# ADR 0019: Elle düzeltme: bağımsız doğrulayıcıyla karar, yer değiştirme ve geri alma

Durum: Kabul edildi (2026-10-24, 7.1).

## Bağlam

Yönetici üretilen programda bir dersi başka bir saate taşımak, bazı dersleri kilitlemek ve
yaptığını geri almak ister (CLAUDE.md bölüm 3). Zorunlu kuralı çiğneyen taşıma engellenmeli,
yalnızca esnek kuralı kötüleştiren taşıma uyarıyla yapılabilmeli. Kuralın kaynağı tek olmalı:
çözücü paketinde zaten çözücüden bağımsız bir doğrulayıcı (`dogrulama.py`) ve kalite ölçümü
(`kalite.py`) var.

İlk sürüm yalnızca boş hücreye taşımaya izin veriyordu. Ölçüm (gerçekçi set, 40 ders): **38'inin
hiç geçerli hedefi yoktu**; mini sette 7'sinin. Şubeler haftanın %80-95'i dolu olduğu için hedef
hücrede neredeyse her zaman şubenin başka bir dersi var ve bu "şube çakışması" sayılıyordu.

## Karar

1. **Karar çözücü paketinde, saf Python'da** (`cozucu/tasima.py`): taşımanın bütün hareketleri
   hesaplanır, sonuç `dogrulama.ihlaller` ile denetlenir, esnek ölçüler `kalite.olc` ile
   karşılaştırılır. API (`elle.py`) yalnızca veritabanı işini yapar; arayüz yalnızca gösterir.
2. **Yalnızca yeni ihlaller engeller.** Program üretildikten sonra veriler değiştiyse programda
   zaten ihlal olabilir (ör. öğretmen sonradan "gelemez" işaretlendi); kullanıcı tam da bunu
   elle düzeltmeye çalışıyor olabilir. İhlaller bir anahtarla (tür + varlıklar) karşılaştırılır.
3. **Yer değiştirme (takas):** hedef saatlerde aynı şubenin başka dersi varsa o ders, taşınan
   dersin boşalttığı saatlere geçer (örtüşmüyorsa aynı konuma, aynı günde kaydırmada sırayla).
   Takas edilen dersin bloğu bölünür ya da öğretmeni doluysa doğrulayıcı engeller; kilitliyse
   takas yapılmaz. Takasla gerçekçi sette hedefsiz ders 38'den 6'ya düştü.
4. **Blok bütün taşınır;** kilitli ders taşınmaz. Temel programdaki kilit türetilen programda
   yalnızca kendi yerleşiminin kilidi olarak sürer (kullanıcı orada açabilir).
5. **Harita:** taşıma başlarken her başlangıç hücresi bir kez değerlendirilir (uygun / uyarı /
   engel + nedenler); sürüklerken her hücre için istek atılmaz. Dağılım şekli girdi başına önbelleğe
   alındı (`BlokHesabi.desen`): gerçekçi sette harita 3 sn → 0,6 sn.
6. **Geri alma:** her taşıma (bütün hareketleriyle) ve kilit değişikliği `program_islemi`
   tablosuna yazılır (migration `ders_programi_0009`, RLS, bileşik FK); geri alma en sondakini
   tersine çevirir. Programın kalite ölçümü ve toplam cezası her değişiklikte yeniden hesaplanır;
   elle düzeltilmiş programda "en iyisi kanıtlandı" sözü gösterilmez.
7. Program satırı işlem boyunca kilitlenir (FOR UPDATE): iki kullanıcının aynı programdaki
   taşımaları birbirini görmeden yazılamaz.

## Değerlendirilen alternatifler

- **Arayüzde doğrulama:** sürüklerken anında tepki verirdi, ama kurallar (blok, öğle arası,
  özel ayarlar) iki dilde iki kez yazılırdı (ADR 0015'in reddettiği şey).
- **Her hedef için ayrı istek (sürüklerken):** 40 istek ve yavaş bir sunucuda takılan bir arayüz.
- **Takas yerine yalnızca boş hücre:** kural basit, ama gerçek bir okulda işlev neredeyse yok.
- **Çözücüyle yeniden yerleştirme (taşınan dersi kilitleyip gerisini çözdürmek):** güçlü ama
  saniyeler sürer ve kullanıcının dokunmadığı dersleri de oynatır; "en az değişiklikle yeniden
  üret" zaten bu ihtiyacı karşılıyor.

## Sonuçları

- Elle düzeltme çözücünün kurallarıyla tutarlı; doğrulayıcıdaki bir eksik hem üretimi hem elle
  düzeltmeyi etkiler (tek yerde düzeltilir). Mutasyon denemesi 24/24.
- Takas zinciri tek adımdır: A, B'nin yerine; B, A'nın yerine. Üç dersi döndürmek iki taşımadır.
- Geri alma yalnızca sondan başadır (yinele yok).

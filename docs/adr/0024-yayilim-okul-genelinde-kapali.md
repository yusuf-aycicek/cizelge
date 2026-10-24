# ADR 0024: Aynı dersin günlere yayılması okul genelinde kapalıdır, derse özel açılır

Durum: Kabul edildi (2026-10-24, K6 sonrası; kullanıcı kararı).

## Bağlam

K6'da "aynı ders günlere yayılsın" kuralı (bir şubenin aynı dersi art arda iki günde olursa ceza)
okul genelinde açık ve "Önemli" (ağırlık 2) olarak geldi. Gerçekçi sette 120 sn ölçümü
(`docs/olcumler.md`, "İkincil kurallar") bunun öğretmen konforunu bozduğunu gösterdi:

- 120 sn sonunda bile 62-63 art arda gün çifti kalıyor; toplam cezanın yarısından fazlası bu kural.
- Öğretmen penceresi 8'den 23'e, eksik boş gün 11'den 19'a çıktı.

Kural yapısı gereği boş gün ve pencereyle çatışır. Öğretmeni dört güne sıkıştırmak aynı dersi art
arda günlere iter. 3 bloklu (2+2+2, 2+2+1) bir ders 5 günlük haftada ancak pazartesi, çarşamba ve
cuma ile yayılabilir. Bütün derslerde istendiğinde çözücünün süresi bu çatışmaya gidiyor.

## Karar

- Kural okul genelinde kapalıdır: varsayılan `{"yayilsin": false}`. API okul geneli
  `yayilsin: true`'yu reddeder: "Aynı dersin günlere yayılması okul genelinde açılamaz; Özel
  ayar ekle ile derse özel açın".
- Kural yalnızca derse ya da ders + şubeye/gruba özel açılır. Kural sınıfında
  `zorunlu_eksenler = {"ders"}` vardır; ders + şube düzeyinde yeniden kapatılabilir.
- Önemi (ağırlığı) okul genelinde ayarlanmaya devam eder: açılan derslerde ne kadar önemli olduğunu
  söyler.
- "Gelişmiş" bölümündeki açıklama, kuralın öğretmenlerin boş gününü ve boş saatlerini
  zorlaştırabileceğini söyler. Onay kutusunun yerinde "Özel ayar ekle"ye yönlendirme vardır.
- Kalite özeti "art arda gün" ölçüsünü yalnızca sıfırdan büyükse gösterir (saat tercihi gibi).
- Saf çözücü paketi okul geneli değeri kabul eder. Böylece ölçüm ve deneyler kuralı bütün
  derslerde açabilir; sınırlama okulun kullandığı API'dedir.

## Değerlendirilen alternatifler

- **Okul genelinde açık, önemi "Önemsiz" (1).** Çatışma azalır ama kaybolmaz: ceza her derste
  durur, çözücü süresinin bir kısmını yine ona harcar. Kullanıcı da çoğu okulun bu kuralı birkaç
  ders (Matematik, Türk Dili ve Edebiyatı) için istediğini söyledi.
- **Okul genelinde kapalı ama açılabilir.** Okul onu bütün derslerde açarsa ölçülen sorun geri
  gelir. Derse özel açma aynı ihtiyacı daha dar karşılar.

## Sonuçları

- Varsayılan okulda kural modele hiçbir şey eklemez. Gerçekçi sette 120 sn'de eski ölçülerin
  (pencere, tercih etmez, eksik boş gün) cezası ortalama 156'dan 123'e indi, ama K6 öncesine (69)
  dönmedi: pencere ortalama 18 (P1: 8), eksik boş gün 15 (P1: 11). Kalan farkın açık kalan "günde
  en az ders" kuralından geldiği ölçüldü; o kural da okul genelinde kapatıldı (ADR 0025,
  `docs/olcumler.md`).
- Migration gerekmez. Okul geneli `yayilsin: true` satırı olan bir okul varsa (K6 ile bu ADR
  arasında açılmış olabilir), "Varsayılana dön" ile silinir. Bu satır çözücüde hâlâ geçerlidir.
- Kural, saat tercihi gibi "yalnızca derse özel" kurallar arasına girer.

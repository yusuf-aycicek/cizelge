# Çözücü planı (Yapım sırası, 1. adım)

Kaynak: CLAUDE.md, bölüm 7 ve 8. Kabul kriteri: gerçekçi set süre sınırı içinde çözülür,
testler geçer ve zamana göre kalite ölçülmüştür.

## Durum

| # | Alt adım | Durum |
|---|---|---|
| 1 | Paket iskeleti, veri modeli, arayüz, ADR'ler | Bitti (commit `1ff93f3`) |
| 2 | Zorunlu kısıtlar, `CpSatCozucu`, doğrulayıcı, mini set | Bitti |
| 3 | Esnek kısıtlar | Bitti |
| 4 | Ön kontroller ve çözülemezlik açıklaması | **Sıradaki** |
| 5 | Ek hedefler: öğretmene boş gün, en az değişiklikle güncelleme | Bekliyor |
| 6 | Veri üretici, gerçekçi ve büyük setler, CLI, zamana göre kalite ölçümü | Bekliyor |

Kapsam güncellemesi (3. alt adımdan sonra): öğretmene boş gün, çözülemezlik açıklaması ve en az
değişiklikle güncelleme eklendi. Süre ölçümü, zamana göre kalite ölçümüne genişletildi.

Çalışma şekli: Her alt adım testler geçince `main` dalına commit edilir. Ardından ne yapıldığı
ve neden öyle yapıldığı kısaca özetlenir. Sonraki alt adıma proje sahibinin onayı olmadan
geçilmez.

## Onaylanan kararlar

1. **Python sürümü:** OR-Tools'un 3.14 için hazır paketi yoksa `cozucu` için 3.12 ile bir sanal
   ortam kurulacaktı. Sonuç: OR-Tools 9.15'in 3.14 paketi var. Sanal ortam Python 3.14 ile
   `cozucu/.venv` içinde kuruldu.
2. **"Günde en fazla N saat" kuralının birimi:** Kural ders ataması bazında değil, (sınıf, ders)
   çifti bazında uygulanır. Böylece ileride aynı derse birden fazla atama girildiğinde de kural
   doğru çalışır.
3. **Varsayılan ceza ağırlıkları:** tercih etmez = 5, öğretmen penceresi = 3, sınıf boşluğu = 10,
   ardışık olmayan ders = 2. Hepsi parametredir ve `kisit.agirlik` ile değiştirilebilir.
   Sonradan eklenenler (onaylandı): boş gün = 4, değişiklik = 20.
5. **Kapsam güncellemesi:** 4 → 5 → 6 sırası ve `program.temel_program_id` alanı onaylandı.
6. **Boş gün kuralı:** "en az gün" değil, "hedeflenen boş gün sayısı" (varsayılan 1). Öğretmenin
   günde en fazla M saat (varsayılan 8) derse girmesi ayrı bir zorunlu kısıttır.
4. **Commit:** Her alt adımın sonunda `main` dalına commit atılır.

## Paket yapısı

```
cozucu/
  pyproject.toml          bağımlılık: yalnızca ortools (+ test için pytest)
  src/cozucu/
    model.py              düz veri yapıları (dataclass)                       [1]
    arayuz.py             ProgramCozucu soyut sınıfı                          [1]
    veri_io.py            JSON <-> model dönüşümü                             [1]
    cpsat.py              CpSatCozucu                                         [2]
    kisitlar/temel.py     KisitKurali taban sınıfı + kayıt defteri            [2]
    kisitlar/zorunlu.py   HaftalikSaat, SinifCakismasi, OgretmenCakismasi,
                          Gelemez, KilitliHucre, GunlukDersSiniri(N)           [2]
                       += OgretmenGunlukSiniri(M)                             [4]
    kisitlar/esnek.py     TercihEtmez, OgretmenPenceresi, ArdisikDers,
                          SinifBoslugu                                        [3]
    dogrulama.py          bağımsız doğrulayıcı (çözücü kodunu kullanmaz)      [2]
    kalite.py             bağımsız kalite ölçümü (boşluk, pencere, ...)       [3]
    on_kontrol.py         çözücüden önce anlaşılır hatalar                    [4]
    celiski.py            çözümsüzlükte çelişen kısıt gruplarını bulur        [4]
    kisitlar/esnek.py  += BosGun, Degisiklik                                  [5]
    uretici.py            sabit tohumlu veri seti üretici                     [6]
    olcum.py              zamana göre kalite (çözüm geri çağırması)           [6]
    cli.py                python -m cozucu <veri.json> --sure 60              [6]
  tests/
```
Köşeli parantezdeki sayı, dosyanın hangi alt adımda yazıldığını gösterir.

## Alt adımlar

### 1. Paket iskeleti, veri modeli, arayüz, ADR'ler (bitti)
- `pyproject.toml`. Uzun süren testler `slow` olarak işaretli ve varsayılan çalıştırmada atlanır.
- `model.py`: girdi ve çıktı veri yapıları (frozen dataclass) ve `CozumDurumu`.
  Durum değerleri: `optimal`, `uygun`, `cozumsuz`, `on_kontrol_hatasi`, `bilinmiyor`.
- `arayuz.py`: `ProgramCozucu.coz(girdi, sure_siniri_sn=60)`. İstisna fırlatmaz, durumu ve
  mesajları sonuçta döner.
- `veri_io.py`: JSON'a yazma ve okuma.
- ADR'ler: 0001 (arayüz ve CP-SAT), 0002 (strategy deseni), 0003 (veri formatı).

### 2. Zorunlu kısıtlar, CpSatCozucu, doğrulayıcı, mini set (bitti)
- `KisitKurali` taban sınıfında tek metot bulunur: `uygula(baglam)`. `baglam` CP-SAT modelini,
  `x[atama, gun, saat]` değişkenlerini ve girdiden hazırlanmış dizinleri taşır. Kayıt defteri
  `tur` adını sınıfa eşler.
- Zorunlu kısıtlar şunlardır:
  - her atama tam haftalık saati kadar yerleşir
  - sınıf çakışması yok
  - öğretmen çakışması yok
  - gelemez saatlerine ders konmaz
  - kilitli hücreler yerinde kalır
  - aynı ders bir sınıfa günde en fazla N saat konur (varsayılan 2, (sınıf, ders) bazında)
- `CpSatCozucu`: modeli kurar, süre sınırıyla çözer, durumu `CozumDurumu`'na çevirir.
- `dogrulama.py`: Bir çözümün tüm zorunlu kısıtları sağladığını çözücüden bağımsız olarak denetler.
- Mini set: 3 sınıf, 5 öğretmen. `veri/mini.json` dosyasına elle yazılır ve gözle kontrol
  edilebilir.
- Testler:
  - her kısıt için küçük bir senaryo
  - doğrulayıcının bilerek bozulmuş programları yakalaması
  - mini setin çözülüp doğrulayıcıdan geçmesi
- Uygulama sırasında verilen kararlar:
  - Varsayılan N (`VARSAYILAN_GUNLUK_DERS_SINIRI`) `model.py` içindedir. Böylece doğrulayıcı
    çözücü koduna bağımlı olmadan aynı değeri okur.
  - Temel beş kural (`TEMEL_KURALLAR`) kayıt defterinde yer almaz ve her zaman uygulanır. Kayıt
    defterinde yalnızca okul geneli kurallar bulunur (şimdilik `gunluk_ders_siniri`).
  - Kayıp referans, aralık dışında gün/saat, bilinmeyen kısıt türü ya da hatalı parametre
    `GirdiHatasi` fırlatır. `CpSatCozucu` bunu `on_kontrol_hatasi` durumuna çevirir. Ayrıntılı ön
    kontrol 4. alt adımda yapılacak.
  - `zorunlu=False` olarak tanımlanmış bir kural şimdilik zorunlu sürümünü kapatır ve not
    bırakır. Kuralın esnek sürümü 3. alt adımda eklenecek. (3. adımda yerini gerçek esnek kip
    aldı.)
  - Mini set: 5 gün × 6 saat. Gelemez: Ayşe pazartesi, Fatma cuma, Mehmet çarşamba 1-2. saat.
    Kilitli hücre: 9-A matematik, salı 1. saat.

### 3. Esnek kısıtlar (bitti)
- Esnek kurallar `(ceza_ifadesi, agirlik)` döndürür. Çözücü ağırlıklı toplamı en aza indirir
  (ADR 0004). Her ceza kullanıcının anlayacağı bir birimi sayar.
- **Tercih etmez:** Tercih edilmeyen saate yerleşen her ders için ceza.
- **Öğretmen penceresi:** Öğretmenin gün içindeki ilk ve son dersi arasındaki her boş saat için
  ceza. Plandaki ilk/son tamsayı değişkenleri yerine "bu saatte ya da önce / sonra dersi var"
  boolean'ları kullanıldı. Model doğrusal kalır ve yayılım daha iyidir.
- **Ardışık ders:** Ceza = o gün o dersin blok sayısı − 1. Günde 2 saatlik derste bu, "bitişik
  olmayan çift ders" sayısıdır. (sınıf, ders) bazında sayılır.
- **Sınıf boşluğu:** Sınıfın, o gün sonrasında hâlâ dersi olan her boş saati için ceza (baştaki
  boşluklar dahil). Plandaki "boş saatten sonra dolu saat" tanımı boşluk geçişlerini sayıyordu.
  Kullanıcının istediği ölçüye (boş saat sayısı, boşluklar gün sonuna) uyması için değiştirildi.
- **Günlük ders sınırı:** Esnek kipi eklendi. N'i aşan her saat için ceza.
- Kurallar "zorunlu olabilir / esnek olabilir" bilgisini taşır. `kisit` tanımındaki `zorunlu` ve
  `agirlik` değerleri kurala aktarılır. Desteklenmeyen kip ya da negatif ağırlık
  `on_kontrol_hatasi` verir. Ağırlık 0 kuralı kapatır.
- Varsayılanlar `kisitlar.VARSAYILAN_KISITLAR` içinde `KisitTanimi` listesi olarak durur. Okulun
  tanımı aynı `tur`'daki varsayılanın yerini alır.
- `kalite.py`: aynı ölçüleri çözücüden bağımsız hesaplar. En iyi çözümde model cezasının bu
  ölçümlerin ağırlıklı toplamına eşit olduğu testle denetlenir.
- Mini set sonucu (öncesi → sonrası): sınıf boşluğu 10 → 0, öğretmen penceresi 13 → 0,
  bitişik olmayan çift ders 9 → 0, tercih etmez ihlali 1 → 0. Süre 0,1 sn'den yaklaşık 5-7 sn'ye
  çıktı (en iyi olduğunun kanıtı dahil).

### 4. Ön kontroller ve çözülemezlik açıklaması
Amaç: çözüm yoksa kullanıcı nedenini kendi diliyle öğrenir, kimlik değil ad görür.
- **Yeni zorunlu kısıt: öğretmen günlük sınırı** (`OgretmenGunlukSiniri`, tur
  `ogretmen_gunluk_siniri`, parametre `m`, varsayılan 8). Bir öğretmen günde en fazla M saat derse
  girer. Kayıt defterinde yer alır, okul M'yi değiştirebilir. Bu adımda eklenmesinin nedeni, ön
  kontrol ve çelişki analizinin bu kuralı da kapsaması gerektiğidir. Doğrulayıcı da bu kuralı
  denetler.
- `model.py`: `CozumSonucu.celiskiler: list[Celiski]`. `Celiski` şu alanlardan oluşur: `tur`,
  `mesaj` (Türkçe, adlarla) ve `ilgili` (öğretmen/sınıf/atama kimlikleri; arayüz ilgili hücreleri
  vurgulayabilsin diye). `mesajlar` alanı genel bilgi için kalır.
- **Ön kontroller** (`on_kontrol.py`, çözücüden önce, hızlı ve kesin):
  - öğretmeni seçilmemiş atama
  - tutarlılık: atamanın sınıfı/dersi/öğretmeni var mı, gün/saat aralıkta mı, aynı hücrede iki
    kilit var mı
  - sınıf: toplam saat > haftalık kapasite
  - öğretmen: toplam saat > kullanılabilir saat ("Ayşe Yılmaz'ın 24 saat dersi var, müsait olduğu
    20 saat var"). Kullanılabilir saat = Σ gün min(o gün müsait saat, M).
  - ders: haftalık saat > (öğretmenin müsait olduğu gün sayısı) × N
  - kilitler: kilitli hücre o öğretmenin gelemez saatinde mi, aynı sınıfa/öğretmene aynı saatte iki
    kilit var mı, bir atamanın kilit sayısı haftalık saatini ya da günlük N sınırını aşıyor mu
  - Bulunan bütün hatalar birlikte raporlanır, ilk hatada durulmaz.
- **Çelişki analizi** (`celiski.py`, ön kontrolden geçip CP-SAT "çözüm yok" derse):
  - Zorunlu kısıtlar gruplara ayrılır ve her grup bir varsayım (assumption) literaline bağlanır:
    atamanın haftalık saati, öğretmenin gelemez saatleri, tek tek kilitler, (sınıf, ders) günlük
    sınırı, öğretmen günlük sınırı. Çakışma kuralları gruba bağlanmaz, her zaman açıktır.
  - Esnek kısıtlar olmadan, yalnızca uygunluk için çözülür. CP-SAT'ın
    `sufficient_assumptions_for_infeasibility` çağrısı çelişen bir grup kümesi verir. Bu küme
    tek iş parçacığında ve süre sınırıyla elde edilir.
  - Küme, gruplar teker teker çıkarılıp yeniden denenerek küçültülür (süre bütçesi içinde). Sonuç
    "hepsi birlikte sağlanamayan en küçük kurallar kümesi" olur.
  - Gruplar Türkçe cümleye çevrilir. Örnek: "Ayşe Yılmaz'ın gelemez saatleri ile 9-A, 9-B ve 10-A
    matematik dersleri (toplam 18 saat) birlikte yerleştirilemiyor."
- Testler: her ön kontrol hatası için en az bir test, ön kontrolden geçen ama çözümsüz senaryolar
  için çelişki kümesinin doğru grupları içerdiğini gösteren testler.
- ADR 0005: çözülemezlik açıklaması (ön kontrol + varsayım tabanlı çelişki çekirdeği).

### 5. Ek hedefler: öğretmene boş gün, en az değişiklikle güncelleme
- **Öğretmene boş gün** (`BosGun`, esnek, varsayılan ağırlık 4, parametre `hedef_bos_gun`,
  varsayılan 1):
  - Her öğretmen ve gün için "bu gün dersi var" boolean'ı tutulur.
  - Günlük sınır = min(M, okulun günlük ders saati).
  - Hedef gün = max(⌈toplam saat / günlük sınır⌉, gün sayısı − hedef boş gün).
  - Ceza = max(0, ders verilen gün − hedef gün).
  - Hedefe ulaşan öğretmen daha fazla sıkıştırılmaz. İlk önerideki "en az gün" formülü
    öğretmeni günde 8 saat aralıksız derse sıkıştırmaya teşvik ediyordu, bu yüzden değiştirildi.
    Yükü yüzünden boş günü mümkün olmayan öğretmene ceza yazılmaz.
  - Not: Belirli bir günün boş olması isteniyorsa bu zaten "gelemez"/"tercih etmez" ile ifade
    edilir. Bu kural yalnızca gün sayısını azaltır.
  - `kalite.py`: `eksik_bos_gun` ölçüsü (hedefe göre eksik kalan boş gün toplamı).
- **En az değişiklikle güncelleme** (`Degisiklik`, esnek, varsayılan ağırlık 20):
  - `CozumGirdisi.temel_yerlesimler: list[Yerlesim]` (isteğe bağlı, varsayılan boş).
  - Eşleştirme atama kimliğiyle değil, (sınıf, ders, gün, saat) ile yapılır. Böylece öğretmeni
    değişen ya da yeniden oluşturulan atama da "aynı ders" sayılır.
  - Ceza: temel programdaki her (sınıf, ders, gün, saat) için yeni programda o ders o saatte
    yoksa 1. Birimi "yer değiştiren ders saati"dir.
  - Temel program ayrıca CP-SAT'a başlangıç ipucu (`add_hint`) olarak verilir. Yalnızca hızlandırır,
    sonucu zorlamaz.
  - Kilitten farkı: kilit zorunludur, bu ise esnektir. Gerektiğinde (ör. yeni öğretmen o saatte
    gelemiyorsa) ders kayar ama yalnızca gerektiği kadar.
  - `kalite.py`: `degisen_yerlesim` ölçüsü. `veri_io` yeni alanı okur ve yazar.
- Testler: boş gün için şu senaryolar: hedefe ulaşılır; hedefe ulaşan öğretmen daha fazla
  sıkıştırılmaz; yükü yüksek öğretmene ceza yazılmaz; kaçınılamazsa ceza tam beklenen değerdir. Güncelleme için şu senaryo: mini set çözülür, bir atamanın öğretmeni değiştirilir ve
  yeni öğretmene gelemez saatler eklenir, yeniden çözülür. Değişen yerleşim sayısı küçük kalır ve
  temel program verilmeden yapılan çözümden açıkça azdır.
- ADR 0006: en az değişiklikle güncelleme (ceza + ipucu, (sınıf, ders) eşleştirmesi). Boş gün
  için ayrı ADR yazılmaz. Mevcut desenlerin (ADR 0002, 0004) bir uygulaması olduğu için plan
  dosyasında not olarak kalır.

### 6. Veri üretici, setler, CLI, zamana göre kalite ölçümü
- Sabit tohumlu üretici: Önce gizli bir geçerli program kurulur, veri ondan türetilir. Böylece
  çözümün var olduğu garanti edilir. Müsaitlik kısıtları da bu programla çelişmeyecek şekilde
  seçilir.
- Gerçekçi set: yaklaşık 24 şube, 45 öğretmen, 5 gün, günde 8 saat, müsaitlik kısıtlarıyla.
- Büyük set: yaklaşık 40 şube, 80 öğretmen.
- `veri/` altına JSON olarak yazılır.
- CLI: Programı sınıf ve öğretmen bazında tablo olarak yazdırır. Ölçüleri ve çelişkileri de
  gösterir.
- **Zamana göre kalite** (`olcum.py`):
  - Tek bir 120 saniyelik çalıştırmada CP-SAT çözüm geri çağırması (solution callback) her
    iyileşmede zamanı ve çözümü kaydeder. 10, 30, 60 ve 120. saniyede o ana kadarki en iyi çözümün
    toplam cezası ve `kalite.olc` ölçüleri tablolanır.
  - Çok iş parçacıklı CP-SAT deterministik olmadığından her set 3 farklı tohumla çalıştırılır.
    Ortalama ve en kötü değerler raporlanır.
  - Sonuçlar `docs/olcumler.md` dosyasına yazılır (makine bilgisi ve OR-Tools sürümüyle).
- **Kalite yetersizse değerlendirilecek iyileştirmeler** (her biri aynı toplam süre bütçesiyle,
  önceki ölçümle karşılaştırılarak):
  - İki aşama: önce yalnızca zorunlu kısıtlarla uygun bir program bulunur, sonra bu program ipucu
    olarak verilip esnek hedefle çözülür.
  - CP-SAT parametreleri: iş parçacığı sayısı, `linearization_level`, LNS ağırlıklı arama.
  - Model sadeleştirme: simetri kırma (ör. aynı seviyenin şubeleri) ve gereksiz yardımcı
    değişkenleri azaltma.
  - Bir iyileştirme kabul edilirse ADR 0007 olarak kaydedilir.
- Testler:
  - gerçekçi set 60 saniye içinde çözülür ve doğrulayıcıdan geçer (kabul kriteri)
  - büyük set ve zamana göre kalite ölçümü `slow` olarak işaretli, ayrı çalışır

# Çözücü planı (Yapım sırası, 1. adım)

Kaynak: CLAUDE.md, bölüm 7 ve 8. Kabul kriteri: gerçekçi set süre sınırı içinde çözülür,
testler geçer ve zamana göre kalite ölçülmüştür.

## Durum

| # | Alt adım | Durum |
|---|---|---|
| 1 | Paket iskeleti, veri modeli, arayüz, ADR'ler | Bitti (commit `1ff93f3`) |
| 2 | Zorunlu kısıtlar, `CpSatCozucu`, doğrulayıcı, mini set | Bitti |
| 3 | Esnek kısıtlar | Bitti |
| 4 | Ön kontroller ve çözülemezlik açıklaması | Bitti |
| 5 | Ek hedefler: öğretmene boş gün, en az değişiklikle güncelleme | Bitti |
| 6 | Veri üretici, gerçekçi ve büyük setler, CLI, zamana göre kalite ölçümü | **Yarım kaldı** (bkz. 6. bölüm, "Durum") |

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
   Sonradan eklenenler (onaylandı): boş gün = 4, değişiklik = 20. (Karar 7 ile güncellendi.)
5. **Kapsam güncellemesi:** 4 → 5 → 6 sırası ve `program.temel_program_id` alanı onaylandı.
7. **Ağırlık güncellemesi (5. alt adımdan sonra):** sınıf boşluğu 10 → 30, değişiklik 20 → 8.
   Gün ortasında boş kalan sınıf okulda kabul edilemez, diğer bütün esnek kurallardan baskın
   olmalı. Değişiklik öğretmen konforu kurallarından (tercih etmez 5, boş gün 4, pencere 3)
   ağır, sınıf boşluğundan hafif kalmalı. Mini sette Mehmet perşembe senaryosu: 8 hücre değişti,
   sınıf boşluğu 0, bir öğretmen boş gününü kaybetti (eksik boş gün 1). Testler ağırlıkları artık
   sabit sayı olarak değil `VARSAYILAN_KISITLAR`'dan okur.
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
    anlatim.py            kimlikleri adlara, gün/saati metne çevirir          [4]
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

### 4. Ön kontroller ve çözülemezlik açıklaması (bitti)
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
- Uygulama sırasında verilen kararlar:
  - Küçültme denemelerinde grup literalleri varsayım olarak değil sabit (`lit == 0/1`) olarak
    verilir ve model her denemede yeniden kurulur. Varsayımlar presolve'a görünmediği için mini
    setteki bir sayma çelişkisinin kanıtı deneme başına 4,4 sn sürüyordu, sabitlerle 0,07 sn
    sürüyor. Varsayım çekirdeği yalnızca aday kümeyi daraltmak için, sürenin en fazla üçte
    biriyle kullanılır.
  - Çelişki analizinin ayrı bir süre bütçesi vardır (`CELISKI_ANALIZ_SURESI_SN` = 30 sn, ana süre
    sınırını aşmaz). Süre dolarsa o ana kadarki küme raporlanır.
  - `on_kontrol` tutarsız veri bulursa kapasite kontrollerini yapmaz, çünkü bozuk referanslarla
    hesap yanıltıcı mesaj üretir. `GirdiHatasi` yalnızca güvenlik ağı olarak kaldı.
  - `CozumSonucu.mesajlar` genel bilgi içindir. Sorunlar `celiskiler` alanında yapılandırılmış
    olarak döner.
  - Testlerde senaryo girdileri `tests/yardimci.py:girdi_kur` ile kurulur: atamalarda geçen
    öğretmen, sınıf ve dersleri kendisi ekler, böylece senaryolar ön kontrolün tutarlılık
    denetiminden geçer.
  - Türkçe iyelik eki (`Ayşe Yılmaz'ın`, `Mehmet Kaya'nın`) ünlü uyumuna göre üretilir.

### 5. Ek hedefler: öğretmene boş gün, en az değişiklikle güncelleme (bitti)
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
- **En az değişiklikle güncelleme** (`Degisiklik`, esnek, varsayılan ağırlık 20, sonra 8):
  - `CozumGirdisi.temel_yerlesimler: list[TemelYerlesim]` (isteğe bağlı, varsayılan boş).
    Plandaki `list[Yerlesim]` yerine (sınıf, ders, gün, saat) taşıyan ayrı bir yapı seçildi.
    Atama silinip yeniden oluşturulunca eski kimlik çözücü girdisinde artık bulunmaz; (sınıf, ders)
    bilgisini worker sağlar. `temel_program(atamalar, yerlesimler)` bir çözümü bu biçime çevirir.
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
- Uygulama sırasında verilen kararlar ve gözlemler:
  - Temel programda olup artık var olmayan dersler (ders kaldırılmış, okul saati kısalmış) sabit
    ceza olarak eklenir. En iyi programı değiştirmez, ama toplam ceza bağımsız ölçümle tutarlı kalır.
  - Kapsam notu (bir sınıf, bir ders, bir öğretmen kalıcı): (sınıf, ders) bazındaki kararların
    "ileride aynı derse birden fazla atama" gerekçesi geçersizleşti. Kod değişmedi, çünkü tek
    atamayla da aynı şekilde çalışıyor. En az değişiklik eşleştirmesi için bu anahtar hâlâ doğru
    seçim.
  - Mini set ölçümü (boş gün kapalı → açık): sınıf boşluğu, pencere, bölünmüş ders ve tercih
    etmez 0 kaldı. Eksik boş gün 3 → 0 oldu.
  - Mini set ölçümü (Mehmet bir gün gelemez, temel programda o gün 5 dersi var): sıfırdan üretim
    71 hücreden 54'ünü değiştirdi. Temel programla ağırlık 20'de 5 hücre değişti, ama 3 sınıf
    boşluğu oluştu. Ağırlık 8'de 7 hücre değişti ve 1 boşluk kaldı, ağırlık 2'de 9 hücre değişti
    ve boşluk kalmadı. Varsayılan ağırlık proje sahibine soruldu; karar 7 ile 8 oldu ve sınıf
    boşluğu 30'a çıktı.
  - Çok iş parçacıklı CP-SAT aynı girdide farklı (eşit cezalı) programlar üretebilir. Bu, 6. adımın
    ölçümlerinde tohum tekrarıyla ele alınacak.

### 6. Veri üretici, setler, CLI, zamana göre kalite ölçümü (yarım kaldı)
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

#### 6. alt adımın durumu (2026-10-13, çalışma burada durduruldu)

**Bitenler** (testler geçiyor: 129 varsayılan + 3 `slow`, hepsi geçti):
- `uretici.py`: sabit tohumlu üretici, "gizli program" yöntemi.
  - MEB lise çizelgesine yakın müfredat: 9-10. sınıflar 40 saat, 11-12. sınıflar 38 saat (5 × 8).
  - Branş öğretmenlerine rastgele 15-30 saatlik yük hedefleri verilir.
  - Öğretmenlerin ~%25'i bir gün tam gelemez, ~%35'inin ek gelemez saatleri vardır (ilk ya da
    son saatlerde), ~%35'inin tercih etmez saatleri vardır.
  - Gizli program CP-SAT ile, yalnızca zorunlu kısıtlarla, tek iş parçacığı ve sabit tohumla
    çözülür. Ek gelemez saatleri yalnızca gizli programdaki boş saatlerden seçilir. Sonunda gizli
    program bağımsız doğrulayıcıdan geçirilir. Tercih etmez saatleri dolu saatlere de düşebilir.
  - Aynı tohum bayt bayt aynı dosyayı üretir (md5 ile doğrulandı).
  - Komut: `python -m cozucu.uretici gercekci veri/gercekci.json --tohum 1`.
- `veri/gercekci.json`: 24 şube, 42 öğretmen, 330 atama, 936 ders saati, yük 15-30, 163
  müsaitlik kaydı. Üretim 34 sn.
- `veri/buyuk.json`: 40 şube, 75 öğretmen, 550 atama, 1560 ders saati, yük 15-30, 248 müsaitlik
  kaydı. Üretim 146 sn.
- `olcum.py`: zamana göre kalite. Tek uzun çalıştırma yapılır, her iyileşen çözüm `CpSatCozucu`'nun
  yeni `gozlemci` kancasıyla kaydedilir. Kontrol noktalarında `kalite.olc` ve
  `agirlikli_ceza` ile ölçülür. Komut: `python -m cozucu.olcum veri/gercekci.json`.
- `cli.py` / `__main__.py`: `python -m cozucu <veri.json> [--sure] [--sinif] [--ogretmen]
  [--kaydet] [--temel]`. Sınıf ve öğretmen tabloları, ölçüler, çelişkiler.
- Testler: `test_uretici.py` (tekrarlanabilirlik, çözülebilirlik, tam dolu sınıflar, gelemez ile
  gizli programın çelişmemesi; `slow`: kayıtlı setlerin özellikleri ve **kabul testi: gerçekçi
  set 60 sn içinde çözülür ve doğrulayıcıdan geçer**), `test_olcum_cli.py`.

**Ölçüm sonuçları** (12 mantıksal çekirdek, 8 iş parçacığı; tablolarda gerçek ceza = bağımsız
ölçümlerin ağırlıklı toplamı, 3 tohum):

Gerçekçi set, taban çizgi (temiz koşullarda ikinci ölçüm):

| Saniye | Gerçek ceza (tohum 0 / 1 / 2) | Sınıf boşluğu | Pencere | Bölünmüş | Tercih etmez | Eksik boş gün |
|---|---|---|---|---|---|---|
| 10 | çözüm yok / 1519 / 1507 | – / 11 / 9 | – / 278 / 287 | – / 76 / 79 | – / 15 / 18 | – / 32 / 32 |
| 30 | 1115 / 892 / 1021 | 1 / 1 / 2 | 248 / 201 / 217 | 78 / 56 / 63 | 17 / 7 / 12 | 25 / 28 / 31 |
| 60 | 791 / 675 / 748 | 0 / 0 / 0 | 182 / 151 / 165 | 47 / 40 / 49 | 11 / 6 / 7 | 24 / 28 / 30 |
| 120 | 596 / 542 / 568 | 0 / 0 / 0 | 137 / 115 / 117 | 32 / 39 / 41 | 9 / 3 / 7 | 19 / 26 / 25 |

İlk çözüm 4-11 sn. Tohum 0'da 10. saniyede henüz çözüm yoktu.

Büyük set, taban çizgi:

| Saniye | Gerçek ceza (tohum 0 / 1 / 2) | Sınıf boşluğu | Pencere | Bölünmüş | Tercih etmez | Eksik boş gün |
|---|---|---|---|---|---|---|
| 10 | 3540 / 3612 / 3451 | 32 / 33 / 34 | 626 / 643 / 582 | 143 / 157 / 153 | 36 / 31 / 35 | 59 / 56 / 51 |
| 30 | 2360 / 2598 / 2414 | 9 / 17 / 11 | 498 / 496 / 500 | 112 / 130 / 135 | 28 / 24 / 22 | 58 / 55 / 51 |
| 60 | 1870 / 1804 / 1694 | 3 / 7 / 2 | 418 / 372 / 384 | 97 / 100 / 101 | 20 / 14 / 16 | 58 / 52 / 50 |
| 120 | 1372 / 1290 / 1246 | 1 / 4 / 0 | 296 / 263 / 285 | 68 / 73 / 78 | 18 / 11 / 11 | 57 / 45 / 45 |

İlk çözüm ~9 sn.

**Değerlendirme: 60. saniyedeki kalite yetersiz.**
- Gerçekçi sette sınıf boşluğu 60. saniyede 0, ama öğretmen penceresi 150-180 saat (öğretmen
  başına haftada ~4 saat) ve 42 öğretmenin 24-30'u boş gününü alamıyor.
- Büyük sette en öncelikli kural olan sınıf boşluğu 60. saniyede hâlâ 2-7.
- Kalite 120. saniyede de hızla iyileşiyor. Gerçekçi set tohum 1 ile 300 sn: 60 sn'de 698,
  120 sn'de 514, 300 sn'de 308 (pencere 60, eksik boş gün 24). Çözücü yakınsamaktan uzak.

**Denenen iyileştirmeler** (gerçekçi set, 3 tohum, 120 sn; ortalama gerçek ceza):

| Strateji | 60 sn | 120 sn |
|---|---|---|
| Taban (8 iş parçacığı) | 738 | 569 |
| İki aşama (önce yalnızca zorunlu, ilk çözüm ipucu olarak) | 788 | 567 |
| `linearization_level=2` | 761 | 536 |
| 12 iş parçacığı | 741 | 539 |

Farklar tohumlar arasındaki dalgalanmanın (±60) içinde kalıyor; hiçbiri anlamlı değil. İki
aşamalı yöntemde ilk aşama 1-2 sn'de uygun çözüm buluyor, ama ipucu tam modelin aramasını
hızlandırmıyor. Deney betikleri bu oturumun geçici klasöründeydi, depoya alınmadı.

**Bulunan asıl sorun: pencere formülasyonunun gevşetilmiş hali çok zayıf.**
300 sn'lik çalıştırmada CP-SAT'ın alt sınırı **−2229** çıktı. Cezaların hepsi negatif olmadığı
için gerçek alt sınır en az 0'dır. Nedeni `OgretmenPenceresi`'ndeki `okulda ≥ once + sonra − 1`
kısıtı: kesirli çözümde (dolu = 0,5) `okulda = 0` olabiliyor ve `okulda − dolu` ceza terimi
negatife düşüyor. Tamsayı çözümlerde formül doğru, testler bu yüzden yakalamadı. Ama arama
yönlendirmesi bozuluyor.

**Yarım kalan iş:**
- Pencere formülasyonu deneyi başlatıldı ama sonucu alınmadan durduruldu. Denenecek iki varyant:
  - A: mevcut formüle geçerli eşitsizlik `okulda ≥ dolu` eklemek. Her tamsayı çözümde zaten doğru,
    ama ceza terimini negatif olmaktan çıkarır.
  - B: yardımcıları tam tanımlamak: `mesgul = dolu`, `once`/`sonra` için `add_max_equality`,
    `okulda = min(once, sonra)` için `add_min_equality`.
  Varyantlar kayıt defterindeki `ogretmen_penceresi` sınıfı değiştirilerek, asıl kodu
  değiştirmeden ölçülür (3 tohum × 120 sn, gerçekçi set). Alt sınırın negatif olmaktan çıkıp
  çıkmadığı da kaydedilir. Benzer bir zayıflık diğer esnek kurallarda da aranmalı. `SinifBoslugu`
  (`sonra ≥ dolu` olduğu için terim negatif olamaz) ve `ArdisikDers` (`ceza ≥ 0`) şimdilik
  güvenli görünüyor.
- Kullanıcının istediği gösterimler henüz yapılmadı:
  1. Zamana göre kalite tablosu: taban çizgi için yukarıda var. Kabul edilen iyileştirmeden sonra
     yeniden ölçülmeli.
  2. Gerçekçi setten bir sınıfın ve bir öğretmenin haftalık programı (CLI ile:
     `python -m cozucu veri/gercekci.json --sinif 9-A --ogretmen <ad>`).
  3. Gerçekçi sette en az değişiklik senaryosu: 60 sn'lik temel program, en yoğun öğretmenin en
     yoğun günü kapatılır, 10 sn ve 60 sn temelli ile 60 sn sıfırdan karşılaştırılır.
  4. Gerçekçi sette çözümsüz örnek: 40 saatlik (tam dolu) bir sınıfın bütün öğretmenleri
     Pazartesi 1. saatte gelemez. Ön kontrolden geçer, çözüm yoktur. Çelişki analizinin süresi ve
     mesajı ölçülür.
  2-4 için betik yazıldı (bu oturumun geçici klasöründe), çalıştırılmadı.
- `docs/olcumler.md` henüz yazılmadı (yukarıdaki tablolar oraya, makine bilgisi ve OR-Tools 9.15
  ile taşınacak).
- Bir iyileştirme kabul edilirse ADR 0007 yazılacak.
- Çözücü adımının (yapım sırası 1) kabul kriterleri değerlendirilecek:
  - "Gerçekçi set süre sınırı içinde çözülür": karşılanıyor (`slow` kabul testi geçti, 60 sn'de
    `uygun` ve doğrulanmış program).
  - "Testler geçer": karşılanıyor (132/132).
  - "Zamana göre kalite ölçülmüştür": ölçüldü, ama kalite yetersiz bulundu ve iyileştirme yarım.

**Pencere varyantları deneyi (2026-10-14, yapıldı; koda alınmadı, proje sahibinin kararı bekleniyor):**
- Betik: `scripts/pencere_deneyi.py`. Sonuçlar: `scripts/sonuclar/pencere_varyantlari.md` (özet,
  her çalıştırmadan sonra yazılır) ve `scripts/sonuclar/pencere_ham.csv` (her iyileşen çözüm).
- Koşullar: gerçekçi set, 60 sn, 8 iş parçacığı, tohum 0/1/2, mevcut formül de aynı betikle
  yeniden ölçüldü. Üç varyant da mini sette doğruluk denetiminden geçti.
- 60. saniyede ortalama gerçek ceza: mevcut 703, A 687, B 1002. A ile mevcut arasındaki fark
  tohum dalgalanmasının içinde. B açıkça daha kötü (pencere 245'e karşı 147-158).
- **Hipotez doğrulanmadı:** A'da da alt sınır negatif kaldı (60 sn'de ortalama −3316; mevcut
  −3768). Yani negatif alt sınırın tek nedeni pencere formülü değil. A ile bütün ceza terimleri
  gevşetilmiş modelde de negatif olamıyor, buna rağmen sınır negatif. Bu durum, CP-SAT'ın 60 sn
  içinde gevşetilmiş modelden anlamlı bir sınır üretemediğini gösteriyor. Neden henüz bilinmiyor.
- Öneri proje sahibine sunuldu: B alınmaz, A'nın getirisi ölçülemeyecek kadar küçük.

**Sıradaki adım (eski liste; 1. madde yukarıdaki deneyle güncellendi):**
1. Pencere varyantları A ve B'yi ölçmek. Alt sınır ve 60 sn kalitesi düzelirse en iyisini
   `esnek.py`'ye almak, mini setteki çapraz kontrol testinin geçtiğini doğrulamak, ADR 0007 yazmak.
2. Gerçekçi ve büyük seti yeni modelle yeniden ölçmek (10/30/60/120 sn, 3 tohum) ve
   `docs/olcumler.md`'ye yazmak.
3. Gösterimler 2-4'ü çalıştırmak.
4. Kalite yine yetersizse değerlendirilecek seçenekler: varsayılan süre sınırını artırmak (ör.
   120-300 sn; worker kuyruğu bunu kaldırır), diğer esnek kuralların formülasyonlarını
   güçlendirmek, simetri kırma.
5. Proje sahibine sonuçları sunup 1. yapım adımının kapanışı için onay almak.

**Ölçüm yaparken dikkat:** Ölçüm sırasında aynı makinede işlemci kullanan başka bir iş (test,
CLI) çalıştırılmamalı. Bu oturumda ilk taban ölçümünün tohum 0'ı bu yüzden bozuldu ve temiz
koşullarda yeniden ölçüldü.


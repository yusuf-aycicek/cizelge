# Çözücü planı (Yapım sırası, 1. adım)

Kaynak: CLAUDE.md, bölüm 7 ve 8. Kabul kriteri: gerçekçi set süre sınırı içinde çözülür ve
testler geçer.

## Durum

| # | Alt adım | Durum |
|---|---|---|
| 1 | Paket iskeleti, veri modeli, arayüz, ADR'ler | Bitti (commit `1ff93f3`) |
| 2 | Zorunlu kısıtlar, `CpSatCozucu`, doğrulayıcı, mini set | **Sıradaki** |
| 3 | Esnek kısıtlar | Bekliyor |
| 4 | Ön kontroller ve çözümsüzlük mesajı | Bekliyor |
| 5 | Veri üretici, gerçekçi ve büyük setler, CLI tablo çıktısı, süre ölçümü | Bekliyor |

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
    kisitlar/esnek.py     TercihEtmez, OgretmenPencere, ArdisikDers,
                          SinifBosluk                                         [3]
    dogrulama.py          bağımsız doğrulayıcı (çözücü kodunu kullanmaz)      [2]
    on_kontrol.py         çözücüden önce anlaşılır hatalar                    [4]
    cli.py                python -m cozucu <veri.json> --sure 60              [5]
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

### 2. Zorunlu kısıtlar, CpSatCozucu, doğrulayıcı, mini set (sıradaki)
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

### 3. Esnek kısıtlar
- Esnek kurallar `(ceza_ifadesi, agirlik)` döndürür. Çözücü toplam cezayı en aza indirir.
- **Tercih etmez:** Tercih edilmeyen saate yerleşen her ders için ceza.
- **Öğretmen penceresi:** Her öğretmen ve gün için ilk ve son ders saati değişkenleri tutulur.
  Pencere = (son − ilk + 1) − o günkü ders sayısı.
- **Ardışık ders:** Aynı ders bir günde 2 saat yerleşmiş ama bitişik değilse ceza.
- **Sınıf boşluğu:** Bir saat boşken sonraki saat doluysa ceza. Böylece dersler günün başından
  itibaren dolar.
- Testler: Her kural için cezanın beklenen yönde çalıştığını gösteren küçük senaryolar.

### 4. Ön kontroller ve çözümsüzlük mesajı
- Öğretmeni seçilmemiş atama var mı?
- Bir sınıfın toplam saati haftalık kapasiteyi aşıyor mu?
- Bir öğretmenin toplam saati müsait olduğu saat sayısını aşıyor mu?
- Bir dersin haftalık saati, gün sayısı × N sınırını aşıyor mu?
- Tutarlılık kontrolleri: atamanın sınıfı, dersi ve öğretmeni var mı? Gün ve saat değerleri aralık
  içinde mi?
- Ön kontrollerden geçip yine de çözüm bulunamazsa, CP-SAT'ın assumption mekanizmasıyla birlikte
  çelişen kısıt grupları raporlanır (ör. "öğretmen X'in gelemez saatleri + kilitli hücreler").
- Testler: Her hata türü için en az bir test yazılır.

### 5. Veri üretici, setler, CLI, süre ölçümü
- Sabit tohumlu üretici: Önce gizli bir geçerli program kurulur, veri ondan türetilir. Böylece
  çözümün var olduğu garanti edilir. Müsaitlik kısıtları da bu programla çelişmeyecek şekilde
  seçilir.
- Gerçekçi set: yaklaşık 24 şube, 45 öğretmen, 5 gün, günde 8 saat, müsaitlik kısıtlarıyla.
- Büyük set: yaklaşık 40 şube, 80 öğretmen.
- `veri/` altına JSON olarak yazılır.
- CLI: Programı sınıf ve öğretmen bazında tablo olarak yazdırır.
- Testler:
  - gerçekçi set 60 saniye içinde çözülür ve doğrulayıcıdan geçer (kabul kriteri)
  - büyük set `slow` olarak işaretli, süre ölçümü için ayrı çalışır

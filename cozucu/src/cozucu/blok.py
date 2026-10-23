"""Blok dersler: bir dersin haftalık saatlerinin hangi bloklara bölündüğü (dağılım şekli).

Ör. 5 saatlik Matematik "2+2+1": bir gün 2 saat art arda, başka bir gün 2 saat art arda, bir
başka gün 1 saat. Her blok ayrı bir güne düşer; blok öğle arasının iki yanına yayılamaz ve günün
uzunluğunu aşamaz.

Tek kaynak burasıdır: çözücüdeki `blok_deseni` kuralı, ön kontrol, çelişki açıklaması ve API
"bu atamanın dağılım şekli ne, nereden geliyor" sorusunu buradan cevaplar.

Desen nereden gelir (en özel kazanır, ADR 0016):
1. Derse ya da ders + şubeye özel ayar: `{"desen": [2, 2, 1]}`; `[]` = blok yok. Açıkça
   istendiği için uygulanamazsa ön kontrol nedenini söyler.
2. Okul geneli: `{"otomatik": true, "varsayilanlar": {"4": [2, 1, 1]}}`. Haftalık saate göre
   önerilen desen (`varsayilanlar` yoksa `otomatik_desen`). Okul `otomatik: false` derse blok yok.
   Okul geneli desen bir **öneridir**: o atamada uygulanamıyorsa (gün sayısı, günlük sınır, gün
   uzunluğu, öğle arası, öğretmenin müsaitliği ya da kilitli hücreler izin vermiyorsa) o atama
   bloksuz kalır. Böylece varsayılan ayar tek başına bir programı çözümsüz yapmaz.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from cozucu.kapsam import cozumle
from cozucu.model import CozumGirdisi, DersAtama, MusaitlikDurumu, OkulAyari

BLOK_DESENI_TURU = "blok_deseni"
# Desende bir bloğun en büyük boyu ve en çok blok sayısı (anlamsız girdileri erken reddetmek için).
EN_BUYUK_BLOK = 8
EN_COK_BLOK = 20


def otomatik_desen(saat: int) -> tuple[int, ...]:
    """Haftalık saatten önerilen desen: olabildiğince 2'li bloklar, tek saat kalırsa sonda 1.

    1 → 1; 2 → 2; 3 → 2+1; 4 → 2+2; 5 → 2+2+1; 6 → 2+2+2.
    """
    return (2,) * (saat // 2) + (1,) * (saat % 2)


def desen_metni(desen: tuple[int, ...] | list[int]) -> str:
    """"2+2+1"; boş desen "blok yok"."""
    return "+".join(map(str, desen)) if desen else "blok yok"


def desen_dogrula(desen: object) -> tuple[int, ...]:
    """Parametre olarak gelen deseni denetler (liste, her blok 1..8 saat). Hata: ValueError."""
    if not isinstance(desen, (list, tuple)) or len(desen) > EN_COK_BLOK:
        raise ValueError(f"desen bir sayı listesi olmalı: {desen!r}")
    if not all(isinstance(b, int) and not isinstance(b, bool) and 1 <= b <= EN_BUYUK_BLOK for b in desen):
        raise ValueError(f"desendeki her blok 1-{EN_BUYUK_BLOK} saat olmalı: {desen!r}")
    # Büyükten küçüğe: aynı desenin tek gösterimi ("1+2" ile "2+1" aynıdır).
    return tuple(sorted(desen, reverse=True))


@dataclass(frozen=True)
class Desen:
    """Bir atamanın geçerli dağılım şekli. `ozel`: derse/şubeye özel ayardan mı (yoksa okul önerisi)."""

    bloklar: tuple[int, ...]
    ozel: bool

    @property
    def metin(self) -> str:
        return desen_metni(self.bloklar)


# --- gün ve blok geometrisi -------------------------------------------------------------------


def blok_sigar_mi(ayar: OkulAyari, gun: int, bas: int, boy: int) -> bool:
    """`boy` saatlik blok `gun` günü `bas` saatinde başlayabilir mi (gün uzunluğu ve öğle arası)."""
    if bas < 0 or bas + boy > ayar.saat_sayisi(gun):
        return False
    return not any(ayar.ogle_arasiyla_ayrilir(gun, s) for s in range(bas, bas + boy - 1))


def baslangiclar(ayar: OkulAyari, gun: int, boy: int) -> list[int]:
    """Bloğun o gün başlayabildiği saatler."""
    return [s for s in range(ayar.saat_sayisi(gun)) if blok_sigar_mi(ayar, gun, s, boy)]


def en_uzun_parca(ayar: OkulAyari) -> int:
    """Öğle arasının böldüğü parçalardan en uzunu (bütün günler içinde): bir blok en çok bu kadar olabilir."""
    return max(
        (boy for g in range(ayar.gun_sayisi) for boy in range(1, ayar.saat_sayisi(g) + 1) if baslangiclar(ayar, g, boy)),
        default=0,
    )


# --- eşleştirme: her blok ayrı bir güne ----------------------------------------------------------


def eslesir(bloklar: list[int], uygun_gunler: dict[int, set[int]]) -> bool:
    """Her öğeye ayrı bir yer atanabilir mi? Ör. her bloğa ayrı bir gün: `bloklar` blok boyları,
    `uygun_gunler[boy]` o boydaki bloğun sığdığı günler.

    İki parçalı eşleştirme (artırım yolu); öğe ve yer sayısı küçük.
    """
    gunun_blogu: dict[int, int] = {}

    def yerlestir(i: int, gorulen: set[int]) -> bool:
        for g in uygun_gunler.get(bloklar[i], ()):
            if g in gorulen:
                continue
            gorulen.add(g)
            if g not in gunun_blogu or yerlestir(gunun_blogu[g], gorulen):
                gunun_blogu[g] = i
                return True
        return False

    return all(yerlestir(i, set()) for i in range(len(bloklar)))


class BlokHesabi:
    """Bir girdi için atamaların desenleri ve uygulanabilirlik denetimleri."""

    def __init__(self, girdi: CozumGirdisi) -> None:
        from cozucu.yuk import YukHesabi  # yuk → anlatim; döngüsel içe aktarmayı önlemek için burada

        self.girdi = girdi
        self.ayar = girdi.ayar
        self.yuk = YukHesabi(girdi)
        okul = girdi._okul_tanimi(BLOK_DESENI_TURU)
        parametreler = okul.parametreler if okul else {}
        self.otomatik: bool = parametreler.get("otomatik", True)
        self.varsayilanlar: dict[int, tuple[int, ...]] = {
            int(k): desen_dogrula(v) for k, v in (parametreler.get("varsayilanlar") or {}).items()
        }
        self._ozeller = [t for t in girdi.kisitlar if t.tur == BLOK_DESENI_TURU and not t.kapsam.okul_mu]
        self._gelemez = {
            (m.ogretmen_id, m.gun, m.saat) for m in girdi.musaitlikler if m.durum is MusaitlikDurumu.GELEMEZ
        }
        self._kilitler: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for k in girdi.kilitli_yerlesimler:
            self._kilitler[k.ders_atama_id].append((k.gun, k.saat))

    # --- desen ----------------------------------------------------------------------------

    def istenen(self, a: DersAtama) -> Desen | None:
        """Ayarlardan gelen desen (uygulanabilirliğe bakmadan); blok yoksa None."""
        ozel = cozumle(self._ozeller, self.girdi.varlik(sinif_id=a.sinif_id, ders_id=a.ders_id))
        if ozel is not None:
            bloklar = desen_dogrula(ozel.parametreler.get("desen", []))
            return Desen(bloklar, ozel=True) if bloklar else None
        if not self.otomatik:
            return None
        bloklar = self.varsayilanlar.get(a.haftalik_saat, otomatik_desen(a.haftalik_saat))
        return Desen(bloklar, ozel=False) if bloklar else None

    def desen(self, a: DersAtama) -> Desen | None:
        """Çözücünün uygulayacağı desen. Okul önerisi uygulanamıyorsa None (atama bloksuz)."""
        d = self.istenen(a)
        if d is None or d.ozel:
            return d
        return d if not self.sorunlar(a, d) else None

    # --- uygulanabilirlik -------------------------------------------------------------------

    def uygun_gunler(self, a: DersAtama, boy: int, ogretmensiz: bool = False) -> set[int]:
        """`boy` saatlik bloğun sığdığı günler: gün uzunluğu, öğle arası ve (istenirse) öğretmenin müsaitliği."""
        sonuc = set()
        for g in range(self.ayar.gun_sayisi):
            for s in baslangiclar(self.ayar, g, boy):
                if ogretmensiz or self._musait(a, g, s, boy):
                    sonuc.add(g)
                    break
        return sonuc

    def _musait(self, a: DersAtama, gun: int, bas: int, boy: int) -> bool:
        return a.ogretmen_id is None or not any((a.ogretmen_id, gun, t) in self._gelemez for t in range(bas, bas + boy))

    def sorunlar(self, a: DersAtama, d: Desen) -> list[str]:
        """Desenin bu atamada neden uygulanamadığı (sorun türü anahtarlarıyla); boşsa uygulanabilir.

        Türler: "toplam", "gunluk_sinir", "gun_sayisi", "gune_sigmaz", "musaitlik", "kilit".
        Ön kontrol bunları kullanıcının diliyle anlatır.
        """
        sorunlar = []
        if sum(d.bloklar) != a.haftalik_saat:
            sorunlar.append("toplam")
        if max(d.bloklar) > self.yuk.ders_siniri(a.sinif_id, a.ders_id):
            sorunlar.append("gunluk_sinir")
        if len(d.bloklar) > self.ayar.gun_sayisi:
            sorunlar.append("gun_sayisi")
        boylar = set(d.bloklar)
        if any(not self.uygun_gunler(a, b, ogretmensiz=True) for b in boylar):
            sorunlar.append("gune_sigmaz")
        elif "gun_sayisi" not in sorunlar and not eslesir(list(d.bloklar), {b: self.uygun_gunler(a, b) for b in boylar}):
            sorunlar.append("musaitlik")
        if not self.kilitler_uyar(a, d):
            sorunlar.append("kilit")
        return sorunlar

    def kilitler_uyar(self, a: DersAtama, d: Desen) -> bool:
        """Kilitli hücreler desene uyar mı?

        Kilitli hücre bir bloğun parçası sayılır; bloğun geri kalanını çözücü kilitli hücrenin
        yanına yerleştirir. Uyması için: aynı gündeki kilitli hücreler tek bir bloğa sığmalı
        (aralarındaki uzaklık bloğun boyunu aşmamalı, öğle arasını kesmemeli) ve her kilitli güne
        ayrı, yeterince büyük bir blok düşmeli. Bloğun kilitli olmayan saatleri de öğretmenin
        "gelemez" saatlerine düşmemeli.
        """
        gunler: dict[int, list[int]] = defaultdict(list)
        for g, s in self._kilitler.get(a.id, []):
            gunler[g].append(s)
        if not gunler:
            return True
        gerekenler = []
        for g, saatler in gunler.items():
            bas, son = min(saatler), max(saatler)
            gerekenler.append((g, bas, son))
        # Her kilitli güne, kilitli aralığı kapsayabilen ve güne sığan bir blok; bloklar ayrı.
        bloklar = sorted(d.bloklar, reverse=True)
        uygun: dict[int, set[int]] = {}
        for i, b in enumerate(bloklar):
            uygun[i] = {
                j for j, (g, bas, son) in enumerate(gerekenler)
                if son - bas + 1 <= b and any(
                    blok_sigar_mi(self.ayar, g, s, b) and self._musait(a, g, s, b) for s in range(son - b + 1, bas + 1)
                )
            }
        # Kilitli günler bloklarla eşleşmeli (her gün bir blok); eşleşmeyen bloklar serbest.
        gun_uygun: dict[int, set[int]] = defaultdict(set)
        for i, gunler_ in uygun.items():
            for j in gunler_:
                gun_uygun[j].add(i)
        return eslesir(list(range(len(gerekenler))), {j: gun_uygun[j] for j in range(len(gerekenler))})


def blok_sayilari(desen: tuple[int, ...]) -> Counter[int]:
    """Boy → o boyda kaç blok."""
    return Counter(desen)

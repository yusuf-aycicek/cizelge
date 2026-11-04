"""Bir programın kalitesini ölçer: esnek kuralların ne kadar ihlal edildiğini sayar.

`dogrulama` gibi çözücüden bağımsızdır (`cpsat` ve `kisitlar` kullanılmaz). Hem testlerde
modeldeki cezanın doğru kurulduğunu çapraz kontrol etmek hem de kullanıcıya "bu program ne
kadar iyi" sorusunun cevabını göstermek için kullanılır. Geçerli (doğrulayıcıdan geçmiş)
bir program bekler.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from cozucu.anlatim import Anlatim
from cozucu.model import (
    BOS_GUN_TURU,
    VARSAYILAN_HEDEF_BOS_GUN,
    CozumGirdisi,
    MusaitlikDurumu,
    Yerlesim,
)
from cozucu.tercihler import (
    EN_AZ_DERS_TURU,
    SAAT_TERCIHI_TURU,
    YAYILIM_TURU,
    cezali_saatler,
    gunluk_en_az_ders,
    yayilsin,
)
from cozucu.yuk import bos_gun_hedefi


# Her ölçünün karşılığı olan esnek kuralın türü. Ağırlıklarla çarpılınca model cezası elde edilir.
OLCU_KURAL_TURU = {
    "sinif_boslugu": "sinif_boslugu",
    "ogretmen_penceresi": "ogretmen_penceresi",
    "bolunmus_ders": "ardisik_ders",
    "tercih_etmez": "tercih_etmez",
    "eksik_bos_gun": BOS_GUN_TURU,
    "fazla_bos_gun": BOS_GUN_TURU,
    "degisen_yerlesim": "degisiklik",
    "saat_tercihi": SAAT_TERCIHI_TURU,
    "az_dersli_gun": EN_AZ_DERS_TURU,
    "art_arda_gun": YAYILIM_TURU,
}


def agirlikli_ceza(olcum: KaliteOlcumu, agirliklar: dict[str, int]) -> int:
    """Ölçümlerin ağırlıklı toplamı; en iyi çözümde modelin toplam cezasına eşittir."""
    return sum(agirliklar.get(tur, 0) * getattr(olcum, alan) for alan, tur in OLCU_KURAL_TURU.items())


@dataclass(frozen=True)
class KaliteOlcumu:
    sinif_boslugu: int  # sınıfın, o gün sonrasında hâlâ dersi olan boş saatleri
    ogretmen_penceresi: int  # öğretmenin ilk ve son dersi arasındaki boş saatleri
    bolunmus_ders: int  # bir dersin aynı gündeki saatleri: blok sayısı - 1 (çift ders: bitişik değilse 1)
    tercih_etmez: int  # "tercih etmez" saatine konan ders sayısı
    eksik_bos_gun: int  # öğretmenlerin hedefe göre eksik kalan boş günleri (toplam)
    # Hedefi kendisine özel olan öğretmenlerin hedeften fazla boş günleri (ör. hedef 0, bir gün boş).
    fazla_bos_gun: int
    degisen_yerlesim: int  # temel programdaki hücrelerden yeni programda olmayanlar (temel yoksa 0)
    # İkincil kurallar (K6). Varsayılanı 0: bu ölçüler eklenmeden önce kaydedilmiş programlar için.
    saat_tercihi: int = 0  # dersin tercih edilen saatleri dışına ya da kaçınılan saate konan ders saati
    az_dersli_gun: int = 0  # öğretmenin geldiği ama en az ders sayısının altında kaldığı gün
    art_arda_gun: int = 0  # bir şubenin aynı dersinin art arda iki günde olduğu gün çifti


def olc(girdi: CozumGirdisi, yerlesimler: list[Yerlesim]) -> KaliteOlcumu:
    atamalar = {a.id: a for a in girdi.atamalar}
    sinif_gun: dict[tuple[str, int], set[int]] = defaultdict(set)
    ogretmen_gun: dict[tuple[str, int], set[int]] = defaultdict(set)
    ders_gun: dict[tuple[str, str, int], set[int]] = defaultdict(set)
    for y in yerlesimler:
        a = atamalar[y.ders_atama_id]
        sinif_gun[a.sinif_id, y.gun].add(y.saat)
        ders_gun[a.sinif_id, a.ders_id, y.gun].add(y.saat)
        if a.ogretmen_id is not None:
            ogretmen_gun[a.ogretmen_id, y.gun].add(y.saat)

    tercih_etmez = sum(
        len(ogretmen_gun.get((m.ogretmen_id, m.gun), set()) & {m.saat})
        for m in girdi.musaitlikler
        if m.durum is MusaitlikDurumu.TERCIH_ETMEZ
    )
    yeni_hucreler = set()
    for y in yerlesimler:
        a = atamalar[y.ders_atama_id]
        yeni_hucreler.add((a.sinif_id, a.ders_id, y.gun, y.saat))
    degisen = sum(
        1 for t in set(girdi.temel_yerlesimler) if (t.sinif_id, t.ders_id, t.gun, t.saat) not in yeni_hucreler
    )
    eksik, fazla = _bos_gun_sapmasi(girdi, ogretmen_gun)
    return KaliteOlcumu(
        sinif_boslugu=sum(max(s) + 1 - len(s) for s in sinif_gun.values()),
        ogretmen_penceresi=sum(max(s) - min(s) + 1 - len(s) for s in ogretmen_gun.values()),
        bolunmus_ders=sum(_blok_sayisi(s, girdi, g) - 1 for (_s, _d, g), s in ders_gun.items()),
        tercih_etmez=tercih_etmez,
        eksik_bos_gun=eksik,
        fazla_bos_gun=fazla,
        degisen_yerlesim=degisen,
        saat_tercihi=_saat_tercihi(girdi, ders_gun),
        az_dersli_gun=_az_dersli_gun(girdi, ogretmen_gun),
        art_arda_gun=_art_arda_gun(girdi, ders_gun),
    )


def ders_gunleri(girdi: CozumGirdisi, yerlesimler: list[Yerlesim]) -> dict[str, int]:
    """Öğretmen -> ders verdiği gün sayısı (raporlama için)."""
    atamalar = {a.id: a for a in girdi.atamalar}
    gunler: dict[str, set[int]] = defaultdict(set)
    for y in yerlesimler:
        o = atamalar[y.ders_atama_id].ogretmen_id
        if o is not None:
            gunler[o].add(y.gun)
    return {o: len(g) for o, g in gunler.items()}


@dataclass(frozen=True)
class KaliteNotu:
    """Esnek bir kuralın bir kişi için tutmadığı yer, kullanıcının diliyle (ör. boş gün hedefi)."""

    tur: str
    mesaj: str
    ilgili: tuple[str, ...]


def bos_gun_notlari(girdi: CozumGirdisi, yerlesimler: list[Yerlesim]) -> list[KaliteNotu]:
    """Boş gün hedefi tutmayan her öğretmen için bir not: "Hasan Şahin: hedef 4 boş gündü, 3
    verilebildi." Hedef kullanıcının girdiği sayıdır (okul geneli ya da öğretmene özel); yükü ya
    da müsaitliği hedefe izin vermiyorsa (`bos_gun_hedefi` hedefi yükseltmişse) nedeni de yazılır,
    yoksa öteki kurallarla dengelendiği söylenir. Hedeften fazla boş gün yalnızca hedef
    öğretmene özelse not edilir (kuralla aynı: okul genelinde fazla boş gün ceza değildir).
    Boş gün kuralı kapalıysa (ağırlık 0) not yoktur."""
    okul = girdi._okul_tanimi(BOS_GUN_TURU)
    if okul is not None and not okul.zorunlu and okul.agirlik == 0:
        return []
    ad = Anlatim(girdi)
    gun_sayisi = girdi.ayar.gun_sayisi
    yuk: dict[str, int] = defaultdict(int)
    for a in girdi.atamalar:
        if a.ogretmen_id is not None:
            yuk[a.ogretmen_id] += a.haftalik_saat
    gunler = {o: set() for o in yuk}
    atamalar = {a.id: a for a in girdi.atamalar}
    for y in yerlesimler:
        o = atamalar[y.ders_atama_id].ogretmen_id
        if o is not None:
            gunler[o].add(y.gun)

    notlar = []
    for o, saat in yuk.items():
        istenen = girdi.parametre(BOS_GUN_TURU, "hedef_bos_gun", VARSAYILAN_HEDEF_BOS_GUN, ogretmen_id=o)
        hedef = bos_gun_hedefi(girdi, o, saat)
        verilen = gun_sayisi - len(gunler[o])
        istenen_gun = gun_sayisi - istenen  # hedef tutsaydı geleceği gün
        if verilen < istenen:
            neden = (
                f" Ders yükü ({saat} saat) ve müsaitliği en az {hedef.gun} gün gelmesini gerektiriyor."
                if hedef.gun > istenen_gun
                else " Program öteki kurallarla (sınıfların boş saati, tercihler) dengelerken daha fazlasını veremedi."
            )
            mesaj = f"{ad.ogretmen(o)}: hedef {istenen} boş gündü, {verilen} verilebildi.{neden}"
        elif hedef.iki_yonlu and verilen > istenen:
            neden = (
                f" Ders yükü ({saat} saat) ya da müsaitliği daha çok gün gelmesine yetmiyor."
                if hedef.gun < istenen_gun
                else ""
            )
            hedef_metni = "boş gün istemiyordu" if istenen == 0 else f"hedef {istenen} boş gündü"
            mesaj = f"{ad.ogretmen(o)}: {hedef_metni}, {verilen} boş gün kaldı.{neden}"
        else:
            continue
        notlar.append(KaliteNotu(tur=BOS_GUN_TURU, mesaj=mesaj, ilgili=(o,)))
    return sorted(notlar, key=lambda n: n.mesaj.casefold())


def _bos_gun_sapmasi(girdi: CozumGirdisi, ogretmen_gun: dict[tuple[str, int], set[int]]) -> tuple[int, int]:
    """(eksik boş gün, fazla boş gün) toplamları; hedef `yuk.bos_gun_hedefi`nden (kuralla aynı).

    Eksik: ders verilen gün − hedef gün (fazla gelmek). Fazla: hedef gün − ders verilen gün, yalnızca
    hedefi kendisine özel öğretmenlerde (iki yönlü ceza).
    """
    yuk: dict[str, int] = defaultdict(int)
    for a in girdi.atamalar:
        if a.ogretmen_id is not None:
            yuk[a.ogretmen_id] += a.haftalik_saat
    calisilan: dict[str, int] = defaultdict(int)
    for o, _g in ogretmen_gun:
        calisilan[o] += 1
    eksik = fazla = 0
    for o, saat in yuk.items():
        hedef = bos_gun_hedefi(girdi, o, saat)
        eksik += max(0, calisilan[o] - hedef.gun)
        if hedef.iki_yonlu:
            fazla += max(0, hedef.gun - calisilan[o])
    return eksik, fazla


def _az_dersli_gun(girdi: CozumGirdisi, ogretmen_gun: dict[tuple[str, int], set[int]]) -> int:
    """Öğretmenin dersi olup en az ders sayısının (`tercihler.gunluk_en_az_ders`) altında kaldığı günler."""
    yuk: dict[str, int] = defaultdict(int)
    for a in girdi.atamalar:
        if a.ogretmen_id is not None:
            yuk[a.ogretmen_id] += a.haftalik_saat
    k = {o: gunluk_en_az_ders(girdi, o, saat) for o, saat in yuk.items()}
    return sum(1 for (o, _g), saatler in ogretmen_gun.items() if len(saatler) < k[o])


def _art_arda_gun(girdi: CozumGirdisi, ders_gun: dict[tuple[str, str, int], set[int]]) -> int:
    """Aynı (şube, ders) art arda iki günde: yayılım kuralı açık olan çiftlerde gün çifti sayısı."""
    acik = {(s, d): yayilsin(girdi, s, d) for s, d, _g in ders_gun}
    return sum(1 for s, d, g in ders_gun if (s, d, g + 1) in ders_gun and acik[s, d])


def _saat_tercihi(girdi: CozumGirdisi, ders_gun: dict[tuple[str, str, int], set[int]]) -> int:
    """Dersin cezalı saatlerine (`tercihler.cezali_saatler`) konan ders saati sayısı."""
    cezali = {(s, d): cezali_saatler(girdi, s, d) for s, d, _g in ders_gun}
    return sum(len(saatler & cezali[s, d]) for (s, d, _g), saatler in ders_gun.items())


def _blok_sayisi(saatler: set[int], girdi: CozumGirdisi, gun: int) -> int:
    """Kesintisiz saat dizisi sayısı: {0,1,4} -> 2. Öğle arası diziyi böler."""
    return sum(1 for s in saatler if s - 1 not in saatler or girdi.ayar.ogle_arasiyla_ayrilir(gun, s - 1))

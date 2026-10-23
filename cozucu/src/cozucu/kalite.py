"""Bir programın kalitesini ölçer: esnek kuralların ne kadar ihlal edildiğini sayar.

`dogrulama` gibi çözücüden bağımsızdır (`cpsat` ve `kisitlar` kullanılmaz). Hem testlerde
modeldeki cezanın doğru kurulduğunu çapraz kontrol etmek hem de kullanıcıya "bu program ne
kadar iyi" sorusunun cevabını göstermek için kullanılır. Geçerli (doğrulayıcıdan geçmiş)
bir program bekler.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from cozucu.model import (
    BOS_GUN_TURU,
    CozumGirdisi,
    MusaitlikDurumu,
    Yerlesim,
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
        bolunmus_ders=sum(_blok_sayisi(s) - 1 for s in ders_gun.values()),
        tercih_etmez=tercih_etmez,
        eksik_bos_gun=eksik,
        fazla_bos_gun=fazla,
        degisen_yerlesim=degisen,
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


def _blok_sayisi(saatler: set[int]) -> int:
    """Kesintisiz saat dizisi sayısı: {0,1,4} -> 2."""
    return sum(1 for s in saatler if s - 1 not in saatler)

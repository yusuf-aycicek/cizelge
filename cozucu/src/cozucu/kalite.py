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
    OGRETMEN_GUNLUK_SINIRI_TURU,
    VARSAYILAN_HEDEF_BOS_GUN,
    VARSAYILAN_OGRETMEN_GUNLUK_SINIRI,
    CozumGirdisi,
    MusaitlikDurumu,
    Yerlesim,
)


@dataclass(frozen=True)
class KaliteOlcumu:
    sinif_boslugu: int  # sınıfın, o gün sonrasında hâlâ dersi olan boş saatleri
    ogretmen_penceresi: int  # öğretmenin ilk ve son dersi arasındaki boş saatleri
    bolunmus_ders: int  # bir dersin aynı gündeki saatleri: blok sayısı - 1 (çift ders: bitişik değilse 1)
    tercih_etmez: int  # "tercih etmez" saatine konan ders sayısı
    eksik_bos_gun: int  # öğretmenlerin hedefe göre eksik kalan boş günleri (toplam)
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
    return KaliteOlcumu(
        sinif_boslugu=sum(max(s) + 1 - len(s) for s in sinif_gun.values()),
        ogretmen_penceresi=sum(max(s) - min(s) + 1 - len(s) for s in ogretmen_gun.values()),
        bolunmus_ders=sum(_blok_sayisi(s) - 1 for s in ders_gun.values()),
        tercih_etmez=tercih_etmez,
        eksik_bos_gun=_eksik_bos_gun(girdi, ogretmen_gun),
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


def _eksik_bos_gun(girdi: CozumGirdisi, ogretmen_gun: dict[tuple[str, int], set[int]]) -> int:
    """Σ öğretmen max(0, ders verilen gün − hedef gün); formül CLAUDE.md bölüm 7'de."""
    gun_sayisi, saat_sayisi = girdi.ayar.gun_sayisi, girdi.ayar.gunluk_ders_saati
    hedef_bos = girdi.parametre(BOS_GUN_TURU, "hedef_bos_gun", VARSAYILAN_HEDEF_BOS_GUN)
    m = girdi.parametre(OGRETMEN_GUNLUK_SINIRI_TURU, "m", VARSAYILAN_OGRETMEN_GUNLUK_SINIRI)
    gunluk_sinir = min(m, saat_sayisi)
    yuk: dict[str, int] = defaultdict(int)
    for a in girdi.atamalar:
        if a.ogretmen_id is not None:
            yuk[a.ogretmen_id] += a.haftalik_saat
    calisilan: dict[str, int] = defaultdict(int)
    for o, _g in ogretmen_gun:
        calisilan[o] += 1
    toplam = 0
    for o, saat in yuk.items():
        hedef_gun = max(-(-saat // gunluk_sinir), gun_sayisi - hedef_bos)
        toplam += max(0, calisilan[o] - hedef_gun)
    return toplam


def _blok_sayisi(saatler: set[int]) -> int:
    """Kesintisiz saat dizisi sayısı: {0,1,4} -> 2."""
    return sum(1 for s in saatler if s - 1 not in saatler)

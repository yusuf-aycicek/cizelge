"""Bir programın kalitesini ölçer: esnek kuralların ne kadar ihlal edildiğini sayar.

`dogrulama` gibi çözücüden bağımsızdır (`cpsat` ve `kisitlar` kullanılmaz). Hem testlerde
modeldeki cezanın doğru kurulduğunu çapraz kontrol etmek hem de kullanıcıya "bu program ne
kadar iyi" sorusunun cevabını göstermek için kullanılır. Geçerli (doğrulayıcıdan geçmiş)
bir program bekler.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from cozucu.model import CozumGirdisi, MusaitlikDurumu, Yerlesim


@dataclass(frozen=True)
class KaliteOlcumu:
    sinif_boslugu: int  # sınıfın, o gün sonrasında hâlâ dersi olan boş saatleri
    ogretmen_penceresi: int  # öğretmenin ilk ve son dersi arasındaki boş saatleri
    bolunmus_ders: int  # bir dersin aynı gündeki saatleri: blok sayısı - 1 (çift ders: bitişik değilse 1)
    tercih_etmez: int  # "tercih etmez" saatine konan ders sayısı


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
    return KaliteOlcumu(
        sinif_boslugu=sum(max(s) + 1 - len(s) for s in sinif_gun.values()),
        ogretmen_penceresi=sum(max(s) - min(s) + 1 - len(s) for s in ogretmen_gun.values()),
        bolunmus_ders=sum(_blok_sayisi(s) - 1 for s in ders_gun.values()),
        tercih_etmez=tercih_etmez,
    )


def _blok_sayisi(saatler: set[int]) -> int:
    """Kesintisiz saat dizisi sayısı: {0,1,4} -> 2."""
    return sum(1 for s in saatler if s - 1 not in saatler)

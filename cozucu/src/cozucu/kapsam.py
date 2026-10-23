"""Kural kapsamı: bir kuralın okul geneli değeri hangi varlıkta, hangi tanımla ezilir (ADR 0016).

Bir kapsam eksenlerin birleşimidir: ders, şube, şube grubu, öğretmen. Boş eksen her şeye uyar;
hepsi boşsa kapsam okul genelidir. Bir varlık (ör. "11-A şubesinin Matematik dersi") için
uyan tanımlardan **en özel olanı** kazanır. Özgüllük puanı doldurulmuş eksenlerin toplamıdır:

    ders 4, şube 2, şube grubu 1, öğretmen 1

Öğretmen ekseni öteki üçüyle aynı kapsamda bulunamaz (kapsam oluşturulurken reddedilir) ve
bir kural ikisini birden desteklemez (`kaydet` reddeder). Böylece öğretmen ailesindeki puan
(1) ders ve şube ailesindeki puanlarla hiçbir zaman karşılaştırılmaz.

Bu modül saf ve tek kaynaktır: çözücü, ön kontrol ve API "değer nereden geliyor" sorusunu
buradan cevaplar.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TypeVar

EKSENLER = ("ders", "sube", "sube_grubu", "ogretmen")
PUAN = {"ders": 4, "sube": 2, "sube_grubu": 1, "ogretmen": 1}
# Öğretmen ailesi öteki eksenlerle karışamaz.
OGRETMEN_AILESI = frozenset({"ogretmen"})
YERLESIM_AILESI = frozenset({"ders", "sube", "sube_grubu"})


@dataclass(frozen=True)
class Kapsam:
    """Bir kural tanımının geçerli olduğu yer. Hepsi boşsa okul geneli."""

    ders_id: str | None = None
    sinif_id: str | None = None
    sube_grubu_id: str | None = None
    ogretmen_id: str | None = None

    def __post_init__(self) -> None:
        if self.sinif_id is not None and self.sube_grubu_id is not None:
            raise ValueError("Bir kapsamda şube ile şube grubu birlikte bulunamaz")
        if self.ogretmen_id is not None and (self.eksenler & YERLESIM_AILESI):
            raise ValueError("Öğretmen kapsamı ders, şube ya da şube grubuyla birleştirilemez")

    @property
    def eksenler(self) -> frozenset[str]:
        degerler = (self.ders_id, self.sinif_id, self.sube_grubu_id, self.ogretmen_id)
        return frozenset(e for e, d in zip(EKSENLER, degerler, strict=True) if d is not None)

    @property
    def okul_mu(self) -> bool:
        return not self.eksenler

    @property
    def puan(self) -> int:
        return sum(PUAN[e] for e in self.eksenler)


OKUL = Kapsam()


@dataclass(frozen=True)
class Varlik:
    """Değeri sorulan şey: bir (şube, ders) çifti ya da bir öğretmen. Eksik eksen bilinmiyor demektir."""

    ders_id: str | None = None
    sinif_id: str | None = None
    sube_grubu_id: str | None = None
    ogretmen_id: str | None = None


def uyar(kapsam: Kapsam, varlik: Varlik) -> bool:
    """Kapsamın doldurduğu her eksen varlıkla aynıysa uyar; boş eksen her şeye uyar."""
    return all(
        k is None or k == v
        for k, v in (
            (kapsam.ders_id, varlik.ders_id),
            (kapsam.sinif_id, varlik.sinif_id),
            (kapsam.sube_grubu_id, varlik.sube_grubu_id),
            (kapsam.ogretmen_id, varlik.ogretmen_id),
        )
    )


T = TypeVar("T")


def cozumle(adaylar: Iterable[T], varlik: Varlik, kapsam: Callable[[T], Kapsam] = lambda t: t.kapsam) -> T | None:
    """Varlığa uyan adaylardan en özelini döner; hiçbiri uymuyorsa None (okul değeri geçerli).

    Aynı puanla iki aday uyuyorsa veri tutarsızdır (aynı kapsamda iki tanım): ValueError.
    """
    en_iyi: T | None = None
    en_iyi_puan = -1
    for aday in adaylar:
        k = kapsam(aday)
        if not uyar(k, varlik):
            continue
        if k.puan == en_iyi_puan:
            raise ValueError(f"Aynı özgüllükte iki tanım aynı varlığa uyuyor: {k}")
        if k.puan > en_iyi_puan:
            en_iyi, en_iyi_puan = aday, k.puan
    return en_iyi

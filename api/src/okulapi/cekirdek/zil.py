"""Zil saatleri: her ders saatinin başlangıç ve bitişi (yalnızca gösterim).

Tek kaynaktır: okul yanıtı (`OkulYanit.zil_saatleri`), ayar ekranının önizlemesi
(`POST /api/okul/zil-onizleme`) ve çıktılar (PDF, Excel) buradan okur. Çözücü saatleri yalnızca
sırayla bilir; zil saatleri ona girmez.

Kural: ilk ders `ilk_ders_baslangic`'ta başlar; dersler arasında teneffüs, öğle arasından sonra
öğle arası süresi kadar beklenir. Kısa günler aynı saatlerle erken biter.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class Zil:
    baslangic: str  # "08:30"
    bitis: str

    @property
    def metin(self) -> str:
        """"08:30–09:10" (kısa çizgi: aralık)."""
        return f"{self.baslangic}–{self.bitis}"


def _bicim(dk: int) -> str:
    return f"{dk // 60 % 24:02d}:{dk % 60:02d}"


def zil_saatleri(
    ilk_ders_baslangic: time | None, saat_sayisi: int, ders_suresi_dk: int, teneffus_dk: int,
    ogle_arasi_dk: int, ogle_arasi_sonra: int | None,
) -> list[Zil] | None:
    """Her ders saatinin zili; başlangıç tanımsızsa None."""
    if ilk_ders_baslangic is None:
        return None
    simdi = ilk_ders_baslangic.hour * 60 + ilk_ders_baslangic.minute
    sonuc: list[Zil] = []
    for s in range(saat_sayisi):
        sonuc.append(Zil(_bicim(simdi), _bicim(simdi + ders_suresi_dk)))
        ogle = ogle_arasi_sonra is not None and s + 1 == ogle_arasi_sonra
        simdi += ders_suresi_dk + (ogle_arasi_dk if ogle else teneffus_dk)
    return sonuc


def ogle_arasi_zili(zil: list[Zil] | None, ogle_arasi_sonra: int | None, ogle_arasi_dk: int) -> Zil | None:
    """Öğle arasının saatleri; öğle arası ya da zil saatleri yoksa None."""
    if not zil or ogle_arasi_sonra is None or ogle_arasi_sonra > len(zil):
        return None
    bas = zil[ogle_arasi_sonra - 1].bitis
    s, d = map(int, bas.split(":"))
    return Zil(bas, _bicim(s * 60 + d + ogle_arasi_dk))


def okulun_zilleri(okul) -> tuple[list[Zil] | None, Zil | None]:
    """Okul kaydının (ORM) zil saatleri (en uzun güne göre) ve öğle arası zili."""
    zil = zil_saatleri(okul.ilk_ders_baslangic, okul.gunluk_ders_saati, okul.ders_suresi_dk,
                       okul.teneffus_dk, okul.ogle_arasi_dk, okul.ogle_arasi_sonra)
    return zil, ogle_arasi_zili(zil, okul.ogle_arasi_sonra, okul.ogle_arasi_dk)

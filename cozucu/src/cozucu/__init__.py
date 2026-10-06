"""Okul ders programı çözücüsü.

Saf Python paketi: veritabanından ve web'den habersizdir. Girdi olarak `CozumGirdisi`
alır, çıktı olarak `CozumSonucu` (yerleşim listesi) döner.
"""

from cozucu.arayuz import ProgramCozucu
from cozucu.cpsat import CpSatCozucu
from cozucu.dogrulama import dogrula
from cozucu.model import (
    CozumDurumu,
    CozumGirdisi,
    CozumSonucu,
    Ders,
    DersAtama,
    KisitTanimi,
    Musaitlik,
    MusaitlikDurumu,
    OkulAyari,
    Ogretmen,
    Sinif,
    Yerlesim,
)

__all__ = [
    "CozumDurumu",
    "CpSatCozucu",
    "dogrula",
    "CozumGirdisi",
    "CozumSonucu",
    "Ders",
    "DersAtama",
    "KisitTanimi",
    "Musaitlik",
    "MusaitlikDurumu",
    "OkulAyari",
    "Ogretmen",
    "ProgramCozucu",
    "Sinif",
    "Yerlesim",
]

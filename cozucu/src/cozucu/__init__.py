"""Okul ders programı çözücüsü.

Saf Python paketi: veritabanından ve web'den habersizdir. Girdi olarak `CozumGirdisi`
alır, çıktı olarak `CozumSonucu` (yerleşim listesi) döner.
"""

from cozucu.arayuz import ProgramCozucu
from cozucu.cpsat import CpSatCozucu
from cozucu.dogrulama import dogrula
from cozucu.kalite import KaliteOlcumu, olc
from cozucu.model import (
    Celiski,
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
    TemelYerlesim,
    Yerlesim,
    temel_program,
)

__all__ = [
    "Celiski",
    "CozumDurumu",
    "CozumGirdisi",
    "CozumSonucu",
    "CpSatCozucu",
    "Ders",
    "DersAtama",
    "KaliteOlcumu",
    "KisitTanimi",
    "Musaitlik",
    "MusaitlikDurumu",
    "OkulAyari",
    "Ogretmen",
    "ProgramCozucu",
    "Sinif",
    "TemelYerlesim",
    "Yerlesim",
    "dogrula",
    "olc",
    "temel_program",
]

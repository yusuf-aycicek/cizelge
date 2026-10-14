"""Ders programı modülü: seviye şablonu, ders atama, müsaitlik, kısıt, program, yerleşim.

Çekirdeğe (öğretmen, sınıf, ders) ve çözücü paketine bağımlıdır; çekirdek bu modülü bilmez.
"""

from pathlib import Path

from okulapi.cekirdek.modul import Modul
from okulapi.moduller.ders_programi import modeller
from okulapi.moduller.ders_programi.api import router

MODUL = Modul(
    ad="ders_programi",
    onek="ders-programi",
    router=router,
    migration_dizini=Path(__file__).parent / "migrations",
    modeller=modeller,
)

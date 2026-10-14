"""Ders programı modülü: seviye şablonu, ders atama, müsaitlik, kısıt, program, yerleşim.

Bu alt adımda yalnızca modül sözleşmesi ve boş migration dalı vardır. Modeller ve endpoint'ler
3. alt adımda eklenir.
"""

from pathlib import Path

from fastapi import APIRouter

from okulapi.cekirdek.modul import Modul

router = APIRouter(tags=["ders programı"])

MODUL = Modul(
    ad="ders_programi",
    onek="ders-programi",
    router=router,
    migration_dizini=Path(__file__).parent / "migrations",
)

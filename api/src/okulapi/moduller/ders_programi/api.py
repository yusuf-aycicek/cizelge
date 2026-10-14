"""Ders programı endpoint'leri (/api/ders-programi/...). Çekirdeğin `crud_router` fabrikasını kullanır.

Not: `from __future__ import annotations` yok (FastAPI tip ipuçlarını çalışma anında okur).
"""

import uuid
from typing import Any

from fastapi import APIRouter

from okulapi.cekirdek.api import crud_router
from okulapi.cekirdek.bagimliliklar import OkulOturumu
from okulapi.moduller.ders_programi import semalar
from okulapi.moduller.ders_programi.servisler import (
    DersAtamaServisi,
    KisitServisi,
    MusaitlikServisi,
    ProgramServisi,
    SeviyeSablonuServisi,
)

router = APIRouter()

sablon_router = APIRouter(prefix="/seviye-sablonlari", tags=["seviye şablonu"])


@sablon_router.post("/uygula", response_model=semalar.SablonUygulamaSonucu)
def sablonu_uygula(veri: semalar.SablonUygula, oturum: OkulOturumu) -> Any:
    """Seviyenin şablonunu o seviyedeki her şubeye uygular (öğretmeni boş atamalar)."""
    return SeviyeSablonuServisi(oturum).uygula(veri.seviye)


program_router = APIRouter(prefix="/programlar", tags=["program"])


@program_router.get("", response_model=list[semalar.ProgramYanit])
def programlari_listele(oturum: OkulOturumu) -> Any:
    return ProgramServisi(oturum).listele()


@program_router.get("/{program_id}", response_model=semalar.ProgramYanit)
def program_getir(program_id: uuid.UUID, oturum: OkulOturumu) -> Any:
    return ProgramServisi(oturum).getir(program_id)


@program_router.get("/{program_id}/yerlesimler", response_model=list[semalar.YerlesimYanit])
def program_yerlesimleri(program_id: uuid.UUID, oturum: OkulOturumu) -> Any:
    return ProgramServisi(oturum).yerlesimler(program_id)


# Özel yollar (/uygula) CRUD'un /{kayit_id} yollarından önce eklenir.
router.include_router(sablon_router)
for alt in (
    crud_router("/seviye-sablonlari", SeviyeSablonuServisi, semalar.SeviyeSablonuOlustur,
                semalar.SeviyeSablonuGuncelle, semalar.SeviyeSablonuYanit, "seviye şablonu"),
    crud_router("/atamalar", DersAtamaServisi, semalar.DersAtamaOlustur, semalar.DersAtamaGuncelle,
                semalar.DersAtamaYanit, "ders atama"),
    crud_router("/musaitlikler", MusaitlikServisi, semalar.MusaitlikOlustur, semalar.MusaitlikGuncelle,
                semalar.MusaitlikYanit, "müsaitlik"),
    crud_router("/kisitlar", KisitServisi, semalar.KisitOlustur, semalar.KisitGuncelle,
                semalar.KisitYanit, "kısıt"),
    program_router,
):
    router.include_router(alt)

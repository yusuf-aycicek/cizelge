"""Uygulama fabrikası: çekirdeği kurar, etkin modülleri yükleyip router'larını bağlar.

Çalıştırma: uvicorn okulapi.main:uygulama_olustur --factory
"""

from __future__ import annotations

from fastapi import FastAPI

from okulapi.ayarlar import Ayarlar
from okulapi.cekirdek import saglik
from okulapi.cekirdek.modul import modulleri_yukle
from okulapi.cekirdek.veritabani import motor_olustur, oturum_fabrikasi


def uygulama_olustur(ayarlar: Ayarlar | None = None) -> FastAPI:
    ayarlar = ayarlar or Ayarlar()
    uygulama = FastAPI(title="Okul Ders Programı API", version="0.1.0")
    uygulama.state.ayarlar = ayarlar
    uygulama.state.motor = motor_olustur(ayarlar.veritabani_url)
    uygulama.state.oturum_fabrikasi = oturum_fabrikasi(uygulama.state.motor)

    uygulama.include_router(saglik.router, prefix="/api")
    moduller = modulleri_yukle(ayarlar.etkin_moduller)
    for modul in moduller:
        uygulama.include_router(modul.router, prefix=f"/api/{modul.onek}")
    uygulama.state.modul_adlari = [m.ad for m in moduller]
    return uygulama
